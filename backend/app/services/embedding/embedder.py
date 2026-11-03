from app.core.config import settings
from app.core.llm_router import llm_router
from typing import List
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Lazy import for optional providers
_cohere_client = None

def _get_cohere_client():
    """Lazy initialization of Cohere client"""
    global _cohere_client
    if _cohere_client is None and settings.COHERE_API_KEY:
        try:
            import cohere
            _cohere_client = cohere.Client(settings.COHERE_API_KEY)
            logger.info("Cohere embedding client initialized")
        except ImportError:
            logger.warning("Cohere SDK not installed. Run: pip install cohere")
        except Exception as e:
            logger.warning(f"Failed to initialize Cohere client: {e}")
    return _cohere_client

class EmbeddingService:
    @staticmethod
    async def get_embedding(text: str) -> List[float]:
        embeddings = await EmbeddingService.get_batch_embeddings([text])
        return embeddings[0]

    @staticmethod
    async def get_batch_embeddings(texts: List[str]) -> List[List[float]]:
        """
        Generates dense vector representations with multi-provider fallback:
        1. Try Cohere (free tier: 1M tokens/month, good for legal text)
        2. Fall back to OpenAI (if Cohere fails)
        3. Fall back to deterministic pseudo-embeddings (for testing)
        
        Cohere embedding model: embed-english-v3.0 (1024 dimensions)
        OpenAI embedding model: text-embedding-3-large (1536 dimensions)
        """
        
        # Try Cohere first (free tier available)
        cohere_client = _get_cohere_client()
        if cohere_client:
            try:
                logger.info(f"Generating embeddings with Cohere for {len(texts)} texts")
                response = cohere_client.embed(
                    texts=texts,
                    model="embed-english-v3.0",
                    input_type="search_document",  # For indexing documents
                    embedding_types=["float"]
                )
                embeddings = response.embeddings.float
                logger.info(f"✓ Cohere embeddings generated successfully ({len(embeddings)} vectors)")
                
                # Pad or truncate to match expected dimensions if needed
                target_dim = settings.EMBEDDING_DIMENSIONS
                result = []
                for emb in embeddings:
                    if len(emb) != target_dim:
                        # Pad with zeros or truncate
                        if len(emb) < target_dim:
                            emb = emb + [0.0] * (target_dim - len(emb))
                        else:
                            emb = emb[:target_dim]
                    result.append(emb)
                return result
                
            except Exception as e:
                logger.warning(f"Cohere embeddings failed: {e}. Trying OpenAI fallback...")
        
        # Fallback to OpenAI
        if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-your"):
            try:
                logger.info(f"Generating embeddings with OpenAI for {len(texts)} texts")
                response = await llm_router.openai.embeddings.create(
                    model=settings.DEFAULT_EMBEDDING_MODEL,
                    input=texts,
                    dimensions=settings.EMBEDDING_DIMENSIONS
                )
                embeddings = [data.embedding for data in response.data]
                logger.info(f"✓ OpenAI embeddings generated successfully")
                return embeddings
            except Exception as e:
                logger.error(f"OpenAI Embeddings API also failed: {e}. Using pseudo-embeddings.")
        
        # Final fallback: deterministic pseudo-embeddings for testing
        logger.warning("No valid embedding API available. Using deterministic pseudo-embeddings for testing.")
        results = []
        for t in texts:
            np.random.seed(abs(hash(t)) % (2**32))
            vec = np.random.normal(0, 1, settings.EMBEDDING_DIMENSIONS)
            vec = vec / np.linalg.norm(vec)
            results.append(vec.tolist())
        return results

embedding_service = EmbeddingService()

