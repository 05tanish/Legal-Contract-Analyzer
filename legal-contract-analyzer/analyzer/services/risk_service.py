import os
import joblib
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# Fallback heuristic risk configuration if risk_config.joblib isn't found
DEFAULT_RISK_WEIGHTS = {
    "non_compete": 3.0,
    "exclusivity": 3.0,
    "uncapped_liability": 4.0,
    "irrevocable_or_perpetual_license": 4.0,
    "termination_for_convenience": 2.0,
    "cap_on_liability": 1.0,
    "audit_rights": 1.0,
    "insurance": 1.0,
    "no_solicit_of_customers": 3.0,
    "no_solicit_of_employees": 3.0,
    "liquidated_damages": 3.0,
    "warranty_duration": 2.0,
}

def get_risk_weights():
    try:
        path = os.path.join(settings.BASE_DIR, 'models', 'risk_config.joblib')
        if os.path.exists(path):
            return joblib.load(path)
    except Exception as e:
        logger.warning(f"Could not load risk_config.joblib, falling back to defaults: {e}")
    return DEFAULT_RISK_WEIGHTS

def get_risk_level(score):
    if score <= 3:
        return "Low"
    elif score <= 7:
        return "Medium"
    else:
        return "High"

def aggregate_clauses_and_calculate_risk(chunks_with_predictions):
    """
    Takes chunks with 'detected_clauses': ['non_compete', ...]
    Aggregates them so each clause appears once, with a list of pages and evidence.
    Returns: (total_risk_score, risk_level, aggregated_dict)
    
    aggregated_dict format:
    {
        "non_compete": {
            "display_name": "Non Compete",
            "risk_weight": 3.0,
            "risk_level": "Medium",
            "pages": [1, 2],
            "evidence": [
                {"page": 1, "text": "...", "score": None},
                ...
            ]
        }
    }
    """
    risk_weights = get_risk_weights()
    aggregated = {}
    
    for chunk in chunks_with_predictions:
        page = chunk['page']
        text = chunk['text']
        detected = chunk.get('detected_clauses', [])
        
        for clause in detected:
            if clause not in aggregated:
                weight = float(risk_weights.get(clause, 0.0))
                
                # Heuristic formatting for display name
                display_name = clause.replace("_", " ").title()
                
                # Clause-level risk level
                if weight == 0:
                    c_level = "Informational"
                elif weight <= 1.5:
                    c_level = "Low"
                elif weight <= 2.5:
                    c_level = "Medium"
                else:
                    c_level = "High"
                    
                aggregated[clause] = {
                    "display_name": display_name,
                    "risk_weight": weight,
                    "risk_level": c_level,
                    "pages": set(),
                    "evidence": []
                }
            
            aggregated[clause]['pages'].add(page)
            # Store top 3 evidence chunks
            if len(aggregated[clause]['evidence']) < 3:
                # To prevent duplicates if text is exactly identical (rare but possible in bad PDFs)
                if not any(e['text'] == text for e in aggregated[clause]['evidence']):
                    aggregated[clause]['evidence'].append({
                        "page": page,
                        "text": text,
                        "score": None
                    })
    
    # Calculate total risk score based ONLY on unique clauses present, not occurrence count
    total_score = sum([c_data['risk_weight'] for c_data in aggregated.values()])
    
    # Convert sets to sorted lists for JSON serialization
    for c_data in aggregated.values():
        c_data['pages'] = sorted(list(c_data['pages']))
        
    return total_score, get_risk_level(total_score), aggregated
