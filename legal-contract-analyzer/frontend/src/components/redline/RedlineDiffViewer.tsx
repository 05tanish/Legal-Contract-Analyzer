import React, { useState } from 'react';
import { Check, Copy } from 'lucide-react';

interface RedlineDiffViewerProps {
  originalText: string;
  proposedRedline: string;
}

export const RedlineDiffViewer: React.FC<RedlineDiffViewerProps> = ({
  originalText,
  proposedRedline,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(proposedRedline);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mt-3 border border-neutral-200 dark:border-[#27272a] rounded-lg overflow-hidden bg-white dark:bg-[#131418] shadow-xs">
      <div className="bg-neutral-50 dark:bg-[#18191e] px-3.5 py-2 border-b border-neutral-200 dark:border-[#27272a] flex items-center justify-between text-xs text-neutral-700 dark:text-neutral-200 font-medium">
        <span className="font-semibold text-neutral-800 dark:text-neutral-100">Suggested Contract Revision</span>
        <button
          onClick={handleCopy}
          className="flex items-center space-x-1 text-xs text-neutral-600 dark:text-neutral-300 hover:text-neutral-900 dark:hover:text-white bg-white dark:bg-neutral-800 hover:bg-neutral-100 dark:hover:bg-neutral-700 border border-neutral-300 dark:border-neutral-700 px-2 py-0.5 rounded transition"
          title="Copy revised clause to clipboard"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? 'Copied' : 'Copy Revised Text'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 text-xs divide-y md:divide-y-0 md:divide-x divide-neutral-200 dark:divide-[#27272a] font-mono">
        {/* Original Clause */}
        <div className="p-3.5 bg-red-50/40 dark:bg-red-950/20">
          <div className="text-[10px] font-bold text-red-700 dark:text-red-400 mb-1.5 flex items-center space-x-1 uppercase tracking-wider">
            <span>Current Clause in Contract</span>
          </div>
          <p className="text-neutral-700 dark:text-neutral-300 leading-relaxed line-through decoration-red-400">
            {originalText}
          </p>
        </div>

        {/* Proposed Redline */}
        <div className="p-3.5 bg-emerald-50/40 dark:bg-emerald-950/20">
          <div className="text-[10px] font-bold text-emerald-700 dark:text-emerald-400 mb-1.5 flex items-center space-x-1 uppercase tracking-wider">
            <span>Suggested Safer Terms</span>
          </div>
          <p className="text-neutral-900 dark:text-neutral-100 leading-relaxed font-sans font-medium">
            {proposedRedline}
          </p>
        </div>
      </div>
    </div>
  );
};
