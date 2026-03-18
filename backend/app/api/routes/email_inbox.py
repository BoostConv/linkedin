"""Email inbox routes — configure and poll email for ideas."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.api.routes.auth import get_current_user
from app.services.email.inbox_poller import poll_inbox

router = APIRouter()
settings = get_settings()


class EmailConfig(BaseModel):
    imap_host: str
    imap_port: int = 993
    email_address: str
    email_password: str


class EmailConfigResponse(BaseModel):
    configured: bool
    email_address: str | None = None
    imap_host: str | None = None


class PollResult(BaseModel):
    processed: int
    errors: int
    details: list[str]


@router.get("/config/", response_model=EmailConfigResponse)
async def get_email_config(
    _: User = Depends(get_current_user),
):
    """Get current email inbox configuration status."""
    return EmailConfigResponse(
        configured=bool(settings.email_imap_host and settings.email_address),
        email_address=settings.email_address if settings.email_address else None,
        imap_host=settings.email_imap_host if settings.email_imap_host else None,
    )


@router.post("/config/")
async def update_email_config(
    data: EmailConfig,
    _: User = Depends(get_current_user),
):
    """Update email inbox configuration.

    Note: This updates the runtime settings. For persistence across restarts,
    update the .env file.
    """
    import imaplib

    # Test the connection first
    try:
        if data.imap_port == 993:
            mail = imaplib.IMAP4_SSL(data.imap_host, data.imap_port)
        else:
            mail = imaplib.IMAP4(data.imap_host, data.imap_port)
        mail.login(data.email_address, data.email_password)
        mail.logout()
    except imaplib.IMAP4.error as e:
        raise HTTPException(
            status_code=400,
            detail=f"Connexion IMAP échouée : {str(e)}. Vérifiez vos identifiants et que l'accès IMAP est activé.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Erreur de connexion : {str(e)}",
        )

    # Update runtime settings
    settings.email_imap_host = data.imap_host
    settings.email_imap_port = data.imap_port
    settings.email_address = data.email_address
    settings.email_password = data.email_password

    # Also write to .env for persistence
    try:
        _update_env_file({
            "EMAIL_IMAP_HOST": data.imap_host,
            "EMAIL_IMAP_PORT": str(data.imap_port),
            "EMAIL_ADDRESS": data.email_address,
            "EMAIL_PASSWORD": data.email_password,
        })
    except Exception:
        pass  # Non-critical — runtime config is already updated

    return {
        "status": "connected",
        "message": f"Connecté à {data.email_address} via {data.imap_host}",
    }


@router.post("/poll/", response_model=PollResult)
async def poll_emails(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Manually trigger email polling to fetch new ideas."""
    if not settings.email_imap_host or not settings.email_address:
        raise HTTPException(
            status_code=400,
            detail="Email inbox non configuré. Configurez d'abord via /email-inbox/config.",
        )

    result = await poll_inbox(db)
    return PollResult(**result)


def _update_env_file(updates: dict[str, str]):
    """Update .env file with new values."""
    import os

    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env")
    if not os.path.exists(env_path):
        return

    with open(env_path, "r") as f:
        lines = f.readlines()

    existing_keys = set()
    new_lines = []
    for line in lines:
        key = line.split("=")[0].strip() if "=" in line else ""
        if key in updates:
            new_lines.append(f"{key}={updates[key]}\n")
            existing_keys.add(key)
        else:
            new_lines.append(line)

    # Add any new keys that weren't in the file
    for key, value in updates.items():
        if key not in existing_keys:
            new_lines.append(f"{key}={value}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)
