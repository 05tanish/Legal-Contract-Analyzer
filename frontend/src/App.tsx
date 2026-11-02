import React, { useState, useEffect } from 'react';
import { Navbar } from './components/layout/Navbar';
import { SplitPdfViewer } from './components/pdf-viewer/SplitPdfViewer';
import { AuditScorecard } from './components/audit/AuditScorecard';
import { FindingsList } from './components/audit/FindingsList';
import { ContractChatDrawer } from './components/chat/ContractChatDrawer';
import { ContractUploader } from './components/upload/ContractUploader';
import { fetchContracts, runAudit, fetchLatestAudit } from './lib/api';
import { Contract, AuditReport } from './types';
import { FileSearch, Sparkles, AlertCircle } from 'lucide-react';

export function App() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [selectedContract, setSelectedContract] = useState<Contract | null>(null);
  const [auditReport, setAuditReport] = useState<AuditReport | null>(null);
  const [isAuditing, setIsAuditing] = useState(false);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [activeCitationPage, setActiveCitationPage] = useState<number | null>(null);
  const [activeCitationSnippet, setActiveCitationSnippet] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load contracts on mount
  useEffect(() => {
    loadContracts();
  }, []);

  const loadContracts = async () => {
    try {
      const data = await fetchContracts();
      setContracts(data);
      if (data.length > 0 && !selectedContract) {
        setSelectedContract(data[0]);
        loadAudit(data[0].id);
      }
    } catch (err: any) {
      console.error(err);
    }
  };

  const loadAudit = async (contractId: string) => {
    try {
      const report = await fetchLatestAudit(contractId);
      setAuditReport(report);
    } catch (err) {
      setAuditReport(null);
    }
  };

  const handleSelectContract = (contract: Contract) => {
    setSelectedContract(contract);
    setActiveCitationPage(null);
    setActiveCitationSnippet(null);
    loadAudit(contract.id);
  };

  const handleTriggerAudit = async () => {
    if (!selectedContract) return;
    setIsAuditing(true);
    setError(null);
    try {
      const report = await runAudit(selectedContract.id);
      setAuditReport(report);
    } catch (err: any) {
      setError(err.message || 'Audit execution failed');
    } finally {
      setIsAuditing(false);
    }
  };

  const handleSelectCitation = (page: number, text: string) => {
    setActiveCitationPage(page);
    setActiveCitationSnippet(text);
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Top Navigation */}
      <Navbar
        contracts={contracts}
        selectedContract={selectedContract}
        onSelectContract={handleSelectContract}
        onOpenUpload={() => setIsUploadOpen(true)}
        onTriggerAudit={handleTriggerAudit}
        isAuditing={isAuditing}
        onToggleChat={() => setIsChatOpen(!isChatOpen)}
        isChatOpen={isChatOpen}
      />

      {/* Main Split-Screen Workspace */}
      <main className="flex-1 flex overflow-hidden">
        {selectedContract ? (
          <>
            {/* Left Pane: Interactive PDF Viewer (50% width) */}
            <div className="w-1/2 h-full flex flex-col shrink-0">
              <SplitPdfViewer
                contractId={selectedContract.id}
                filename={selectedContract.filename}
                totalPages={selectedContract.total_pages}
                activeCitationPage={activeCitationPage}
                activeCitationSnippet={activeCitationSnippet}
              />
            </div>

            {/* Right Pane: AI Playbook Audit & Redlines (50% width) */}
            <div className="flex-1 h-full overflow-y-auto bg-slate-950 p-6">
              {error && (
                <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center space-x-2 text-sm text-red-400">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {auditReport ? (
                <div>
                  <AuditScorecard audit={auditReport} />
                  <FindingsList
                    findings={auditReport.findings}
                    onSelectCitation={handleSelectCitation}
                  />
                </div>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-center p-8 border border-dashed border-slate-800 rounded-2xl bg-slate-900/20">
                  <FileSearch className="w-14 h-14 text-slate-600 mb-3" />
                  <h3 className="text-base font-semibold text-slate-300">Ready for Playbook Audit</h3>
                  <p className="text-xs text-slate-500 max-w-sm mt-1 mb-6">
                    Click "Run Playbook Audit" in the header to audit this contract against enterprise risk benchmarks using LangGraph & Hybrid Vector Search.
                  </p>
                  <button
                    onClick={handleTriggerAudit}
                    disabled={isAuditing}
                    className="flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-lg text-sm font-semibold shadow-lg shadow-indigo-600/30 transition"
                  >
                    <Sparkles className="w-4 h-4" />
                    <span>Start Audit Now</span>
                  </button>
                </div>
              )}
            </div>

            {/* Collapsible Chat Drawer */}
            <ContractChatDrawer
              contractId={selectedContract.id}
              isOpen={isChatOpen}
              onClose={() => setIsChatOpen(false)}
              onSelectCitation={handleSelectCitation}
            />
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
            <div className="w-16 h-16 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center mb-4">
              <FileSearch className="w-8 h-8 text-indigo-400" />
            </div>
            <h2 className="text-xl font-bold text-white mb-2">No Contract Selected</h2>
            <p className="text-sm text-slate-400 max-w-md mb-6">
              Upload a PDF agreement (NDA, MSA, SaaS) to experience layout-aware ingestion, hybrid vector retrieval, and automated redlining.
            </p>
            <button
              onClick={() => setIsUploadOpen(true)}
              className="bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl font-semibold text-sm shadow-lg shadow-indigo-600/30 transition"
            >
              Upload First Contract
            </button>
          </div>
        )}
      </main>

      {/* Upload Modal */}
      <ContractUploader
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={(c) => {
          setContracts((prev) => [c, ...prev]);
          handleSelectContract(c);
        }}
      />
    </div>
  );
}

export default App;

