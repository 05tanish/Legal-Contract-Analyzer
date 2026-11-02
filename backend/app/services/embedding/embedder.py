from app.core.config import settings
from app.core.llm_router import llm_router
from typing import List
import numpy as np
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    @staticmethod
    async def get_embedding(text: str) -> List[float]:
        embeddings = await EmbeddingService.get_batch_embeddings([text])
        return embeddings[0]

    @staticmethod
    async def get_batch_embeddings(texts: List[str]) -> List[List[float]]:
        """
        Generates dense vector representations using text-embedding-3-large or text-embedding-3-small.
        Has offline deterministic fallback if no API key is set for local developer testing.
        """
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("sk-your"):
            logger.warning("No valid OPENAI_API_KEY detected. Using deterministic pseudo-embeddings for testing.")
            # Deterministic pseudo-embedding based on hash for local development/offline testing
            results = []
            for t in texts:
                np.random.seed(abs(hash(t)) % (2**32))
                vec = np.random.normal(0, 1, settings.EMBEDDING_DIMENSIONS)
                vec = vec / np.linalg.norm(vec)
                results.append(vec.tolist())
            return results

        try:
            response = await llm_router.openai.embeddings.create(
                model=settings.DEFAULT_EMBEDDING_MODEL,
                input=texts,
                dimensions=settings.EMBEDDING_DIMENSIONS
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"Error calling OpenAI Embeddings API: {e}")
            raise e

embedding_service = EmbeddingService()

