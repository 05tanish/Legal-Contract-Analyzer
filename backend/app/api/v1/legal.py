from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.db.session import get_db
from app.db.models import LegalStatute, LegalSection, CourtJudgment
from app.schemas.legal import LegalSearchRequest, LegalSearchResponse, LegalSearchHit
from app.services.rag.legal_search import legal_search_engine
from scripts.seed_indian_law import seed_indian_legal_corpus

router = APIRouter()

@router.post("/search", response_model=LegalSearchResponse)
async def search_legal_corpus(
    payload: LegalSearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Search Indian Central Acts, Bare Act sections, and landmark Supreme Court decisions.
    """
    doc_type = None if payload.document_type == "ALL" else payload.document_type
    hits = await legal_search_engine.search(
        query=payload.query,
        db=db,
        top_k=payload.top_k,
        document_type=doc_type
    )

    results = [
        LegalSearchHit(
            legal_id=h.get("legal_id", ""),
            document_type=h.get("document_type", "STATUTE_SECTION"),
            title=h.get("title", ""),
            content=h.get("content", ""),
            score=round(h.get("fused_score", h.get("score", 0.0)), 4),
            act_name=h.get("act_name"),
            section_number=h.get("section_number"),
            case_title=h.get("case_title"),
            neutral_citation=h.get("neutral_citation"),
            ratio_decidendi=h.get("ratio_decidendi"),
            source_url=h.get("source_url"),
            status=h.get("status", "CURRENT")
        )
        for h in hits
    ]

    return LegalSearchResponse(
        query=payload.query,
        total_hits=len(results),
        results=results
    )

@router.get("/statutes")
async def list_statutes(db: AsyncSession = Depends(get_db)):
    """List all indexed Indian Acts (Bare Acts)."""
    res = await db.execute(select(LegalStatute).order_by(LegalStatute.act_year))
    statutes = res.scalars().all()
    return [
        {
            "id": s.id,
            "act_name": s.act_name,
            "act_year": s.act_year,
            "act_number": s.act_number,
            "short_title": s.short_title,
            "jurisdiction": s.jurisdiction,
            "source_url": s.source_url,
            "status": s.status
        }
        for s in statutes
    ]

@router.get("/statutes/{statute_id}/sections")
async def get_statute_sections(statute_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve all sections of a specific Indian Act."""
    res = await db.execute(select(LegalSection).where(LegalSection.statute_id == statute_id).order_by(LegalSection.section_number))
    sections = res.scalars().all()
    return [
        {
            "id": sec.id,
            "section_number": sec.section_number,
            "section_title": sec.section_title,
            "content": sec.content,
            "explanation_text": sec.explanation_text,
            "status": sec.status
        }
        for sec in sections
    ]

@router.get("/judgments")
async def list_judgments(db: AsyncSession = Depends(get_db)):
    """List all indexed landmark Supreme Court decisions."""
    res = await db.execute(select(CourtJudgment).order_by(CourtJudgment.judgment_date.desc()))
    judgments = res.scalars().all()
    return [
        {
            "id": j.id,
            "case_title": j.case_title,
            "neutral_citation": j.neutral_citation,
            "standard_citation": j.standard_citation,
            "court_name": j.court_name,
            "judgment_date": str(j.judgment_date),
            "headnote": j.headnote,
            "ratio_decidendi": j.ratio_decidendi,
            "source_url": j.source_url
        }
        for j in judgments
    ]

@router.post("/seed")
async def trigger_seed_corpus():
    """Admin endpoint to populate / re-seed the Indian Legal Corpus."""
    try:
        await seed_indian_legal_corpus()
        return {"status": "SUCCESS", "message": "Indian Legal Corpus seeded successfully into PostgreSQL and Qdrant."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Seeding failed: {str(e)}")

