from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from app.core.config import settings
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class QdrantService:
    def __init__(self):
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        try:
            if settings.QDRANT_API_KEY:
                self.client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
            else:
                self.client = QdrantClient(url=settings.QDRANT_URL)
            self._ensure_collection_exists()
        except Exception as e:
            logger.warning(f"Could not connect to Qdrant at {settings.QDRANT_URL}: {e}. Local fallback will be used.")
            # In-memory client for local dev/testing if docker container is not running yet
            self.client = QdrantClient(":memory:")
            self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=settings.EMBEDDING_DIMENSIONS,
                        distance=qmodels.Distance.COSINE
                    )
                )
                # Create payload index on contract_id for sub-millisecond filtering
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="contract_id",
                    field_schema=qmodels.PayloadSchemaType.KEYWORD
                )
                logger.info(f"Initialized Qdrant collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error checking/creating Qdrant collection: {e}")

    def upsert_chunks(self, points: List[Dict[str, Any]]):
        """
        Batch upserts chunk vectors and metadata payloads into Qdrant.
        """
        qdrant_points = [
            qmodels.PointStruct(
                id=p["id"],
                vector=p["vector"],
                payload={
                    "contract_id": p["contract_id"],
                    "chunk_id": p["id"],
                    "page_number": p["page_number"],
                    "parent_id": p.get("parent_id"),
                    "section_title": p.get("section_title"),
                    "content": p["content"],
                    "is_parent": p.get("is_parent", False)
                }
            )
            for p in points
        ]

        # Batch upsert in slices of 100
        batch_size = 100
        for i in range(0, len(qdrant_points), batch_size):
            batch = qdrant_points[i:i + batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch
            )
        logger.info(f"Successfully indexed {len(points)} chunks into Qdrant.")

    def search_dense(self, query_vector: List[float], contract_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Searches dense embeddings with a hard contract_id payload filter.
        """
        query_filter = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="contract_id",
                    match=qmodels.MatchValue(value=contract_id)
                ),
                # Filter to only retrieve child chunks (high-precision)
                qmodels.FieldCondition(
                    key="is_parent",
                    match=qmodels.MatchValue(value=False)
                )
            ]
        )

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True
        )

        return [
            {
                "chunk_id": hit.payload.get("chunk_id"),
                "score": hit.score,
                "content": hit.payload.get("content"),
                "page_number": hit.payload.get("page_number"),
                "parent_id": hit.payload.get("parent_id"),
                "section_title": hit.payload.get("section_title"),
            }
            for hit in results
        ]

qdrant_service = QdrantService()

