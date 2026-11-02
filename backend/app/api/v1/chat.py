from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import Contract, ContractChunk
from app.schemas.audit import ChatQueryRequest, ChatQueryResponse, ClauseCitation
from app.services.rag.hybrid_search import hybrid_search_engine
from app.services.rag.reranker import legal_reranker
from app.core.llm_router import llm_router
from app.core.config import settings

router = APIRouter()

@router.post("", response_model=ChatQueryResponse)
async def query_contract(
    payload: ChatQueryRequest,
    db: AsyncSession = Depends(get_db)
):
    # Verify contract
    res = await db.execute(select(Contract).where(Contract.id == payload.contract_id))
    contract = res.scalars().first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found.")

    # Retrieve chunks
    chunks_res = await db.execute(select(ContractChunk).where(ContractChunk.contract_id == payload.contract_id))
    chunks = chunks_res.scalars().all()
    if not chunks:
        raise HTTPException(status_code=400, detail="Contract is not indexed.")

    chunks_data = [
        {
            "id": c.id,
            "page_number": c.page_number,
            "section_title": c.section_title,
            "content": c.content,
            "parent_id": c.parent_id,
            "is_parent": c.is_parent
        }
        for c in chunks
    ]

    # 1. Hybrid Search
    candidates = await hybrid_search_engine.search(
        query=payload.query,
        contract_id=payload.contract_id,
        all_contract_chunks=chunks_data,
        top_k=15
    )

    # 2. Rerank
    top_chunks = legal_reranker.rerank(query=payload.query, candidates=candidates, top_n=4)

    if not top_chunks:
        return ChatQueryResponse(
            answer="No relevant sections found in this contract matching your query.",
            citations=[]
        )

    # Citations
    citations = [
        ClauseCitation(
            page_number=c["page_number"],
            section_reference=c.get("section_title"),
            verbatim_text=c["content"][:250] + "..."
        )
        for c in top_chunks
    ]

    has_api_keys = bool(settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-your"))

    if has_api_keys:
        context_str = "\n\n".join([f"[Page {c['page_number']} | {c.get('section_title', '')}]: {c['content']}" for c in top_chunks])
        prompt = f"""You are a specialized Legal AI Assistant reviewing contract '{contract.filename}'.
Answer the user's question accurately using ONLY the contract context provided below.
Cite the relevant section and page numbers in your response.

Context:
{context_str}

User Question: {payload.query}
"""
        response = await llm_router.openai.chat.completions.create(
            model=settings.DEFAULT_FAST_LLM,
            messages=[
                {"role": "system", "content": "You are a precise corporate legal assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        answer = response.choices[0].message.content
    else:
        # High quality offline fallback
        top_c = top_chunks[0]
        answer = f"Based on Section '{top_c.get('section_title', 'General')}' (Page {top_c['page_number']}), the contract stipulates:\n\n\"{top_c['content'][:400]}...\""

    return ChatQueryResponse(
        answer=answer,
        citations=citations
    )

