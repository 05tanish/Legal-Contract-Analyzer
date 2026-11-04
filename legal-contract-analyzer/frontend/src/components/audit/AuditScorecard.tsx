import React, { useState } from 'react';
import { AlertCircle, AlertTriangle, CheckCircle2, Copy, Check, RefreshCw } from 'lucide-react';
import { AuditReport } from '../../types';

interface AuditScorecardProps {
  audit: AuditReport;
  onReindex?: () => void;
  isReindexing?: boolean;
}

export const AuditScorecard: React.FC<AuditScorecardProps> = ({ audit, onReindex, isReindexing }) => {
  const [copied, setCopied] = useState(false);

  const getRiskConfig = (level: string) => {
    switch (level) {
      case 'CRITICAL':
      case 'HIGH':
        return {
          textColor: 'text-red-600 dark:text-red-400',
          bgColor: 'bg-red-50 dark:bg-red-950/30',
          borderColor: 'border-red-200 dark:border-red-900/50',
          icon: AlertCircle,
          label: 'HIGH RISK',
          subtext: 'Multiple clauses require revision before signing.',
        };
      case 'MEDIUM':
        return {
          textColor: 'text-amber-600 dark:text-amber-400',
          bgColor: 'bg-amber-50 dark:bg-amber-950/30',
          borderColor: 'border-amber-200 dark:border-amber-900/50',
          icon: AlertTriangle,
          label: 'MODERATE RISK',
          subtext: 'A few clauses should be reviewed or amended.',
        };
      default:
        return {
          textColor: 'text-emerald-600 dark:text-emerald-400',
          bgColor: 'bg-emerald-50 dark:bg-emerald-950/30',
          borderColor: 'border-emerald-200 dark:border-emerald-900/50',
          icon: CheckCircle2,
          label: 'LOW RISK',
          subtext: 'Terms appear well-balanced and standard.',
        };
    }
  };

  const config = getRiskConfig(audit.risk_level);
  const Icon = config.icon;

  const criticalCount = audit.findings.filter((f) => f.severity === 'CRITICAL').length;
  const highCount = audit.findings.filter((f) => f.severity === 'HIGH').length;
  const mediumCount = audit.findings.filter((f) => f.severity === 'MEDIUM').length;
  const lowCount = audit.findings.filter((f) => f.severity === 'LOW' || f.severity === 'ACCEPTABLE').length;

  const handleCopySummary = () => {
    if (audit.executive_summary) {
      navigator.clipboard.writeText(audit.executive_summary);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="saas-card p-6 mb-6 bg-white dark:bg-[#131418] border border-neutral-200 dark:border-[#23252a] rounded-lg">
      {/* 2-Column Overview Grid */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-stretch">
        {/* Left Column: Big Risk Display */}
        <div className="md:col-span-5 flex flex-col justify-center items-center text-center p-6 rounded-lg bg-neutral-50/70 dark:bg-[#18191e] border border-neutral-200/80 dark:border-[#27272a]">
          <span className="text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-2">
            Overall Risk Assessment
          </span>
          <div className="my-2">
            <Icon className={`w-12 h-12 ${config.textColor}`} />
          </div>
          <h2 className={`font-serif text-3xl font-bold tracking-tight ${config.textColor}`}>
            {config.label}
          </h2>
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1 max-w-xs">
            {config.subtext}
          </p>
          <div className="mt-3 flex items-center space-x-2">
            <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-700 text-neutral-800 dark:text-neutral-200 shadow-xs font-mono">
              Risk Score: {audit.overall_risk_score} / 100
            </span>
          </div>
        </div>

        {/* Right Column: Breakdown & Metrics */}
        <div className="md:col-span-7 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-neutral-200 dark:border-[#27272a]">
              <h4 className="font-semibold text-neutral-900 dark:text-neutral-100 text-sm">
                Summary of Issues Found
              </h4>
              {onReindex && (
                <button
                  onClick={onReindex}
                  disabled={isReindexing}
                  className="text-xs text-neutral-500 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-white flex items-center space-x-1 transition disabled:opacity-50"
                  title="Refresh review and re-check this contract"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isReindexing ? 'animate-spin' : ''}`} />
                  <span>{isReindexing ? 'Refreshing...' : 'Refresh Review'}</span>
                </button>
              )}
            </div>

            {/* Severity Cards Row */}
            <div className="grid grid-cols-4 gap-2.5 mt-3">
              <div className="bg-red-50/60 dark:bg-red-950/30 border border-red-200 dark:border-red-900/50 rounded-lg p-2.5 text-center">
                <span className="block text-red-600 dark:text-red-400 font-bold text-lg leading-tight">{criticalCount}</span>
                <span className="text-[10px] font-medium text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">Critical</span>
              </div>
              <div className="bg-amber-50/60 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/50 rounded-lg p-2.5 text-center">
                <span className="block text-amber-600 dark:text-amber-400 font-bold text-lg leading-tight">{highCount}</span>
                <span className="text-[10px] font-medium text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">High Risk</span>
              </div>
              <div className="bg-amber-50/30 dark:bg-amber-950/20 border border-amber-100 dark:border-amber-900/30 rounded-lg p-2.5 text-center">
                <span className="block text-amber-600 dark:text-amber-400 font-bold text-lg leading-tight">{mediumCount}</span>
                <span className="text-[10px] font-medium text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">Moderate</span>
              </div>
              <div className="bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900/50 rounded-lg p-2.5 text-center">
                <span className="block text-emerald-600 dark:text-emerald-400 font-bold text-lg leading-tight">{lowCount}</span>
                <span className="text-[10px] font-medium text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">Safe</span>
              </div>
            </div>
          </div>

          {/* Quick Details */}
          <div className="mt-4 pt-3 border-t border-neutral-100 dark:border-[#27272a] grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs text-neutral-600 dark:text-neutral-400">
            <div>
              <span className="text-[10px] text-neutral-500 uppercase font-medium">Flagged Items</span>
              <span className="font-semibold text-neutral-900 dark:text-neutral-200">{audit.findings.length} Items</span>
            </div>
            <div>
              <span className="text-[10px] text-neutral-500 uppercase font-medium">Review Status</span>
              <span className="font-semibold text-neutral-900 dark:text-neutral-200">Complete</span>
            </div>
            <div>
              <span className="text-[10px] text-neutral-500 uppercase font-medium">Reviewed On</span>
              <span className="font-semibold text-neutral-900 dark:text-neutral-200">
                {audit.created_at ? new Date(audit.created_at).toLocaleDateString() : 'Today'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Executive Summary Snippet (Black card styling) */}
      {audit.executive_summary && (
        <div className="mt-5 p-4 rounded-lg bg-black border border-neutral-800 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <h5 className="font-semibold text-xs text-white uppercase tracking-wider">
              Executive Summary
            </h5>
            <button
              onClick={handleCopySummary}
              className="flex items-center space-x-1 text-xs text-neutral-400 hover:text-white transition"
              title="Copy executive summary"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-neutral-400" />}
              <span>{copied ? 'Copied' : 'Copy Summary'}</span>
            </button>
          </div>
          <p className="text-xs text-neutral-300 leading-relaxed line-clamp-3 font-sans">
            {audit.executive_summary}
          </p>
        </div>
      )}
    </div>
  );
};
