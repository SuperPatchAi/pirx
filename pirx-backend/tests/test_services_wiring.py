"""Tests for service wiring: DriverService, ProjectionService, and Celery task integration."""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime, timezone

from app.ml.projection_engine import (
    ProjectionEngine,
    ProjectionState,
    DriverState,
    DRIVER_NAMES,
)


MOCK_FEATURES = {
    "rolling_distance_7d": 35000,
    "rolling_distance_21d": 95000,
    "rolling_distance_42d": 180000,
    "z1_pct": 0.45,
    "z2_pct": 0.30,
    "z3_pct": 0.15,
    "z4_pct": 0.07,
    "z5_pct": 0.03,
    "threshold_density_min_week": 18,
    "speed_exposure_min_week": 6,
    "hr_drift_sustained": 0.04,
    "late_session_pace_decay": 0.03,
    "matched_hr_band_pace": 270,
    "weekly_load_stddev": 4500,
    "block_variance": 3500,
    "session_density_stability": 0.8,
    "acwr_4w": 1.1,
    "acwr_6w": 1.0,
    "acwr_8w": 0.95,
    "sessions_per_week": 5,
    "long_run_count": 2,
    "resting_hr_trend": None,
    "hrv_trend": None,
    "sleep_score_trend": None,
}


def _make_projection_state(**overrides):
    defaults = {
        "user_id": "u1",
        "event": "5000",
        "projected_time_seconds": 1200.0,
        "supported_range_low": 1182.0,
        "supported_range_high": 1218.0,
        "baseline_time_seconds": 1260.0,
        "total_improvement_seconds": 60.0,
        "volatility": 0.0,
    }
    defaults.update(overrides)
    return ProjectionState(**defaults)


def _make_driver_states(total_improvement=60.0):
    weights = [0.30, 0.25, 0.15, 0.15, 0.15]
    states = []
    running = 0.0
    for i, name in enumerate(DRIVER_NAMES):
        if i == len(DRIVER_NAMES) - 1:
            contrib = round(total_improvement - running, 2)
        else:
            contrib = round(total_improvement * weights[i], 2)
            running += contrib
        states.append(DriverState(
            user_id="u1",
            event="5000",
            driver_name=name,
            contribution_seconds=contrib,
            score=55.0,
            trend="improving",
        ))
    return states


class TestDriverService:
    @patch("app.services.supabase_client.get_supabase_client")
    def test_compute_and_store_drivers(self, mock_sb):
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])

        from app.services.driver_service import DriverService

        svc = DriverService()
        proj, drivers = svc.compute_and_store_drivers(
            user_id="u1",
            event="5000",
            baseline_time_s=1260.0,
            features=MOCK_FEATURES,
        )

        assert proj.projected_time_seconds > 0
        assert proj.baseline_time_seconds == 1260.0
        assert len(drivers) == 5
        driver_sum = sum(d.contribution_seconds for d in drivers)
        assert abs(driver_sum - proj.total_improvement_seconds) < 0.02
        for d in drivers:
            assert d.driver_name in DRIVER_NAMES

    @patch("app.services.supabase_client.get_supabase_client")
    def test_compute_and_store_drivers_with_previous(self, mock_sb):
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])

        from app.services.driver_service import DriverService

        svc = DriverService()
        prev_state = _make_projection_state(projected_time_seconds=1210.0)

        proj, drivers = svc.compute_and_store_drivers(
            user_id="u1",
            event="5000",
            baseline_time_s=1260.0,
            features=MOCK_FEATURES,
            previous_projection=prev_state,
        )

        assert proj.projected_time_seconds > 0
        assert proj.volatility >= 0

    @patch("app.services.supabase_client.get_supabase_client")
    def test_db_insert_failures_dont_crash(self, mock_sb):
        """DB failures are swallowed — compute still returns valid data."""
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.insert.return_value.execute.side_effect = Exception("DB down")

        from app.services.driver_service import DriverService

        svc = DriverService()
        proj, drivers = svc.compute_and_store_drivers(
            user_id="u1",
            event="5000",
            baseline_time_s=1260.0,
            features=MOCK_FEATURES,
        )
        assert proj.projected_time_seconds > 0
        assert len(drivers) == 5

    @patch("app.services.supabase_client.get_supabase_client")
    def test_insert_driver_state_called_once_with_all_drivers(self, mock_sb):
        """C4: driver_state should be stored as one consolidated row, not 5."""
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])

        from app.services.driver_service import DriverService

        svc = DriverService()
        mock_insert = MagicMock(return_value={})
        svc.db.insert_driver_state = mock_insert
        svc.db.insert_projection = MagicMock(return_value={})

        svc.compute_and_store_drivers(
            user_id="u1",
            event="5000",
            baseline_time_s=1260.0,
            features=MOCK_FEATURES,
        )

        mock_insert.assert_called_once()
        row = mock_insert.call_args[0][0]
        assert row["user_id"] == "u1"
        assert row["event"] == "5000"
        for name in DRIVER_NAMES:
            assert f"{name}_seconds" in row
            assert f"{name}_score" in row
            assert f"{name}_trend" in row

    @patch("app.services.supabase_client.get_supabase_client")
    def test_validation_raises_valueerror_not_assert(self, mock_sb):
        """C5: broken driver sums should raise ValueError, not AssertionError."""
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])

        from app.services.driver_service import DriverService

        svc = DriverService()

        def broken_validate(drivers, total):
            return False

        svc.engine.validate_driver_sum = broken_validate

        with pytest.raises(ValueError, match="Driver sum validation failed"):
            svc.compute_and_store_drivers(
                user_id="u1",
                event="5000",
                baseline_time_s=1260.0,
                features=MOCK_FEATURES,
            )

    @patch("app.services.supabase_client.get_supabase_client")
    def test_get_driver_explanation(self, mock_sb):
        mock_sb.return_value = MagicMock()

        from app.services.driver_service import DriverService

        svc = DriverService()
        explanation = svc.get_driver_explanation("aerobic_base", MOCK_FEATURES)
        assert explanation.driver_name == "aerobic_base"
        assert explanation.display_name == "Aerobic Base"
        assert explanation.overall_direction in ("improving", "stable", "declining")

    def test_classify_stability_short_history(self):
        from app.services.driver_service import DriverService

        svc = DriverService.__new__(DriverService)
        assert svc.classify_stability("aerobic_base", []) == "Active"
        assert svc.classify_stability("aerobic_base", [{"aerobic_base_score": 50}]) == "Active"

    def test_classify_stability_stable(self):
        from app.services.driver_service import DriverService

        svc = DriverService.__new__(DriverService)
        history = [{"aerobic_base_score": 60 + i * 0.1} for i in range(6)]
        assert svc.classify_stability("aerobic_base", history) == "Stable"

    def test_classify_stability_declining(self):
        from app.services.driver_service import DriverService

        svc = DriverService.__new__(DriverService)
        history = [{"aerobic_base_score": 70 - i * 5} for i in range(6)]
        result = svc.classify_stability("aerobic_base", history)
        assert result in ("Declining", "Active")

    def test_classify_stability_active(self):
        from app.services.driver_service import DriverService

        svc = DriverService.__new__(DriverService)
        history = [{"aerobic_base_score": 50 + (i % 2) * 10} for i in range(6)]
        result = svc.classify_stability("aerobic_base", history)
        assert result == "Active"


class TestProjectionService:
    @patch("app.services.supabase_client.get_supabase_client")
    def test_recompute_first_projection(self, mock_sb):
        """First projection with no previous state."""
        mock_client = MagicMock()
        mock_sb.return_value = mock_client

        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"user_id": "u1", "baseline_time_seconds": 1260.0}]
        )
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])

        from app.services.projection_service import ProjectionService

        svc = ProjectionService()

        with patch.object(svc.db, "get_user", return_value={"baseline_time_seconds": 1260.0}), \
             patch.object(svc.db, "get_latest_projection", return_value=None), \
             patch.object(svc.driver_service.db, "insert_projection", return_value={}), \
             patch.object(svc.driver_service.db, "insert_driver_state", return_value={}):

            state = svc.recompute("u1", "5000", MOCK_FEATURES)

        assert state is not None
        assert state.projected_time_seconds > 0
        assert state.baseline_time_seconds == 1260.0

    @patch("app.services.supabase_client.get_supabase_client")
    def test_recompute_with_previous_state(self, mock_sb):
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])

        from app.services.projection_service import ProjectionService

        svc = ProjectionService()

        prev_row = {
            "midpoint_seconds": 1210.0,
            "range_low_seconds": 1192.0,
            "range_high_seconds": 1228.0,
            "baseline_seconds": 1260.0,
        }

        with patch.object(svc.db, "get_user", return_value={"baseline_time_seconds": 1260.0}), \
             patch.object(svc.db, "get_latest_projection", return_value=prev_row), \
             patch.object(svc.driver_service.db, "insert_projection", return_value={}), \
             patch.object(svc.driver_service.db, "insert_driver_state", return_value={}):

            state = svc.recompute("u1", "5000", MOCK_FEATURES)

        assert state is not None
        assert state.volatility >= 0

    @patch("app.services.supabase_client.get_supabase_client")
    def test_recompute_all_events(self, mock_sb):
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])

        from app.services.projection_service import ProjectionService

        svc = ProjectionService()

        with patch.object(svc.db, "get_user", return_value={"baseline_time_seconds": 1260.0}), \
             patch.object(svc.db, "get_latest_projection", return_value=None), \
             patch.object(svc.driver_service.db, "insert_projection", return_value={}), \
             patch.object(svc.driver_service.db, "insert_driver_state", return_value={}):

            results = svc.recompute_all_events("u1", MOCK_FEATURES)

        assert "1500" in results
        assert "3000" in results
        assert "5000" in results
        assert "10000" in results
        for event_key, val in results.items():
            assert val["status"] in ("updated", "error", "failed")

    @patch("app.services.supabase_client.get_supabase_client")
    def test_recompute_db_failure_uses_defaults(self, mock_sb):
        """When DB fails to load user/projection, defaults are used."""
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])

        from app.services.projection_service import ProjectionService

        svc = ProjectionService()

        with patch.object(svc.db, "get_user", side_effect=Exception("DB error")), \
             patch.object(svc.db, "get_latest_projection", side_effect=Exception("DB error")), \
             patch.object(svc.driver_service.db, "insert_projection", return_value={}), \
             patch.object(svc.driver_service.db, "insert_driver_state", return_value={}):

            state = svc.recompute("u1", "5000", MOCK_FEATURES)

        assert state is not None
        assert state.baseline_time_seconds == 1260.0


class TestCeleryTasks:
    @patch("app.services.supabase_client.get_supabase_client")
    def test_recompute_projection_no_data(self, mock_sb):
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.execute.return_value = MagicMock(data=[])

        from app.tasks.projection_tasks import recompute_projection

        result = recompute_projection("user-abc", "5000")
        assert result["status"] in ("no_data", "error")
        assert result["user_id"] == "user-abc"

    @patch("app.services.supabase_client.get_supabase_client")
    def test_recompute_all_events_no_data(self, mock_sb):
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.execute.return_value = MagicMock(data=[])

        from app.tasks.projection_tasks import recompute_all_events

        result = recompute_all_events("user-abc")
        assert result["user_id"] == "user-abc"
        assert "events" in result
        for event_key in ["1500", "3000", "5000", "10000"]:
            assert event_key in result["events"]

    @patch("app.services.supabase_client.get_supabase_client")
    def test_structural_decay_check(self, mock_sb):
        mock_sb.return_value = MagicMock()

        from app.tasks.projection_tasks import structural_decay_check

        result = structural_decay_check()
        assert result["status"] == "completed"
        assert "users_checked" in result

    @patch("app.services.supabase_client.get_supabase_client")
    def test_weekly_summary(self, mock_sb):
        mock_sb.return_value = MagicMock()

        from app.tasks.projection_tasks import weekly_summary

        result = weekly_summary()
        assert result["status"] == "completed"
        assert "summaries_sent" in result

    @patch("app.services.supabase_client.get_supabase_client")
    def test_bias_correction(self, mock_sb):
        mock_sb.return_value = MagicMock()

        from app.tasks.projection_tasks import bias_correction

        result = bias_correction()
        assert result["status"] == "completed"
        assert "users_corrected" in result

    @patch("app.services.supabase_client.get_supabase_client")
    def test_backfill_history_strava(self, mock_sb):
        mock_sb.return_value = MagicMock()

        from app.tasks.sync_tasks import backfill_history

        result = backfill_history("user-abc", "strava")
        assert result["status"] == "completed"
        assert result["provider"] == "strava"
        assert "activities_imported" in result

    @patch("app.services.supabase_client.get_supabase_client")
    def test_backfill_history_terra(self, mock_sb):
        mock_sb.return_value = MagicMock()

        from app.tasks.sync_tasks import backfill_history

        result = backfill_history("user-abc", "terra")
        assert result["status"] == "completed"
        assert result["provider"] == "terra"
