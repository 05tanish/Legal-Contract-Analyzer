from app.core.config import settings
from app.core.llm_router import llm_router
from typing import List
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Lazy import for optional providers
_sentence_transformer = None

def _get_sentence_transformer():
    """Lazy initialization of Sentence Transformer model (free, runs locally)"""
    global _sentence_transformer
    if _sentence_transformer is None:
        try:
            from sentence_transformers import SentenceTransformer
            # Use all-MiniLM-L6-v2: fast, lightweight, 384 dims, good quality
            # Will download model on first use (~80MB)
            _sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Sentence Transformer model loaded (all-MiniLM-L6-v2)")
        except ImportError:
            logger.warning("Sentence Transformers not installed. Run: pip install sentence-transformers")
        except Exception as e:
            logger.warning(f"Failed to load Sentence Transformer model: {e}")
    return _sentence_transformer

class EmbeddingService:
    @staticmethod
    async def get_embedding(text: str) -> List[float]:
        embeddings = await EmbeddingService.get_batch_embeddings([text])
        return embeddings[0]

    @staticmethod
    async def get_batch_embeddings(texts: List[str]) -> List[List[float]]:
        """
        Generates dense vector representations with multi-provider fallback:
        1. Try Sentence Transformers (FREE, runs locally, no API key needed)
        2. Fall back to OpenAI (if local model fails)
        3. Fall back to deterministic pseudo-embeddings (for testing)
        
        Sentence Transformer model: all-MiniLM-L6-v2 (384 dimensions, ~80MB)
        OpenAI embedding model: text-embedding-3-large (configurable dimensions)
        """
        
        # Try Sentence Transformers first (100% free, no API key)
        model = _get_sentence_transformer()
        if model:
            try:
                logger.info(f"Generating embeddings with Sentence Transformers for {len(texts)} texts")
                # Generate embeddings (returns numpy arrays)
                embeddings = model.encode(texts, convert_to_tensor=False, show_progress_bar=False)
                
                # Convert to list and handle dimension mismatch
                target_dim = settings.EMBEDDING_DIMENSIONS
                result = []
                for emb in embeddings:
                    emb_list = emb.tolist() if hasattr(emb, 'tolist') else list(emb)
                    
                    # Pad or truncate to match expected dimensions
                    if len(emb_list) != target_dim:
                        if len(emb_list) < target_dim:
                            # Pad with zeros
                            emb_list = emb_list + [0.0] * (target_dim - len(emb_list))
                        else:
                            # Truncate
                            emb_list = emb_list[:target_dim]
                    result.append(emb_list)
                
                logger.info(f"✓ Sentence Transformer embeddings generated successfully ({len(result)} vectors)")
                return result
                
            except Exception as e:
                logger.warning(f"Sentence Transformers failed: {e}. Trying OpenAI fallback...")
        
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

