from app.services.agents.state import ContractAuditState
from app.schemas.audit import ExtractedFinding, AuditAnalysisResult
from app.core.llm_router import llm_router
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

async def extractor_node(state: ContractAuditState):
    """
    Structured extraction node using Instructor with Pydantic schema validation.
    Extracts deviations from the playbook with character-exact quotes and page citations.
    """
    rules = state.get("playbook_rules", [])
    retrieved_contexts = state.get("retrieved_contexts", {})
    extracted_findings = []

    # Check if real LLM API keys are active
    has_api_keys = bool(settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-your")) or bool(settings.ANTHROPIC_API_KEY)

    if has_api_keys:
        try:
            client, model_name = llm_router.get_structured_client()

            for rule in rules:
                category = rule.get("category", "")
                chunks = retrieved_contexts.get(category, [])
                if not chunks:
                    continue

                context_blocks = "\n\n".join([
                    f"[Page {c['page_number']} | Section: {c.get('section_title', 'General')}]:\n{c.get('parent_full_text', c['content'])}"
                    for c in chunks
                ])

                prompt = f"""You are a Senior Corporate Legal Counsel auditing a contract against our corporate playbook.
Rule Category: {category}
Our Standard Requirement: {rule.get('standard_requirement')}
Unacceptable Trigger Terms: {rule.get('unacceptable_triggers')}
Default Severity if Violated: {rule.get('severity_if_violated')}

Review the contract excerpts below. If there is a violation or deviation, extract it strictly using the schema.
You MUST provide an exact VERBATIM quote from the text. Do not paraphrase the quoted text.
If the contract is compliant or silent, mark severity as 'ACCEPTABLE' or 'LOW'.

Contract Excerpts:
{context_blocks}
"""

                finding = await client.chat.completions.create(
                    model=model_name,
                    response_model=ExtractedFinding,
                    messages=[
                        {"role": "system", "content": "You are a precise corporate legal compliance auditor. Output strictly formatted JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1
                )
                extracted_findings.append(finding)

        except Exception as e:
            logger.warning(f"LLM extraction error: {e}. Falling back to rule-based extractor.")
            has_api_keys = False

    if not has_api_keys:
        # High-precision deterministic fallback rule engine (preserves CUAD logic)
        for rule in rules:
            category = rule.get("category", "")
            chunks = retrieved_contexts.get(category, [])
            triggers = [t.lower() for t in rule.get("unacceptable_triggers", [])]
            
            matched_chunk = None
            matched_trigger = None

            for c in chunks:
                text_lower = c["content"].lower()
                for tr in triggers:
                    if tr in text_lower:
                        matched_chunk = c
                        matched_trigger = tr
                        break
                if matched_chunk:
                    break

            if matched_chunk:
                extracted_findings.append(ExtractedFinding(
                    clause_category=category,
                    severity=rule.get("severity_if_violated", "HIGH"),
                    original_text=matched_chunk["content"][:300] + "...",
                    page_number=matched_chunk["page_number"],
                    section_reference=matched_chunk.get("section_title") or f"Page {matched_chunk['page_number']}",
                    playbook_rule=rule.get("standard_requirement", ""),
                    deviation_explanation=f"Contract contains non-standard language matching trigger: '{matched_trigger}'.",
                    proposed_redline=rule.get("fallback_recommendation", "Align with standard corporate playbook wording."),
                    confidence_score=0.92
                ))
            elif chunks:
                top_c = chunks[0]
                extracted_findings.append(ExtractedFinding(
                    clause_category=category,
                    severity="ACCEPTABLE",
                    original_text=top_c["content"][:200] + "...",
                    page_number=top_c["page_number"],
                    section_reference=top_c.get("section_title") or f"Page {top_c['page_number']}",
                    playbook_rule=rule.get("standard_requirement", ""),
                    deviation_explanation="Standard compliant clause identified.",
                    proposed_redline="No amendment required.",
                    confidence_score=0.88
                ))

    return {"extracted_findings": extracted_findings}

