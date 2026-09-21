from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt as _bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User

MAX_BCRYPT_BYTES = 72


def _patch_passlib_bcrypt() -> None:
    """Keep passlib working with bcrypt 4.1+/5.x on modern Python."""
    if not hasattr(_bcrypt, "__about__"):
        class _BcryptAbout:
            __version__ = getattr(_bcrypt, "__version__", "4.2.0")

        _bcrypt.__about__ = _BcryptAbout()  # type: ignore[attr-defined]

    original_hashpw = _bcrypt.hashpw
    original_checkpw = _bcrypt.checkpw

    def hashpw(password, salt):
        if isinstance(password, str):
            password = password.encode("utf-8")
        if len(password) > MAX_BCRYPT_BYTES:
            password = password[:MAX_BCRYPT_BYTES]
        return original_hashpw(password, salt)

    def checkpw(password, hashed_password):
        if isinstance(password, str):
            password = password.encode("utf-8")
        if len(password) > MAX_BCRYPT_BYTES:
            password = password[:MAX_BCRYPT_BYTES]
        return original_checkpw(password, hashed_password)

    _bcrypt.hashpw = hashpw  # type: ignore[method-assign]
    _bcrypt.checkpw = checkpw  # type: ignore[method-assign]


_patch_passlib_bcrypt()

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > MAX_BCRYPT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is too long. Use at most 72 bytes.",
        )
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        subject = payload.get("sub")
        if not subject:
            raise credentials_exception
        user_id = UUID(str(subject))
    except (JWTError, ValueError) as exc:
        raise credentials_exception from exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    return user
