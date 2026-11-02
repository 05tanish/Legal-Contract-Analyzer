import React, { useState } from 'react';
import { Send, X, Bot, User, MapPin, Sparkles } from 'lucide-react';
import { askContract } from '../../lib/api';
import { ClauseCitation } from '../../types';

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  citations?: ClauseCitation[];
}

interface ContractChatDrawerProps {
  contractId: string;
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
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'init-1',
      sender: 'assistant',
      text: 'Hello! I am your Legal Contract Copilot. Ask me any question about clauses, indemnities, liability limits, or termination rights in this document.',
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
      const res = await askContract(contractId, input);
      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: res.answer,
        citations: res.citations,
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
    <div className="w-96 border-l border-slate-800 bg-slate-900/95 flex flex-col h-full shadow-2xl z-20 shrink-0">
      {/* Header */}
      <div className="h-12 border-b border-slate-800 px-4 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Bot className="w-4 h-4 text-indigo-400" />
          <span className="text-sm font-semibold text-white">Legal Copilot</span>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-white">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Messages Feed */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4 text-xs">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex flex-col ${m.sender === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div
              className={`p-3 rounded-xl max-w-[90%] leading-relaxed ${
                m.sender === 'user'
                  ? 'bg-indigo-600 text-white font-medium'
                  : 'bg-slate-800/80 text-slate-200 border border-slate-700/60'
              }`}
            >
              <p className="whitespace-pre-line">{m.text}</p>

              {/* Grounded Citations */}
              {m.citations && m.citations.length > 0 && (
                <div className="mt-2.5 pt-2 border-t border-slate-700/60 space-y-1.5">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block">
                    Grounded Citations:
                  </span>
                  {m.citations.map((c, i) => (
                    <button
                      key={i}
                      onClick={() => onSelectCitation(c.page_number, c.verbatim_text)}
                      className="flex items-center space-x-1.5 text-[11px] text-indigo-400 hover:text-indigo-300 bg-indigo-950/40 border border-indigo-500/20 px-2 py-0.5 rounded w-full text-left truncate transition"
                    >
                      <MapPin className="w-3 h-3 shrink-0" />
                      <span className="truncate">Page {c.page_number}: {c.verbatim_text}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex items-center space-x-2 text-slate-400">
            <div className="w-3 h-3 border border-indigo-400 border-t-transparent rounded-full animate-spin" />
            <span>Consulting contract embeddings...</span>
          </div>
        )}
      </div>

      {/* Input Box */}
      <form onSubmit={handleSend} className="p-3 border-t border-slate-800 flex items-center space-x-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about this contract..."
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

