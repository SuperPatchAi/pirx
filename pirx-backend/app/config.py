from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""
    supabase_db_url: str = ""

    openai_api_key: str = ""
    google_api_key: str = ""

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_webhook_verify_token: str = "pirx-strava-verify"

    terra_api_key: str = ""
    terra_dev_id: str = ""
    terra_webhook_secret: str = ""

    vapid_private_key: str = ""
    vapid_public_key: str = ""
    vapid_subject: str = "mailto:admin@pirx.app"

    cors_origins: list[str] = ["http://localhost:3000"]

    api_url: str = "http://localhost:8000"

    sentry_dsn: str = ""
    token_encryption_key: str = ""

    @property
    def jwt_signing_secret(self) -> str:
        """Return the JWT secret for verifying Supabase tokens.

        Falls back to supabase_anon_key for development if SUPABASE_JWT_SECRET
        is not set. In production, set the JWT secret from Supabase Dashboard →
        Settings → API → JWT Secret.
        """
        return self.supabase_jwt_secret or self.supabase_anon_key


settings = Settings()
