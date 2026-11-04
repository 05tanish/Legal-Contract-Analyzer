from app.services.agents.state import ContractAuditState
from app.services.rag.hybrid_search import hybrid_search_engine
from app.services.rag.reranker import legal_reranker
import logging

logger = logging.getLogger(__name__)

async def retriever_node(state: ContractAuditState):
    """
    Decomposes playbook rules into targeted retrieval queries,
    runs Hybrid Search (Dense + BM25) + Cross-Encoder Reranker,
    and enriches matches with Parent Section context.
    """
    contract_id = state["contract_id"]
    rules = state.get("playbook_rules", [])
    all_chunks = state.get("all_chunks", [])
    parent_map = state.get("parent_chunks_map", {})

    retrieved_contexts = {}

    for rule in rules:
        category = rule.get("category", "")
        unacceptable = " ".join(rule.get("unacceptable_triggers", []))
        query = f"{category} {rule.get('standard_requirement', '')} {unacceptable}"

        # 1. Run Hybrid Search
        candidates = await hybrid_search_engine.search(
            query=query,
            contract_id=contract_id,
            all_contract_chunks=all_chunks,
            top_k=15
        )

        # 2. Run Cross-Encoder Reranker
        reranked = legal_reranker.rerank(query=query, candidates=candidates, top_n=4)

        # 3. Inject full Parent Context if available for high-context LLM analysis
        for item in reranked:
            pid = item.get("parent_id")
            if pid and pid in parent_map:
                item["parent_full_text"] = parent_map[pid]
            else:
                item["parent_full_text"] = item["content"]

        retrieved_contexts[category] = reranked

    logger.info(f"Retriever Node: Retrieved & reranked context for {len(rules)} playbook rules.")
    return {"retrieved_contexts": retrieved_contexts}

