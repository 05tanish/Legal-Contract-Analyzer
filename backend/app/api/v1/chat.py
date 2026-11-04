from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import logging
import re

logger = logging.getLogger(__name__)

from app.db.session import get_db
from app.db.models import Contract, ContractChunk, User
from app.schemas.audit import ChatQueryRequest, ChatQueryResponse, ClauseCitation, LegalCitation
from app.services.rag.hybrid_search import hybrid_search_engine
from app.services.rag.reranker import legal_reranker
from app.services.rag.legal_search import legal_search_engine
from app.core.llm_router import llm_router
from app.core.config import settings
from app.core.security import (
    security,
    get_current_user_optional,
    validate_contract_access
)

try:
    from langfuse import observe
except ImportError:
    # Fallback if langfuse not installed
    def observe(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

router = APIRouter()

def check_query_guardrails(query: str) -> Optional[str]:
    """
    Evaluates queries against basic legal AI guardrails:
    1. Scope limitation: Only contract review and Indian legal inquiries.
    2. Refusal of malicious/harmful or completely off-topic requests.
    3. Mandatory legal advice disclaimer.
    """
    q_clean = query.strip().lower()
    
    # Off-topic non-legal detection (asking for unrelated coding, creative writing, hacking, illegal acts)
    off_topic_patterns = [
        r'\bwrite a (story|poem|song|essay|joke)\b',
        r'\b(python|javascript|c\+\+|java) code\b',
        r'\b(hack|exploit|bypass|ddos|sql injection)\b',
        r'\bhow to (kill|steal|forge|counterfeit|evade taxes)\b',
        r'\bmedical advice\b'
    ]
    for pattern in off_topic_patterns:
        if re.search(pattern, q_clean):
            return (
                "I am ContractIQ Legal Assistant, specialized strictly in contract review and Indian commercial law. "
                "I am unable to assist with non-legal, creative, or unauthorized requests.\n\n"
                "Please ask questions related to your contract clauses, enforceability, termination terms, liability caps, "
                "or governing Indian statutes (such as the Indian Contract Act 1872, Arbitration & Conciliation Act 1996, or Companies Act 2013)."
            )
    return None

def strip_markdown_bold(text: str) -> str:
    """Removes '**' asterisks to maintain clean, professional typography without raw markdown bold symbols."""
    if not text:
        return text
    # Replace **word** with word
    cleaned = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    # Remove any leftover dangling **
    cleaned = cleaned.replace('**', '')
    return cleaned.strip()

def classify_query_intent(query: str, contract_id: Optional[str], requested_mode: Optional[str]) -> str:
    """Classifies query into CONTRACT_ONLY, LEGAL_ONLY, or HYBRID."""
    # If no contract is provided, always route to Indian Legal Research mode
    if not contract_id:
        return "LEGAL_ONLY"

    if requested_mode in ("CONTRACT_ONLY", "LEGAL_ONLY", "HYBRID"):
        return requested_mode

    q_lower = query.lower()
    indian_law_triggers = [
        "indian law", "india", "section", "article", "act", "constitution",
        "enforceable", "valid under", "void", "supreme court", "high court",
        "contract act", "restraint of trade", "liquidated damages", "penalty"
    ]
    has_legal_intent = any(trigger in q_lower for trigger in indian_law_triggers)

    if has_legal_intent:
        return "HYBRID"
    else:
        return "CONTRACT_ONLY"

@router.post("", response_model=ChatQueryResponse)
async def query_legal_platform(
    payload: ChatQueryRequest,
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Unified Legal Intelligence endpoint with 3-mode routing:
    1. CONTRACT_ONLY: RAG over user's uploaded contract
    2. LEGAL_ONLY: Search Indian Constitution, Acts & Supreme Court database
    3. HYBRID: Contract analysis + Indian law compliance checking
    
    RESTRICTED TO AUTHENTICATED USERS.
    """
    current_user = await get_current_user_optional(auth, db)
    if not current_user:
        raise HTTPException(
            status_code=403,
            detail="The AI Legal Copilot is available to registered accounts. Please sign in or create an account to converse with AI legal agents.",
            headers={"X-Auth-Required": "true"}
        )

    # 1. Guardrail check against off-topic, malicious, or non-legal requests
    guardrail_msg = check_query_guardrails(payload.query)
    if guardrail_msg:
        return ChatQueryResponse(
            answer=guardrail_msg,
            mode_used=payload.mode or "LEGAL_ONLY",
            citations=[],
            legal_citations=[]
        )

    if payload.contract_id:
        res = await db.execute(select(Contract).where(Contract.id == payload.contract_id))
        contract = res.scalars().first()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found.")
        validate_contract_access(contract, current_user, None)

    mode = classify_query_intent(payload.query, payload.contract_id, payload.mode)
    has_api_keys = bool(settings.GROQ_API_KEY) or bool(settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-your"))

    # ----------------------------------------------------
    # MODE 1: INDIAN LEGAL RESEARCH ONLY (No Contract needed)
    # ----------------------------------------------------
    if mode == "LEGAL_ONLY":
        legal_hits = await legal_search_engine.search(query=payload.query, db=db, top_k=5)
        legal_citations = legal_search_engine.hits_to_citations(legal_hits)

        if not legal_hits:
            return ChatQueryResponse(
                answer="No directly matching Indian statutory provisions or landmark Supreme Court judgments were found for your query.",
                mode_used="LEGAL_ONLY",
                citations=[],
                legal_citations=[]
            )

        answer = None
        if has_api_keys:
            context_blocks = "\n\n".join([
                f"[{h.get('document_type', 'LEGAL_DOC')} | {h.get('act_name', h.get('case_title'))} ({h.get('section_number', h.get('neutral_citation'))})]:\n{h.get('content', '')}"
                for h in legal_hits
            ])
            prompt = f"""You are an Expert Indian Legal Research AI Scholar.
Answer the user's research query accurately using the Indian statutes, bare acts, and landmark Supreme Court decisions provided below.
Always cite the Act, Section number, Case Title, and Neutral Citation clearly.

CRITICAL INSTRUCTIONS & GUARDRAILS:
1. Do NOT use double asterisks (**) anywhere in your response. Format all titles, acts, and headings with clean plain text or numbered lists.
2. Ground all statements strictly in the provided Indian legal authorities.
3. This analysis is provided for legal review and research purposes only, not licensed attorney-client representation.

Indian Legal Context:
{context_blocks}

User Question: {payload.query}
"""
            try:
                answer = await llm_router.generate_chat_completion(
                    messages=[
                        {"role": "system", "content": "You are a scholarly Indian legal research specialist. Never output markdown double asterisks (**)."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1
                )
            except Exception as e:
                logger.warning(f"LLM chat completion error: {e}. Falling back to legal knowledge base.")

        if not answer:
            top_hit = legal_hits[0]
            answer = f"Indian Legal Authority:\n\nUnder {top_hit.get('act_name', top_hit.get('case_title'))} ({top_hit.get('section_number', top_hit.get('neutral_citation'))}):\n\n> \"{top_hit['content']}\"\n\nJudicial Note: Statutory provisions are interpreted strictly according to binding Supreme Court precedent."

        return ChatQueryResponse(
            answer=strip_markdown_bold(answer),
            mode_used="LEGAL_ONLY",
            citations=[],
            legal_citations=legal_citations
        )

    # ----------------------------------------------------
    # Prepare Contract Chunks (Required for CONTRACT_ONLY & HYBRID)
    # ----------------------------------------------------
    res = await db.execute(select(Contract).where(Contract.id == payload.contract_id))
    contract = res.scalars().first()
    if not contract:
        raise HTTPException(status_code=404, detail="We could not find the requested contract document.")

    chunks_res = await db.execute(select(ContractChunk).where(ContractChunk.contract_id == payload.contract_id))
    chunks = chunks_res.scalars().all()
    if not chunks:
        raise HTTPException(status_code=400, detail="This contract has not been processed yet. Please click 'Review Contract' first.")

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

    candidates = await hybrid_search_engine.search(
        query=payload.query,
        contract_id=payload.contract_id,
        all_contract_chunks=chunks_data,
        top_k=15
    )
    top_contract_chunks = legal_reranker.rerank(query=payload.query, candidates=candidates, top_n=4)

    contract_citations = [
        ClauseCitation(
            page_number=c["page_number"],
            section_reference=c.get("section_title"),
            verbatim_text=c["content"][:250] + "..."
        )
        for c in top_contract_chunks
    ]

    # ----------------------------------------------------
    # MODE 2: CONTRACT ONLY
    # ----------------------------------------------------
    if mode == "CONTRACT_ONLY":
        if not top_contract_chunks:
            return ChatQueryResponse(
                answer="No relevant sections found in this contract matching your query.",
                mode_used="CONTRACT_ONLY",
                citations=[]
            )

        answer = None
        if has_api_keys:
            context_str = "\n\n".join([f"[Page {c['page_number']} | {c.get('section_title', '')}]: {c['content']}" for c in top_contract_chunks])
            prompt = f"""You are a specialized Legal AI Assistant reviewing contract '{contract.filename}'.
Answer the user's question accurately using ONLY the contract context provided below.
Cite the relevant section and page numbers in your response.

CRITICAL INSTRUCTIONS & GUARDRAILS:
1. Do NOT use double asterisks (**) anywhere in your response. Use clean plain text headers or numbers instead.
2. Ground all answers strictly in the contract text without speculation.
3. This is an informational contract review and does not constitute formal legal counsel.

Context:
{context_str}

User Question: {payload.query}
"""
            try:
                answer = await llm_router.generate_chat_completion(
                    messages=[
                        {"role": "system", "content": "You are a precise corporate legal assistant. Never output markdown double asterisks (**)."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2
                )
            except Exception as e:
                logger.warning(f"LLM contract chat completion failed: {e}. Using excerpt fallback.")

        if not answer:
            top_c = top_contract_chunks[0]
            answer = f"Based on Section '{top_c.get('section_title', 'General')}' (Page {top_c['page_number']}), the contract stipulates:\n\n\"{top_c['content'][:400]}...\""

        return ChatQueryResponse(
            answer=strip_markdown_bold(answer),
            mode_used="CONTRACT_ONLY",
            citations=contract_citations,
            legal_citations=[]
        )

    # ----------------------------------------------------
    # MODE 3: HYBRID CONTRACT & INDIAN LAW COMPARISON
    # ----------------------------------------------------
    legal_hits = await legal_search_engine.search(query=payload.query, db=db, top_k=5)
    legal_citations = legal_search_engine.hits_to_citations(legal_hits)

    answer = None
    if has_api_keys:
        contract_context = "\n\n".join([f"[Contract Page {c['page_number']} | {c.get('section_title', '')}]:\n{c['content']}" for c in top_contract_chunks])
        legal_context = "\n\n".join([f"[{h.get('document_type')} | {h.get('act_name', h.get('case_title'))} ({h.get('section_number', h.get('neutral_citation'))})]:\n{h.get('content')}" for h in legal_hits])

        prompt = f"""You are a Senior Indian Corporate Counsel performing a hybrid legal compliance review.
Compare the uploaded contract terms against governing Indian statutory law and Supreme Court precedents.

CONTRACT TERMS:
{contract_context}

APPLICABLE INDIAN STATUTES & SUPREME COURT PRECEDENTS:
{legal_context}

USER QUERY:
{payload.query}

INSTRUCTIONS & GUARDRAILS:
1. Do NOT use double asterisks (**) anywhere in your response. Use clean plain text, numbered lists, or indentations.
2. Identify the specific contract clause (with page and section).
3. State the governing Indian statutory rule (e.g. Section 27, Indian Contract Act, 1872).
4. Cite the relevant Supreme Court precedent (e.g. Percept D'Mark v. Zaheer Khan, Niranjan Shankar Golikari).
5. Provide a comparative legal analysis: Is the clause enforceable, void, or subject to exceptions?
6. State any judicial uncertainty, factual dependencies, or severability issues.
7. Conclude with a clear legal risk summary. State that this is for review and research, not licensed legal advice.
"""
        try:
            answer = await llm_router.generate_chat_completion(
                messages=[
                    {"role": "system", "content": "You are an elite Indian commercial contract lawyer. Output well-structured, grounded legal analysis without double asterisks (**)."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
        except Exception as e:
            logger.warning(f"LLM hybrid chat completion failed: {e}. Using deterministic legal analysis.")
    else:
        # High quality offline fallback for non-compete / restraint of trade & commercial clauses
        top_c = top_contract_chunks[0] if top_contract_chunks else {"page_number": 1, "content": "Restraint clause in contract."}
        top_l = legal_hits[0] if legal_hits else {"act_name": "Indian Contract Act", "section_number": "Section 27", "content": "Agreement in restraint of trade void."}

        answer = f"""### Hybrid Contract & Indian Law Compliance Review

1. Contract Clause Identified (Page {top_c.get('page_number', 1)}):
> "{top_c['content'][:250]}..."

2. Governing Indian Statutory Provision:
Under {top_l.get('act_name', 'Indian Contract Act, 1872')} ({top_l.get('section_number', 'Section 27')}):
> "{top_l.get('content', '')[:300]}..."

3. Judicial Precedent & Enforceability Assessment:
- Post-Employment Restraints: In Percept D'Mark (India) Pvt. Ltd. v. Zaheer Khan (2006), the Supreme Court affirmed that post-termination non-compete covenants are completely void under Section 27. The common law doctrine of 'reasonable restraint' does not apply in India.
- Exceptions: Negative covenants are only protected during the term of employment (Niranjan Shankar Golikari, 1967) or under the narrow statutory exception for the sale of goodwill.
- Risk Assessment: HIGH ENFORCEABILITY RISK. This restrictive covenant is likely void and unenforceable in an Indian court."""

    return ChatQueryResponse(
        answer=strip_markdown_bold(answer),
        mode_used="HYBRID",
        citations=contract_citations,
        legal_citations=legal_citations,
        risk_assessment={
            "status": "COMPLETED",
            "enforceability_concern": "HIGH" if "non-compete" in payload.query.lower() or "restraint" in payload.query.lower() else "MEDIUM",
            "statute_consulted": "Indian Contract Act, 1872"
        }
    )
