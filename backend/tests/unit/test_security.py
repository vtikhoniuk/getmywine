"""Unit tests for security module (password hashing, JWT)."""
from datetime import timedelta

# Tests are written FIRST (TDD) - they will fail until implementation


class TestPasswordHashing:
    """Tests for password hashing functionality."""

    def test_hash_password_returns_hash(self):
        """Password hashing should return a bcrypt hash."""
        from app.core.security import hash_password

        password = "testpassword123"
        hashed = hash_password(password)

        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self):
        """Correct password should verify successfully."""
        from app.core.security import hash_password, verify_password

        password = "testpassword123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Incorrect password should fail verification."""
        from app.core.security import hash_password, verify_password

        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_hash_password_different_each_time(self):
        """Same password should produce different hashes (salt)."""
        from app.core.security import hash_password

        password = "testpassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2  # Different salts


class TestJWT:
    """Tests for JWT token functionality."""

    def test_create_access_token(self):
        """Should create a valid JWT token."""
        from app.core.security import create_access_token

        user_id = "test-user-id"
        token = create_access_token(subject=user_id)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expiry(self):
        """Should create token with custom expiry."""
        from app.core.security import create_access_token

        user_id = "test-user-id"
        expires = timedelta(hours=1)
        token = create_access_token(subject=user_id, expires_delta=expires)

        assert token is not None

    def test_verify_token_valid(self):
        """Valid token should be verified successfully."""
        from app.core.security import create_access_token, verify_token

        user_id = "test-user-id"
        token = create_access_token(subject=user_id)
        payload = verify_token(token)

        assert payload is not None
        assert payload.get("sub") == user_id

    def test_verify_token_invalid(self):
        """Invalid token should return None."""
        from app.core.security import verify_token

        invalid_token = "invalid.token.here"
        payload = verify_token(invalid_token)

        assert payload is None

    def test_verify_token_expired(self):
        """Expired token should return None."""
        from app.core.security import create_access_token, verify_token

        user_id = "test-user-id"
        # Create token that expires immediately
        token = create_access_token(subject=user_id, expires_delta=timedelta(seconds=-1))
        payload = verify_token(token)

        assert payload is None
