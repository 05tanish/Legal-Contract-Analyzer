import React, { useState } from 'react';
import { Send, X, MapPin, Scale, BookOpen, ExternalLink } from 'lucide-react';
import { askLegalPlatform } from '../../lib/api';
import { ClauseCitation, LegalCitation, QueryMode } from '../../types';

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  modeUsed?: QueryMode;
  citations?: ClauseCitation[];
  legalCitations?: LegalCitation[];
  enforceabilityRisk?: string;
}

interface ContractChatDrawerProps {
  contractId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onSelectCitation: (page: number, text: string) => void;
}

export const ContractChatDrawer: React.FC<ContractChatDrawerProps> = ({
  contractId,
  isOpen,
  onClose,
  onSelectCitation,
}) => {
  const [activeMode, setActiveMode] = useState<QueryMode>(contractId ? 'HYBRID' : 'LEGAL_ONLY');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'init-1',
      sender: 'assistant',
      text: 'Welcome to LexAI Indian Legal Research & Contract Copilot.\n\nChoose a mode above:\n• **Contract Only:** Query your uploaded agreement.\n• **Indian Law:** Search the Constitution, Bare Acts & Supreme Court precedents.\n• **Hybrid Analysis:** Check if your contract clauses comply with Indian law.',
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  if (!isOpen) return null;

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text: input,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await askLegalPlatform(input, contractId || undefined, activeMode);
      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: res.answer,
        modeUsed: res.mode_used,
        citations: res.citations,
        legalCitations: res.legal_citations,
        enforceabilityRisk: res.risk_assessment?.enforceability_concern,
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: 'assistant',
          text: 'Error generating response. Please ensure backend services are active.',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-[430px] border-l border-slate-800 bg-slate-900/95 flex flex-col h-full shadow-2xl z-20 shrink-0">
      {/* Header */}
      <div className="h-14 border-b border-slate-800 px-4 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Scale className="w-4 h-4 text-indigo-400" />
          <span className="text-sm font-semibold text-white tracking-tight">LexAI Research & Copilot</span>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-white transition">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* 3-Mode Selector Pill Bar */}
      <div className="bg-slate-950/70 p-2.5 border-b border-slate-800">
        <div className="grid grid-cols-3 gap-1 bg-slate-900 p-1 rounded-lg border border-slate-800 text-[11px] font-medium">
          <button
            onClick={() => setActiveMode('CONTRACT_ONLY')}
            disabled={!contractId}
            className={`py-1 rounded-md transition ${
              activeMode === 'CONTRACT_ONLY'
                ? 'bg-indigo-600 text-white font-semibold'
                : 'text-slate-400 hover:text-slate-200 disabled:opacity-30'
            }`}
          >
            Contract
          </button>
          <button
            onClick={() => setActiveMode('LEGAL_ONLY')}
            className={`py-1 rounded-md transition ${
              activeMode === 'LEGAL_ONLY'
                ? 'bg-indigo-600 text-white font-semibold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Indian Law
          </button>
          <button
            onClick={() => setActiveMode('HYBRID')}
            disabled={!contractId}
            className={`py-1 rounded-md transition ${
              activeMode === 'HYBRID'
                ? 'bg-indigo-600 text-white font-semibold'
                : 'text-slate-400 hover:text-slate-200 disabled:opacity-30'
            }`}
          >
            Hybrid
          </button>
        </div>
      </div>

      {/* Messages Feed */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4 text-xs">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex flex-col ${m.sender === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div
              className={`p-3.5 rounded-xl max-w-[95%] leading-relaxed ${
                m.sender === 'user'
                  ? 'bg-indigo-600 text-white font-medium'
                  : 'bg-slate-800/80 text-slate-200 border border-slate-700/60'
              }`}
            >
              {/* Mode indicator badge */}
              {m.modeUsed && (
                <div className="flex items-center space-x-1.5 mb-2">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-semibold uppercase">
                    {m.modeUsed.replace('_', ' ')}
                  </span>
                  {m.enforceabilityRisk && (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-red-500/20 text-red-300 border border-red-500/30 font-semibold uppercase">
                      {m.enforceabilityRisk} RISK
                    </span>
                  )}
                </div>
              )}

              <p className="whitespace-pre-line text-slate-200">{m.text}</p>

              {/* Contract Citations */}
              {m.citations && m.citations.length > 0 && (
                <div className="mt-3 pt-2.5 border-t border-slate-700/60 space-y-1.5">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center space-x-1">
                    <BookOpen className="w-3 h-3 text-indigo-400" />
                    <span>Contract Citations:</span>
                  </span>
                  {m.citations.map((c, i) => (
                    <button
                      key={i}
                      onClick={() => onSelectCitation(c.page_number, c.verbatim_text)}
                      className="flex items-center space-x-1.5 text-[11px] text-indigo-300 hover:text-indigo-200 bg-indigo-950/40 hover:bg-indigo-950/70 border border-indigo-500/30 px-2 py-1 rounded w-full text-left truncate transition"
                    >
                      <MapPin className="w-3 h-3 shrink-0 text-indigo-400" />
                      <span className="truncate">Page {c.page_number}: {c.verbatim_text}</span>
                    </button>
                  ))}
                </div>
              )}

              {/* Indian Legal Citations */}
              {m.legalCitations && m.legalCitations.length > 0 && (
                <div className="mt-2.5 pt-2 border-t border-slate-700/60 space-y-1.5">
                  <span className="text-[10px] uppercase font-bold text-emerald-400 tracking-wider flex items-center space-x-1">
                    <Scale className="w-3 h-3 text-emerald-400" />
                    <span>Indian Statutory & Judicial Citations:</span>
                  </span>
                  {m.legalCitations.map((lc, idx) => (
                    <div
                      key={idx}
                      className="text-[11px] bg-emerald-950/20 border border-emerald-500/30 rounded p-2 text-emerald-200 space-y-0.5"
                    >
                      <div className="flex items-center justify-between font-semibold text-emerald-300">
                        <span>
                          {lc.citation_type === 'COURT_JUDGMENT'
                            ? `⚖️ ${lc.case_title}`
                            : `📜 ${lc.act_name} - ${lc.section_number}`}
                        </span>
                        {lc.official_url && (
                          <a
                            href={lc.official_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-emerald-400 hover:text-white inline-flex items-center space-x-0.5"
                          >
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                      <p className="text-[10px] text-slate-300 font-mono italic">
                        {lc.principle || lc.section_title || 'Binding legal authority'}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex items-center space-x-2 text-slate-400 text-xs">
            <div className="w-3 h-3 border border-indigo-400 border-t-transparent rounded-full animate-spin" />
            <span>Consulting contract & Indian law vectors...</span>
          </div>
        )}
      </div>

      {/* Input Box */}
      <form onSubmit={handleSend} className="p-3 border-t border-slate-800 flex items-center space-x-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={
            activeMode === 'LEGAL_ONLY'
              ? 'Ask about Indian Constitution, Acts or Supreme Court law...'
              : activeMode === 'HYBRID'
              ? 'Ask if contract terms are valid under Indian law...'
              : 'Ask a question about this contract...'
          }
          className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
        <button
          type="submit"
          disabled={!input.trim() || isLoading}
          className="p-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white rounded-lg transition"
        >
          <Send className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
};
