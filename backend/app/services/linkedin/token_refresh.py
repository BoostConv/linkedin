"""Automatic LinkedIn token refresh service."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.linkedin.client import refresh_access_token


async def ensure_valid_token(db: AsyncSession, user: User) -> str | None:
    """Ensure the user has a valid LinkedIn access token.

    If the token is expired or about to expire (within 30 minutes),
    refresh it automatically.

    Returns the valid access token, or None if refresh fails.
    """
    if not user.linkedin_access_token:
        return None

    # Check expiration
    if user.linkedin_token_expires_at:
        buffer = timedelta(minutes=30)
        if user.linkedin_token_expires_at - buffer <= datetime.now(timezone.utc):
            # Token expired or about to expire — refresh
            if not user.linkedin_refresh_token:
                return None

            try:
                token_data = await refresh_access_token(user.linkedin_refresh_token)
                user.linkedin_access_token = token_data["access_token"]
                if "refresh_token" in token_data:
                    user.linkedin_refresh_token = token_data["refresh_token"]
                if "expires_in" in token_data:
                    user.linkedin_token_expires_at = datetime.now(timezone.utc) + timedelta(
                        seconds=token_data["expires_in"]
                    )
                await db.commit()
                await db.refresh(user)
            except Exception:
                return None

    return user.linkedin_access_token
