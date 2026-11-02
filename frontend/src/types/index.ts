export type RiskSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'ACCEPTABLE';

export interface ClauseCitation {
  page_number: number;
  section_reference?: string;
  verbatim_text: string;
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
  error_message?: string;
  created_at: string;
  chunks_count?: number;
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

