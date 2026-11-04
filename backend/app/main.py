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

async def background_seed_worker():
    """Seeds the Indian legal knowledge base asynchronously in the background so HTTP server opens immediately."""
    await asyncio.sleep(2)
    try:
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
                logger.info("Indian Legal Corpus is empty. Running background initial seeding...")
                await seed_indian_legal_corpus()
                logger.info("Indian Legal Corpus seeded successfully in background.")
    except Exception as e:
        logger.warning(f"Background corpus seeding note: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist and directories exist
    logger.info("Initializing Legal Contract Analyzer services...")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Initialize database with automatic fallback
    try:
        from app.db.session import init_db
        await init_db()
    except Exception as e:
        logger.error(f"Database initialization non-fatal warning: {e}")

    # Start background workers (non-blocking!)
    cleanup_task = asyncio.create_task(periodic_guest_cleanup_worker())
    seed_task = asyncio.create_task(background_seed_worker())

    yield

    # Shutdown
    cleanup_task.cancel()
    seed_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    try:
        await seed_task
    except asyncio.CancelledError:
        pass

    try:
        from app.db.session import engine
        await engine.dispose()
    except Exception:
        pass
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
@app.get(f"{settings.API_V1_PREFIX}/health", tags=["System"])
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

# Serve production frontend Single Page Application (SPA) if dist directory exists
_dist_candidates = [
    os.path.join(_backend_dir, "../frontend/dist"),
    os.path.join(_backend_dir, "frontend/dist"),
    os.path.join(_backend_dir, "dist"),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../frontend/dist")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../dist")),
]
_frontend_dist = next((cand for cand in _dist_candidates if os.path.exists(cand) and os.path.exists(os.path.join(cand, "index.html"))), None)

if _frontend_dist:
    logger.info(f"Serving production frontend SPA from {_frontend_dist}")
    _assets_dir = os.path.join(_frontend_dist, "assets")
    if os.path.exists(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="spa_assets")

    from fastapi.responses import FileResponse
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        if full_path.startswith("api") or full_path in ("health", "docs", "redoc", "openapi.json"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not Found")
        target_file = os.path.join(_frontend_dist, full_path)
        if os.path.exists(target_file) and os.path.isfile(target_file):
            return FileResponse(target_file)
        return FileResponse(os.path.join(_frontend_dist, "index.html"))



