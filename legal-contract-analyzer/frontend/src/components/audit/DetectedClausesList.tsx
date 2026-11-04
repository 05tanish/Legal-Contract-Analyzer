import React, { useState, useMemo } from 'react';
import {
  Search,
  Lock,
  ArrowRight,
  Sparkles
} from 'lucide-react';
import { DetectedClause, RiskSeverity } from '../../types';

interface DetectedClausesListProps {
  clauses: DetectedClause[];
  isGuest: boolean;
  onSelectCitation: (page: number, text: string) => void;
  onOpenAuth?: () => void;
}

export const DetectedClausesList: React.FC<DetectedClausesListProps> = ({
  clauses,
  isGuest,
  onSelectCitation,
  onOpenAuth,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterSeverity, setFilterSeverity] = useState('ALL');

  const filtered = useMemo(() => {
    return clauses.filter((c) => {
      const matchSeverity = filterSeverity === 'ALL' || c.severity === filterSeverity;
      const matchSearch =
        !searchQuery.trim() ||
        c.category_title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.snippet.toLowerCase().includes(searchQuery.toLowerCase());
      return matchSeverity && matchSearch;
    });
  }, [clauses, filterSeverity, searchQuery]);

  const getBadge = (severity: RiskSeverity) => {
    switch (severity) {
      case 'CRITICAL':
        return 'bg-red-950/60 text-red-300 border-red-800/80';
      case 'HIGH':
        return 'bg-rose-950/60 text-rose-300 border-rose-800/80';
      case 'MEDIUM':
        return 'bg-amber-950/60 text-amber-300 border-amber-800/80';
      default:
        return 'bg-neutral-800 text-neutral-300 border-neutral-700';
    }
  };

  return (
    <div className="space-y-4">
      {/* Guest Mode Explanatory Notice */}
      {isGuest && (
        <div className="p-4 bg-[#14151a] border border-[#27272f] rounded-lg flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs shadow-xs">
          <div className="flex items-start space-x-3">
            <div className="w-8 h-8 rounded-full bg-neutral-800 flex items-center justify-center shrink-0 mt-0.5 text-neutral-300">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h5 className="font-semibold text-neutral-200">
                Lightweight Clause Detection (Guest Mode)
              </h5>
              <p className="text-neutral-400 mt-0.5">
                Identified {clauses.length} standard legal clauses using pre-trained NLP models.
                Sign in to run full multi-agent risk audits, Indian statutory verification, and automated redlines.
              </p>
            </div>
          </div>
          {onOpenAuth && (
            <button
              onClick={onOpenAuth}
              className="bg-white hover:bg-neutral-200 text-neutral-950 px-3.5 py-1.5 rounded-md text-xs font-semibold shrink-0 transition flex items-center space-x-1.5 shadow-xs"
            >
              <Lock className="w-3 h-3" />
              <span>Unlock Full Audit</span>
            </button>
          )}
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="p-3 bg-[#131418] border border-[#23252a] rounded-lg flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5">
        <div className="relative flex-1">
          <Search className="w-3.5 h-3.5 text-neutral-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search detected clauses or keywords..."
            className="w-full bg-[#18191e] border border-[#27272a] rounded-md pl-9 pr-3 py-1.5 text-xs text-neutral-200 placeholder-neutral-500 focus:outline-hidden focus:border-neutral-500 font-sans"
          />
        </div>
        <div className="flex items-center space-x-1 overflow-x-auto">
          {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'].map((sev) => (
            <button
              key={sev}
              onClick={() => setFilterSeverity(sev)}
              className={`px-2.5 py-1 rounded text-[11px] font-medium transition ${
                filterSeverity === sev
                  ? 'bg-neutral-800 text-white border border-neutral-700'
                  : 'text-neutral-400 hover:text-neutral-200'
              }`}
            >
              {sev === 'ALL' ? `All (${clauses.length})` : sev}
            </button>
          ))}
        </div>
      </div>

      {/* Clauses Cards List */}
      <div className="space-y-2.5">
        {filtered.length === 0 ? (
          <div className="p-8 text-center bg-[#131418] border border-[#23252a] rounded-lg text-xs text-neutral-400">
            No clauses match the current filter.
          </div>
        ) : (
          filtered.map((clause, idx) => (
            <div
              key={`${clause.category_id}_${clause.page_number}_${idx}`}
              className="p-4 bg-[#131418] hover:bg-[#16171d] border border-[#23252a] rounded-lg transition shadow-xs"
            >
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="flex items-center space-x-2">
                  <span className="font-serif font-bold text-sm text-neutral-100">
                    {clause.category_title}
                  </span>
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${getBadge(clause.severity)}`}>
                    {clause.severity}
                  </span>
                </div>
                <button
                  onClick={() => onSelectCitation(clause.page_number, clause.snippet)}
                  className="text-xs text-neutral-400 hover:text-white flex items-center space-x-1 transition underline shrink-0"
                  title={`View on Page ${clause.page_number}`}
                >
                  <span>Page {clause.page_number}</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>

              <p className="text-xs text-neutral-400 mb-2.5">
                {clause.description}
              </p>

              <div className="bg-[#18191e] p-2.5 rounded border border-[#27272a] text-xs font-mono text-neutral-300 italic">
                "{clause.snippet}"
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

