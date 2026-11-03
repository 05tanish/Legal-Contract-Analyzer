import { Contract, AuditReport, Playbook, ClauseCitation, ChatQueryResponse, QueryMode, LegalSearchHit } from '../types';

const API_BASE = '/api/v1';

export async function fetchContracts(): Promise<Contract[]> {
  const res = await fetch(`${API_BASE}/contracts`);
  if (!res.ok) throw new Error('Failed to load contracts');
  return res.json();
}

export async function uploadContract(file: File): Promise<Contract> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/contracts/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(err.detail || 'Upload failed');
  }
  return res.json();
}

export async function fetchContract(contractId: string): Promise<Contract> {
  const res = await fetch(`${API_BASE}/contracts/${contractId}`);
  if (!res.ok) throw new Error('Failed to fetch contract details');
  return res.json();
}

export async function runAudit(contractId: string): Promise<AuditReport> {
  const res = await fetch(`${API_BASE}/audit/${contractId}`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Audit failed' }));
    throw new Error(err.detail || 'Audit execution failed');
  }
  return res.json();
}

export async function fetchLatestAudit(contractId: string): Promise<AuditReport | null> {
  const res = await fetch(`${API_BASE}/audit/${contractId}/latest`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error('Failed to fetch audit report');
  return res.json();
}

export async function fetchPlaybooks(): Promise<Playbook[]> {
  const res = await fetch(`${API_BASE}/playbooks`);
  if (!res.ok) throw new Error('Failed to fetch playbooks');
  return res.json();
}

export async function askLegalPlatform(
  query: string,
  contractId?: string,
  mode?: QueryMode
): Promise<ChatQueryResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      contract_id: contractId || null,
      mode: mode || null
    }),
  });
  if (!res.ok) throw new Error('Chat query failed');
  return res.json();
}

// Backwards compatibility alias
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
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, document_type: docType, top_k: 5 }),
  });
  if (!res.ok) throw new Error('Legal corpus search failed');
  return res.json();
}

export function getPdfUrl(contractId: string): string {
  return `${API_BASE}/contracts/${contractId}/pdf`;
}
