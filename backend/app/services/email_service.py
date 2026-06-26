"""Email service powered by Resend.

Provides reusable email sending utilities for ResearchOS.

Currently supports:
- Password reset emails

Future extensions:
- Email verification
- Project invitations
- Workflow completion notifications
"""

from __future__ import annotations

import resend

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class EmailService:
    """Reusable email service."""

    @staticmethod
    async def send_email(
        *,
        to: str,
        subject: str,
        html: str,
    ) -> bool:
        """Send an email via Resend.

        Args:
            to: Recipient email.
            subject: Email subject.
            html: HTML email body.

        Returns:
            True if sent successfully, otherwise False.
        """

        settings = get_settings()

        if not settings.resend_api_key:
            logger.error(
                "email.resend_not_configured",
            )
            return False

        resend.api_key = settings.resend_api_key

        try:
            response = resend.Emails.send(
                {
                    "from": settings.email_from,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                }
            )

            logger.info(
                "email.sent",
                to=to,
                subject=subject,
                response=str(response),
            )

            return True

        except Exception as exc:
            logger.exception(
                "email.failed",
                to=to,
                error=str(exc),
            )
            return False

    @staticmethod
    async def send_password_reset_email(
        *,
        email: str,
        name: str,
        reset_url: str,
    ) -> bool:
        """Send password reset email."""

        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;">
            <h2>Reset your ResearchOS password</h2>

            <p>Hello {name},</p>

            <p>
                We received a request to reset your password.
            </p>

            <p>
                Click the button below to create a new password.
            </p>

            <p style="margin:32px 0;">
                <a
                    href="{reset_url}"
                    style="
                        background:#2563eb;
                        color:white;
                        padding:12px 24px;
                        text-decoration:none;
                        border-radius:8px;
                        font-weight:bold;
                    "
                >
                    Reset Password
                </a>
            </p>

            <p>
                This link will expire in <strong>1 hour</strong>.
            </p>

            <p>
                If you didn't request this change,
                you can safely ignore this email.
            </p>

            <hr>

            <small>
                ResearchOS Team
            </small>
        </div>
        """

        return await EmailService.send_email(
            to=email,
            subject="Reset your ResearchOS password",
            html=html,
        )