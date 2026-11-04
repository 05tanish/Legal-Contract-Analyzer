import { useState, useEffect } from 'react';
import { Navbar } from './components/layout/Navbar';
import { HomePage } from './components/home/HomePage';
import { HistoryPage } from './components/history/HistoryPage';
import { SplitPdfViewer } from './components/pdf-viewer/SplitPdfViewer';
import { AuditScorecard } from './components/audit/AuditScorecard';
import { FindingsList } from './components/audit/FindingsList';
import { DetectedClausesList } from './components/audit/DetectedClausesList';
import { ContractChatDrawer } from './components/chat/ContractChatDrawer';
import { ContractUploader } from './components/upload/ContractUploader';
import { AuthModal } from './components/auth/AuthModal';
import {
  fetchContracts,
  runAudit,
  fetchLatestAudit,
  reindexContract,
  downloadAuditReport,
  fetchCurrentUser,
  getAuthToken,
  removeAuthToken,
  resetGuestSessionId,
  deleteContract,
  detectClauses,
  getStoredUser,
  getStoredActiveContract,
  setStoredActiveContract,
  removeStoredUser
} from './lib/api';
import { Contract, AuditReport, User, DetectedClause } from './types';
import {
  FileText,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  Download,
  Cloud,
  Layers,
  Columns,
  Trash2,
  Lock,
  Clock,
  ShieldAlert,
  FileCheck,
  FileSearch,
  ScanLine
} from 'lucide-react';

export function App() {
  // Navigation & View States with Persistence across reloads
  const [currentView, setCurrentView] = useState<'home' | 'workspace' | 'history'>(() => {
    const saved = localStorage.getItem('contractiq_current_view');
    if (saved === 'workspace' || saved === 'history') return saved;
    return 'home';
  });
  const [workspaceMode, setWorkspaceMode] = useState<'split' | 'document' | 'analysis'>('split');
  const [activeTab, setActiveTab] = useState<'overview' | 'clauses' | 'findings' | 'summary' | 'metadata'>('overview');

  // Contracts & Review States with Local Storage Persistence
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [selectedContract, setSelectedContract] = useState<Contract | null>(() => getStoredActiveContract());
  const [auditReport, setAuditReport] = useState<AuditReport | null>(null);
  const [detectedClauses, setDetectedClauses] = useState<DetectedClause[]>([]);
  const [isAuditing, setIsAuditing] = useState(false);
  const [isDetectingClauses, setIsDetectingClauses] = useState(false);
  const [isReindexing, setIsReindexing] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Modals & Drawers
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  // Citations & Notifications
  const [activeCitationPage, setActiveCitationPage] = useState<number | null>(null);
  const [activeCitationSnippet, setActiveCitationSnippet] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Auth & Dark Theme States (Synchronous initial session from localStorage; DARK IS DEFAULT)
  const [currentUser, setCurrentUser] = useState<User | null>(() => getStoredUser());
  const [isDarkMode, setIsDarkMode] = useState<boolean>(() => {
    const saved = localStorage.getItem('contractiq_theme');
    return saved ? saved === 'dark' : true;
  });

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  // Sync Dark Theme class to <html>
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('contractiq_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('contractiq_theme', 'light');
    }
  }, [isDarkMode]);

  // Persist current view across page reloads
  useEffect(() => {
    localStorage.setItem('contractiq_current_view', currentView);
  }, [currentView]);

  // Persist selected contract to localStorage
  useEffect(() => {
    if (selectedContract) {
      setStoredActiveContract(selectedContract);
    }
  }, [selectedContract]);

  // Initialize session and contracts on mount
  useEffect(() => {
    loadSession();
    // If a contract was already active, immediately load its audit and clauses without waiting
    const initialContract = getStoredActiveContract();
    if (initialContract) {
      loadAudit(initialContract.id);
      loadDetectedClauses(initialContract.id);
    }
  }, []);

  const loadSession = async () => {
    const token = getAuthToken();
    if (!token) {
      // Unauthenticated session
      return;
    }
    try {
      const user = await fetchCurrentUser();
      if (user) {
        setCurrentUser(user);
        await loadContracts();
      } else {
        // Explicit 401
        setCurrentUser(null);
        setContracts([]);
      }
    } catch {
      // On network blip, preserve cached user
    }
  };

  const loadContracts = async () => {
    // Contract history is strictly reserved for authenticated users
    if (!getAuthToken()) {
      setContracts([]);
      return;
    }
    try {
      const data = await fetchContracts();
      setContracts(data);
      if (data.length > 0) {
        const savedContract = getStoredActiveContract();
        const activeMatch = savedContract ? data.find((c) => c.id === savedContract.id) : null;
        const target = activeMatch || selectedContract || data[0];
        setSelectedContract(target);
        setStoredActiveContract(target);
        loadAudit(target.id);
        loadDetectedClauses(target.id);
      }
    } catch (err: any) {
      console.error('Failed to load contracts:', err);
    }
  };

  const loadAudit = async (contractId: string) => {
    try {
      const report = await fetchLatestAudit(contractId);
      setAuditReport(report);
    } catch {
      setAuditReport(null);
    }
  };

  const loadDetectedClauses = async (contractId: string) => {
    try {
      const res = await detectClauses(contractId);
      setDetectedClauses(res.clauses || []);
    } catch {
      setDetectedClauses([]);
    }
  };

  const handleSelectContract = (contract: Contract) => {
    setSelectedContract(contract);
    setStoredActiveContract(contract);
    setActiveCitationPage(null);
    setActiveCitationSnippet(null);
    setError(null);
    setCurrentView('workspace');
    loadAudit(contract.id);
    loadDetectedClauses(contract.id);
  };

  const handleTriggerAudit = async () => {
    if (!selectedContract) return;

    // Enforce authentication for full multi-agent audit
    if (!currentUser) {
      setIsAuthOpen(true);
      setError('Full multi-agent legal reviews, Indian statutory verification, and automated redlines require an account. Please sign in or register.');
      return;
    }

    setIsAuditing(true);
    setError(null);
    try {
      const report = await runAudit(selectedContract.id);
      setAuditReport(report);
      showToast('Comprehensive legal review completed.');
      setActiveTab('overview');
    } catch (err: any) {
      if (err.code === 'AUTH_REQUIRED') {
        setIsAuthOpen(true);
      }
      setError(err.message || 'Unable to review this contract right now. Please try again.');
    } finally {
      setIsAuditing(false);
    }
  };

  const handleTriggerClauseDetection = async () => {
    if (!selectedContract) return;
    setIsDetectingClauses(true);
    setError(null);
    try {
      const res = await detectClauses(selectedContract.id);
      setDetectedClauses(res.clauses || []);
      setActiveTab('clauses');
      showToast(`Detected ${res.total_clauses_detected} clauses across the document.`);
    } catch (err: any) {
      setError(err.message || 'Unable to detect clauses at this time.');
    } finally {
      setIsDetectingClauses(false);
    }
  };

  const handleDeleteContract = async () => {
    if (!selectedContract) return;
    setIsDeleting(true);
    try {
      await deleteContract(selectedContract.id);
      const remaining = contracts.filter((c) => c.id !== selectedContract.id);
      setContracts(remaining);
      setShowDeleteModal(false);
      showToast('Document permanently removed.');
      if (remaining.length > 0) {
        handleSelectContract(remaining[0]);
      } else {
        setSelectedContract(null);
        setCurrentView('home');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to delete contract.');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleReindex = async () => {
    if (!selectedContract) return;
    setIsReindexing(true);
    setError(null);
    try {
      const updated = await reindexContract(selectedContract.id);
      setSelectedContract(updated);
      showToast('Document refreshed and re-indexed.');
      await loadDetectedClauses(updated.id);
      if (currentUser) {
        const report = await runAudit(selectedContract.id);
        setAuditReport(report);
      }
    } catch (err: any) {
      setError(err.message || 'Unable to refresh this document right now.');
    } finally {
      setIsReindexing(false);
    }
  };

  const handleExport = () => {
    if (selectedContract && auditReport) {
      downloadAuditReport(selectedContract, auditReport);
      showToast('Summary report downloaded.');
    }
  };

  const handleSelectCitation = (page: number, text: string) => {
    setActiveCitationPage(page);
    setActiveCitationSnippet(text);
    if (workspaceMode === 'analysis') {
      setWorkspaceMode('split');
    }
    showToast(`Navigated to Page ${page}`);
  };

  const handleToggleChat = () => {
    if (!currentUser) {
      setIsAuthOpen(true);
      setError('The AI Legal Copilot is available to registered accounts. Please sign in or register.');
      return;
    }
    setIsChatOpen(!isChatOpen);
  };

  const handleSignOut = () => {
    removeAuthToken();
    removeStoredUser();
    resetGuestSessionId();
    setStoredActiveContract(null);
    localStorage.removeItem('contractiq_current_view');
    setCurrentUser(null);
    setContracts([]);
    setSelectedContract(null);
    setAuditReport(null);
    setDetectedClauses([]);
    setCurrentView('home');
    showToast('Signed out successfully.');
  };

  return (
    <div className={`w-full ${currentView === 'workspace' ? 'h-screen h-[100dvh] overflow-hidden' : 'min-h-screen overflow-y-auto'} flex flex-col ${isDarkMode ? 'bg-[#0c0d10] text-neutral-100' : 'bg-[#fcfcfc] text-neutral-900'} font-sans transition-colors duration-150`}>
      {/* Top Navbar */}
      <Navbar
        contracts={contracts}
        selectedContract={selectedContract}
        onSelectContract={handleSelectContract}
        onNavigateHome={() => setCurrentView('home')}
        onNavigateHistory={() => {
          if (currentUser) {
            setCurrentView('history');
          } else {
            setIsAuthOpen(true);
          }
        }}
        onOpenUpload={() => setIsUploadOpen(true)}
        onTriggerAudit={handleTriggerAudit}
        isAuditing={isAuditing}
        onToggleChat={handleToggleChat}
        isChatOpen={isChatOpen}
        auditReport={auditReport}
        onExportReport={handleExport}
        isDarkMode={isDarkMode}
        onToggleDarkMode={() => setIsDarkMode(!isDarkMode)}
        currentUser={currentUser}
        onOpenAuth={() => setIsAuthOpen(true)}
        onSignOut={handleSignOut}
        currentView={currentView}
      />

      {/* Global Toast Notification */}
      {toastMessage && (
        <div className="fixed top-20 right-6 z-50 bg-neutral-900 text-white px-4 py-2.5 rounded-lg shadow-2xl border border-neutral-700 flex items-center space-x-2 text-xs font-medium animate-in fade-in slide-in-from-top-4 duration-150">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden min-h-0">
        {currentView === 'home' || (currentView === 'history' && !currentUser) ? (
          /* ==================== 1. DEFAULT HOME PAGE ==================== */
          <HomePage
            contracts={currentUser ? contracts : []}
            onSelectContract={handleSelectContract}
            onOpenUpload={() => setIsUploadOpen(true)}
            onOpenLegalGuide={handleToggleChat}
            onOpenAuth={() => setIsAuthOpen(true)}
            onNavigateHistory={() => {
              if (currentUser) {
                setCurrentView('history');
              } else {
                setIsAuthOpen(true);
              }
            }}
            isLoggedIn={!!currentUser}
          />
        ) : currentView === 'history' && currentUser ? (
          /* ==================== 2. CONTRACT HISTORY PAGE ==================== */
          <HistoryPage
            contracts={contracts}
            currentUser={currentUser}
            onSelectContract={handleSelectContract}
            onOpenUpload={() => setIsUploadOpen(true)}
            onOpenAuth={() => setIsAuthOpen(true)}
            onDeleteContract={(c) => {
              setSelectedContract(c);
              setShowDeleteModal(true);
            }}
          />
        ) : (
          /* ==================== 3. CONTRACT REVIEW WORKSPACE ==================== */
          selectedContract ? (
            <div className="flex-1 flex flex-col h-[calc(100vh-4rem)] overflow-hidden min-h-0">
              {/* Guest Document Expiration Notice */}
              {selectedContract.is_guest && (
                <div className="bg-amber-950/40 border-b border-amber-900/60 px-4 py-2 flex flex-wrap items-center justify-between gap-2 text-xs text-amber-200 shrink-0 select-none">
                  <div className="flex items-center space-x-2">
                    <Clock className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                    <span>
                      <strong>Guest Session:</strong> This document is stored temporarily and will be automatically purged after 24 hours.
                    </span>
                  </div>
                  <button
                    onClick={() => setIsAuthOpen(true)}
                    className="bg-amber-400/20 hover:bg-amber-400/30 text-amber-200 px-2.5 py-1 rounded text-[11px] font-semibold border border-amber-500/40 transition"
                  >
                    Sign in to Save Permanently
                  </button>
                </div>
              )}

              {/* Workspace Action & Mode Bar */}
              <div className="bg-[#121316] border-b border-[#23252a] px-3 sm:px-6 py-2.5 flex flex-wrap items-center justify-between gap-3 shrink-0 shadow-xs">
                {/* Contract title and page badge */}
                <div className="flex items-center space-x-3 truncate min-w-0">
                  <button
                    onClick={() => setCurrentView('home')}
                    className="text-xs text-neutral-400 hover:text-white flex items-center space-x-1 transition shrink-0"
                    title="Return to Home"
                  >
                    <span>← Home</span>
                  </button>
                  <h2 className="font-serif font-bold text-sm sm:text-base text-neutral-100 truncate max-w-[160px] sm:max-w-md" title={selectedContract.filename}>
                    {selectedContract.filename}
                  </h2>
                  <span className="text-[11px] text-neutral-400 font-mono bg-neutral-800/80 px-2 py-0.5 rounded border border-neutral-700 shrink-0">
                    {selectedContract.total_pages || 1} {selectedContract.total_pages === 1 ? 'Page' : 'Pages'}
                  </span>
                  {selectedContract.cloudinary_url && (
                    <a
                      href={selectedContract.cloudinary_url}
                      target="_blank"
                      rel="noreferrer"
                      className="hidden md:inline-flex items-center space-x-1 text-xs text-neutral-400 hover:text-neutral-200 underline transition shrink-0"
                    >
                      <Cloud className="w-3.5 h-3.5 text-neutral-400" />
                      <span>Cloud Copy</span>
                    </a>
                  )}
                </div>

                {/* View Mode Controls (Full Width, Split, Analysis) */}
                <div className="flex items-center space-x-2">
                  <div className="flex items-center bg-[#18191e] border border-[#27272a] rounded-lg p-0.5 text-xs font-medium">
                    <button
                      onClick={() => setWorkspaceMode('split')}
                      className={`px-2.5 py-1 rounded-md transition flex items-center space-x-1 ${
                        workspaceMode === 'split'
                          ? 'bg-neutral-800 text-white shadow-xs'
                          : 'text-neutral-400 hover:text-white'
                      }`}
                      title="View Document and Analysis side by side"
                    >
                      <Columns className="w-3.5 h-3.5" />
                      <span className="hidden sm:inline">Side-by-Side</span>
                    </button>
                    <button
                      onClick={() => setWorkspaceMode('document')}
                      className={`px-2.5 py-1 rounded-md transition flex items-center space-x-1 ${
                        workspaceMode === 'document'
                          ? 'bg-neutral-800 text-white shadow-xs'
                          : 'text-neutral-400 hover:text-white'
                      }`}
                      title="Expand Document to full width"
                    >
                      <FileText className="w-3.5 h-3.5" />
                      <span className="hidden sm:inline">Document Only</span>
                    </button>
                    <button
                      onClick={() => setWorkspaceMode('analysis')}
                      className={`px-2.5 py-1 rounded-md transition flex items-center space-x-1 ${
                        workspaceMode === 'analysis'
                          ? 'bg-neutral-800 text-white shadow-xs'
                          : 'text-neutral-400 hover:text-white'
                      }`}
                      title="Expand Analysis to full width"
                    >
                      <FileCheck className="w-3.5 h-3.5" />
                      <span className="hidden sm:inline">Analysis Only</span>
                    </button>
                  </div>

                  {/* Clause Detection Action (Lightweight, Open to Guests) */}
                  <button
                    onClick={handleTriggerClauseDetection}
                    disabled={isDetectingClauses}
                    className="bg-[#18191e] hover:bg-[#202128] text-neutral-200 px-3 py-1 rounded-md text-xs font-semibold border border-[#27272a] transition flex items-center space-x-1.5 shadow-xs"
                    title="Run fast local NLP clause detection"
                  >
                    <ScanLine className={`w-3.5 h-3.5 ${isDetectingClauses ? 'animate-spin' : ''}`} />
                    <span className="hidden md:inline">{isDetectingClauses ? 'Detecting...' : 'Detect Clauses'}</span>
                  </button>

                  {/* Full Legal Review Action (Auth Only) */}
                  <button
                    onClick={handleTriggerAudit}
                    disabled={isAuditing}
                    className="bg-white hover:bg-neutral-200 disabled:opacity-40 text-neutral-950 px-3 py-1 rounded-md text-xs font-semibold transition flex items-center space-x-1.5 shadow-xs"
                    title={currentUser ? 'Run full multi-agent audit' : 'Sign in to run full audit'}
                  >
                    {!currentUser && <Lock className="w-3 h-3 mr-0.5 text-neutral-600" />}
                    <RefreshCw className={`w-3.5 h-3.5 ${isAuditing ? 'animate-spin' : ''}`} />
                    <span>{isAuditing ? 'Reviewing...' : auditReport ? 'Re-review' : 'Start Review'}</span>
                  </button>

                  {/* Delete Contract Action */}
                  <button
                    onClick={() => setShowDeleteModal(true)}
                    className="p-1.5 rounded-md hover:bg-red-950/40 text-neutral-400 hover:text-red-400 border border-transparent hover:border-red-900/40 transition"
                    title="Delete contract permanently"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Responsive Split or Full Pane Workspace: 100% Full Height & Width */}
              <div className="flex-1 flex flex-col md:flex-row overflow-hidden min-h-0 w-full relative">
                {/* Left Pane: PDF Document Viewer */}
                {workspaceMode !== 'analysis' && (
                  <div
                    className={`${
                      workspaceMode === 'split' ? 'w-full md:w-1/2' : 'w-full'
                    } h-full min-h-0 flex flex-col shrink-0 relative`}
                  >
                    <SplitPdfViewer
                      contractId={selectedContract.id}
                      filename={selectedContract.filename}
                      totalPages={selectedContract.total_pages}
                      activeCitationPage={activeCitationPage}
                      activeCitationSnippet={activeCitationSnippet}
                      cloudinaryUrl={selectedContract.cloudinary_url}
                      isExpanded={workspaceMode === 'document'}
                      onToggleExpand={() => setWorkspaceMode(workspaceMode === 'document' ? 'split' : 'document')}
                    />
                  </div>
                )}

                {/* Right Pane: Analysis & Tabs */}
                {workspaceMode !== 'document' && (
                  <div
                    className={`${
                      workspaceMode === 'split' ? 'w-full md:w-1/2 min-w-0' : 'w-full min-w-0'
                    } h-full min-h-0 overflow-y-auto p-4 sm:p-6 flex flex-col bg-[#0c0d10]`}
                  >
                    {/* Error Notice */}
                    {error && (
                      <div className="mb-4 p-3.5 bg-red-950/40 border border-red-900/60 rounded-lg flex items-center justify-between text-xs text-red-300">
                        <div className="flex items-center space-x-2">
                          <AlertCircle className="w-4 h-4 shrink-0 text-red-400" />
                          <span>{error}</span>
                        </div>
                        <button
                          onClick={() => setError(null)}
                          className="text-red-300 hover:text-white font-semibold underline"
                        >
                          Dismiss
                        </button>
                      </div>
                    )}

                    {/* Analysis Tabs */}
                    <div className="border-b border-[#23252a] mb-6 flex items-center justify-between overflow-x-auto">
                      <div className="flex space-x-5 text-xs sm:text-sm font-medium shrink-0">
                        <button
                          onClick={() => setActiveTab('overview')}
                          className={`pb-3 relative transition ${
                            activeTab === 'overview'
                              ? 'text-white font-semibold border-b-2 border-white'
                              : 'text-neutral-400 hover:text-neutral-200'
                          }`}
                        >
                          Overview
                        </button>

                        <button
                          onClick={() => setActiveTab('clauses')}
                          className={`pb-3 relative transition flex items-center space-x-1.5 ${
                            activeTab === 'clauses'
                              ? 'text-white font-semibold border-b-2 border-white'
                              : 'text-neutral-400 hover:text-neutral-200'
                          }`}
                        >
                          <span>Detected Clauses</span>
                          {detectedClauses.length > 0 && (
                            <span className="text-xs bg-neutral-800 text-neutral-300 px-1.5 py-0.5 rounded font-mono">
                              {detectedClauses.length}
                            </span>
                          )}
                        </button>

                        <button
                          onClick={() => setActiveTab('findings')}
                          className={`pb-3 relative transition flex items-center space-x-1.5 ${
                            activeTab === 'findings'
                              ? 'text-white font-semibold border-b-2 border-white'
                              : 'text-neutral-400 hover:text-neutral-200'
                          }`}
                        >
                          <span>Risks & Redlines</span>
                          {auditReport && (
                            <span className="text-xs bg-neutral-800 text-neutral-300 px-1.5 py-0.5 rounded font-mono">
                              {auditReport.findings.length}
                            </span>
                          )}
                        </button>

                        <button
                          onClick={() => setActiveTab('summary')}
                          className={`pb-3 relative transition ${
                            activeTab === 'summary'
                              ? 'text-white font-semibold border-b-2 border-white'
                              : 'text-neutral-400 hover:text-neutral-200'
                          }`}
                        >
                          Executive Summary
                        </button>

                        <button
                          onClick={() => setActiveTab('metadata')}
                          className={`pb-3 relative transition ${
                            activeTab === 'metadata'
                              ? 'text-white font-semibold border-b-2 border-white'
                              : 'text-neutral-400 hover:text-neutral-200'
                          }`}
                        >
                          Document Details
                        </button>
                      </div>

                      {auditReport && (
                        <button
                          onClick={handleExport}
                          className="hidden sm:flex items-center space-x-1.5 text-xs text-neutral-400 hover:text-white pb-2 transition shrink-0"
                          title="Download summary report"
                        >
                          <Download className="w-3.5 h-3.5" />
                          <span>Download Report</span>
                        </button>
                      )}
                    </div>

                    {/* Tab 1: OVERVIEW */}
                    {activeTab === 'overview' && (
                      <div>
                        {auditReport ? (
                          <>
                            <AuditScorecard
                              audit={auditReport}
                              onReindex={handleReindex}
                              isReindexing={isReindexing}
                            />

                            {/* Summary Metrics */}
                            <div className="p-6 mb-6 bg-black border border-neutral-800 rounded-lg shadow-xs">
                              <h4 className="font-serif font-bold text-base text-white mb-3 pb-2 border-b border-neutral-800">
                                Review Summary
                              </h4>
                              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                                <div className="p-3 bg-neutral-950 rounded border border-neutral-800/80">
                                  <span className="text-[10px] text-neutral-400 uppercase block font-medium">Pages Ingested</span>
                                  <span className="text-base font-bold text-white">{selectedContract.total_pages}</span>
                                </div>
                                <div className="p-3 bg-neutral-950 rounded border border-neutral-800/80">
                                  <span className="text-[10px] text-neutral-400 uppercase block font-medium">Deviations Found</span>
                                  <span className="text-base font-bold text-white">{auditReport.findings.length}</span>
                                </div>
                                <div className="p-3 bg-neutral-950 rounded border border-neutral-800/80">
                                  <span className="text-[10px] text-neutral-400 uppercase block font-medium">Review Benchmark</span>
                                  <span className="text-sm font-semibold text-neutral-200">Indian Contract Law Standard</span>
                                </div>
                                <div className="p-3 bg-neutral-950 rounded border border-neutral-800/80">
                                  <span className="text-[10px] text-neutral-400 uppercase block font-medium">Storage Policy</span>
                                  <span className="text-sm font-semibold text-neutral-200">
                                    {selectedContract.is_guest ? 'Temporary (24h Retention)' : 'Persistent Cloud Storage'}
                                  </span>
                                </div>
                              </div>
                            </div>

                            {/* Priority Issues Preview */}
                            <div className="p-6 bg-black border border-neutral-800 rounded-lg shadow-xs">
                              <div className="flex items-center justify-between mb-4 pb-2 border-b border-neutral-800">
                                <h4 className="font-serif font-bold text-base text-white">
                                  Highest Priority Issues
                                </h4>
                                <button
                                  onClick={() => setActiveTab('findings')}
                                  className="text-xs font-medium text-neutral-300 hover:text-white underline"
                                >
                                  View All Issues ({auditReport.findings.length}) →
                                </button>
                              </div>
                              <FindingsList
                                findings={auditReport.findings.slice(0, 3)}
                                onSelectCitation={handleSelectCitation}
                              />
                            </div>
                          </>
                        ) : (
                          /* Not yet reviewed state */
                          <div className="saas-card p-8 sm:p-12 text-center flex flex-col items-center justify-center bg-[#131418] border border-[#23252a] rounded-lg">
                            <div className="w-12 h-12 rounded-full bg-neutral-800 flex items-center justify-center mb-4 text-neutral-300">
                              <FileSearch className="w-6 h-6" />
                            </div>
                            <h3 className="font-serif font-bold text-lg text-neutral-100 mb-1">
                              Ready for Legal Review
                            </h3>
                            <p className="text-xs text-neutral-400 max-w-md mx-auto mb-6 leading-relaxed">
                              {selectedContract.total_pages} pages parsed and indexed.
                              {!currentUser ? (
                                <>
                                  {' '}As a guest, you can run instant <strong>Cause & Clause Detection</strong> below. Sign in to run complete multi-agent risk audits and automated redlines.
                                </>
                              ) : (
                                <>
                                  {' '}Click below to launch the multi-agent legal audit, verify clauses against Indian statutes, and generate redline revisions.
                                </>
                              )}
                            </p>

                            <div className="flex flex-wrap items-center justify-center gap-3">
                              <button
                                onClick={handleTriggerClauseDetection}
                                disabled={isDetectingClauses}
                                className="bg-[#1e1f26] hover:bg-[#252630] text-neutral-200 px-5 py-2.5 rounded-md text-xs font-semibold border border-[#2a2b34] shadow-xs transition flex items-center space-x-2"
                              >
                                <ScanLine className={`w-3.5 h-3.5 ${isDetectingClauses ? 'animate-spin' : ''}`} />
                                <span>{isDetectingClauses ? 'Detecting Clauses...' : 'Detect Key Clauses'}</span>
                              </button>

                              <button
                                onClick={handleTriggerAudit}
                                disabled={isAuditing}
                                className="bg-white hover:bg-neutral-200 disabled:opacity-40 text-neutral-950 px-5 py-2.5 rounded-md text-xs font-semibold shadow-xs transition flex items-center space-x-2"
                              >
                                {!currentUser && <Lock className="w-3.5 h-3.5 text-neutral-600" />}
                                <RefreshCw className={`w-3.5 h-3.5 ${isAuditing ? 'animate-spin' : ''}`} />
                                <span>{isAuditing ? 'Reviewing...' : 'Start Full Legal Audit'}</span>
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Tab 2: DETECTED CLAUSES (Lightweight CUAD ML detection) */}
                    {activeTab === 'clauses' && (
                      <DetectedClausesList
                        clauses={detectedClauses}
                        isGuest={Boolean(selectedContract.is_guest)}
                        onSelectCitation={handleSelectCitation}
                        onOpenAuth={() => setIsAuthOpen(true)}
                      />
                    )}

                    {/* Tab 3: RISK ANALYSIS & REDLINES */}
                    {activeTab === 'findings' && (
                      <div>
                        {auditReport ? (
                          <FindingsList
                            findings={auditReport.findings}
                            onSelectCitation={handleSelectCitation}
                          />
                        ) : (
                          <div className="saas-card p-8 text-center text-xs text-neutral-400 bg-[#131418] border border-[#23252a] rounded-lg">
                            <p className="mb-4">
                              Full legal risk analysis and redlines are generated during the complete audit.
                            </p>
                            <button
                              onClick={handleTriggerAudit}
                              className="bg-white hover:bg-neutral-200 text-neutral-950 px-4 py-2 rounded-md font-semibold text-xs transition inline-flex items-center space-x-1.5"
                            >
                              {!currentUser && <Lock className="w-3 h-3 text-neutral-600" />}
                              <span>{currentUser ? 'Run Complete Audit' : 'Sign In to Run Audit'}</span>
                            </button>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Tab 4: EXECUTIVE BRIEF */}
                    {activeTab === 'summary' && (
                      <div className="p-6 bg-black border border-neutral-800 rounded-lg shadow-xs">
                        <div className="p-3 bg-neutral-950 border border-neutral-800 rounded-md mb-6 text-xs text-neutral-300 leading-relaxed">
                          <span className="font-semibold text-white">Executive Summary:</span> Key commercial provisions, obligations, and risk assessment for legal counsel.
                        </div>

                        <h3 className="font-serif font-bold text-xl text-white mb-3">
                          Executive Summary
                        </h3>
                        <div className="text-xs text-neutral-200 leading-relaxed space-y-4 whitespace-pre-line font-sans">
                          {auditReport?.executive_summary ? (
                            <div className="bg-neutral-950 p-5 rounded-md border border-neutral-800 font-sans leading-relaxed text-neutral-200">
                              {auditReport.executive_summary}
                            </div>
                          ) : (
                            <p className="text-neutral-500 italic">
                              Summary not yet generated. Complete the full audit to view executive briefing.
                            </p>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Tab 5: METADATA & INGESTION */}
                    {activeTab === 'metadata' && (
                      <div className="p-6 space-y-4 bg-black border border-neutral-800 rounded-lg shadow-xs">
                        <h3 className="font-serif font-bold text-lg text-white mb-2 flex items-center space-x-2">
                          <Layers className="w-4 h-4 text-neutral-400" />
                          <span>Document Details</span>
                        </h3>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
                          <div className="bg-neutral-950 p-3.5 rounded border border-neutral-800">
                            <span className="text-[10px] text-neutral-400 block uppercase font-sans">Document ID</span>
                            <span className="text-neutral-200 truncate block mt-0.5">{selectedContract.id}</span>
                          </div>
                          <div className="bg-neutral-950 p-3.5 rounded border border-neutral-800">
                            <span className="text-[10px] text-neutral-400 block uppercase font-sans">Total Pages</span>
                            <span className="text-neutral-200 block mt-0.5">{selectedContract.total_pages} Pages</span>
                          </div>
                          <div className="bg-neutral-950 p-3.5 rounded border border-neutral-800">
                            <span className="text-[10px] text-neutral-400 block uppercase font-sans">Workflow Mode</span>
                            <span className="text-neutral-200 block mt-0.5">
                              {selectedContract.is_guest ? 'Guest (Temporary TTL)' : 'Authenticated (Persistent)'}
                            </span>
                          </div>
                          <div className="bg-neutral-950 p-3.5 rounded border border-neutral-800">
                            <span className="text-[10px] text-neutral-400 block uppercase font-sans">Cloud Storage</span>
                            {selectedContract.cloudinary_url ? (
                              <a
                                href={selectedContract.cloudinary_url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-neutral-200 underline block truncate mt-0.5 font-sans hover:text-white"
                                title="View Cloudinary asset"
                              >
                                Cloudinary Raw Asset →
                              </a>
                            ) : (
                              <span className="text-neutral-400 block mt-0.5 font-sans">Local Temporary Storage</span>
                            )}
                          </div>
                        </div>

                        <div className="pt-4 flex justify-between items-center">
                          <button
                            onClick={() => setShowDeleteModal(true)}
                            className="flex items-center space-x-1.5 text-xs text-red-400 hover:text-red-300 transition"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            <span>Delete Contract</span>
                          </button>

                          <button
                            onClick={handleReindex}
                            disabled={isReindexing}
                            className="flex items-center space-x-2 text-xs font-medium bg-neutral-800 hover:bg-neutral-700 text-neutral-200 px-4 py-2 rounded-md border border-neutral-700 transition"
                          >
                            <RefreshCw className={`w-3.5 h-3.5 ${isReindexing ? 'animate-spin' : ''}`} />
                            <span>{isReindexing ? 'Refreshing...' : 'Re-index Document'}</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <HomePage
              contracts={contracts}
              onSelectContract={handleSelectContract}
              onOpenUpload={() => setIsUploadOpen(true)}
              onOpenLegalGuide={handleToggleChat}
              onOpenAuth={() => setIsAuthOpen(true)}
              onNavigateHistory={() => {
          if (currentUser) {
            setCurrentView('history');
          } else {
            setIsAuthOpen(true);
          }
        }}
              isLoggedIn={!!currentUser}
            />
          )
        )}

        {/* Collapsible Legal Assistant Drawer (Protected for Auth) */}
        <ContractChatDrawer
          contractId={selectedContract?.id || null}
          isOpen={isChatOpen}
          onClose={() => setIsChatOpen(false)}
          onSelectCitation={handleSelectCitation}
        />
      </main>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && selectedContract && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[#16171b] border border-[#27272f] rounded-lg max-w-md w-full p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center space-x-3 text-red-400 mb-3">
              <ShieldAlert className="w-6 h-6 shrink-0" />
              <h3 className="font-serif font-bold text-lg text-neutral-100">
                Permanently Delete Document?
              </h3>
            </div>
            <p className="text-xs text-neutral-300 leading-relaxed mb-6">
              This will permanently delete <strong>{selectedContract.filename}</strong>, along with all associated vector embeddings from Qdrant, cloud backups on Cloudinary, and review findings. This action cannot be undone.
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowDeleteModal(false)}
                disabled={isDeleting}
                className="px-4 py-2 text-xs font-medium rounded-md text-neutral-300 hover:text-white bg-neutral-800 hover:bg-neutral-700 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteContract}
                disabled={isDeleting}
                className="px-4 py-2 text-xs font-semibold rounded-md text-white bg-red-600 hover:bg-red-500 disabled:opacity-40 transition flex items-center space-x-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>{isDeleting ? 'Deleting...' : 'Delete Permanently'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Upload Modal */}
      <ContractUploader
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={(c) => {
          setContracts((prev) => [c, ...prev]);
          handleSelectContract(c);
          showToast(`"${c.filename}" uploaded successfully.`);
        }}
      />

      {/* User Authentication Modal */}
      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onAuthSuccess={async (user) => {
          setCurrentUser(user);
          // 1. Immediately remove temporary status on the active contract so banner disappears instantly
          setSelectedContract((prev) => {
            if (!prev) return null;
            return {
              ...prev,
              is_guest: false,
              expires_at: undefined,
              user_id: user.id
            };
          });
          // 2. Fetch updated persistent contracts from backend (now claimed by the user)
          try {
            const data = await fetchContracts();
            setContracts(data);
            if (selectedContract) {
              const currentInList = data.find((c) => c.id === selectedContract.id);
              if (currentInList) {
                setSelectedContract(currentInList);
                setStoredActiveContract(currentInList);
              }
            } else if (data.length > 0) {
              setSelectedContract(data[0]);
              setStoredActiveContract(data[0]);
            }
          } catch (err) {
            console.error('Failed to reload contracts after auth:', err);
          }
          showToast(`Welcome back, ${user.full_name || user.email}!`);
        }}
      />
    </div>
  );
}

export default App;
