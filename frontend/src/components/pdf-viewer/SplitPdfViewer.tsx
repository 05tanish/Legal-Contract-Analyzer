import React, { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, AlertTriangle, ExternalLink } from 'lucide-react';
import { getPdfUrl } from '../../lib/api';

interface SplitPdfViewerProps {
  contractId: string;
  filename: string;
  totalPages: number;
  activeCitationPage: number | null;
  activeCitationSnippet: string | null;
}

export const SplitPdfViewer: React.FC<SplitPdfViewerProps> = ({
  contractId,
  filename,
  totalPages,
  activeCitationPage,
  activeCitationSnippet,
}) => {
  const [currentPage, setCurrentPage] = useState<number>(1);

  useEffect(() => {
    if (activeCitationPage) {
      setCurrentPage(activeCitationPage);
    }
  }, [activeCitationPage]);

  const pdfUrl = `${getPdfUrl(contractId)}#page=${currentPage}`;

  return (
    <div className="flex flex-col h-full bg-slate-950 border-r border-slate-800 relative">
      {/* Viewer Toolbar */}
      <div className="h-12 border-b border-slate-800 bg-slate-900/80 px-4 flex items-center justify-between">
        <div className="flex items-center space-x-2 truncate">
          <span className="text-xs font-semibold text-slate-300 truncate">{filename}</span>
          <span className="text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded">
            {totalPages} Pages
          </span>
        </div>

        {/* Page Nav */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage <= 1}
            className="p-1 rounded hover:bg-slate-800 disabled:opacity-40 text-slate-300"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-xs text-slate-300 font-mono">
            Page {currentPage} / {totalPages || 1}
          </span>
          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages || 1, p + 1))}
            disabled={currentPage >= (totalPages || 1)}
            className="p-1 rounded hover:bg-slate-800 disabled:opacity-40 text-slate-300"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* External Link */}
        <div className="flex items-center space-x-1">
          <a
            href={getPdfUrl(contractId)}
            target="_blank"
            rel="noreferrer"
            className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition"
            title="Open in new tab"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>
      </div>

      {/* Active Citation Focus Banner */}
      {activeCitationSnippet && (
        <div className="bg-amber-500/10 border-b border-amber-500/30 px-4 py-2 flex items-start space-x-2 text-xs text-amber-300 animate-fadeIn">
          <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
          <div className="flex-1">
            <span className="font-semibold text-amber-200">Grounded Citation (Page {activeCitationPage}):</span>
            <p className="font-mono text-slate-300 mt-0.5 italic line-clamp-2">"{activeCitationSnippet}"</p>
          </div>
        </div>
      )}

      {/* PDF Viewport */}
      <div className="flex-1 w-full h-full bg-slate-900 overflow-hidden relative">
        <iframe
          key={`${contractId}-${currentPage}`}
          src={pdfUrl}
          title="Contract PDF Viewer"
          className="w-full h-full border-none"
        />
      </div>
    </div>
  );
};

