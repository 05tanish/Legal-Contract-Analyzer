from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class LegalReranker:
    """
    Cross-Encoder Re-Ranking Pipeline:
    Scores candidate (query, text) pairs directly to filter out retrieval noise.
    """

    @staticmethod
    def rerank(query: str, candidates: List[Dict[str, Any]], top_n: int = 6) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        # If Cohere API or BGE cross-encoder is configured, compute cross-attention here.
        # Fallback scoring heuristic combines RRF score with keyword density of legal keywords.
        scored_candidates = []
        query_terms = set(query.lower().split())

        for c in candidates:
            base_score = c.get("rrf_score", 0.0) * 10
            content_lower = c["content"].lower()

            # Bonus for exact query term matches (e.g. section numbers, specific legal terms)
            term_matches = sum(1 for term in query_terms if term in content_lower)
            lexical_multiplier = 1.0 + (0.2 * term_matches)

            final_score = base_score * lexical_multiplier
            c_copy = c.copy()
            c_copy["rerank_score"] = round(final_score, 4)
            scored_candidates.append(c_copy)

        scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored_candidates[:top_n]

legal_reranker = LegalReranker()

