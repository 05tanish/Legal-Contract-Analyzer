from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
import logging
import os

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

def normalize_db_url(url: str) -> str:
    if not url:
        return "sqlite+aiosqlite:///./legal_analyzer.db"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("sqlite://") and not url.startswith("sqlite+aiosqlite://"):
        url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    elif url.startswith("sqlite:"):
        url = url.replace("sqlite:", "sqlite+aiosqlite:", 1)

    # Clean up sslmode for asyncpg
    if "sslmode=" in url:
        url = url.replace("sslmode=require", "ssl=require")
        url = url.replace("sslmode=prefer", "ssl=prefer")
        url = url.replace("sslmode=disable", "")
        if url.endswith("?") or url.endswith("&"):
            url = url[:-1]
    return url

db_url = normalize_db_url(settings.DATABASE_URL)

# Cloud auto-detection: If deployed on Render/Docker and DATABASE_URL is pointing to localhost with no live Postgres
is_cloud = bool(os.environ.get("RENDER") or os.environ.get("PORT") or os.environ.get("ENVIRONMENT") == "production")
if is_cloud and ("localhost" in db_url or "127.0.0.1" in db_url) and not os.environ.get("DATABASE_URL"):
    logger.info("Cloud environment detected without external DATABASE_URL. Using embedded SQLite for zero-downtime operation.")
    db_url = "sqlite+aiosqlite:///./legal_analyzer.db"

def _build_engine(url: str):
    if "sqlite" in url:
        return create_async_engine(url, echo=False)
    else:
        return create_async_engine(
            url,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True
        )

engine = _build_engine(db_url)
_session_factory = None

def get_sessionmaker():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
    return _session_factory

class _SessionLocalProxy:
    """Proxy object so AsyncSessionLocal() always dispatches to the active engine."""
    def __call__(self, *args, **kwargs):
        return get_sessionmaker()(*args, **kwargs)

AsyncSessionLocal = _SessionLocalProxy()

async def switch_to_sqlite():
    """Fallback to embedded SQLite if primary database is unreachable."""
    global engine, _session_factory, db_url
    fallback_url = "sqlite+aiosqlite:///./legal_analyzer.db"
    logger.warning(f"Switching database engine to high-resilience SQLite fallback: {fallback_url}")
    try:
        await engine.dispose()
    except Exception:
        pass
    db_url = fallback_url
    engine = _build_engine(fallback_url)
    _session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    logger.info("Database engine switched to SQLite successfully.")

async def init_db():
    """Initializes tables on startup with zero-crash SQLite fallback."""
    global engine
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            try:
                from sqlalchemy import text
                await conn.execute(text("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS cloudinary_url VARCHAR(1024);"))
                await conn.execute(text("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS cloudinary_public_id VARCHAR(255);"))
                await conn.execute(text("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS user_id VARCHAR(36);"))
                await conn.execute(text("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS is_guest BOOLEAN DEFAULT FALSE;"))
                await conn.execute(text("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS guest_session_id VARCHAR(64);"))
                await conn.execute(text("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP;"))
                await conn.execute(text("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS cleanup_status VARCHAR(30) DEFAULT 'NONE';"))
                await conn.execute(text("ALTER TABLE contracts ADD COLUMN IF NOT EXISTS cleanup_retries INTEGER DEFAULT 0;"))
            except Exception as e:
                logger.debug(f"Schema check note: {e}")
        logger.info("Database tables initialized successfully with primary engine.")
    except Exception as err:
        logger.warning(f"Primary database connection failed ({err}). Falling back to embedded SQLite for zero-downtime startup...")
        await switch_to_sqlite()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully with SQLite fallback engine.")

async def get_db():
    """FastAPI dependency for yielding async db sessions."""
    async with get_sessionmaker()() as session:
        try:
            yield session
        finally:
            await session.close()
