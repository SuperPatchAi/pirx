import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()


_known_users: set[str] = set()


def _ensure_public_user(user_id: str, email: str | None) -> None:
    """Create a public.users row if one doesn't exist yet.

    Supabase Auth creates auth.users on sign-up, but the public.users table
    (referenced by FK from chat_threads, activities, etc.) must be populated
    separately. This upsert is idempotent and cached in-memory per server lifetime.
    """
    if user_id in _known_users:
        return
    try:
        from app.services.supabase_client import SupabaseService
        db = SupabaseService()
        db.upsert_user(user_id, email or f"{user_id}@placeholder.pirx")
        _known_users.add(user_id)
    except Exception as e:
        logger.warning("ensure_public_user failed (non-fatal): %s", e)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Validate a Supabase-issued JWT.

    Strategy:
    1. Try local JWT decode with SUPABASE_JWT_SECRET (fastest, no network).
    2. If that fails, verify via Supabase Auth API (auth.getUser) as fallback.

    After auth succeeds, ensures a public.users row exists for FK integrity.
    """
    token = credentials.credentials
    user: dict | None = None

    # Strategy 1: local JWT decode
    if settings.jwt_signing_secret:
        try:
            payload = jwt.decode(
                token,
                settings.jwt_signing_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: no sub claim"
                )
            user = {"user_id": user_id, "email": payload.get("email")}
        except JWTError:
            logger.debug("Local JWT decode failed, falling back to Supabase auth API")

    # Strategy 2: verify via Supabase auth.getUser()
    if user is None:
        user = await _verify_via_supabase(token)

    import asyncio
    await asyncio.to_thread(_ensure_public_user, user["user_id"], user.get("email"))
    return user


async def _verify_via_supabase(token: str) -> dict:
    """Verify token by calling Supabase Auth's getUser endpoint."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.supabase_url}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": settings.supabase_anon_key,
                },
            )
        if resp.status_code == 200:
            data = resp.json()
            user_id = data.get("id")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="No user ID in token"
                )
            return {"user_id": user_id, "email": data.get("email")}
        logger.warning("Supabase auth verification returned %d: %s", resp.status_code, resp.text[:200])
    except httpx.HTTPError as e:
        logger.error("Supabase auth verification network error: %s", e)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )
