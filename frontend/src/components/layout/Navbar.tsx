import React from 'react';
import { ShieldAlert, FileText, Play, UploadCloud, MessageSquare } from 'lucide-react';
import { Contract } from '../../types';

interface NavbarProps {
  contracts: Contract[];
  selectedContract: Contract | null;
  onSelectContract: (contract: Contract) => void;
  onOpenUpload: () => void;
  onTriggerAudit: () => void;
  isAuditing: boolean;
  onToggleChat: () => void;
  isChatOpen: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  contracts,
  selectedContract,
  onSelectContract,
  onOpenUpload,
  onTriggerAudit,
  isAuditing,
  onToggleChat,
  isChatOpen,
}) => {
  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/90 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center space-x-3">
        <div className="w-9 h-9 rounded-lg bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-600/30">
          <ShieldAlert className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-bold text-lg text-white tracking-tight">LexAI</span>
            <span className="text-xs bg-indigo-500/20 text-indigo-400 font-mono px-2 py-0.5 rounded border border-indigo-500/30">RAG 2.0</span>
          </div>
          <p className="text-xs text-slate-400">Enterprise Contract Intelligence & Redlining</p>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {/* Contract Selector */}
        {contracts.length > 0 && (
          <div className="flex items-center space-x-2">
            <FileText className="w-4 h-4 text-slate-400" />
            <select
              value={selectedContract?.id || ''}
              onChange={(e) => {
                const found = contracts.find((c) => c.id === e.target.value);
                if (found) onSelectContract(found);
              }}
              className="bg-slate-800 border border-slate-700 text-sm text-slate-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500 max-w-xs truncate"
            >
              {contracts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.filename} ({c.total_pages} pgs)
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Upload Button */}
        <button
          onClick={onOpenUpload}
          className="flex items-center space-x-2 bg-slate-800 hover:bg-slate-700 text-slate-200 px-3.5 py-1.5 rounded-lg text-sm font-medium border border-slate-700 transition"
        >
          <UploadCloud className="w-4 h-4 text-slate-300" />
          <span>Upload Contract</span>
        </button>

        {/* Chat / Legal Research Drawer Toggle */}
        <button
          onClick={onToggleChat}
          className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-sm font-medium border transition ${
            isChatOpen
              ? 'bg-indigo-600/20 text-indigo-300 border-indigo-500/50'
              : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          <span>Legal Copilot & Indian Law</span>
        </button>

        {/* Run Audit Button */}
        {selectedContract && (
          <button
            onClick={onTriggerAudit}
            disabled={isAuditing}
            className="flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 text-white px-4 py-1.5 rounded-lg text-sm font-semibold shadow-md shadow-indigo-600/20 transition cursor-pointer disabled:cursor-not-allowed"
          >
            {isAuditing ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Auditing Playbook...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-white" />
                <span>Run Playbook Audit</span>
              </>
            )}
          </button>
        )}
      </div>
    </header>
  );
};

