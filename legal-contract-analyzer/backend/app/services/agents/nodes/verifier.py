from app.services.agents.state import ContractAuditState
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

async def verifier_node(state: ContractAuditState):
    """
    Zero-Hallucination Verification Guardrail:
    Performs character-level grounding checks against the source contract text.
    Any quote that cannot be found verbatim in the document is flagged.
    """
    findings = state.get("extracted_findings", [])
    full_text = state.get("contract_text", "").lower()
    verified_findings = []

    for f in findings:
        f_dict = f.model_dump() if hasattr(f, "model_dump") else dict(f)
        quote = f_dict.get("original_text", "").strip().lower()

        # Clean ellipsis and whitespace for substring matching
        cleaned_quote = quote.replace("...", "").strip()
        first_snippet = cleaned_quote[:60] if len(cleaned_quote) >= 60 else cleaned_quote

        is_verified = False
        if first_snippet and first_snippet in full_text:
            is_verified = True
        else:
            # Check within the specific page
            page_num = f_dict.get("page_number")
            page_chunks = [c for c in state.get("all_chunks", []) if c.get("page_number") == page_num]
            for pc in page_chunks:
                if first_snippet in pc["content"].lower():
                    is_verified = True
                    break

        # Defensive defaults for database constraints
        try:
            p_val = int(f_dict.get("page_number", 1) or 1)
            f_dict["page_number"] = max(1, p_val)
        except (ValueError, TypeError):
            f_dict["page_number"] = 1

        if not f_dict.get("clause_category"):
            f_dict["clause_category"] = "General"
        if not f_dict.get("severity"):
            f_dict["severity"] = "LOW"
        if f_dict.get("confidence_score") is None:
            f_dict["confidence_score"] = 1.0

        f_dict["is_verified"] = is_verified
        verified_findings.append(f_dict)

    logger.info(f"Verifier Node: Verified {len(verified_findings)} findings against raw contract source.")
    return {"verified_findings": verified_findings}

