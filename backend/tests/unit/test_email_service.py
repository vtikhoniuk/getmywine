"""Unit tests for EmailService."""
import pytest
from unittest.mock import AsyncMock, patch


class TestEmailService:
    """Tests for email service functionality."""

    @pytest.mark.asyncio
    async def test_send_password_reset_email(self):
        """Should send password reset email."""
        from app.services.email import EmailService

        email_service = EmailService()

        # Mock the SMTP send
        with patch.object(
            email_service, "_send_email", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = True

            result = await email_service.send_password_reset(
                email="test@example.com",
                token="test-token-123",
                reset_url="http://localhost:8000/password-reset/confirm",
            )

            assert result is True
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_email_contains_reset_link(self):
        """Reset email should contain the reset link."""
        from app.services.email import EmailService

        email_service = EmailService()
        token = "test-token-123"
        reset_url = "http://localhost:8000/password-reset/confirm"

        # Get email content
        content = email_service._build_password_reset_email(
            token=token,
            reset_url=reset_url,
        )

        assert token in content or reset_url in content

    def test_email_service_init_with_settings(self):
        """EmailService should use settings for SMTP config."""
        from app.services.email import EmailService

        email_service = EmailService()

        assert hasattr(email_service, "smtp_host")
        assert hasattr(email_service, "smtp_port")
