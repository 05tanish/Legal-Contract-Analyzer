export type RiskSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'ACCEPTABLE';

export type QueryMode = 'CONTRACT_ONLY' | 'LEGAL_ONLY' | 'HYBRID';

export interface ClauseCitation {
  page_number: number;
  section_reference?: string;
  verbatim_text: string;
}

export interface LegalCitation {
  citation_type: 'STATUTE_SECTION' | 'COURT_JUDGMENT';
  act_name?: string;
  section_number?: string;
  section_title?: string;
  case_title?: string;
  neutral_citation?: string;
  court_name?: string;
  principle?: string;
  official_url?: string;
  status?: string;
}

export interface RiskFinding {
  id: string;
  clause_category: string;
  severity: RiskSeverity;
  original_text: string;
  page_number: number;
  section_reference?: string;
  playbook_rule?: string;
  deviation_explanation?: string;
  proposed_redline?: string;
  is_verified: boolean;
  confidence_score: number;
  legal_citations?: LegalCitation[];
}

export interface AuditReport {
  id: string;
  contract_id: string;
  playbook_id?: string;
  overall_risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  executive_summary?: string;
  status: string;
  latency_ms?: number;
  cost_usd?: number;
  created_at: string;
  findings: RiskFinding[];
}

export interface Contract {
  id: string;
  filename: string;
  file_size_bytes: number;
  total_pages: number;
  contract_type: string;
  status: 'PENDING' | 'PROCESSING' | 'READY' | 'FAILED';
  cloudinary_url?: string;
  cloudinary_public_id?: string;
  is_guest?: boolean;
  guest_session_id?: string;
  expires_at?: string;
  user_id?: string;
  error_message?: string;
  created_at: string;
  chunks_count?: number;
}

export interface DetectedClause {
  category_id: string;
  category_title: string;
  severity: RiskSeverity;
  description: string;
  page_number: number;
  section_title: string;
  snippet: string;
  method: 'CUAD_ML' | 'HEURISTIC';
}

export interface ClauseDetectionResponse {
  contract_id: string;
  filename: string;
  total_clauses_detected: number;
  is_guest: boolean;
  expires_at?: string;
  clauses: DetectedClause[];
}

export interface PlaybookRule {
  category: string;
  standard_requirement: string;
  unacceptable_triggers: string[];
  severity_if_violated: string;
  fallback_recommendation?: string;
}

export interface Playbook {
  id: string;
  name: string;
  description?: string;
  rules: PlaybookRule[];
  is_default: boolean;
}

export interface ChatQueryResponse {
  answer: string;
  mode_used: QueryMode;
  citations: ClauseCitation[];
  legal_citations: LegalCitation[];
  risk_assessment?: {
    status?: string;
    enforceability_concern?: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
    statute_consulted?: string;
  };
}

export interface LegalSearchHit {
  legal_id: string;
  document_type: string;
  title: string;
  content: string;
  score: number;
  act_name?: string;
  section_number?: string;
  case_title?: string;
  neutral_citation?: string;
  ratio_decidendi?: string;
  source_url?: string;
  status?: string;
}

export interface User {
  id: string;
  email: string;
  full_name?: string;
  avatar_url?: string;
  created_at?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

