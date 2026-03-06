import time

from jose import jwt

from app.config import settings


def make_test_token(user_id="test-user-123", email="test@pirx.com"):
    """Create a valid-looking JWT for testing."""
    payload = {
        "sub": user_id,
        "email": email,
        "aud": "authenticated",
        "role": "authenticated",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, settings.jwt_signing_secret, algorithm="HS256")


def test_health_no_auth_required(client):
    """Health endpoint should not require authentication."""
    response = client.get("/health")
    assert response.status_code == 200


def test_protected_endpoint_no_token(client):
    """Protected endpoints should reject requests without a token."""
    response = client.get("/projection")
    assert response.status_code in (401, 403)


def test_protected_endpoint_invalid_token(client):
    """Protected endpoints should return 401 with invalid token."""
    response = client.get(
        "/projection", headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == 401


def test_protected_endpoint_with_valid_token(client):
    """Protected endpoints should work with valid JWT."""
    token = make_test_token()
    response = client.get(
        "/projection", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code != 401
    assert response.status_code != 403
