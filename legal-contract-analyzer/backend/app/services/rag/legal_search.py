from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.services.vector_store.qdrant_client import qdrant_service
from app.services.embedding.embedder import embedding_service
from app.db.models import LegalStatute, LegalSection, CourtJudgment
from app.schemas.audit import LegalCitation
import logging

logger = logging.getLogger(__name__)

class LegalSearchEngine:
    """
    Hybrid Retrieval Engine for Indian Statutory & Judicial Law:
    - Dense Vector Search in Qdrant ('indian_legal_corpus')
    - Exact Lexical Lookup in PostgreSQL (Act name, Section number, Case title)
    - RRF Fusion for combining statutory bare texts and judicial headnotes
    """

    @staticmethod
    async def search(
        query: str,
        db: AsyncSession,
        top_k: int = 5,
        document_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        # 1. Dense Semantic Search in Qdrant
        query_vector = await embedding_service.get_embedding(query)
        dense_hits = qdrant_service.search_legal_corpus(
            query_vector=query_vector,
            document_type=document_type,
            limit=20
        )

        # 2. Sparse / Alphanumeric Search in PostgreSQL
        # Extract potential section numbers or key phrases
        query_terms = query.lower().split()
        section_candidates = [t.strip(",.()") for t in query_terms if t.strip(",.()").isdigit() or t.startswith("sec") or t.startswith("art")]

        sparse_hits = []
        # Check sections matching terms
        if section_candidates:
            num_clean = [s.replace("section", "").replace("sec", "").replace("art", "").replace("article", "").strip() for s in section_candidates]
            stmt = (
                select(LegalSection, LegalStatute)
                .join(LegalStatute, LegalSection.statute_id == LegalStatute.id)
                .where(or_(*[LegalSection.section_number.ilike(f"%{n}%") for n in num_clean if n]))
                .limit(10)
            )
            res = await db.execute(stmt)
            for sec, stat in res.all():
                sparse_hits.append({
                    "legal_id": sec.id,
                    "document_type": "STATUTE_SECTION",
                    "act_name": stat.act_name,
                    "act_year": stat.act_year,
                    "section_number": sec.section_number,
                    "title": sec.section_title or f"Section {sec.section_number}",
                    "content": sec.content,
                    "source_url": stat.source_url,
                    "status": sec.status,
                    "score": 0.95
                })

        # 3. Reciprocal Rank Fusion (RRF)
        fused = {}
        # Dense ranking
        for rank, hit in enumerate(dense_hits):
            lid = hit.get("legal_id", hit.get("section_number", str(rank)))
            fused[lid] = fused.get(lid, 0.0) + (1.0 / (60 + rank + 1))
            hit["fused_score"] = fused[lid]

        # Merge sparse hits with high priority
        for rank, hit in enumerate(sparse_hits):
            lid = hit["legal_id"]
            fused[lid] = fused.get(lid, 0.0) + (1.0 / (60 + rank + 1)) * 1.5
            hit["fused_score"] = fused[lid]
            if not any(d.get("legal_id") == lid for d in dense_hits):
                dense_hits.append(hit)

        dense_hits.sort(key=lambda x: x.get("fused_score", x.get("score", 0.0)), reverse=True)
        return dense_hits[:top_k]

    @staticmethod
    def hits_to_citations(hits: List[Dict[str, Any]]) -> List[LegalCitation]:
        citations = []
        for h in hits:
            if h.get("document_type") == "COURT_JUDGMENT":
                citations.append(LegalCitation(
                    citation_type="COURT_JUDGMENT",
                    case_title=h.get("case_title", h.get("title")),
                    neutral_citation=h.get("neutral_citation", "Neutral Citation Available"),
                    court_name=h.get("court_name", "Supreme Court of India"),
                    principle=h.get("ratio_decidendi", h.get("content", ""))[:250] + "...",
                    official_url=h.get("source_url")
                ))
            else:
                citations.append(LegalCitation(
                    citation_type="STATUTE_SECTION",
                    act_name=h.get("act_name", "Central Act"),
                    section_number=h.get("section_number", "Section"),
                    section_title=h.get("title", ""),
                    official_url=h.get("source_url"),
                    status=h.get("status", "CURRENT")
                ))
        return citations

legal_search_engine = LegalSearchEngine()

