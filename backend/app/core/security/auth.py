from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt

from app.core.config.settings import get_settings


async def get_current_user_id(
    authorization: str | None = Header(default=None),
) -> str:
    settings = get_settings()

    if settings.app_env.lower() != "production":
        return "00000000-0000-0000-0000-000000000000"

    if not settings.supabase_jwt_secret:
        return "00000000-0000-0000-0000-000000000000"

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    token = authorization.replace("Bearer ", "", 1)

    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user id",
        )
    return user_id


CurrentUserId = Depends(get_current_user_id)
