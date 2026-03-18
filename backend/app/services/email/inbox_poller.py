"""Email inbox poller — transforms incoming emails into ideas.

Connects to an IMAP mailbox (Gmail, Outlook, etc.) and converts
each unread email into an idea in the ideas inbox.

Usage:
  1. Create a dedicated email address (e.g., ideas@yourdomain.com or a Gmail alias)
  2. Configure IMAP settings in .env
  3. Forward interesting content to that address
  4. The poller runs every 5 minutes via Celery Beat (or manually via API)
"""
import imaplib
import email
import re
import logging
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.idea import Idea
from app.api.routes.auth import DEFAULT_USER_ID

logger = logging.getLogger(__name__)
settings = get_settings()


def decode_mime_header(header: str | None) -> str:
    """Decode a MIME-encoded email header."""
    if not header:
        return ""
    decoded_parts = decode_header(header)
    parts = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            parts.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(part)
    return " ".join(parts)


def extract_urls(text: str) -> list[str]:
    """Extract URLs from text."""
    url_pattern = re.compile(
        r'https?://[^\s<>"\')\]]+',
        re.IGNORECASE,
    )
    return url_pattern.findall(text)


def get_email_body(msg: email.message.Message) -> str:
    """Extract the text body from an email message."""
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            # Skip attachments
            if "attachment" in content_disposition:
                continue

            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
                    break  # Prefer plain text
            elif content_type == "text/html" and not body:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    html = payload.decode(charset, errors="replace")
                    # Basic HTML stripping
                    body = re.sub(r'<[^>]+>', ' ', html)
                    body = re.sub(r'\s+', ' ', body).strip()
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            body = payload.decode(charset, errors="replace")

    return body.strip()


def clean_forwarded_content(body: str) -> str:
    """Clean up forwarded email content, removing email signatures and noise."""
    # Remove common email signatures
    sig_markers = [
        "\n-- \n",  # Standard sig separator
        "\n__",     # Underscore separator
        "\nSent from my",
        "\nEnvoyé de mon",
        "\nGet Outlook for",
    ]
    for marker in sig_markers:
        idx = body.find(marker)
        if idx > 0:
            body = body[:idx]

    # Trim excessive whitespace
    body = re.sub(r'\n{3,}', '\n\n', body)
    return body.strip()


IGNORED_SENDERS = [
    "noreply@google.com",
    "no-reply@accounts.google.com",
    "accounts-noreply@google.com",
    "googlecommunityteam-noreply@google.com",
    "noreply@",
    "no-reply@",
    "mailer-daemon@",
    "postmaster@",
    "security@",
    "notifications@",
]

IGNORED_SUBJECTS = [
    "validation en deux",
    "alerte de sécurité",
    "security alert",
    "information about your new",
    "bienvenue sur",
    "welcome to",
    "verify your email",
    "vérifiez votre",
    "confirm your",
    "mot de passe",
    "password",
    "your google account",
    "votre compte google",
]


def is_system_email(from_addr: str, subject: str) -> bool:
    """Check if an email is a system/transactional email to ignore."""
    from_lower = from_addr.lower()
    subject_lower = subject.lower()

    for sender in IGNORED_SENDERS:
        if sender in from_lower:
            return True

    for subj in IGNORED_SUBJECTS:
        if subj in subject_lower:
            return True

    return False


def determine_input_type(subject: str, body: str, urls: list[str]) -> str:
    """Determine the type of idea based on email content."""
    # If the email is mostly a URL
    if urls and len(body.split()) < 20:
        return "url"

    # If it looks like a list of themes
    lines = [l.strip() for l in body.split("\n") if l.strip()]
    if len(lines) >= 3 and all(len(l) < 100 for l in lines[:5]):
        return "theme_list"

    return "raw_idea"


async def poll_inbox(db: AsyncSession) -> dict:
    """Connect to IMAP inbox, fetch unread emails, create ideas.

    Returns:
        dict with keys: processed (int), errors (int), details (list)
    """
    imap_host = settings.email_imap_host
    imap_port = settings.email_imap_port
    email_address = settings.email_address
    email_password = settings.email_password

    if not all([imap_host, email_address, email_password]):
        return {"processed": 0, "errors": 0, "details": ["Email not configured"]}

    results = {"processed": 0, "errors": 0, "details": []}

    try:
        # Connect to IMAP
        if imap_port == 993:
            mail = imaplib.IMAP4_SSL(imap_host, imap_port)
        else:
            mail = imaplib.IMAP4(imap_host, imap_port)

        mail.login(email_address, email_password)
        mail.select("INBOX")

        # Search for unread emails
        status, messages = mail.search(None, "UNSEEN")
        if status != "OK" or not messages[0]:
            mail.logout()
            return {"processed": 0, "errors": 0, "details": ["No new emails"]}

        email_ids = messages[0].split()
        logger.info(f"Found {len(email_ids)} unread email(s)")

        for email_id in email_ids:
            try:
                # Fetch email
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                if status != "OK":
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                subject = decode_mime_header(msg.get("Subject"))
                from_addr = decode_mime_header(msg.get("From"))

                # Skip system/transactional emails
                if is_system_email(from_addr, subject):
                    logger.info(f"Skipping system email: {subject}")
                    mail.store(email_id, "+FLAGS", "\\Seen")
                    results["details"].append(f"Ignored system email: {subject}")
                    continue

                body = get_email_body(msg)
                body = clean_forwarded_content(body)

                # Extract URLs
                urls = extract_urls(body)
                # Also check subject for URLs
                urls.extend(extract_urls(subject))
                urls = list(set(urls))  # Dedupe

                # Build the idea content
                # Combine subject and body for the raw_input
                raw_input_parts = []
                if subject and subject.lower() not in ["(no subject)", "fwd:", "fw:", "re:"]:
                    # Clean forwarding prefixes
                    clean_subject = re.sub(r'^(Fwd?:|Re:)\s*', '', subject, flags=re.IGNORECASE).strip()
                    if clean_subject:
                        raw_input_parts.append(clean_subject)

                if body:
                    # Limit body length for the idea
                    truncated_body = body[:2000]
                    raw_input_parts.append(truncated_body)

                raw_input = "\n\n".join(raw_input_parts) if raw_input_parts else subject or "(Email sans contenu)"

                # Determine input type
                input_type = determine_input_type(subject, body, urls)

                # Pick the first URL as source_url if available
                source_url = urls[0] if urls else None

                # Check for duplicates (same raw_input in last 24h)
                from datetime import timedelta
                cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
                existing = await db.execute(
                    select(Idea).where(
                        Idea.user_id == DEFAULT_USER_ID,
                        Idea.raw_input == raw_input,
                        Idea.created_at >= cutoff,
                    )
                )
                if existing.scalar_one_or_none():
                    logger.info(f"Skipping duplicate email: {subject}")
                    results["details"].append(f"Duplicate skipped: {subject}")
                    continue

                # Create the idea
                idea = Idea(
                    user_id=DEFAULT_USER_ID,
                    input_type=input_type,
                    raw_input=raw_input,
                    source_url=source_url,
                    tags={"source": "email", "from": from_addr},
                )
                db.add(idea)
                await db.commit()
                await db.refresh(idea)

                # Try AI analysis (best-effort)
                try:
                    from app.services.ai.idea_analyzer import analyze_idea
                    await analyze_idea(db, idea.id)
                except Exception as e:
                    logger.warning(f"AI analysis failed for email idea: {e}")

                results["processed"] += 1
                results["details"].append(f"Created idea from: {subject}")
                logger.info(f"Created idea from email: {subject}")

                # Mark as read (already done by IMAP fetch with UNSEEN filter,
                # but explicitly flag it)
                mail.store(email_id, "+FLAGS", "\\Seen")

            except Exception as e:
                results["errors"] += 1
                results["details"].append(f"Error processing email: {str(e)}")
                logger.error(f"Error processing email {email_id}: {e}")

        mail.logout()

    except imaplib.IMAP4.error as e:
        results["errors"] += 1
        results["details"].append(f"IMAP connection error: {str(e)}")
        logger.error(f"IMAP error: {e}")
    except Exception as e:
        results["errors"] += 1
        results["details"].append(f"Unexpected error: {str(e)}")
        logger.error(f"Email polling error: {e}")

    return results
