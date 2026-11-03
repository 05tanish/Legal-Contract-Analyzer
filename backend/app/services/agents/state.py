from typing import TypedDict, List, Dict, Any, Optional
from app.schemas.audit import ExtractedFinding

class ContractAuditState(TypedDict):
    contract_id: str
    contract_text: str
    contract_type: str
    playbook_name: str
    playbook_rules: List[Dict[str, Any]]
    all_chunks: List[Dict[str, Any]]
    parent_chunks_map: Dict[str, str] # parent_id -> full parent text
    retrieved_contexts: Dict[str, List[Dict[str, Any]]] # rule_category -> list of reranked chunks
    legal_contexts: Optional[Dict[str, List[Dict[str, Any]]]] # rule_category -> matching Indian Acts/Cases
    extracted_findings: List[ExtractedFinding]
    verified_findings: List[Dict[str, Any]]
    overall_risk_score: float
    risk_level: str
    executive_summary: str
    query_mode: Optional[str] # CONTRACT_ONLY, LEGAL_ONLY, HYBRID
    error: Optional[str]
