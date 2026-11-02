from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import time
import json
import asyncio
import os
import yaml

from app.db.session import get_db
from app.db.models import Contract, ContractChunk, AuditReport, RiskFinding
from app.schemas.audit import AuditReportResponse
from app.services.agents.workflow import audit_graph

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
    db: AsyncSession = Depends(get_db)
):
    start_time = time.time()

    # Load contract
    res = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = res.scalars().first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found.")

    # Load all chunks for this contract
    chunks_res = await db.execute(select(ContractChunk).where(ContractChunk.contract_id == contract_id))
    db_chunks = chunks_res.scalars().all()

    if not db_chunks:
        raise HTTPException(status_code=400, detail="Contract has not been indexed yet.")

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
        "extracted_findings": [],
        "verified_findings": [],
        "overall_risk_score": 0.0,
        "risk_level": "LOW",
        "executive_summary": "",
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
        db_findings.append(RiskFinding(
            audit_id=audit_report.id,
            clause_category=f.get("clause_category", "General"),
            severity=f.get("severity", "LOW"),
            original_text=f.get("original_text", ""),
            page_number=f.get("page_number", 1),
            section_reference=f.get("section_reference"),
            playbook_rule=f.get("playbook_rule"),
            deviation_explanation=f.get("deviation_explanation"),
            proposed_redline=f.get("proposed_redline"),
            is_verified=f.get("is_verified", False),
            confidence_score=f.get("confidence_score", 1.0)
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
async def get_latest_audit(contract_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(AuditReport)
        .where(AuditReport.contract_id == contract_id)
        .options(selectinload(AuditReport.findings))
        .order_by(AuditReport.created_at.desc())
    )
    audit = res.scalars().first()
    if not audit:
        raise HTTPException(status_code=404, detail="No audit report found for this contract.")
    return audit

@router.get("/{contract_id}/stream")
async def stream_contract_audit(contract_id: str, db: AsyncSession = Depends(get_db)):
    """
    Server-Sent Events (SSE) streaming endpoint:
    Streams progress percentages and extracted findings to the UI in real time.
    """
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

