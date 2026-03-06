class ProjectionService:
    """Handles projection computation and retrieval.

    Responsibilities:
    - Load per-user ML model (LMC/KNN/LSTM/Gradient Boosting depending on data maturity)
    - Compute new driver states (5 drivers must sum to total improvement)
    - Apply volatility dampening
    - Store immutable Projection_State and Driver_State rows
    - Trigger Supabase Realtime notification
    """

    pass
