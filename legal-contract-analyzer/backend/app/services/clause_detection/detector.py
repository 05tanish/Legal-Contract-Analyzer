import os
import re
import string
import logging
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)

def preprocess_text(text: str) -> str:
    """Cleans legal text matching CUAD ML training logic."""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'<[^>]+>', '', text)
    text = text.translate(str.maketrans(string.punctuation, ' ' * len(string.punctuation)))
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# Mapping of CUAD category identifiers to human-readable names and risk profiles
CATEGORY_METADATA = {
    "cap_on_liability": {
        "title": "Cap on Liability",
        "severity": "HIGH",
        "description": "Sets a monetary maximum on liability for breaches."
    },
    "uncapped_liability": {
        "title": "Uncapped Liability",
        "severity": "CRITICAL",
        "description": "Exposes parties to unlimited damages without financial ceiling."
    },
    "governing_law": {
        "title": "Governing Law & Jurisdiction",
        "severity": "MEDIUM",
        "description": "Specifies governing statutory framework and competent courts."
    },
    "non_compete": {
        "title": "Non-Compete / Restraint of Trade",
        "severity": "CRITICAL",
        "description": "Restricts commercial or employment activities (void under Section 27 Indian Contract Act)."
    },
    "termination_for_convenience": {
        "title": "Termination for Convenience",
        "severity": "MEDIUM",
        "description": "Allows unilateral cancellation of the contract without breach."
    },
    "liquidated_damages": {
        "title": "Liquidated Damages / Penalty",
        "severity": "HIGH",
        "description": "Pre-estimates contractual damages (governed by Section 74 Indian Contract Act)."
    },
    "ip_ownership_assignment": {
        "title": "Intellectual Property Assignment",
        "severity": "HIGH",
        "description": "Transfers ownership rights of created works or patents."
    },
    "anti_assignment": {
        "title": "Anti-Assignment Clause",
        "severity": "LOW",
        "description": "Prohibits delegation or transfer of contract rights without prior written consent."
    },
    "audit_rights": {
        "title": "Audit & Inspection Rights",
        "severity": "MEDIUM",
        "description": "Grants rights to inspect books, facilities, or records."
    },
    "no_solicit_of_employees": {
        "title": "Non-Solicitation of Personnel",
        "severity": "MEDIUM",
        "description": "Restricts recruitment of employees or contractors."
    },
    "notice_period_to_terminate_renewal": {
        "title": "Notice Period for Renewal / Termination",
        "severity": "MEDIUM",
        "description": "Mandatory prior notice timeline before termination or renewal."
    },
    "confidentiality": {
        "title": "Confidential Information & Non-Disclosure",
        "severity": "MEDIUM",
        "description": "Obligations to maintain confidentiality of proprietary assets."
    },
    "indemnity": {
        "title": "Indemnification & Hold Harmless",
        "severity": "HIGH",
        "description": "Compensates for losses, liabilities, and legal defense costs."
    },
    "dispute_resolution": {
        "title": "Dispute Resolution & Arbitration",
        "severity": "MEDIUM",
        "description": "Establishes mediation, conciliation, or arbitration procedures."
    }
}

# Rule-based fallback keywords for zero-shot clause identification
HEURISTIC_PATTERNS = {
    "non_compete": re.compile(r'\b(restraint of trade|non[- ]compete|covenant not to compete|shall not engage in any competing)\b', re.IGNORECASE),
    "cap_on_liability": re.compile(r'\b(aggregate liability shall not exceed|limitation of liability|maximum liability|cap on liability)\b', re.IGNORECASE),
    "uncapped_liability": re.compile(r'\b(unlimited liability|no limitation of liability shall apply|uncapped liability)\b', re.IGNORECASE),
    "indemnity": re.compile(r'\b(indemnify|hold harmless|defend and hold harmless|indemnification)\b', re.IGNORECASE),
    "confidentiality": re.compile(r'\b(confidential information|non[- ]disclosure|proprietary information|keep secret)\b', re.IGNORECASE),
    "governing_law": re.compile(r'\b(governed by the laws of|jurisdiction of the courts of|governing law)\b', re.IGNORECASE),
    "termination_for_convenience": re.compile(r'\b(terminate this agreement for any reason|terminate without cause|termination for convenience)\b', re.IGNORECASE),
    "liquidated_damages": re.compile(r'\b(liquidated damages|agreed sum of damages|penalty for delay)\b', re.IGNORECASE),
    "ip_ownership_assignment": re.compile(r'\b(intellectual property rights|work made for hire|assigns all right, title and interest)\b', re.IGNORECASE),
    "dispute_resolution": re.compile(r'\b(arbitration and conciliation act|arbitration|dispute resolution|amicable settlement)\b', re.IGNORECASE),
}

class LightweightClauseDetector:
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.categories = None
        self._is_loaded = False
        self._load_model()

    def _load_model(self):
        """Attempts to load pre-trained CUAD model artifacts."""
        try:
            import joblib
            candidate_dirs = [
                os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../legal-contract-analyzer/models")),
                os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../models")),
                os.path.abspath(os.path.join(os.path.dirname(__file__), "../../models")),
            ]
            for c_dir in candidate_dirs:
                model_p = os.path.join(c_dir, "best_model.joblib")
                vec_p = os.path.join(c_dir, "tfidf_vectorizer.joblib")
                cat_p = os.path.join(c_dir, "clause_categories.joblib")
                if os.path.exists(model_p) and os.path.exists(vec_p) and os.path.exists(cat_p):
                    self.model = joblib.load(model_p)
                    self.vectorizer = joblib.load(vec_p)
                    cats_data = joblib.load(cat_p)
                    if hasattr(cats_data, "classes_"):
                        self.categories = cats_data.classes_
                    elif isinstance(cats_data, (list, np.ndarray)):
                        self.categories = np.array(cats_data)
                    self._is_loaded = True
                    logger.info(f"Loaded CUAD clause detector from {c_dir}")
                    return
        except Exception as e:
            logger.warning(f"Note: Could not load joblib clause model ({e}). Using heuristic detector.")
            self._is_loaded = False

    def detect_clauses_in_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fast, lightweight clause identification over document chunks.
        Suitable for Guest users without executing full LangGraph multi-agent redlining.
        """
        if not chunks:
            return []

        results = []
        seen_keys = set()

        # 1. Try ML model if loaded
        if self._is_loaded and self.model is not None and self.vectorizer is not None:
            try:
                raw_texts = [c.get("content", "") for c in chunks]
                cleaned = [preprocess_text(t) for t in raw_texts]
                X = self.vectorizer.transform(cleaned)

                predictions_matrix = None
                if hasattr(self.model, "decision_function"):
                    scores = self.model.decision_function(X)
                    predictions_matrix = scores > 0
                elif hasattr(self.model, "predict_proba"):
                    probas = self.model.predict_proba(X)
                    if isinstance(probas, list):
                        predictions_matrix = np.array([p[:, 1] for p in probas]).T >= 0.45
                    else:
                        predictions_matrix = probas >= 0.45
                else:
                    predictions_matrix = self.model.predict(X)

                for i, chunk in enumerate(chunks):
                    row_mask = np.array(predictions_matrix[i], dtype=bool)
                    detected_cats = self.categories[row_mask].tolist() if self.categories is not None else []
                    
                    for raw_cat in detected_cats:
                        meta = CATEGORY_METADATA.get(raw_cat, {
                            "title": raw_cat.replace("_", " ").title(),
                            "severity": "MEDIUM",
                            "description": f"Standard {raw_cat.replace('_', ' ')} provision."
                        })
                        snippet = chunk.get("content", "")[:250].strip() + ("..." if len(chunk.get("content", "")) > 250 else "")
                        dedup_key = (chunk.get("page_number", 1), raw_cat)
                        if dedup_key not in seen_keys:
                            seen_keys.add(dedup_key)
                            results.append({
                                "category_id": raw_cat,
                                "category_title": meta["title"],
                                "severity": meta["severity"],
                                "description": meta["description"],
                                "page_number": chunk.get("page_number", 1),
                                "section_title": chunk.get("section_title") or f"Page {chunk.get('page_number', 1)} Clause",
                                "snippet": snippet,
                                "method": "CUAD_ML"
                            })
            except Exception as e:
                logger.warning(f"CUAD inference encountered error: {e}. Falling back to heuristics.")

        # 2. Heuristic supplement / fallback to guarantee comprehensive coverage
        for chunk in chunks:
            content = chunk.get("content", "")
            for raw_cat, pattern in HEURISTIC_PATTERNS.items():
                match = pattern.search(content)
                if match:
                    dedup_key = (chunk.get("page_number", 1), raw_cat)
                    if dedup_key not in seen_keys:
                        seen_keys.add(dedup_key)
                        meta = CATEGORY_METADATA.get(raw_cat, {
                            "title": raw_cat.replace("_", " ").title(),
                            "severity": "MEDIUM",
                            "description": f"Standard {raw_cat.replace('_', ' ')} provision."
                        })
                        start = max(0, match.start() - 40)
                        end = min(len(content), match.end() + 180)
                        snippet = ("..." if start > 0 else "") + content[start:end].strip() + ("..." if end < len(content) else "")
                        results.append({
                            "category_id": raw_cat,
                            "category_title": meta["title"],
                            "severity": meta["severity"],
                            "description": meta["description"],
                            "page_number": chunk.get("page_number", 1),
                            "section_title": chunk.get("section_title") or f"Page {chunk.get('page_number', 1)} Clause",
                            "snippet": snippet,
                            "method": "HEURISTIC"
                        })

        # Sort results by page number then severity (CRITICAL, HIGH, MEDIUM, LOW)
        severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        results.sort(key=lambda x: (x.get("page_number", 1), severity_rank.get(x.get("severity", "MEDIUM"), 2)))
        return results

clause_detector = LightweightClauseDetector()

