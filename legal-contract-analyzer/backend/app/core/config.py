from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
_root_dir = os.path.abspath(os.path.join(_backend_dir, ".."))

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "Legal Contract Intelligence Platform"
    API_V1_PREFIX: str = "/api/v1"
    
    # CORS Origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://legal_admin:legal_secret_pass@localhost:5432/legal_analyzer_db"

    # Qdrant Vector Store
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_NAME: str = "legal_contracts"
    QDRANT_LEGAL_COLLECTION_NAME: str = "indian_legal_corpus"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM Settings
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    DEFAULT_FAST_LLM: str = "gpt-4o-mini"
    DEFAULT_REASONING_LLM: str = "qwen/qwen3.8-27b"  # Active model on Groq account
    DEFAULT_EMBEDDING_MODEL: str = "text-embedding-3-large"
    # Sentence Transformers (all-MiniLM-L6-v2) produces 384-dim vectors.
    EMBEDDING_DIMENSIONS: int = 384

    # Langfuse Observability
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # Authentication & Security
    SECRET_KEY: str = "contractiq_enterprise_super_secret_legal_key_2026"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 14

    # Guest Workflow & Automatic Cleanup
    GUEST_CONTRACT_RETENTION_HOURS: int = 24  # Configurable TTL for guest contracts
    CLEANUP_INTERVAL_MINUTES: int = 15       # Scheduled cleanup frequency

    # Cloudinary Storage
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # File Uploads
    UPLOAD_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../uploads"))
    MAX_FILE_SIZE_MB: int = 50

    def model_post_init(self, __context):
        if not os.path.isabs(self.UPLOAD_DIR):
            self.UPLOAD_DIR = os.path.abspath(os.path.join(_root_dir, self.UPLOAD_DIR.lstrip("./")))
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)

    model_config = SettingsConfigDict(
        env_file=[
            os.path.join(_backend_dir, ".env"),
            os.path.join(_root_dir, ".env"),
            ".env"
        ],
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

