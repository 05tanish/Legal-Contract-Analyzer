import {
  Contract,
  AuditReport,
  Playbook,
  ClauseCitation,
  ChatQueryResponse,
  QueryMode,
  LegalSearchHit,
  User,
  AuthResponse,
  ClauseDetectionResponse
} from '../types';

// Production configurable API base URL
const rawBase = (import.meta as any).env?.VITE_API_URL || '';
const API_BASE = rawBase ? `${rawBase.replace(/\/$/, '')}/api/v1` : '/api/v1';

const TOKEN_KEY = 'contractiq_auth_token';
const GUEST_SESSION_KEY = 'contractiq_guest_session_id';
const USER_KEY = 'contractiq_user';
const ACTIVE_CONTRACT_KEY = 'contractiq_active_contract';

export function getAuthToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setAuthToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeAuthToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  removeStoredUser();
}

export function getStoredUser(): User | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setStoredUser(user: User): void {
  try {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch {}
}

export function removeStoredUser(): void {
  localStorage.removeItem(USER_KEY);
}

export function getStoredActiveContract(): Contract | null {
  try {
    const raw = localStorage.getItem(ACTIVE_CONTRACT_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setStoredActiveContract(contract: Contract | null): void {
  try {
    if (contract) {
      localStorage.setItem(ACTIVE_CONTRACT_KEY, JSON.stringify(contract));
      localStorage.setItem('contractiq_selected_contract_id', contract.id);
    } else {
      localStorage.removeItem(ACTIVE_CONTRACT_KEY);
      localStorage.removeItem('contractiq_selected_contract_id');
    }
  } catch {}
}

export function getGuestSessionId(): string {
  let session = localStorage.getItem(GUEST_SESSION_KEY);
  if (!session) {
    session = 'gst_' + Math.random().toString(36).substring(2, 12) + '_' + Date.now();
    localStorage.setItem(GUEST_SESSION_KEY, session);
  }
  return session;
}

export function resetGuestSessionId(): string {
  const newSession = 'gst_' + Math.random().toString(36).substring(2, 12) + '_' + Date.now();
  localStorage.setItem(GUEST_SESSION_KEY, newSession);
  return newSession;
}

export function getHeaders(custom: Record<string, string> = {}): Record<string, string> {
  const headers: Record<string, string> = {
    'X-Guest-Session-ID': getGuestSessionId(),
    ...custom
  };
  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export async function loginUser(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Invalid credentials.' }));
    throw new Error(err.detail || 'Invalid email or password.');
  }
  const data: AuthResponse = await res.json();
  setAuthToken(data.access_token);
  if (data.user) {
    setStoredUser(data.user);
  }
  return data;
}

export async function registerUser(email: string, password: string, fullName?: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Registration failed.' }));
    throw new Error(err.detail || 'Could not complete registration.');
  }
  const data: AuthResponse = await res.json();
  setAuthToken(data.access_token);
  if (data.user) {
    setStoredUser(data.user);
  }
  return data;
}

export async function googleAuth(payload: {
  credential?: string;
  email?: string;
  full_name?: string;
  avatar_url?: string;
  google_id?: string;
}): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/auth/google`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Google sign-in failed.' }));
    throw new Error(err.detail || 'Unable to sign in with Google.');
  }
  const data: AuthResponse = await res.json();
  setAuthToken(data.access_token);
  if (data.user) {
    setStoredUser(data.user);
  }
  return data;
}

export async function fetchCurrentUser(): Promise<User | null> {
  const token = getAuthToken();
  if (!token) {
    removeStoredUser();
    return null;
  }
  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: getHeaders(),
    });
    // ONLY clear auth if backend explicitly returns 401 Unauthorized
    if (res.status === 401) {
      removeAuthToken();
      return null;
    }
    if (!res.ok) {
      // Temporary network or server glitch: preserve existing cached user session
      return getStoredUser();
    }
    const user = await res.json();
    setStoredUser(user);
    return user;
  } catch {
    // Connection latency or offline: do not wipe session
    return getStoredUser();
  }
}

export async function checkBackendHealth(): Promise<{ status: string; environment?: string }> {
  const root = rawBase ? rawBase.replace(/\/$/, '') : '';
  const res = await fetch(`${root}/health`);
  if (!res.ok) throw new Error('Service is temporarily unavailable. Please try again shortly.');
  return res.json();
}

export async function fetchContracts(): Promise<Contract[]> {
  const res = await fetch(`${API_BASE}/contracts`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error('Could not load contracts. Please refresh the page.');
  return res.json();
}

export async function uploadContract(file: File): Promise<Contract> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/contracts/upload`, {
    method: 'POST',
    headers: {
      'X-Guest-Session-ID': getGuestSessionId(),
      ...(getAuthToken() ? { 'Authorization': `Bearer ${getAuthToken()}` } : {})
    },
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'We were unable to process this document. Please try again.' }));
    throw new Error(err.detail || 'We were unable to process this document. Please try again.');
  }
  return res.json();
}

export async function fetchContract(contractId: string): Promise<Contract> {
  const res = await fetch(`${API_BASE}/contracts/${contractId}`, {
    headers: getHeaders(),
  });
  if (res.status === 410) {
    throw new Error('This temporary guest document has expired and was cleaned up. Please upload a new contract.');
  }
  if (!res.ok) throw new Error('Could not find the requested contract.');
  return res.json();
}

export async function deleteContract(contractId: string): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${API_BASE}/contracts/${contractId}`, {
    method: 'DELETE',
    headers: getHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to delete contract.' }));
    throw new Error(err.detail || 'Failed to delete contract.');
  }
  return res.json();
}

export async function detectClauses(contractId: string): Promise<ClauseDetectionResponse> {
  const res = await fetch(`${API_BASE}/contracts/${contractId}/detect-clauses`, {
    method: 'POST',
    headers: getHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Could not detect clauses.' }));
    throw new Error(err.detail || 'Could not detect clauses for this document.');
  }
  return res.json();
}

export async function reindexContract(contractId: string): Promise<Contract> {
  const res = await fetch(`${API_BASE}/contracts/${contractId}/reindex`, {
    method: 'POST',
    headers: getHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Could not refresh document. Please try again.' }));
    throw new Error(err.detail || 'Could not refresh document. Please try again.');
  }
  return res.json();
}

export async function runAudit(contractId: string): Promise<AuditReport> {
  const res = await fetch(`${API_BASE}/audit/${contractId}`, {
    method: 'POST',
    headers: getHeaders(),
  });
  if (res.status === 403) {
    const err = await res.json().catch(() => ({}));
    const error: any = new Error(err.detail || 'Sign-in is required to run a full legal review.');
    error.code = 'AUTH_REQUIRED';
    throw error;
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unable to analyze contract. Please try again.' }));
    throw new Error(err.detail || 'Unable to analyze this contract right now. Please try again.');
  }
  return res.json();
}

export async function fetchLatestAudit(contractId: string): Promise<AuditReport | null> {
  const res = await fetch(`${API_BASE}/audit/${contractId}/latest`, {
    headers: getHeaders(),
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error('Could not retrieve analysis report.');
  return res.json();
}

export async function fetchPlaybooks(): Promise<Playbook[]> {
  const res = await fetch(`${API_BASE}/playbooks`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error('Could not load review rules.');
  return res.json();
}

export async function askLegalPlatform(
  query: string,
  contractId?: string,
  mode?: QueryMode
): Promise<ChatQueryResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      query,
      contract_id: contractId || null,
      mode: mode || null
    }),
  });
  if (res.status === 403) {
    const err = await res.json().catch(() => ({}));
    const error: any = new Error(err.detail || 'Sign-in required for AI Legal Copilot.');
    error.code = 'AUTH_REQUIRED';
    throw error;
  }
  if (!res.ok) throw new Error('Unable to answer right now. Please try asking again.');
  return res.json();
}

export async function askContract(
  contractId: string,
  query: string
): Promise<{ answer: string; citations: ClauseCitation[] }> {
  const res = await askLegalPlatform(query, contractId, 'CONTRACT_ONLY');
  return {
    answer: res.answer,
    citations: res.citations
  };
}

export async function searchLegalCorpus(query: string, docType: string = 'ALL'): Promise<{ query: string; total_hits: number; results: LegalSearchHit[] }> {
  const res = await fetch(`${API_BASE}/legal/search`, {
    method: 'POST',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ query, document_type: docType, top_k: 5 }),
  });
  if (!res.ok) throw new Error('Search failed. Please try a different query.');
  return res.json();
}

export function getPdfUrl(contractId: string): string {
  const token = getAuthToken();
  const guestSession = getGuestSessionId();
  const params = new URLSearchParams();
  if (token) params.set('token', token);
  if (guestSession) params.set('guest_session_id', guestSession);
  const qs = params.toString();
  return `${API_BASE}/contracts/${contractId}/pdf${qs ? `?${qs}` : ''}`;
}

export async function claimGuestSession(): Promise<{ claimed_count: number; user_id: string }> {
  const res = await fetch(`${API_BASE}/auth/claim`, {
    method: 'POST',
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error('Failed to claim guest session.');
  return res.json();
}

export function downloadAuditReport(contract: Contract, audit: AuditReport) {
  const lines = [
    `# Contract Review & Legal Risk Summary`,
    `**Document Name:** ${contract.filename}`,
    `**Overall Risk Assessment:** ${audit.risk_level} (${audit.overall_risk_score} / 100 Risk Score)`,
    `**Review Date:** ${new Date(audit.created_at).toLocaleDateString()}`,
    contract.cloudinary_url ? `**Document Copy:** [View Original File](${contract.cloudinary_url})` : '',
    ``,
    `## Executive Summary`,
    audit.executive_summary || 'No summary available.',
    ``,
    `## Identified Issues & Suggested Amendments (${audit.findings.length})`,
    ``
  ];

  audit.findings.forEach((f, idx) => {
    lines.push(`### ${idx + 1}. [${f.severity} RISK] ${f.clause_category} (Page ${f.page_number})`);
    lines.push(`**Standard Best Practice:** ${f.playbook_rule || 'Industry Standard'}`);
    lines.push(`**Why This Is a Risk:** ${f.deviation_explanation}`);
    lines.push(`\n**Current Contract Text:**`);
    lines.push(`> ${f.original_text}`);
    if (f.proposed_redline && f.severity !== 'ACCEPTABLE') {
      lines.push(`\n**Suggested Safer Language:**`);
      lines.push(`\`\`\`\n${f.proposed_redline}\n\`\`\``);
    }
    lines.push(``);
  });

  const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `Legal_Review_${contract.filename.replace(/\.pdf$/i, '')}.md`;
  a.click();
  URL.revokeObjectURL(url);
}
