"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    google_places_api_key: str = ""
    yelp_api_key: str = ""

    anthropic_api_key: str = ""

    cloudflare_r2_endpoint: str = ""
    cloudflare_r2_access_key: str = ""
    cloudflare_r2_secret_key: str = ""
    cloudflare_r2_bucket: str = "webagency-assets"

    vercel_token: str = ""
    vercel_team_id: str | None = None
    agency_domain: str = "youragency.com"

    resend_api_key: str = ""
    hunter_api_key: str | None = None

    outreach_daily_cap: int = 20
    review_mode: bool = True

    base_dir: str = "."


settings = Settings()
