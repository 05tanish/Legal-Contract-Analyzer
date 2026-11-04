import React, { useState, useMemo } from 'react';
import { ChevronDown, ChevronUp, MapPin, Search, AlertCircle, BookOpen } from 'lucide-react';
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
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [expandedId, setExpandedId] = useState<string | null>(findings[0]?.id || null);

  const getSeverityBadge = (severity: RiskSeverity) => {
    switch (severity) {
      case 'CRITICAL':
        return { label: 'CRITICAL', class: 'bg-red-50 text-red-700 border-red-200 dark:bg-red-950/40 dark:text-red-300 dark:border-red-900/60' };
      case 'HIGH':
        return { label: 'HIGH RISK', class: 'bg-red-50 text-red-700 border-red-200 dark:bg-red-950/40 dark:text-red-300 dark:border-red-900/60' };
      case 'MEDIUM':
        return { label: 'MODERATE', class: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-900/60' };
      case 'LOW':
        return { label: 'LOW RISK', class: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-900/60' };
      default:
        return { label: 'SAFE', class: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-900/60' };
    }
  };

  const filterTabs = [
    { key: 'ALL', label: 'All Issues' },
    { key: 'CRITICAL', label: 'Critical' },
    { key: 'HIGH', label: 'High Risk' },
    { key: 'MEDIUM', label: 'Moderate' },
    { key: 'ACCEPTABLE', label: 'Standard' },
  ];

  const filtered = useMemo(() => {
    return findings.filter((f) => {
      const matchSeverity = filterSeverity === 'ALL' || f.severity === filterSeverity;
      const matchSearch =
        !searchQuery.trim() ||
        f.clause_category.toLowerCase().includes(searchQuery.toLowerCase()) ||
        f.deviation_explanation?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        f.original_text.toLowerCase().includes(searchQuery.toLowerCase());
      return matchSeverity && matchSearch;
    });
  }, [findings, filterSeverity, searchQuery]);

  return (
    <div className="space-y-4">
      {/* Search & Filter Bar */}
      <div className="saas-card p-3 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 bg-white dark:bg-[#131418] border border-neutral-200 dark:border-[#23252a] rounded-lg">
        {/* Search Input */}
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-neutral-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by keyword (e.g., liability, termination, non-compete)..."
            className="w-full bg-neutral-50/70 dark:bg-[#18191e] border border-neutral-300 dark:border-[#27272a] rounded-md pl-9 pr-3 py-1.5 text-xs text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 dark:placeholder-neutral-500 focus:outline-none focus:border-neutral-500"
          />
        </div>

        {/* Severity Filter Tabs */}
        <div className="flex items-center space-x-1 text-xs overflow-x-auto pb-1 md:pb-0">
          {filterTabs.map((tab) => {
            const count = tab.key === 'ALL' ? findings.length : findings.filter((f) => f.severity === tab.key).length;
            const isActive = filterSeverity === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => setFilterSeverity(tab.key)}
                className={`px-2.5 py-1 rounded-md transition font-medium text-xs whitespace-nowrap flex items-center space-x-1 border ${
                  isActive
                    ? 'bg-neutral-900 dark:bg-white text-white dark:text-neutral-950 border-neutral-900 dark:border-white shadow-xs font-semibold'
                    : 'bg-white dark:bg-[#18191e] text-neutral-600 dark:text-neutral-400 border-neutral-200 dark:border-[#27272a] hover:bg-neutral-50 dark:hover:bg-neutral-800 hover:text-neutral-900 dark:hover:text-white'
                }`}
              >
                <span>{tab.label}</span>
                <span className={`text-[10px] font-mono ${isActive ? 'text-neutral-300 dark:text-neutral-700' : 'text-neutral-400 dark:text-neutral-500'}`}>
                  ({count})
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Findings Accordion Items */}
      <div className="space-y-3">
        {filtered.length === 0 ? (
          <div className="text-center p-8 saas-card bg-white dark:bg-[#131418] border border-neutral-200 dark:border-[#23252a] text-neutral-500 dark:text-neutral-400 text-xs rounded-lg">
            No issues found matching your search. Everything looks clear under these filters.
          </div>
        ) : (
          filtered.map((item) => {
            const isExpanded = expandedId === item.id;
            const badge = getSeverityBadge(item.severity);
            return (
              <div
                key={item.id}
                className="saas-card bg-white dark:bg-[#131418] border border-neutral-200 dark:border-[#23252a] rounded-lg transition overflow-hidden"
              >
                {/* Header Row */}
                <div
                  onClick={() => setExpandedId(isExpanded ? null : item.id)}
                  className={`p-4 flex items-center justify-between cursor-pointer select-none transition ${
                    isExpanded
                      ? 'bg-neutral-50/80 dark:bg-[#18191e] border-b border-neutral-200 dark:border-[#23252a]'
                      : 'hover:bg-neutral-50/50 dark:hover:bg-neutral-800/30'
                  }`}
                >
                  <div className="flex items-center space-x-3 truncate">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase tracking-wider shrink-0 ${badge.class}`}
                    >
                      {badge.label}
                    </span>

                    <h4 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 truncate">
                      {item.clause_category}
                    </h4>

                    {item.section_reference && (
                      <span className="text-xs text-neutral-500 dark:text-neutral-400 font-mono hidden sm:inline">
                        § {item.section_reference}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center space-x-3 shrink-0 ml-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectCitation(item.page_number, item.original_text);
                      }}
                      className="hidden sm:inline-flex items-center space-x-1 text-xs text-neutral-600 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-white bg-white dark:bg-neutral-800 hover:bg-neutral-100 dark:hover:bg-neutral-700 px-2 py-1 rounded border border-neutral-200 dark:border-neutral-700 transition"
                      title="Jump to page in contract PDF"
                    >
                      <MapPin className="w-3 h-3 text-neutral-500 dark:text-neutral-400" />
                      <span>Page {item.page_number}</span>
                    </button>

                    <div className="text-neutral-400 dark:text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-200">
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </div>
                  </div>
                </div>

                {/* Expanded Details Body */}
                {isExpanded && (
                  <div className="p-4 sm:p-5 space-y-4 text-xs">
                    {/* Verbatim Contract Quote / Evidence Box */}
                    <div>
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[11px] font-semibold text-neutral-600 dark:text-neutral-400 uppercase tracking-wider flex items-center space-x-1.5">
                          <span>Clause Text in Document</span>
                          <span className="text-neutral-400 dark:text-neutral-500 font-mono">(Page {item.page_number})</span>
                        </span>
                        <button
                          onClick={() => onSelectCitation(item.page_number, item.original_text)}
                          className="text-xs text-neutral-700 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-white underline font-medium"
                        >
                          View in document
                        </button>
                      </div>
                      <div className="evidence-box">
                        {item.original_text}
                      </div>
                    </div>

                    {/* Deviation Analysis & Corporate Rule */}
                    {item.deviation_explanation && (
                      <div className="bg-neutral-50 dark:bg-[#18191e] p-3.5 rounded-md border border-neutral-200 dark:border-[#27272a]">
                        <h5 className="font-semibold text-neutral-900 dark:text-neutral-100 mb-1 flex items-center space-x-1.5">
                          <AlertCircle className="w-3.5 h-3.5 text-neutral-700 dark:text-neutral-300" />
                          <span>Why This Is a Risk</span>
                        </h5>
                        <p className="text-neutral-700 dark:text-neutral-300 leading-relaxed font-sans">
                          {item.deviation_explanation}
                        </p>
                        {item.playbook_rule && (
                          <div className="mt-2 pt-2 border-t border-neutral-200 dark:border-[#27272a] text-neutral-600 dark:text-neutral-400 text-[11px]">
                            <span className="font-semibold text-neutral-800 dark:text-neutral-200">Recommended Standard: </span>
                            {item.playbook_rule}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Indian Law Reference / Statutory Precedents */}
                    {item.legal_citations && item.legal_citations.length > 0 && (
                      <div className="bg-amber-50/40 dark:bg-amber-950/20 p-3.5 rounded-md border border-amber-200/80 dark:border-amber-900/40">
                        <h5 className="font-semibold text-amber-900 dark:text-amber-300 mb-2 flex items-center space-x-1.5">
                          <BookOpen className="w-3.5 h-3.5 text-amber-800 dark:text-amber-400" />
                          <span>Applicable Indian Legal Rights & Landmark Cases</span>
                        </h5>
                        <div className="space-y-2">
                          {item.legal_citations.map((lc, idx) => (
                            <div key={idx} className="bg-white dark:bg-[#121316] p-2.5 rounded border border-amber-200/60 dark:border-amber-900/40 text-xs">
                              <div className="flex items-center justify-between">
                                <span className="font-semibold text-neutral-900 dark:text-neutral-100">
                                  {lc.act_name ? `${lc.act_name} — Section ${lc.section_number}` : lc.case_title}
                                </span>
                                {lc.status && (
                                  <span className="text-[10px] bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 px-1.5 py-0.5 rounded font-mono">
                                    {lc.status}
                                  </span>
                                )}
                              </div>
                              {lc.principle && (
                                <p className="text-neutral-600 dark:text-neutral-400 mt-1 leading-relaxed">
                                  {lc.principle}
                                </p>
                              )}
                              {lc.official_url && (
                                <a
                                  href={lc.official_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-neutral-800 dark:text-neutral-200 hover:text-black dark:hover:text-white underline text-[11px] block mt-1"
                                >
                                  Read official statute or judgment →
                                </a>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Redline Amendment Diff */}
                    {item.proposed_redline && (
                      <RedlineDiffViewer
                        originalText={item.original_text}
                        proposedRedline={item.proposed_redline}
                      />
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
