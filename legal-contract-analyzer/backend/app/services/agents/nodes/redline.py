from app.services.agents.state import ContractAuditState
import logging

logger = logging.getLogger(__name__)

async def redline_node(state: ContractAuditState):
    """
    Synthesizes overall contract risk, generates executive review summary,
    and formats negotiation redline recommendations.
    """
    findings = state.get("verified_findings", [])
    
    # Severity weight scoring
    weights = {
        "CRITICAL": 35.0,
        "HIGH": 20.0,
        "MEDIUM": 10.0,
        "LOW": 5.0,
        "ACCEPTABLE": 0.0
    }

    raw_score = 0.0
    critical_count = 0
    high_count = 0

    for f in findings:
        sev = f.get("severity", "LOW").upper()
        raw_score += weights.get(sev, 5.0)
        if sev == "CRITICAL":
            critical_count += 1
        elif sev == "HIGH":
            high_count += 1

    overall_score = min(100.0, round(raw_score, 1))

    # Risk level classification
    if overall_score >= 60.0 or critical_count > 0:
        risk_level = "CRITICAL"
    elif overall_score >= 35.0 or high_count > 0:
        risk_level = "HIGH"
    elif overall_score >= 15.0:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # Executive Summary Generation
    summary_parts = [
        f"Contract audit completed against the '{state.get('playbook_name', 'Standard Playbook')}' benchmark.",
        f"Overall Risk Assessment: {risk_level} (Score: {overall_score}/100).",
        f"Detected {critical_count} Critical, {high_count} High-risk deviations requiring legal redlines."
    ]

    actionable_findings = [f for f in findings if f.get("severity") in ("CRITICAL", "HIGH")]
    if actionable_findings:
        summary_parts.append("\nTop Key Action Items for Negotiation:")
        for idx, af in enumerate(actionable_findings[:3], start=1):
            summary_parts.append(f"{idx}. {af.get('clause_category')}: {af.get('deviation_explanation')} (Page {af.get('page_number')})")

    executive_summary = "\n".join(summary_parts)

    return {
        "overall_risk_score": overall_score,
        "risk_level": risk_level,
        "executive_summary": executive_summary
    }

