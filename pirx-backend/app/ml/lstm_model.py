"""PyTorch LSTM model for per-user projection with Optuna hyperparameter tuning.

Architecture from Dash 2024: 17 neurons, sequence length 11, batch 56, 50% dropout.
Huber loss for GPS-outlier robustness, Adam optimizer.
Per-user models (individual networks beat global per Dash 2024).
"""
import logging
from io import BytesIO
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

logger = logging.getLogger(__name__)

LSTM_FEATURE_NAMES = [
    "rolling_distance_7d",
    "rolling_distance_21d",
    "rolling_distance_42d",
    "rolling_distance_90d",
    "sessions_per_week",
    "long_run_count",
    "z1_pct",
    "z2_pct",
    "z4_pct",
    "z5_pct",
    "threshold_density_min_week",
    "speed_exposure_min_week",
    "matched_hr_band_pace",
    "hr_drift_sustained",
    "late_session_pace_decay",
    "weekly_load_stddev",
    "acwr_4w",
]

MIN_LSTM_SAMPLES = 60


class PirxLSTM(nn.Module):
    """LSTM network for time-series projection prediction."""

    def __init__(
        self,
        input_dim: int = 17,
        hidden_dim: int = 17,
        num_layers: int = 1,
        dropout: float = 0.5,
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers

        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        lstm_out, _ = self.lstm(x)
        last_hidden = lstm_out[:, -1, :]
        dropped = self.dropout(last_hidden)
        return self.fc(dropped).squeeze(-1)


class LSTMTrainer:
    """Handles training, validation, and serialization of PirxLSTM models."""

    def __init__(
        self,
        hidden_dim: int = 17,
        dropout: float = 0.5,
        learning_rate: float = 1e-3,
        batch_size: int = 56,
        seq_length: int = 11,
        max_epochs: int = 100,
        patience: int = 10,
    ):
        self.hidden_dim = hidden_dim
        self.dropout = dropout
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.seq_length = seq_length
        self.max_epochs = max_epochs
        self.patience = patience
        self.feature_names = list(LSTM_FEATURE_NAMES)
        self.model: Optional[PirxLSTM] = None

    def train(
        self,
        feature_rows: list[dict],
        targets: list[float],
    ) -> dict:
        """Train LSTM on sequential feature snapshots.

        Args:
            feature_rows: Chronologically ordered feature dicts.
            targets: Performance delta targets aligned with feature_rows.

        Returns:
            Training metrics dict.
        """
        if len(feature_rows) < MIN_LSTM_SAMPLES:
            return {"status": "insufficient_data", "samples": len(feature_rows)}

        X_seq, y_seq = self._build_sequences(feature_rows, targets)
        if len(X_seq) < 10:
            return {"status": "insufficient_sequences", "samples": len(feature_rows),
                    "sequences": len(X_seq)}

        split = max(1, int(len(X_seq) * 0.8))
        X_train, X_val = X_seq[:split], X_seq[split:]
        y_train, y_val = y_seq[:split], y_seq[split:]

        train_ds = TensorDataset(X_train, y_train)
        train_loader = DataLoader(
            train_ds, batch_size=self.batch_size, shuffle=True,
        )

        input_dim = X_train.shape[2]
        self.model = PirxLSTM(
            input_dim=input_dim,
            hidden_dim=self.hidden_dim,
            dropout=self.dropout,
        )
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
        criterion = nn.HuberLoss()

        best_val_loss = float("inf")
        epochs_without_improvement = 0
        best_state = None
        epoch = 0

        for epoch in range(self.max_epochs):
            self.model.train()
            epoch_loss = 0.0
            n_batches = 0

            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                preds = self.model(batch_X)
                loss = criterion(preds, batch_y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()
                epoch_loss += loss.item()
                n_batches += 1

            self.model.eval()
            with torch.no_grad():
                val_preds = self.model(X_val)
                val_loss = criterion(val_preds, y_val).item()

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                epochs_without_improvement = 0
                best_state = {k: v.clone() for k, v in self.model.state_dict().items()}
            else:
                epochs_without_improvement += 1

            if epochs_without_improvement >= self.patience:
                logger.info("Early stopping at epoch %d", epoch + 1)
                break

        if best_state is not None:
            self.model.load_state_dict(best_state)

        self.model.eval()
        with torch.no_grad():
            val_preds = self.model(X_val)
            val_mae = float(torch.mean(torch.abs(val_preds - y_val)).item())

        return {
            "status": "trained",
            "samples": len(feature_rows),
            "sequences": len(X_seq),
            "val_loss": round(best_val_loss, 4),
            "val_mae": round(val_mae, 2),
            "epochs_trained": epoch + 1,
        }

    def predict(self, feature_sequence: list[dict]) -> Optional[float]:
        """Predict from a sequence of recent feature snapshots."""
        if self.model is None:
            return None

        seq_len = min(len(feature_sequence), self.seq_length)
        if seq_len == 0:
            return None

        padded = feature_sequence[-seq_len:]
        X = self._features_to_array(padded)
        X_tensor = torch.tensor(X, dtype=torch.float32).unsqueeze(0)

        if X_tensor.shape[1] < self.seq_length:
            pad_size = self.seq_length - X_tensor.shape[1]
            padding = torch.zeros(1, pad_size, X_tensor.shape[2])
            X_tensor = torch.cat([padding, X_tensor], dim=1)

        self.model.eval()
        with torch.no_grad():
            return float(self.model(X_tensor).item())

    def validate(self, feature_rows: list[dict], targets: list[float]) -> dict:
        """Validate on held-out sequential data."""
        if self.model is None:
            return {"status": "not_trained"}

        X_seq, y_seq = self._build_sequences(feature_rows, targets)
        if len(X_seq) == 0:
            return {"status": "no_sequences"}

        self.model.eval()
        with torch.no_grad():
            preds = self.model(X_seq)
            errors = preds - y_seq
            mae = float(torch.mean(torch.abs(errors)).item())
            huber = float(nn.HuberLoss()(preds, y_seq).item())

        return {
            "status": "validated",
            "samples": len(X_seq),
            "mae": round(mae, 2),
            "huber_loss": round(huber, 4),
        }

    def serialize(self) -> bytes:
        """Serialize model weights to bytes."""
        if self.model is None:
            raise ValueError("Cannot serialize untrained model")
        buf = BytesIO()
        torch.save(self.model.state_dict(), buf)
        return buf.getvalue()

    def load_weights(self, weight_bytes: bytes, input_dim: int = 17) -> None:
        """Load model weights from bytes."""
        self.model = PirxLSTM(
            input_dim=input_dim,
            hidden_dim=self.hidden_dim,
            dropout=self.dropout,
        )
        buf = BytesIO(weight_bytes)
        state_dict = torch.load(buf, map_location="cpu", weights_only=True)
        self.model.load_state_dict(state_dict)
        self.model.eval()

    def _build_sequences(
        self, feature_rows: list[dict], targets: list[float],
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Build sliding-window sequences for LSTM training."""
        X_all = self._features_to_array(feature_rows)
        y_all = np.array(targets, dtype=np.float32)

        sequences = []
        labels = []

        for i in range(self.seq_length, len(X_all)):
            sequences.append(X_all[i - self.seq_length: i])
            labels.append(y_all[i])

        if not sequences:
            return torch.zeros(0), torch.zeros(0)

        X_tensor = torch.tensor(np.array(sequences), dtype=torch.float32)
        y_tensor = torch.tensor(np.array(labels), dtype=torch.float32)
        return X_tensor, y_tensor

    def _features_to_array(self, feature_rows: list[dict]) -> np.ndarray:
        """Convert feature dicts to numpy array."""
        rows = []
        for features in feature_rows:
            row = []
            for name in self.feature_names:
                v = features.get(name)
                if v is None:
                    row.append(0.0)
                else:
                    f = float(v)
                    row.append(0.0 if f != f else f)
            rows.append(row)
        return np.array(rows, dtype=np.float32)
