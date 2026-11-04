import os
import sys

# Ensure backend root is always first on sys.path regardless of where uvicorn is invoked from
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# Ensure user site-packages are registered if running under user install
_user_site = os.path.expanduser("~/Library/Python/3.12/lib/python/site-packages")
if os.path.exists(_user_site) and _user_site not in sys.path:
    sys.path.append(_user_site)

# Polyfill 'packaging' for langchain_core/langgraph if not installed as standalone top-level package
if 'packaging' not in sys.modules:
    try:
        import packaging
    except ImportError:
        for vendor_prefix in ['setuptools._vendor.packaging', 'pip._vendor.packaging']:
            try:
                base = __import__(vendor_prefix, fromlist=['packaging'])
                sys.modules['packaging'] = base
                for sub in ['version', 'specifiers', 'requirements', 'markers', 'tags', 'utils']:
                    try:
                        smod = __import__(f'{vendor_prefix}.{sub}', fromlist=[sub])
                        sys.modules[f'packaging.{sub}'] = smod
                    except Exception:
                        pass
                break
            except Exception:
                pass

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
import logging

from app.core.config import settings
from app.db.session import engine, Base, get_db
import app.db.models  # Ensures all ORM models are registered with Base.metadata

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("legal_contract_analyzer")

async def periodic_guest_cleanup_worker():
    """Background worker that runs periodically to purge expired guest contracts."""
    from app.services.cleanup.guest_cleanup_service import guest_cleanup_service
    from app.db.session import AsyncSessionLocal

    interval_seconds = max(60, settings.CLEANUP_INTERVAL_MINUTES * 60)
    logger.info(f"Started automated guest contract cleanup task (runs every {settings.CLEANUP_INTERVAL_MINUTES}m).")

    while True:
        try:
            await asyncio.sleep(interval_seconds)
            async with AsyncSessionLocal() as session:
                await guest_cleanup_service.run_cleanup(session)
        except asyncio.CancelledError:
            logger.info("Automated guest cleanup task stopped.")
            break
        except Exception as e:
            logger.error(f"Error in automated guest cleanup task: {e}")
            await asyncio.sleep(30)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist and directories exist
    logger.info("Initializing Legal Contract Analyzer services...")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
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
    logger.info("Database tables initialized successfully.")

    # Start periodic guest contract cleanup background task
    cleanup_task = asyncio.create_task(periodic_guest_cleanup_worker())

    # Auto-seed core Indian legal corpus if empty
    try:
        # Ensure scripts package is importable from app context
        import sys
        import os as _os
        backend_root = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../.."))
        if backend_root not in sys.path:
            sys.path.insert(0, backend_root)

        from scripts.seed_indian_law import seed_indian_legal_corpus
        from app.db.session import AsyncSessionLocal
        from app.db.models import LegalStatute
        from sqlalchemy import select
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(LegalStatute).limit(1))
            if not res.scalars().first():
                logger.info("Indian Legal Corpus is empty. Running initial seeding on startup...")
                await seed_indian_legal_corpus()
                logger.info("Indian Legal Corpus seeded successfully.")
    except Exception as e:
        logger.warning(f"Auto-seed check non-blocking note: {e}")

    yield

    # Shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    await engine.dispose()
    logger.info("Database connection closed.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise-Grade Agentic Legal Contract RAG & Redlining API",
    version="2.0.0",
    lifespan=lifespan
)

# CORS Middleware (Allows localhost, Vercel, Render, Railway, and production domains)
_cors_origins = list(settings.CORS_ORIGINS) if hasattr(settings, "CORS_ORIGINS") else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"^https?://.*$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health Check
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "qdrant_url": settings.QDRANT_URL,
        "version": "2.0.0"
    }

# Mount static uploads directory for direct PDF viewing if needed
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/static/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include API routes (will be populated in Phase 5)
from app.api.v1.auth import router as auth_router
from app.api.v1.contracts import router as contracts_router
from app.api.v1.audit import router as audit_router
from app.api.v1.playbooks import router as playbooks_router
from app.api.v1.chat import router as chat_router
from app.api.v1.legal import router as legal_router

app.include_router(auth_router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(contracts_router, prefix=f"{settings.API_V1_PREFIX}/contracts", tags=["Contracts"])
app.include_router(audit_router, prefix=f"{settings.API_V1_PREFIX}/audit", tags=["Audit & Redlining"])
app.include_router(playbooks_router, prefix=f"{settings.API_V1_PREFIX}/playbooks", tags=["Playbooks"])
app.include_router(chat_router, prefix=f"{settings.API_V1_PREFIX}/chat", tags=["Contract & Legal QA"])
app.include_router(legal_router, prefix=f"{settings.API_V1_PREFIX}/legal", tags=["Indian Legal Research"])

@app.post(f"{settings.API_V1_PREFIX}/system/cleanup", tags=["System"])
async def trigger_manual_cleanup(
    db = Depends(get_db)
):
    """Manually triggers the background expired guest contract cleanup job."""
    from app.services.cleanup.guest_cleanup_service import guest_cleanup_service
    report = await guest_cleanup_service.run_cleanup(db)
    return report


