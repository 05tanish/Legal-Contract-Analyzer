from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import logging

from app.core.config import settings
from app.db.session import engine, Base

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("legal_contract_analyzer")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist and directories exist
    logger.info("Initializing Legal Contract Analyzer services...")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized successfully.")
    yield
    # Shutdown
    await engine.dispose()
    logger.info("Database connection closed.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise-Grade Agentic Legal Contract RAG & Redlining API",
    version="2.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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
from app.api.v1.contracts import router as contracts_router
from app.api.v1.audit import router as audit_router
from app.api.v1.playbooks import router as playbooks_router
from app.api.v1.chat import router as chat_router

app.include_router(contracts_router, prefix=f"{settings.API_V1_PREFIX}/contracts", tags=["Contracts"])
app.include_router(audit_router, prefix=f"{settings.API_V1_PREFIX}/audit", tags=["Audit & Redlining"])
app.include_router(playbooks_router, prefix=f"{settings.API_V1_PREFIX}/playbooks", tags=["Playbooks"])
app.include_router(chat_router, prefix=f"{settings.API_V1_PREFIX}/chat", tags=["Contract QA"])

