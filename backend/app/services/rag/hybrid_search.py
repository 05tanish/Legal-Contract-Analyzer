from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
from app.services.vector_store.qdrant_client import qdrant_service
from app.services.embedding.embedder import embedding_service
import logging

logger = logging.getLogger(__name__)

class HybridSearchEngine:
    """
    Implements Dual-Stage Hybrid Search:
    - Dense Semantic Search (Qdrant Cosine Similarity)
    - Sparse Lexical Search (BM25 Okapi for exact clause names & legal numbers)
    - Reciprocal Rank Fusion (RRF) combines both rankings
    """

    @staticmethod
    def reciprocal_rank_fusion(dense_results: List[Dict[str, Any]], sparse_results: List[Dict[str, Any]], k: int = 60) -> List[Dict[str, Any]]:
        scores = {}
        item_lookup = {}

        # Process dense scores
        for rank, item in enumerate(dense_results):
            cid = item["chunk_id"]
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (k + rank + 1))
            item_lookup[cid] = item

        # Process sparse scores
        for rank, item in enumerate(sparse_results):
            cid = item["chunk_id"]
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (k + rank + 1))
            if cid not in item_lookup:
                item_lookup[cid] = item

        # Sort combined candidates by fused RRF score descending
        sorted_cids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        fused_items = []
        for cid in sorted_cids:
            item = item_lookup[cid].copy()
            item["rrf_score"] = scores[cid]
            fused_items.append(item)

        return fused_items

    @classmethod
    async def search(cls, query: str, contract_id: str, all_contract_chunks: List[Dict[str, Any]], top_k: int = 15) -> List[Dict[str, Any]]:
        # 1. Dense Semantic Search
        query_vector = await embedding_service.get_embedding(query)
        dense_hits = qdrant_service.search_dense(query_vector=query_vector, contract_id=contract_id, limit=30)

        # 2. Sparse BM25 Search
        sparse_hits = []
        child_chunks = [c for c in all_contract_chunks if not c.get("is_parent", False)]
        if child_chunks:
            corpus = [c["content"].lower().split() for c in child_chunks]
            tokenized_query = query.lower().split()
            bm25 = BM25Okapi(corpus)
            doc_scores = bm25.get_scores(tokenized_query)

            # Sort indices by BM25 score
            top_sparse_indices = sorted(range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True)[:30]
            for idx in top_sparse_indices:
                if doc_scores[idx] > 0:
                    c = child_chunks[idx]
                    sparse_hits.append({
                        "chunk_id": c["id"],
                        "score": float(doc_scores[idx]),
                        "content": c["content"],
                        "page_number": c["page_number"],
                        "parent_id": c.get("parent_id"),
                        "section_title": c.get("section_title")
                    })

        # 3. Reciprocal Rank Fusion
        fused_candidates = cls.reciprocal_rank_fusion(dense_hits, sparse_hits, k=60)
        return fused_candidates[:top_k]

hybrid_search_engine = HybridSearchEngine()

