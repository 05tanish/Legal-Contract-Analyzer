import React, { useState } from 'react';
import {
  Scale,
  FileText,
  Play,
  MessageSquare,
  Download,
  Sun,
  Moon,
  User as UserIcon,
  LogOut,
  ChevronDown,
  FolderOpen
} from 'lucide-react';
import { Contract, AuditReport, User } from '../../types';

interface NavbarProps {
  contracts: Contract[];
  selectedContract: Contract | null;
  onSelectContract: (contract: Contract) => void;
  onNavigateHome: () => void;
  onNavigateHistory: () => void;
  onOpenUpload: () => void;
  onTriggerAudit: () => void;
  isAuditing: boolean;
  onToggleChat: () => void;
  isChatOpen: boolean;
  auditReport?: AuditReport | null;
  onExportReport?: () => void;
  isDarkMode: boolean;
  onToggleDarkMode: () => void;
  currentUser: User | null;
  onOpenAuth: () => void;
  onSignOut: () => void;
  currentView: 'home' | 'workspace' | 'history';
}

export const Navbar: React.FC<NavbarProps> = ({
  contracts,
  selectedContract,
  onSelectContract,
  onNavigateHome,
  onNavigateHistory,
  onOpenUpload,
  onTriggerAudit,
  isAuditing,
  onToggleChat,
  isChatOpen,
  auditReport,
  onExportReport,
  isDarkMode,
  onToggleDarkMode,
  currentUser,
  onOpenAuth,
  onSignOut,
  currentView,
}) => {
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  return (
    <header className="bg-[#121316] text-neutral-100 border-b border-[#23252a] sticky top-0 z-30 transition-colors select-none">
      <div className="max-w-7xl mx-auto h-16 px-4 sm:px-6 flex items-center justify-between">
        {/* Brand: Taraju (Scales of Justice) + ContractIQ (Redirects to Home) */}
        <div className="flex items-center space-x-6">
          <div
            onClick={onNavigateHome}
            className="flex items-center space-x-2.5 cursor-pointer group"
            title="ContractIQ — Go to Home Page"
          >
            {/* Taraju Logo (Scales of Justice) */}
            <div className="w-8 h-8 rounded-lg bg-neutral-800 border border-neutral-700 flex items-center justify-center text-neutral-100 shadow-sm transition group-hover:bg-neutral-700">
              <Scale className="w-4 h-4" strokeWidth={2.2} />
            </div>
            <div className="flex flex-col">
              <span className="font-serif font-bold text-xl text-white tracking-tight leading-tight">
                ContractIQ
              </span>
              <span className="text-[10px] text-neutral-400 font-sans tracking-normal hidden sm:block">
                Legal Risk & Compliance Analyzer
              </span>
            </div>
          </div>

          {/* Top navigation links */}
          <nav className="hidden md:flex items-center space-x-1 text-xs font-medium text-neutral-400">
            <button
              onClick={onNavigateHome}
              className={`px-3 py-1.5 rounded-md transition ${
                currentView === 'home'
                  ? 'text-white bg-neutral-800 font-semibold'
                  : 'hover:text-white hover:bg-neutral-800/60'
              }`}
            >
              Home
            </button>
            {currentUser && (
              <button
                onClick={onNavigateHistory}
                className={`px-3 py-1.5 rounded-md transition flex items-center space-x-1.5 ${
                  currentView === 'history'
                    ? 'text-white bg-neutral-800 font-semibold'
                    : 'hover:text-white hover:bg-neutral-800/60'
                }`}
              >
                <span>History</span>
                {contracts.length > 0 && (
                  <span className="text-[10px] bg-neutral-700 text-neutral-200 px-1.5 py-0.2 rounded-full font-mono">
                    {contracts.length}
                  </span>
                )}
              </button>
            )}
            <button
              onClick={onOpenUpload}
              className="px-3 py-1.5 rounded-md hover:text-white hover:bg-neutral-800/60 transition"
            >
              Upload Document
            </button>
            <button
              onClick={onToggleChat}
              className="px-3 py-1.5 rounded-md hover:text-white hover:bg-neutral-800/60 transition"
            >
              Indian Legal Guide
            </button>
          </nav>
        </div>

        {/* Right Section: Actions, Theme Toggle & User Auth */}
        <div className="flex items-center space-x-2 sm:space-x-3">
          {/* Active Contract Switcher (visible in workspace for authenticated users) */}
          {currentUser && contracts.length > 0 && currentView === 'workspace' && (
            <div className="flex items-center space-x-1.5">
              <FileText className="w-4 h-4 text-neutral-500 hidden lg:block" />
              <select
                value={selectedContract?.id || ''}
                onChange={(e) => {
                  const found = contracts.find((c) => c.id === e.target.value);
                  if (found) onSelectContract(found);
                }}
                className="bg-[#18191e] hover:bg-[#202128] border border-[#27272a] text-xs font-medium text-neutral-200 rounded-md px-2.5 py-1.5 focus:outline-none focus:border-neutral-500 max-w-[150px] sm:max-w-[200px] truncate transition cursor-pointer shadow-xs"
                title="Switch document"
              >
                {contracts.map((c) => (
                  <option key={c.id} value={c.id} className="bg-[#121316] text-neutral-200">
                    {c.filename} ({c.total_pages} {c.total_pages === 1 ? 'pg' : 'pgs'})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Export Report CTA */}
          {auditReport && onExportReport && currentView === 'workspace' && (
            <button
              onClick={onExportReport}
              className="hidden lg:flex items-center space-x-1.5 bg-[#18191e] hover:bg-[#22232a] text-neutral-300 hover:text-white px-3 py-1.5 rounded-md text-xs font-medium border border-[#27272a] transition shadow-xs"
              title="Download summary report"
            >
              <Download className="w-3.5 h-3.5 text-neutral-400" />
              <span>Export</span>
            </button>
          )}

          {/* Legal Research / Chat Toggle */}
          <button
            onClick={onToggleChat}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium border transition ${
              isChatOpen
                ? 'bg-neutral-800 text-white border-neutral-700 shadow-xs'
                : 'bg-[#18191e] hover:bg-[#22232a] text-neutral-300 hover:text-white border-[#27272a]'
            }`}
            title="Ask questions to the Legal Assistant"
          >
            <MessageSquare className="w-3.5 h-3.5 text-neutral-400" />
            <span className="hidden sm:inline">Legal Assistant</span>
          </button>

          {/* Run Review CTA */}
          {selectedContract && currentView === 'workspace' && (
            <button
              onClick={onTriggerAudit}
              disabled={isAuditing}
              className="flex items-center space-x-1.5 bg-white hover:bg-neutral-200 disabled:opacity-50 text-neutral-950 px-3.5 py-1.5 rounded-md text-xs font-semibold shadow-xs transition cursor-pointer disabled:cursor-not-allowed"
            >
              {isAuditing ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-neutral-400 border-t-neutral-900 rounded-full animate-spin" />
                  <span>Reviewing...</span>
                </>
              ) : (
                <>
                  <Play className="w-3 h-3 fill-neutral-900" />
                  <span>Review Contract</span>
                </>
              )}
            </button>
          )}

          {/* Dark / Light Mode Toggle Button */}
          <button
            onClick={onToggleDarkMode}
            className="p-2 rounded-md bg-[#18191e] hover:bg-[#22232a] text-neutral-400 hover:text-neutral-100 border border-[#27272a] transition"
            title={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {isDarkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-neutral-400" />}
          </button>

          {/* User Auth Section */}
          {currentUser ? (
            <div className="relative">
              <button
                onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                className="flex items-center space-x-2 bg-[#18191e] hover:bg-[#22232a] border border-[#27272a] py-1 px-2.5 rounded-lg text-xs font-medium text-neutral-200 transition"
              >
                <div className="w-6 h-6 rounded-full bg-neutral-700 flex items-center justify-center text-white text-[11px] font-bold">
                  {currentUser.full_name ? currentUser.full_name.charAt(0).toUpperCase() : 'U'}
                </div>
                <span className="max-w-[100px] truncate hidden sm:inline">
                  {currentUser.full_name || currentUser.email}
                </span>
                <ChevronDown className="w-3.5 h-3.5 text-neutral-500" />
              </button>

              {isUserMenuOpen && (
                <div className="absolute right-0 mt-2 w-52 rounded-lg bg-[#18191e] border border-[#27272a] shadow-xl py-1 text-xs text-neutral-300 z-50">
                  <div className="px-3 py-2 border-b border-[#27272a]">
                    <p className="font-semibold text-white truncate">{currentUser.full_name || 'Legal Counsel'}</p>
                    <p className="text-[11px] text-neutral-500 truncate">{currentUser.email}</p>
                  </div>
                  <button
                    onClick={() => {
                      setIsUserMenuOpen(false);
                      onNavigateHistory();
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-neutral-800 text-neutral-200 hover:text-white flex items-center space-x-2 transition"
                  >
                    <FolderOpen className="w-3.5 h-3.5 text-neutral-400" />
                    <span>Contract History</span>
                  </button>
                  <button
                    onClick={() => {
                      setIsUserMenuOpen(false);
                      onSignOut();
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-neutral-800 text-red-400 hover:text-red-300 flex items-center space-x-2 transition border-t border-[#27272a]"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    <span>Sign Out</span>
                  </button>
                </div>
              )}
            </div>
          ) : (
            <button
              onClick={onOpenAuth}
              className="flex items-center space-x-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 border border-neutral-700 px-3 py-1.5 rounded-md text-xs font-semibold transition"
            >
              <UserIcon className="w-3.5 h-3.5" />
              <span>Sign In</span>
            </button>
          )}
        </div>
      </div>

      {/* Audit Progress Line */}
      {isAuditing && (
        <div className="h-0.5 w-full bg-neutral-800 overflow-hidden">
          <div className="h-full bg-neutral-200 w-full animate-pulse" />
        </div>
      )}
    </header>
  );
};
