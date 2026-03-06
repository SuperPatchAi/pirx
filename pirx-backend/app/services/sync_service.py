class SyncService:
    """Handles wearable data synchronization.

    Responsibilities:
    - Manage OAuth connections for Garmin, COROS, Strava via Terra API
    - Process incoming webhook payloads (Terra and Strava)
    - Normalize activity data into NormalizedActivity schema
    - Parse FIT files for detailed lap/HR data
    - Trigger feature engineering pipeline after new activity sync
    - Handle historical backfill on initial wearable connection
    """

    pass
