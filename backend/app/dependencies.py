import logging
import uuid
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

_engine = None
_session_factory = None
_redis_client = None

bearer_scheme = HTTPBearer(auto_error=False)


def get_engine(settings: Settings | None = None):
    global _engine
    if _engine is None:
        s = settings or get_settings()
        _engine = create_async_engine(s.database_url, echo=False, pool_pre_ping=True)
    return _engine


def get_session_factory(settings: Settings | None = None):
    global _session_factory
    if _session_factory is None:
        engine = get_engine(settings)
        _session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def get_gemini_client():
    """Returns None for now — implemented in Session 02 (gemini/client.py)."""
    return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Decode JWT and return User ORM instance."""
    from app.models.user import User

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.app_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
