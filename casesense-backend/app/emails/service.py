"""
EmailService — Blueprint §75.6.

Transports:
  - console     (dev default; logs the rendered mail)
  - smtp        (aiosmtplib via SMTP_URL)
  - api_generic (httpx POST to EMAIL_API_BASE, e.g. Brevo)

Emails never carry legal content — links + generic notices only.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger("casesense.emails")

TEMPLATES = ("verify_email", "reset_password", "security_notice", "password_changed")


def _render_subject(template: str) -> str:
    subjects = {
        "verify_email": "Confirm your CaseSense email address",
        "reset_password": "Reset your CaseSense password",
        "security_notice": "Important security notice from CaseSense",
        "password_changed": "Your CaseSense password was changed",
    }
    return subjects.get(template, "CaseSense")


def _render_body(template: str, params: dict) -> str:
    link = params.get("link", "")
    if template == "verify_email":
        code = params.get("code", "")
        return f"Your CaseSense verification code is: {code}\n\nIt expires in 10 minutes. Do not share this code. If you did not create a CaseSense account, you can ignore this email."
    if template == "reset_password":
        return f"Reset your password using this link: {link}\n\nThis link expires in 60 minutes. If you did not request it, you can ignore this email."
    if template == "security_notice":
        return "Your CaseSense account recently had a security-relevant action. If this was not you, contact support immediately."
    if template == "password_changed":
        return "Your CaseSense password was changed. If this was not you, contact support immediately."
    return link


class EmailService:
    """Provider-neutral email sender. In dev the default transport logs the mail."""

    @classmethod
    async def send(
        cls,
        db: AsyncSession,
        to_email: str,
        template: str,
        params: dict | None = None,
        user_id: uuid.UUID | None = None,
        related_resource_type: str | None = None,
        related_resource_id: str | None = None,
        background_tasks: "fastapi.BackgroundTasks | None" = None,
    ) -> None:
        """Queue an email to `email_outbox` in the caller's transaction (same txn rule §75.6)."""
        if template not in TEMPLATES:
            raise ValueError(f"Unknown email template: {template}")

        from app.modules.users.models import EmailOutbox

        outbox = EmailOutbox(
            user_id=user_id,
            to_email=to_email,
            template=template,
            status="QUEUED",
            related_resource_type=related_resource_type,
            related_resource_id=related_resource_id,
        )
        db.add(outbox)
        await db.flush()

        if background_tasks:
            background_tasks.add_task(
                cls.dispatch_outbox,
                outbox_id=outbox.id,
                to_email=to_email,
                template=template,
                params=params,
            )

    @classmethod
    async def dispatch_outbox(
        cls,
        outbox_id,
        to_email: str,
        template: str,
        params: dict | None = None,
    ) -> None:
        """Background task to deliver the email and update the DB status."""
        from datetime import datetime, timezone
        from app.db.engine import get_job_session
        from app.modules.users.models import EmailOutbox

        success = await cls.deliver(to_email, template, params)

        async with get_job_session() as db:
            outbox = await db.get(EmailOutbox, outbox_id)
            if outbox:
                outbox.attempts += 1
                if success:
                    outbox.status = "SENT"
                    outbox.sent_at = datetime.now(timezone.utc)
                else:
                    outbox.status = "FAILED"
                    outbox.last_error = "Failed to deliver via transport"

    @classmethod
    async def deliver(
        cls,
        to_email: str,
        template: str,
        params: dict | None = None,
    ) -> bool:
        """Actually send a queued email. Returns True on success."""
        params = params or {}
        subject = _render_subject(template)
        body = _render_body(template, params)

        transport = settings.EMAIL_TRANSPORT
        if transport == "console":
            logger.info(
                "[email:console] To=%s Subject=%s\n%s", to_email, subject, body
            )
            return True
        if transport == "smtp":
            return await cls._send_smtp(to_email, subject, body)
        if transport == "api_generic":
            return await cls._send_api(to_email, subject, body)
        logger.warning("Unknown EMAIL_TRANSPORT=%s", transport)
        return False

    @classmethod
    async def _send_smtp(cls, to_email: str, subject: str, body: str) -> bool:
        try:
            import aiosmtplib  # type: ignore

            from email.message import EmailMessage

            message = EmailMessage()
            message["From"] = settings.EMAIL_FROM
            message["To"] = to_email
            message["Subject"] = subject
            message.set_content(body)
            await aiosmtplib.send(message, from_addr=settings.EMAIL_FROM)
            return True
        except Exception as exc:  # pragma: no cover
            logger.exception("SMTP send failed", error=str(exc))
            return False

    @classmethod
    async def _send_api(cls, to_email: str, subject: str, body: str) -> bool:
        try:
            import httpx
            import email.utils

            name, email_address = email.utils.parseaddr(settings.EMAIL_FROM)
            if not email_address:
                email_address = settings.EMAIL_FROM
            
            sender_payload = {"email": email_address}
            if name:
                sender_payload["name"] = name

            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    settings.EMAIL_API_BASE,
                    headers={"api-key": settings.EMAIL_API_KEY},
                    json={
                        "sender": sender_payload,
                        "to": [{"email": to_email}],
                        "subject": subject,
                        "textContent": body,
                    },
                )
                return response.status_code < 300
        except Exception as exc:  # pragma: no cover
            logger.exception("API email send failed", error=str(exc))
            return False
