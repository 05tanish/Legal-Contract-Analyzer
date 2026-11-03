from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal
from datetime import date, datetime

class LegalSectionCitation(BaseModel):
    act_name: str
    section_number: str
    section_title: Optional[str] = None
    verbatim_text: str
    official_url: Optional[str] = None
    status: str = "CURRENT"

class CasePrecedentCitation(BaseModel):
    case_title: str
    neutral_citation: str
    standard_citation: Optional[str] = None
    court_name: str = "Supreme Court of India"
    judgment_date: Optional[str] = None
    ratio_decidendi: str
    official_url: Optional[str] = None

class LegalSearchRequest(BaseModel):
    query: str
    document_type: Optional[Literal["STATUTE_SECTION", "COURT_JUDGMENT", "ALL"]] = "ALL"
    act_name: Optional[str] = None
    top_k: int = 5

class LegalSearchHit(BaseModel):
    legal_id: str
    document_type: str
    title: str
    content: str
    score: float
    act_name: Optional[str] = None
    section_number: Optional[str] = None
    case_title: Optional[str] = None
    neutral_citation: Optional[str] = None
    ratio_decidendi: Optional[str] = None
    source_url: Optional[str] = None
    status: str = "CURRENT"

class LegalSearchResponse(BaseModel):
    query: str
    total_hits: int
    results: List[LegalSearchHit]

class LegalStatuteCreate(BaseModel):
    act_name: str
    act_year: int
    act_number: Optional[str] = None
    short_title: str
    jurisdiction: str = "Central"
    source_url: Optional[str] = None
    status: str = "CURRENT"

class LegalStatuteResponse(LegalStatuteCreate):
    id: str
    created_at: datetime
    sections_count: int = 0

    model_config = ConfigDict(from_attributes=True)

