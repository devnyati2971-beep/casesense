"""
Email service — Blueprint §75.6 (provider-neutral).

Bodies are never stored; only template names + metadata go to `email_outbox`.
"""

from app.emails.service import EmailService

__all__ = ["EmailService"]