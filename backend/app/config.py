import os

from pydantic_settings import BaseSettings
from functools import lru_cache


def _fix_db_url(url: str, async_driver: bool = False) -> str:
    """Convert Render's postgres:// to postgresql:// and optionally add asyncpg driver."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if async_driver and "asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


class Settings(BaseSettings):
    # App
    app_name: str = "LinkedIn Automation"
    debug: bool = False
    secret_key: str = "change-me-in-production"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/linkedin_automation"
    database_url_sync: str = "postgresql://postgres:postgres@db:5432/linkedin_automation"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # LinkedIn OAuth
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_redirect_uri: str = "http://localhost:8000/api/auth/linkedin/callback"

    # Anthropic (Claude)
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"

    # OpenAI (DALL-E)
    openai_api_key: str = ""

    # Apify
    apify_api_token: str = ""

    # Cloudflare R2
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "linkedin-assets"

    # Email Inbox (for idea collection via email)
    email_imap_host: str = ""
    email_imap_port: int = 993
    email_address: str = ""
    email_password: str = ""  # App password for Gmail, or regular password

    # CORS
    cors_origins: str = "http://localhost:3000"

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60 * 24 * 7  # 7 days

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    # Auto-fix Render's postgres:// URLs
    s.database_url = _fix_db_url(s.database_url, async_driver=True)
    s.database_url_sync = _fix_db_url(s.database_url_sync, async_driver=False)
    return s
