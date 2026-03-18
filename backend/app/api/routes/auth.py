"""Auth routes — single-user mode (no login required)."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User

router = APIRouter()
settings = get_settings()

# Fixed UUID for the single default user
DEFAULT_USER_ID = "00000000-1111-2222-3333-444444444444"


async def get_current_user(
    db: AsyncSession = Depends(get_db),
) -> User:
    """Return the default user — no authentication needed (single-user tool)."""
    result = await db.execute(select(User).where(User.id == DEFAULT_USER_ID))
    user = result.scalar_one_or_none()

    if user is None:
        # Auto-create the default user
        user = User(
            id=DEFAULT_USER_ID,
            email="sebastien@boostconversion.com",
            hashed_password="not-used",
            full_name="Sébastien Tortu",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    is_active: bool
    linkedin_person_id: str | None = None

    model_config = {"from_attributes": True}


@router.get("/me/")
async def me(current_user: User = Depends(get_current_user)):
    return current_user


# LinkedIn OAuth
@router.get("/linkedin/authorize/")
async def linkedin_authorize():
    from app.services.linkedin.client import get_authorization_url
    import secrets
    state = secrets.token_urlsafe(32)
    return {"authorization_url": get_authorization_url(state), "state": state}


@router.get("/linkedin/callback/")
async def linkedin_callback(
    code: str,
    state: str = "",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.linkedin.client import exchange_code_for_token, get_user_profile

    token_data = await exchange_code_for_token(code)
    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 5184000)  # Default 60 days

    profile = await get_user_profile(access_token)

    current_user.linkedin_access_token = access_token
    current_user.linkedin_refresh_token = refresh_token
    current_user.linkedin_token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    current_user.linkedin_person_id = profile.get("sub")

    await db.commit()

    return {"status": "connected", "linkedin_name": profile.get("name")}
