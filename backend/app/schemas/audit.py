from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime

class ClauseCitation(BaseModel):
    page_number: int = Field(description="Page number where the text appears")
    section_reference: Optional[str] = Field(None, description="Section heading, e.g. 'Section 12.3'")
    verbatim_text: str = Field(description="Exact verbatim quote from the contract")

class LegalCitation(BaseModel):
    citation_type: Literal["STATUTE_SECTION", "COURT_JUDGMENT"] = "STATUTE_SECTION"
    act_name: Optional[str] = None
    section_number: Optional[str] = None
    section_title: Optional[str] = None
    case_title: Optional[str] = None
    neutral_citation: Optional[str] = None
    court_name: Optional[str] = "Supreme Court of India"
    principle: Optional[str] = None
    official_url: Optional[str] = None
    status: str = "CURRENT"

class ExtractedFinding(BaseModel):
    clause_category: str = Field(description="Category, e.g., 'Limitation of Liability', 'Non-Compete'")
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "ACCEPTABLE"]
    original_text: str = Field(description="Direct clause quote from the contract")
    page_number: int = Field(description="Page number")
    section_reference: Optional[str] = Field(None, description="Section heading if available")
    playbook_rule: str = Field(description="The standard corporate playbook requirement or Indian legal standard")
    deviation_explanation: str = Field(description="Why this clause deviates from corporate policy or Indian law")
    proposed_redline: str = Field(description="Proposed revised wording to mitigate risk")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    legal_citations: List[LegalCitation] = Field(default_factory=list, description="Referenced Indian Acts or Precedents")

class AuditAnalysisResult(BaseModel):
    executive_summary: str = Field(description="Overview of contract review and top risk exposures")
    overall_risk_score: float = Field(description="0 (Safe) to 100 (Extremely Risky)", ge=0.0, le=100.0)
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    findings: List[ExtractedFinding] = Field(default_factory=list)

class FindingResponse(BaseModel):
    id: str
    clause_category: str
    severity: str
    original_text: str
    page_number: int
    section_reference: Optional[str] = None
    playbook_rule: Optional[str] = None
    deviation_explanation: Optional[str] = None
    proposed_redline: Optional[str] = None
    is_verified: bool
    confidence_score: float

    model_config = ConfigDict(from_attributes=True)

class AuditReportResponse(BaseModel):
    id: str
    contract_id: str
    playbook_id: Optional[str] = None
    overall_risk_score: float
    risk_level: str
    executive_summary: Optional[str] = None
    status: str
    latency_ms: Optional[float] = None
    cost_usd: Optional[float] = None
    created_at: datetime
    findings: List[FindingResponse] = []

    model_config = ConfigDict(from_attributes=True)

class ChatQueryRequest(BaseModel):
    query: str
    contract_id: Optional[str] = None
    mode: Optional[Literal["CONTRACT_ONLY", "LEGAL_ONLY", "HYBRID"]] = None

class ChatQueryResponse(BaseModel):
    answer: str
    mode_used: str = "CONTRACT_ONLY"
    citations: List[ClauseCitation] = []
    legal_citations: List[LegalCitation] = []
    risk_assessment: Optional[Dict[str, Any]] = None
