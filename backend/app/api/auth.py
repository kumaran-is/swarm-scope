import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.dependencies import get_db
from app.models.user import User
from app.schemas.user import TokenResponse, UserCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12, bcrypt__ident="2b")


def _hash_password(password: str) -> str:
    return str(pwd_context.hash(password))


def _verify_password(plain: str, hashed: str) -> bool:
    return bool(pwd_context.verify(plain, hashed))


def _create_token(
    data: dict,
    expires_delta: timedelta,
    secret: str,
    algorithm: str,
) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(UTC) + expires_delta
    return str(jwt.encode(to_encode, secret, algorithm=algorithm))


def _make_tokens(user_id: uuid.UUID, settings: Settings) -> TokenResponse:
    access_token = _create_token(
        {"sub": str(user_id), "type": "access"},
        timedelta(minutes=30),
        settings.app_secret_key,
        settings.jwt_algorithm,
    )
    refresh_token = _create_token(
        {"sub": str(user_id), "type": "refresh"},
        timedelta(days=7),
        settings.app_secret_key,
        settings.jwt_algorithm,
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(email=body.email, password_hash=_hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("Registered user %s", user.id)
    return _make_tokens(user.id, settings)


@router.post("/token", response_model=TokenResponse)
async def login(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None or not _verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    logger.info("Login user %s", user.id)
    return _make_tokens(user.id, settings)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: dict,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    from jose import JWTError

    token = body.get("refresh_token", "")
    try:
        payload = jwt.decode(token, settings.app_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "refresh":
            raise ValueError("Not a refresh token")
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    result = await db.execute(select(User).where(User.id == user_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return _make_tokens(user_id, settings)
