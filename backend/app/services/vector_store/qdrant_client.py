from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from app.core.config import settings
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class QdrantService:
    def __init__(self):
        self.contract_collection = settings.QDRANT_COLLECTION_NAME
        self.legal_collection = settings.QDRANT_LEGAL_COLLECTION_NAME
        try:
            if settings.QDRANT_API_KEY:
                self.client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
            else:
                self.client = QdrantClient(url=settings.QDRANT_URL)
            self._ensure_collections_exist()
        except Exception as e:
            logger.warning(f"Could not connect to Qdrant at {settings.QDRANT_URL}: {e}. Local in-memory fallback will be used.")
            # In-memory client for local dev/testing if docker container is not running yet
            self.client = QdrantClient(":memory:")
            self._ensure_collections_exist()

    def _ensure_collections_exist(self):
        try:
            collections = self.client.get_collections().collections
            existing_names = {c.name for c in collections}

            # 1. Contract Collection (Private / Tenant-scoped)
            if self.contract_collection not in existing_names:
                self.client.create_collection(
                    collection_name=self.contract_collection,
                    vectors_config=qmodels.VectorParams(
                        size=settings.EMBEDDING_DIMENSIONS,
                        distance=qmodels.Distance.COSINE
                    )
                )
                self.client.create_payload_index(
                    collection_name=self.contract_collection,
                    field_name="contract_id",
                    field_schema=qmodels.PayloadSchemaType.KEYWORD
                )
                self.client.create_payload_index(
                    collection_name=self.contract_collection,
                    field_name="is_parent",
                    field_schema=qmodels.PayloadSchemaType.BOOL
                )
                logger.info(f"Initialized Qdrant collection: {self.contract_collection}")

            # 2. Indian Legal Knowledge Corpus (Shared across users)
            if self.legal_collection not in existing_names:
                self.client.create_collection(
                    collection_name=self.legal_collection,
                    vectors_config=qmodels.VectorParams(
                        size=settings.EMBEDDING_DIMENSIONS,
                        distance=qmodels.Distance.COSINE
                    )
                )
                self.client.create_payload_index(
                    collection_name=self.legal_collection,
                    field_name="document_type",
                    field_schema=qmodels.PayloadSchemaType.KEYWORD
                )
                self.client.create_payload_index(
                    collection_name=self.legal_collection,
                    field_name="act_name",
                    field_schema=qmodels.PayloadSchemaType.KEYWORD
                )
                self.client.create_payload_index(
                    collection_name=self.legal_collection,
                    field_name="section_number",
                    field_schema=qmodels.PayloadSchemaType.KEYWORD
                )
                logger.info(f"Initialized Qdrant collection: {self.legal_collection}")

        except Exception as e:
            logger.error(f"Error checking/creating Qdrant collections: {e}")

    # ----------------------------------------------------
    # Private Contract Operations
    # ----------------------------------------------------
    def upsert_chunks(self, points: List[Dict[str, Any]]):
        """Batch upserts chunk vectors and metadata payloads into legal_contracts."""
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

        batch_size = 100
        for i in range(0, len(qdrant_points), batch_size):
            batch = qdrant_points[i:i + batch_size]
            self.client.upsert(
                collection_name=self.contract_collection,
                points=batch
            )
        logger.info(f"Indexed {len(points)} contract chunks into {self.contract_collection}.")

    def search_dense(self, query_vector: List[float], contract_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Searches dense embeddings with a hard contract_id payload filter."""
        query_filter = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="contract_id",
                    match=qmodels.MatchValue(value=contract_id)
                ),
                qmodels.FieldCondition(
                    key="is_parent",
                    match=qmodels.MatchValue(value=False)
                )
            ]
        )

        results = self.client.query_points(
            collection_name=self.contract_collection,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True
        ).points

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

    # ----------------------------------------------------
    # Indian Legal Corpus Operations
    # ----------------------------------------------------
    def upsert_legal_points(self, points: List[Dict[str, Any]]):
        """Batch upserts statutory sections and judgments into indian_legal_corpus."""
        qdrant_points = [
            qmodels.PointStruct(
                id=p["id"],
                vector=p["vector"],
                payload={
                    "legal_id": p["id"],
                    "document_type": p["document_type"], # "STATUTE_SECTION" or "COURT_JUDGMENT"
                    "act_name": p.get("act_name"),
                    "act_year": p.get("act_year"),
                    "section_number": p.get("section_number"),
                    "title": p.get("title"),
                    "content": p["content"],
                    "case_title": p.get("case_title"),
                    "neutral_citation": p.get("neutral_citation"),
                    "ratio_decidendi": p.get("ratio_decidendi"),
                    "court_name": p.get("court_name"),
                    "judgment_date": str(p.get("judgment_date", "")),
                    "source_url": p.get("source_url"),
                    "status": p.get("status", "CURRENT")
                }
            )
            for p in points
        ]

        batch_size = 100
        for i in range(0, len(qdrant_points), batch_size):
            batch = qdrant_points[i:i + batch_size]
            self.client.upsert(
                collection_name=self.legal_collection,
                points=batch
            )
        logger.info(f"Indexed {len(points)} points into {self.legal_collection}.")

    def search_legal_corpus(
        self,
        query_vector: List[float],
        document_type: Optional[str] = None,
        act_name: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Searches the Indian Legal Corpus with optional metadata filters."""
        must_conditions = []
        if document_type:
            must_conditions.append(
                qmodels.FieldCondition(key="document_type", match=qmodels.MatchValue(value=document_type))
            )
        if act_name:
            must_conditions.append(
                qmodels.FieldCondition(key="act_name", match=qmodels.MatchValue(value=act_name))
            )

        query_filter = qmodels.Filter(must=must_conditions) if must_conditions else None

        results = self.client.query_points(
            collection_name=self.legal_collection,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True
        ).points

        return [
            {
                "legal_id": hit.payload.get("legal_id"),
                "score": hit.score,
                "document_type": hit.payload.get("document_type"),
                "act_name": hit.payload.get("act_name"),
                "act_year": hit.payload.get("act_year"),
                "section_number": hit.payload.get("section_number"),
                "title": hit.payload.get("title"),
                "content": hit.payload.get("content"),
                "case_title": hit.payload.get("case_title"),
                "neutral_citation": hit.payload.get("neutral_citation"),
                "ratio_decidendi": hit.payload.get("ratio_decidendi"),
                "court_name": hit.payload.get("court_name"),
                "source_url": hit.payload.get("source_url"),
                "status": hit.payload.get("status", "CURRENT")
            }
            for hit in results
        ]

qdrant_service = QdrantService()
