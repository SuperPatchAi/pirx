from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Decode and validate a Supabase-issued JWT from the Authorization header.

    NOTE: In production, replace `supabase_jwt_secret` with the actual JWT secret
    from Supabase Dashboard → Settings → API → JWT Secret. The anon key works for
    development because Supabase signs tokens with the project's JWT secret, which
    matches the anon key's HMAC secret in local/dev environments.
    """
    token = credentials.credentials
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
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
        return {"user_id": user_id, "email": payload.get("email")}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
