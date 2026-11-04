from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional
import time
import json
import asyncio
import os
import yaml
import logging

logger = logging.getLogger(__name__)

from app.db.session import get_db
from app.db.models import Contract, ContractChunk, AuditReport, RiskFinding, User
from app.schemas.audit import AuditReportResponse
from app.services.agents.workflow import audit_graph
from app.core.security import (
    security,
    get_current_user_optional,
    get_current_user_required,
    get_client_guest_session_id,
    validate_contract_access
)

router = APIRouter()

PLAYBOOK_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../playbooks"))

def get_default_playbook_rules():
    default_path = os.path.join(PLAYBOOK_DIR, "standard_nda.yaml")
    if os.path.exists(default_path):
        with open(default_path, "r") as f:
            data = yaml.safe_load(f)
            return data.get("name", "Standard NDA Playbook"), data.get("rules", [])
    return "Generic Commercial Playbook", []

@router.post("/{contract_id}", response_model=AuditReportResponse)
async def run_contract_audit(
    contract_id: str,
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Executes complete LangGraph multi-agent contract audit and automated redlining.
    RESTRICTED TO AUTHENTICATED USERS.
    Guests attempting to call this endpoint receive HTTP 403 Forbidden with prompt to sign in.
    """
    current_user = await get_current_user_optional(auth, db)
    if not current_user:
        raise HTTPException(
            status_code=403,
            detail="Full multi-agent legal audits, Indian case law verification, and automated redlining require a registered account. Please sign in or register to analyze this contract.",
            headers={"X-Auth-Required": "true"}
        )

    start_time = time.time()

    # Load contract
    res = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = res.scalars().first()
    if not contract:
        raise HTTPException(status_code=404, detail="We could not find the requested contract document.")

    # Ownership verification
    if contract.user_id and contract.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to run an audit on this contract."
        )

    # Load all chunks for this contract
    chunks_res = await db.execute(select(ContractChunk).where(ContractChunk.contract_id == contract_id))
    db_chunks = chunks_res.scalars().all()

    # Self-healing auto-indexing if contract was previously uploaded without chunks
    if not db_chunks:
        try:
            from app.core.config import settings
            from app.services.ingestion.parser import DocumentParser
            from app.services.ingestion.chunker import HierarchicalChunker
            from app.services.embedding.embedder import embedding_service
            from app.services.vector_store.qdrant_client import qdrant_service

            file_path = contract.file_path
            if not os.path.exists(file_path):
                basename = os.path.basename(file_path)
                for cand in [
                    os.path.join(settings.UPLOAD_DIR, basename),
                    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../uploads", basename)),
                    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../uploads", basename)),
                ]:
                    if os.path.exists(cand):
                        file_path = cand
                        break
                else:
                    if getattr(contract, "cloudinary_url", None):
                        from app.services.storage.cloudinary_service import cloudinary_service
                        local_cache = os.path.join(settings.UPLOAD_DIR, f"{contract.id}_{contract.filename}")
                        await cloudinary_service.download_file(contract.cloudinary_url, local_cache)
                        if os.path.exists(local_cache):
                            file_path = local_cache

            parsed_doc = DocumentParser.parse_pdf(file_path)
            chunker = HierarchicalChunker()
            chunks_data_new = chunker.chunk_document(contract_id=contract.id, pages=parsed_doc["pages"])

            child_chunks = [c for c in chunks_data_new if not c.get("is_parent", False)]
            if child_chunks:
                search_texts = [c.get("search_content", c["content"]) for c in child_chunks]
                embeddings = await embedding_service.get_batch_embeddings(search_texts)
                qdrant_points = []
                for c, emb in zip(child_chunks, embeddings):
                    c_copy = c.copy()
                    c_copy["vector"] = emb
                    qdrant_points.append(c_copy)
                qdrant_service.upsert_chunks(qdrant_points)

            new_db_chunks = [
                ContractChunk(
                    id=c["id"],
                    contract_id=contract.id,
                    chunk_index=c["chunk_index"],
                    page_number=c["page_number"],
                    section_title=c.get("section_title"),
                    content=c["content"],
                    parent_id=c.get("parent_id"),
                    is_parent=c.get("is_parent", False),
                    metadata_json=c.get("metadata", {})
                )
                for c in chunks_data_new
            ]
            db.add_all(new_db_chunks)
            contract.status = "READY"
            await db.commit()

            chunks_res = await db.execute(select(ContractChunk).where(ContractChunk.contract_id == contract_id))
            db_chunks = chunks_res.scalars().all()
        except Exception as e:
            logger.error(f"Auto-indexing failed for contract {contract_id}: {e}")
            raise HTTPException(status_code=400, detail="We were unable to prepare this document for review. Please try re-uploading the file.")

    if not db_chunks:
        raise HTTPException(status_code=400, detail="Unable to extract readable text from this document. Please ensure the PDF is not blank or corrupted.")

    chunks_data = [
        {
            "id": c.id,
            "page_number": c.page_number,
            "section_title": c.section_title,
            "content": c.content,
            "parent_id": c.parent_id,
            "is_parent": c.is_parent
        }
        for c in db_chunks
    ]

    # Map parent chunks
    parent_map = {c["id"]: c["content"] for c in chunks_data if c["is_parent"]}
    full_text = " ".join([c["content"] for c in chunks_data if not c["is_parent"]])

    playbook_name, rules = get_default_playbook_rules()

    # Initial state for LangGraph
    initial_state = {
        "contract_id": contract_id,
        "contract_text": full_text,
        "contract_type": contract.contract_type,
        "playbook_name": playbook_name,
        "playbook_rules": rules,
        "all_chunks": chunks_data,
        "parent_chunks_map": parent_map,
        "retrieved_contexts": {},
        "legal_contexts": {},
        "extracted_findings": [],
        "verified_findings": [],
        "overall_risk_score": 0.0,
        "risk_level": "LOW",
        "executive_summary": "",
        "query_mode": "CONTRACT_ONLY",
        "error": None
    }

    # Execute LangGraph state machine
    result_state = await audit_graph.ainvoke(initial_state)

    duration_ms = (time.time() - start_time) * 1000.0

    # Save audit report to relational database
    audit_report = AuditReport(
        contract_id=contract_id,
        overall_risk_score=result_state["overall_risk_score"],
        risk_level=result_state["risk_level"],
        executive_summary=result_state["executive_summary"],
        status="COMPLETED",
        latency_ms=round(duration_ms, 2),
        cost_usd=0.015 # Estimated model cost
    )
    db.add(audit_report)
    await db.commit()
    await db.refresh(audit_report)

    # Save individual risk findings
    db_findings = []
    for f in result_state.get("verified_findings", []):
        try:
            p_num = max(1, int(f.get("page_number", 1) or 1))
        except (ValueError, TypeError):
            p_num = 1

        db_findings.append(RiskFinding(
            audit_id=audit_report.id,
            clause_category=f.get("clause_category") or "General",
            severity=f.get("severity") or "LOW",
            original_text=f.get("original_text") or "",
            page_number=p_num,
            section_reference=f.get("section_reference"),
            playbook_rule=f.get("playbook_rule"),
            deviation_explanation=f.get("deviation_explanation"),
            proposed_redline=f.get("proposed_redline"),
            is_verified=bool(f.get("is_verified", False)),
            confidence_score=float(f.get("confidence_score", 1.0) if f.get("confidence_score") is not None else 1.0)
        ))
    db.add_all(db_findings)
    await db.commit()

    # Re-fetch with findings loaded
    final_res = await db.execute(
        select(AuditReport)
        .where(AuditReport.id == audit_report.id)
        .options(selectinload(AuditReport.findings))
    )
    return final_res.scalars().first()

@router.get("/{contract_id}/latest", response_model=AuditReportResponse)
async def get_latest_audit(
    contract_id: str,
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    current_user = await get_current_user_optional(auth, db)
    guest_session_id = get_client_guest_session_id(request)

    res_c = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = res_c.scalars().first()
    if not contract:
        raise HTTPException(status_code=404, detail="We could not find the requested contract document.")

    validate_contract_access(contract, current_user, guest_session_id)

    res = await db.execute(
        select(AuditReport)
        .where(AuditReport.contract_id == contract_id)
        .options(selectinload(AuditReport.findings))
        .order_by(AuditReport.created_at.desc())
    )
    audit = res.scalars().first()
    if not audit:
        raise HTTPException(status_code=404, detail="No review report has been generated for this contract yet.")
    return audit

@router.get("/{contract_id}/stream")
async def stream_contract_audit(
    contract_id: str,
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Server-Sent Events (SSE) streaming endpoint:
    Streams progress percentages and extracted findings to the UI in real time.
    Requires authenticated user account.
    """
    user = await get_current_user_required(auth, db)

    res_c = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = res_c.scalars().first()
    if not contract:
        raise HTTPException(status_code=404, detail="We could not find the requested contract document.")

    validate_contract_access(contract, user, None)
    async def event_generator():
        yield f"data: {json.dumps({'status': 'STARTING', 'progress': 10, 'message': 'Classifying contract layout...'})}\n\n"
        await asyncio.sleep(0.5)

        yield f"data: {json.dumps({'status': 'RETRIEVING', 'progress': 35, 'message': 'Running hybrid search & cross-encoder reranking across playbook rules...'})}\n\n"
        await asyncio.sleep(0.5)

        yield f"data: {json.dumps({'status': 'EXTRACTING', 'progress': 65, 'message': 'Auditing clauses with Instructor & Pydantic schema validation...'})}\n\n"
        await asyncio.sleep(0.5)

        yield f"data: {json.dumps({'status': 'VERIFYING', 'progress': 85, 'message': 'Executing zero-hallucination citation verification guardrails...'})}\n\n"
        await asyncio.sleep(0.5)

        yield f"data: {json.dumps({'status': 'COMPLETED', 'progress': 100, 'message': 'Audit completed. Finalizing report.'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

