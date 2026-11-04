import React, { useState } from 'react';
import { Send, X, Scale, ExternalLink, Copy, Check, Trash2 } from 'lucide-react';
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
  timestamp?: string;
}

interface ContractChatDrawerProps {
  contractId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onSelectCitation: (page: number, text: string) => void;
}

const STARTER_PROMPTS = [
  { label: 'Is the non-compete enforceable?', query: 'Is the non-compete clause in my agreement enforceable under Indian law?' },
  { label: 'Termination notice period?', query: 'What is the termination notice period and breach remedies specified in the contract?' },
  { label: 'Can employer restrict future jobs?', query: 'Explain Section 27 of the Indian Contract Act and landmark Supreme Court rulings on restraint of trade.' },
  { label: 'Which courts have jurisdiction?', query: 'What is the governing law, dispute resolution venue, and arbitration mechanism?' },
];

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
      text: 'Hello! I\'m your ContractIQ Legal Assistant.\n\nAsk me anything about your agreement or your rights under Indian law. For example:\n• "Is my non-compete clause legally binding?"\n• "What happens if I terminate early?"\n• "Are there any one-sided liability clauses in this agreement?"',
      timestamp: 'Just now',
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSendQuery = async (queryText: string) => {
    if (!queryText.trim() || isLoading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text: queryText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await askLegalPlatform(queryText, contractId || undefined, activeMode);
      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: res.answer,
        modeUsed: res.mode_used,
        citations: res.citations,
        legalCitations: res.legal_citations,
        enforceabilityRisk: res.risk_assessment?.enforceability_concern,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: 'assistant',
          text: 'I was unable to retrieve an answer right now. Please try asking again in a moment.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleClear = () => {
    setMessages([
      {
        id: Date.now().toString(),
        sender: 'assistant',
        text: 'Chat history cleared. What would you like to know about your contract or Indian law?',
        timestamp: 'Just now',
      },
    ]);
  };

  return (
    <aside className="fixed inset-y-0 right-0 w-full sm:w-[460px] md:w-[500px] bg-white dark:bg-[#121316] text-neutral-900 dark:text-neutral-100 border-l border-neutral-200 dark:border-[#23252a] z-40 flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
      {/* Header */}
      <div className="h-16 border-b border-neutral-200 dark:border-[#23252a] px-4 flex items-center justify-between bg-white dark:bg-[#121316] shrink-0">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded bg-neutral-900 dark:bg-neutral-800 flex items-center justify-center text-white">
            <Scale className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-serif font-bold text-base text-neutral-900 dark:text-white leading-tight">
              Legal Contract Assistant
            </h3>
            <p className="text-[11px] text-neutral-500 dark:text-neutral-400">
              Clear answers about your contract & Indian legal rights
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-1">
          <button
            onClick={handleClear}
            className="p-1.5 rounded-md text-neutral-400 hover:text-neutral-700 dark:hover:text-white hover:bg-neutral-100 dark:hover:bg-neutral-800 transition"
            title="Clear chat history"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          <button
            onClick={onClose}
            className="p-1.5 rounded-md text-neutral-400 hover:text-neutral-700 dark:hover:text-white hover:bg-neutral-100 dark:hover:bg-neutral-800 transition"
            title="Close Assistant"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Legal Guardrail & Informational Guidance Banner */}
      <div className="bg-neutral-900 border-b border-neutral-800 px-4 py-1.5 text-[10px] text-neutral-400 flex items-center justify-between">
        <span>Informational Legal Guidance. Not formal attorney representation.</span>
        <span className="font-mono text-neutral-400">Indian Law Corpus</span>
      </div>

      {/* Mode Selector Tabs */}
      <div className="px-4 py-2 border-b border-neutral-200 dark:border-[#23252a] bg-neutral-50/70 dark:bg-[#18191e] flex items-center space-x-1.5 text-xs shrink-0">
        <span className="text-[10px] uppercase font-bold text-neutral-400 mr-1 font-mono">Scope:</span>
        <button
          onClick={() => setActiveMode('HYBRID')}
          disabled={!contractId}
          className={`px-2.5 py-1 rounded-md font-medium transition ${
            activeMode === 'HYBRID'
              ? 'bg-neutral-900 dark:bg-white text-white dark:text-neutral-950 font-semibold shadow-xs'
              : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white hover:bg-neutral-200/60 dark:hover:bg-neutral-800 disabled:opacity-40'
          }`}
          title="Compare contract clauses against Indian legal standards"
        >
          Contract & Indian Law
        </button>
        <button
          onClick={() => setActiveMode('CONTRACT_ONLY')}
          disabled={!contractId}
          className={`px-2.5 py-1 rounded-md font-medium transition ${
            activeMode === 'CONTRACT_ONLY'
              ? 'bg-neutral-900 dark:bg-white text-white dark:text-neutral-950 font-semibold shadow-xs'
              : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white hover:bg-neutral-200/60 dark:hover:bg-neutral-800 disabled:opacity-40'
          }`}
          title="Search within this agreement only"
        >
          This Contract
        </button>
        <button
          onClick={() => setActiveMode('LEGAL_ONLY')}
          className={`px-2.5 py-1 rounded-md font-medium transition ${
            activeMode === 'LEGAL_ONLY'
              ? 'bg-neutral-900 dark:bg-white text-white dark:text-neutral-950 font-semibold shadow-xs'
              : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white hover:bg-neutral-200/60 dark:hover:bg-neutral-800'
          }`}
          title="General inquiries on Indian Bare Acts and Supreme Court rulings"
        >
          Indian Legal Guide
        </button>
      </div>

      {/* Message List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m) => {
          const isUser = m.sender === 'user';
          return (
            <div
              key={m.id}
              className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
            >
              <div
                className={`max-w-[90%] rounded-lg p-3.5 text-xs shadow-xs ${
                  isUser
                    ? 'bg-neutral-900 dark:bg-neutral-800 text-white'
                    : 'bg-neutral-50 dark:bg-[#18191e] text-neutral-800 dark:text-neutral-200 border border-neutral-200 dark:border-[#27272a]'
                }`}
              >
                {/* Assistant Message Header */}
                {!isUser && (
                  <div className="flex items-center justify-between mb-1.5 pb-1 border-b border-neutral-200/60 dark:border-[#27272a] text-[10px] text-neutral-500 dark:text-neutral-400">
                    <span className="font-semibold text-neutral-700 dark:text-neutral-300">ContractIQ Explanation</span>
                    <button
                      onClick={() => handleCopy(m.id, m.text)}
                      className="text-neutral-400 hover:text-neutral-700 dark:hover:text-white flex items-center space-x-1"
                      title="Copy response"
                    >
                      {copiedId === m.id ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                    </button>
                  </div>
                )}

                {/* Body Content without raw markdown asterisks */}
                <div className="whitespace-pre-line leading-relaxed font-sans">
                  {m.text.replace(/\*\*/g, '')}
                </div>

                {/* Grounded Contract Citations */}
                {m.citations && m.citations.length > 0 && (
                  <div className="mt-3 pt-2.5 border-t border-neutral-200 dark:border-[#27272a] space-y-1.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-500 dark:text-neutral-400 block">
                      Found in your contract
                    </span>
                    {m.citations.map((c, i) => (
                      <div
                        key={i}
                        onClick={() => onSelectCitation(c.page_number, c.verbatim_text)}
                        className="bg-white dark:bg-[#121316] p-2 rounded border border-neutral-200 dark:border-[#27272a] hover:border-neutral-400 dark:hover:border-neutral-600 cursor-pointer transition text-[11px]"
                      >
                        <div className="font-semibold text-neutral-800 dark:text-neutral-200 flex items-center justify-between">
                          <span>Page {c.page_number}</span>
                          <span className="text-neutral-400 text-[10px]">View in document →</span>
                        </div>
                        <p className="font-mono text-neutral-600 dark:text-neutral-400 line-clamp-2 mt-0.5">
                          "{c.verbatim_text}"
                        </p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Statutory Indian Law Citations */}
                {m.legalCitations && m.legalCitations.length > 0 && (
                  <div className="mt-3 pt-2.5 border-t border-neutral-200 dark:border-[#27272a] space-y-1.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800 dark:text-amber-400 block">
                      Relevant Indian Laws & Landmark Rulings
                    </span>
                    {m.legalCitations.map((lc, idx) => (
                      <div key={idx} className="bg-amber-50/50 dark:bg-amber-950/20 p-2 rounded border border-amber-200 dark:border-amber-900/40 text-[11px]">
                        <div className="font-semibold text-neutral-900 dark:text-neutral-100">
                          {lc.act_name ? `${lc.act_name} § ${lc.section_number}` : lc.case_title}
                        </div>
                        {lc.principle && (
                          <p className="text-neutral-700 dark:text-neutral-300 mt-0.5 leading-relaxed">
                            {lc.principle}
                          </p>
                        )}
                        {lc.official_url && (
                          <a
                            href={lc.official_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-neutral-900 dark:text-neutral-200 underline text-[10px] flex items-center space-x-1 mt-1 font-medium"
                          >
                            <span>Read official law or court case</span>
                            <ExternalLink className="w-2.5 h-2.5" />
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <span className="text-[10px] text-neutral-400 dark:text-neutral-500 mt-1 font-mono px-1">
                {m.timestamp}
              </span>
            </div>
          );
        })}

        {isLoading && (
          <div className="flex items-center space-x-2 text-xs text-neutral-500 dark:text-neutral-400 p-3 bg-neutral-50 dark:bg-[#18191e] rounded-lg border border-neutral-200 dark:border-[#27272a] w-fit">
            <div className="w-3.5 h-3.5 border-2 border-neutral-400 border-t-neutral-800 dark:border-t-white rounded-full animate-spin" />
            <span>Looking up contract clauses and relevant legal rulings...</span>
          </div>
        )}
      </div>

      {/* Starter Prompts */}
      <div className="px-4 py-2 border-t border-neutral-200 dark:border-[#23252a] bg-neutral-50/60 dark:bg-[#18191e]/60 overflow-x-auto whitespace-nowrap shrink-0">
        <div className="flex space-x-1.5">
          {STARTER_PROMPTS.map((p, idx) => (
            <button
              key={idx}
              onClick={() => handleSendQuery(p.query)}
              disabled={isLoading}
              className="text-[11px] bg-white dark:bg-[#18191e] hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-700 dark:text-neutral-300 px-2.5 py-1 rounded-md border border-neutral-200 dark:border-[#27272a] transition font-medium disabled:opacity-50"
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Input Box */}
      <div className="p-4 border-t border-neutral-200 dark:border-[#23252a] bg-white dark:bg-[#121316] shrink-0">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendQuery(input);
          }}
          className="flex items-center space-x-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
            placeholder="Ask a question about your contract or Indian law..."
            className="flex-1 bg-neutral-50 dark:bg-[#18191e] border border-neutral-300 dark:border-[#27272a] rounded-md px-3 py-2 text-xs text-neutral-900 dark:text-white placeholder-neutral-400 dark:placeholder-neutral-500 focus:outline-none focus:border-neutral-500"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="bg-neutral-900 dark:bg-white hover:bg-neutral-800 dark:hover:bg-neutral-200 disabled:opacity-40 text-white dark:text-neutral-950 p-2 rounded-md transition cursor-pointer disabled:cursor-not-allowed shadow-xs"
            title="Send inquiry"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </aside>
  );
};
