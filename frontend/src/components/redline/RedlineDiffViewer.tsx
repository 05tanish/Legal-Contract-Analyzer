import React from 'react';
import { Check, Copy } from 'lucide-react';

interface RedlineDiffViewerProps {
  originalText: string;
  proposedRedline: string;
}

export const RedlineDiffViewer: React.FC<RedlineDiffViewerProps> = ({
  originalText,
  proposedRedline,
}) => {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(proposedRedline);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mt-3 border border-slate-800 rounded-lg overflow-hidden bg-slate-950/70">
      <div className="bg-slate-900/80 px-3 py-1.5 border-b border-slate-800 flex items-center justify-between text-xs text-slate-400 font-medium">
        <span className="flex items-center space-x-1.5">
          <span>Proposed Redline Amendment</span>
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center space-x-1 text-slate-400 hover:text-indigo-400 transition"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? 'Copied' : 'Copy Clause'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 text-xs divide-y md:divide-y-0 md:divide-x divide-slate-800 font-mono">
        {/* Original Clause */}
        <div className="p-3 bg-red-950/10">
          <div className="text-[11px] font-semibold text-red-400 mb-1 flex items-center space-x-1 uppercase">
            <span>Original (Current Terms)</span>
          </div>
          <p className="text-slate-300 leading-relaxed line-through decoration-red-500/50">
            {originalText}
          </p>
        </div>

        {/* Proposed Redline */}
        <div className="p-3 bg-emerald-950/10">
          <div className="text-[11px] font-semibold text-emerald-400 mb-1 flex items-center space-x-1 uppercase">
            <span>Proposed Standard Language</span>
          </div>
          <p className="text-emerald-200 leading-relaxed font-sans font-medium">
            {proposedRedline}
          </p>
        </div>
      </div>
    </div>
  );
};

