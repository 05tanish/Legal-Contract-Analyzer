import React from 'react';
import { ShieldCheck, ShieldAlert, AlertOctagon, Clock, DollarSign, Sparkles } from 'lucide-react';
import { AuditReport } from '../../types';

interface AuditScorecardProps {
  audit: AuditReport;
}

export const AuditScorecard: React.FC<AuditScorecardProps> = ({ audit }) => {
  const getSeverityStyle = (level: string) => {
    switch (level) {
      case 'CRITICAL':
        return {
          bg: 'bg-red-500/10 border-red-500/30 text-red-400',
          badge: 'bg-red-500 text-white',
          icon: AlertOctagon,
        };
      case 'HIGH':
        return {
          bg: 'bg-orange-500/10 border-orange-500/30 text-orange-400',
          badge: 'bg-orange-500 text-white',
          icon: ShieldAlert,
        };
      case 'MEDIUM':
        return {
          bg: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
          badge: 'bg-amber-500 text-slate-900',
          icon: ShieldAlert,
        };
      default:
        return {
          bg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
          badge: 'bg-emerald-500 text-white',
          icon: ShieldCheck,
        };
    }
  };

  const style = getSeverityStyle(audit.risk_level);
  const Icon = style.icon;

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 mb-6 shadow-sm">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className={`p-2.5 rounded-lg border ${style.bg}`}>
            <Icon className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Playbook Risk Assessment</span>
              <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${style.badge}`}>
                {audit.risk_level} RISK
              </span>
            </div>
            <div className="flex items-baseline space-x-2 mt-0.5">
              <span className="text-3xl font-extrabold text-white">{audit.overall_risk_score}</span>
              <span className="text-sm text-slate-500 font-mono">/ 100 Risk Score</span>
            </div>
          </div>
        </div>

        {/* Telemetry metadata */}
        <div className="flex items-center space-x-3 text-xs text-slate-400 font-mono">
          {audit.latency_ms && (
            <div className="flex items-center space-x-1 bg-slate-800/80 px-2.5 py-1 rounded-md border border-slate-700/60">
              <Clock className="w-3.5 h-3.5 text-indigo-400" />
              <span>{Math.round(audit.latency_ms)}ms</span>
            </div>
          )}
          {audit.cost_usd && (
            <div className="flex items-center space-x-1 bg-slate-800/80 px-2.5 py-1 rounded-md border border-slate-700/60">
              <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
              <span>${audit.cost_usd.toFixed(3)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Executive Summary */}
      {audit.executive_summary && (
        <div className="bg-slate-950/60 rounded-lg p-3.5 border border-slate-800/70 text-xs text-slate-300 leading-relaxed font-sans">
          <div className="flex items-center space-x-1.5 text-indigo-400 font-semibold mb-1">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Executive Legal Brief</span>
          </div>
          <p className="whitespace-pre-line">{audit.executive_summary}</p>
        </div>
      )}
    </div>
  );
};

