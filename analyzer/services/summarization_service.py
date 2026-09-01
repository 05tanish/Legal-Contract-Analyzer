import re

LEGAL_KEYWORDS = {
    'agreement', 'party', 'parties', 'employee', 'employer', 'payment', 
    'compensation', 'term', 'renewal', 'termination', 'notice', 
    'confidentiality', 'non-compete', 'non-solicitation', 'intellectual property', 
    'license', 'ownership', 'liability', 'indemnification', 'insurance', 
    'governing law', 'jurisdiction', 'arbitration', 'dispute', 'audit', 
    'exclusivity', 'assignment', 'warranty', 'representation', 'shall', 'may',
    'provided', 'subject to', 'unless', 'except'
}

def score_sentence(sentence, detected_clauses_in_chunk):
    """
    Scores a sentence based on legal keywords and if it belongs to a chunk that triggered a clause.
    """
    score = 0
    words = set(re.findall(r'\b\w+\b', sentence.lower()))
    
    # Keyword overlap
    overlap = words.intersection(LEGAL_KEYWORDS)
    score += len(overlap)
    
    # Boost if chunk had a detected clause
    if detected_clauses_in_chunk:
        score += 2 * len(detected_clauses_in_chunk)
        
    # Penalty for very short or very long sentences
    if len(words) < 5 or len(words) > 100:
        score -= 2
        
    return score

def generate_summary(chunks_with_predictions, aggregated_clauses):
    """
    Generates deterministic extractive summary and categorized points.
    Returns a dictionary matching the ContractSummary model structure.
    """
    summary_data = {
        "overview": "",
        "contract_type": "",
        "parties": [],
        "key_obligations": [],
        "key_restrictions": [],
        "payment_terms": [],
        "term_and_renewal": [],
        "termination_terms": [],
        "confidentiality_terms": [],
        "intellectual_property_terms": [],
        "liability_terms": [],
        "insurance_terms": [],
        "governing_law_terms": [],
        "important_dates": [],
        "notable_risks": [],
        "missing_or_unclear_items": [],
        "evidence_links": [] # list of dicts for SummaryEvidence
    }
    
    # 1. Extractive Overview (Top 3 highest scoring sentences globally)
    all_sentences = []
    for chunk in chunks_with_predictions:
        text = chunk['text']
        page = chunk['page']
        detected = chunk.get('detected_clauses', [])
        
        # Split chunk into sentences safely
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for s in sentences:
            s_clean = s.strip()
            if s_clean:
                all_sentences.append({
                    "text": s_clean,
                    "page": page,
                    "score": score_sentence(s_clean, detected),
                    "chunk_detected": detected
                })
                
    # Sort by score descending
    all_sentences.sort(key=lambda x: x['score'], reverse=True)
    
    top_overview = all_sentences[:3]
    summary_data["overview"] = " ".join([s['text'] for s in top_overview])
    
    # 2. Map aggregated clauses to specific categories
    # This uses the ML model's output to construct the structured summary
    
    def add_to_category(category_key, section_name, clause_keys):
        found = False
        for c_key in clause_keys:
            if c_key in aggregated_clauses:
                found = True
                c_data = aggregated_clauses[c_key]
                # Add to json field
                summary_data[category_key].append(c_data['display_name'])
                # Add to evidence
                if c_data['evidence']:
                    top_ev = c_data['evidence'][0]
                    summary_data["evidence_links"].append({
                        "section_name": section_name,
                        "page_number": top_ev['page'],
                        "text": top_ev['text'],
                        "score": c_data['risk_weight']
                    })
        if not found:
            summary_data["missing_or_unclear_items"].append(f"{section_name} not clearly identified in the extracted text.")
            
    # Contract Type / Name
    if "document_name" in aggregated_clauses:
        ev = aggregated_clauses["document_name"]["evidence"]
        if ev:
            summary_data["contract_type"] = ev[0]["text"][:200]
    else:
        summary_data["contract_type"] = "Not clearly identified in the extracted text."
        
    # Parties
    add_to_category("parties", "Parties", ["parties"])
    
    # Key Obligations / Restrictions
    add_to_category("key_restrictions", "Restrictions", ["non_compete", "exclusivity", "no_solicit_of_customers", "no_solicit_of_employees", "non_disparagement", "anti_assignment", "price_restrictions", "volume_restriction"])
    add_to_category("key_obligations", "Obligations", ["minimum_commitment", "audit_rights", "post_termination_services"])
    
    # Payments
    add_to_category("payment_terms", "Payment and Compensation", ["revenue_profit_sharing"])
    
    # Term & Dates
    add_to_category("term_and_renewal", "Term and Renewal", ["renewal_term"])
    add_to_category("important_dates", "Important Dates", ["agreement_date", "effective_date", "expiration_date"])
    
    # Termination
    add_to_category("termination_terms", "Termination", ["termination_for_convenience", "notice_period_to_terminate_renewal"])
    
    # IP
    add_to_category("intellectual_property_terms", "Intellectual Property", ["ip_ownership_assignment", "joint_ip_ownership", "license_grant", "source_code_escrow"])
    
    # Liability
    add_to_category("liability_terms", "Liability and Indemnification", ["uncapped_liability", "cap_on_liability", "liquidated_damages", "warranty_duration"])
    
    # Insurance
    add_to_category("insurance_terms", "Insurance", ["insurance"])
    
    # Governing Law
    add_to_category("governing_law_terms", "Governing Law and Disputes", ["governing_law"])
    
    # Notable Risks
    high_risks = [c_data['display_name'] for c_key, c_data in aggregated_clauses.items() if c_data['risk_level'] == "High"]
    summary_data["notable_risks"] = high_risks if high_risks else ["No High-risk clauses detected."]

    return summary_data
