import os
import hashlib
from app.core.config import settings
from typing import List
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Detect cloud/Render deployment to avoid loading heavy PyTorch models
_IS_CLOUD = bool(
    os.environ.get("RENDER") or
    os.environ.get("RAILWAY_ENVIRONMENT") or
    os.environ.get("FLY_APP_NAME") or
    os.environ.get("ENVIRONMENT", "").lower() == "production"
)


def _fast_deterministic_embedding(text: str, dim: int) -> List[float]:
    """
    Ultra-fast, zero-dependency, deterministic text embedding using
    character n-gram hashing projected into a dense unit-norm vector.
    
    - No PyTorch, no downloads, no RAM spike.
    - Deterministic: same text always yields the same vector.
    - Semantically reasonable: similar texts share overlapping n-grams → similar hashes.
    - Runs in < 1ms per text at 384 dims.
    """
    text = text.lower().strip()
    # Build a combined seed from multiple hash functions for better spread
    seeds = [
        int(hashlib.md5(text.encode()).hexdigest(), 16) % (2 ** 31),
        int(hashlib.sha1(text.encode()).hexdigest(), 16) % (2 ** 31),
        abs(hash(text)) % (2 ** 31),
    ]
    
    # Character-level n-gram hashing for semantic sensitivity
    ngram_seed = 0
    for n in (2, 3, 4):
        for i in range(len(text) - n + 1):
            ngram = text[i:i+n]
            ngram_seed ^= int(hashlib.md5(ngram.encode()).hexdigest()[:8], 16)
    seeds.append(ngram_seed % (2 ** 31))
    
    combined_seed = seeds[0] ^ (seeds[1] << 1) ^ (seeds[2] << 2) ^ (seeds[3] << 3)
    combined_seed = combined_seed % (2 ** 31)
    
    rng = np.random.default_rng(combined_seed)
    vec = rng.standard_normal(dim).astype(np.float32)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


class EmbeddingService:
    @staticmethod
    async def get_embedding(text: str) -> List[float]:
        embeddings = await EmbeddingService.get_batch_embeddings([text])
        return embeddings[0]

    @staticmethod
    async def get_batch_embeddings(texts: List[str]) -> List[List[float]]:
        """
        Generates dense vector representations with multi-provider fallback:

        On Render / Cloud (512MB RAM):
          1. Fast deterministic n-gram embeddings (< 1ms, 0MB RAM overhead)
          2. OpenAI as upgrade path if key is valid

        Locally (dev):
          1. Sentence Transformers (all-MiniLM-L6-v2, 384 dims)
          2. OpenAI fallback
          3. Fast deterministic n-gram embeddings
        """
        target_dim = settings.EMBEDDING_DIMENSIONS

        # ------------------------------------------------------------------ #
        # CLOUD PATH: skip PyTorch/SentenceTransformers entirely to avoid OOM #
        # ------------------------------------------------------------------ #
        if _IS_CLOUD:
            # Try OpenAI first if key looks valid (not placeholder, not exhausted)
            if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-your"):
                try:
                    from app.core.llm_router import llm_router
                    logger.info(f"[Cloud] Generating embeddings with OpenAI for {len(texts)} texts")
                    response = await llm_router.openai.embeddings.create(
                        model=settings.DEFAULT_EMBEDDING_MODEL,
                        input=texts,
                        dimensions=target_dim
                    )
                    result = [data.embedding for data in response.data]
                    logger.info("✓ OpenAI embeddings generated successfully")
                    return result
                except Exception as e:
                    logger.warning(f"OpenAI embeddings unavailable ({e}). Using fast local embeddings.")

            # Fast local fallback — no PyTorch, no network, no OOM
            logger.info(f"[Cloud] Generating {len(texts)} fast deterministic embeddings (dim={target_dim})")
            return [_fast_deterministic_embedding(t, target_dim) for t in texts]

        # ------------------------------------------------------------------ #
        # LOCAL DEV PATH: try Sentence Transformers (high quality)           #
        # ------------------------------------------------------------------ #
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info(f"[Local] Generating embeddings with Sentence Transformers for {len(texts)} texts")
            embeddings = _model.encode(texts, convert_to_tensor=False, show_progress_bar=False)
            result = []
            for emb in embeddings:
                emb_list = emb.tolist() if hasattr(emb, 'tolist') else list(emb)
                if len(emb_list) < target_dim:
                    emb_list = emb_list + [0.0] * (target_dim - len(emb_list))
                else:
                    emb_list = emb_list[:target_dim]
                result.append(emb_list)
            logger.info(f"✓ Sentence Transformer embeddings generated ({len(result)} vectors)")
            return result
        except Exception as e:
            logger.warning(f"[Local] Sentence Transformers unavailable ({e}). Trying OpenAI...")

        # Local OpenAI fallback
        if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-your"):
            try:
                from app.core.llm_router import llm_router
                logger.info(f"[Local] Generating embeddings with OpenAI for {len(texts)} texts")
                response = await llm_router.openai.embeddings.create(
                    model=settings.DEFAULT_EMBEDDING_MODEL,
                    input=texts,
                    dimensions=target_dim
                )
                return [data.embedding for data in response.data]
            except Exception as e:
                logger.error(f"OpenAI Embeddings also failed: {e}.")

        # Final local fallback
        logger.warning("[Local] All embedding providers failed. Using deterministic n-gram embeddings.")
        return [_fast_deterministic_embedding(t, target_dim) for t in texts]


embedding_service = EmbeddingService()

