"""Email service for sending emails."""
import logging

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailService:
    """Service for sending emails."""

    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.smtp_from = settings.smtp_from

    async def send_password_reset(
        self,
        email: str,
        token: str,
        reset_url: str = "http://localhost:8000/password-reset/confirm",
    ) -> bool:
        """
        Send password reset email.

        Returns:
            True if sent successfully, False otherwise
        """
        subject = "Сброс пароля — GetMyWine"
        body = self._build_password_reset_email(token, reset_url)

        return await self._send_email(email, subject, body)

    def _build_password_reset_email(self, token: str, reset_url: str) -> str:
        """Build password reset email content."""
        return f"""
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 8px 8px 0 0;">
                <h1 style="color: white; margin: 0;">🍷 GetMyWine</h1>
            </div>
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px;">
                <h2 style="color: #333; margin-top: 0;">Сброс пароля</h2>
                <p style="color: #666; line-height: 1.6;">
                    Вы запросили сброс пароля для вашего аккаунта GetMyWine.
                    Нажмите на кнопку ниже, чтобы установить новый пароль.
                </p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}?token={token}"
                       style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                              color: white;
                              padding: 14px 28px;
                              text-decoration: none;
                              border-radius: 8px;
                              font-weight: 600;
                              display: inline-block;">
                        Сбросить пароль
                    </a>
                </div>
                <p style="color: #999; font-size: 14px;">
                    Ссылка действительна в течение 1 часа.
                    Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо.
                </p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">
                    © 2026 GetMyWine. Все права защищены.
                </p>
            </div>
        </body>
        </html>
        """

    async def _send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
    ) -> bool:
        """Send email via SMTP."""
        if not self.smtp_host:
            logger.warning("SMTP not configured, skipping email send")
            return False

        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.smtp_from
            message["To"] = to_email

            html_part = MIMEText(body, "html")
            message.attach(html_part)

            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                start_tls=True,
            )

            logger.info(f"Email sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
