import React, { useState } from 'react';
import { AlertCircle, CheckCircle2, ChevronDown, ChevronUp, MapPin, Shield } from 'lucide-react';
import { RiskFinding, RiskSeverity } from '../../types';
import { RedlineDiffViewer } from '../redline/RedlineDiffViewer';

interface FindingsListProps {
  findings: RiskFinding[];
  onSelectCitation: (page: number, text: string) => void;
}

export const FindingsList: React.FC<FindingsListProps> = ({
  findings,
  onSelectCitation,
}) => {
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');
  const [expandedId, setExpandedId] = useState<string | null>(findings[0]?.id || null);

  const getSeverityBadge = (severity: RiskSeverity) => {
    switch (severity) {
      case 'CRITICAL':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'HIGH':
        return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
      case 'MEDIUM':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'LOW':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      default:
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
    }
  };

  const filtered = findings.filter((f) => {
    if (filterSeverity === 'ALL') return true;
    return f.severity === filterSeverity;
  });

  return (
    <div>
      {/* Filters Bar */}
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-sm font-semibold text-white flex items-center space-x-2">
          <span>Identified Deviations & Clauses</span>
          <span className="text-xs bg-slate-800 text-slate-400 font-mono px-2 py-0.5 rounded-full">
            {findings.length}
          </span>
        </h4>

        <div className="flex items-center space-x-1.5 text-xs">
          {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'ACCEPTABLE'].map((sev) => (
            <button
              key={sev}
              onClick={() => setFilterSeverity(sev)}
              className={`px-2.5 py-1 rounded-md transition font-medium ${
                filterSeverity === sev
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              {sev}
            </button>
          ))}
        </div>
      </div>

      {/* Cards List */}
      <div className="space-y-3">
        {filtered.map((item) => {
          const isExpanded = expandedId === item.id;
          return (
            <div
              key={item.id}
              className="bg-slate-900/70 border border-slate-800 hover:border-slate-700 rounded-xl transition overflow-hidden shadow-sm"
            >
              <div
                onClick={() => setExpandedId(isExpanded ? null : item.id)}
                className="p-4 cursor-pointer flex items-start justify-between select-none"
              >
                <div className="flex items-start space-x-3">
                  <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-md border mt-0.5 ${getSeverityBadge(item.severity)}`}>
                    {item.severity}
                  </span>
                  <div>
                    <h5 className="text-sm font-semibold text-white tracking-tight">{item.clause_category}</h5>
                    <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">{item.deviation_explanation}</p>
                  </div>
                </div>

                <div className="flex items-center space-x-3 shrink-0">
                  {/* Jump to Page citation button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectCitation(item.page_number, item.original_text);
                    }}
                    className="flex items-center space-x-1 text-xs text-indigo-400 bg-indigo-500/10 hover:bg-indigo-500/20 px-2.5 py-1 rounded-md border border-indigo-500/30 transition"
                  >
                    <MapPin className="w-3.5 h-3.5" />
                    <span>Page {item.page_number}</span>
                  </button>

                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4 text-slate-500" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-slate-500" />
                  )}
                </div>
              </div>

              {/* Expanded Card Details */}
              {isExpanded && (
                <div className="px-4 pb-4 pt-1 border-t border-slate-800/80 text-xs space-y-3">
                  {/* Playbook Standard */}
                  <div>
                    <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block mb-1">
                      Standard Playbook Guideline
                    </span>
                    <p className="text-slate-300 bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/60 leading-relaxed">
                      {item.playbook_rule || 'Corporate standard policy applies.'}
                    </p>
                  </div>

                  {/* Redline comparison */}
                  {item.proposed_redline && item.severity !== 'ACCEPTABLE' && (
                    <RedlineDiffViewer
                      originalText={item.original_text}
                      proposedRedline={item.proposed_redline}
                    />
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

