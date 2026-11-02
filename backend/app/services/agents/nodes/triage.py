from app.services.agents.state import ContractAuditState
import logging

logger = logging.getLogger(__name__)

async def triage_node(state: ContractAuditState) -> Dict_updates:
    """
    Analyzes document header / first page to classify contract type (NDA, SaaS, MSA, Vendor).
    """
    text_sample = state.get("contract_text", "")[:3000].lower()
    
    contract_type = "COMMERCIAL_AGREEMENT"
    if "non-disclosure" in text_sample or "confidentiality agreement" in text_sample or "nda" in text_sample:
        contract_type = "NDA"
    elif "master services agreement" in text_sample or "msa" in text_sample:
        contract_type = "MSA"
    elif "software as a service" in text_sample or "saas" in text_sample:
        contract_type = "SAAS"
    elif "employment agreement" in text_sample:
        contract_type = "EMPLOYMENT"

    logger.info(f"Triage Node: Identified contract {state['contract_id']} as {contract_type}")
    return {"contract_type": contract_type}

