import React, { useState, useEffect, useRef } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  ExternalLink,
  Cloud,
  Maximize2,
  Minimize2,
  Download,
  ZoomIn,
  ZoomOut,
  PanelLeftClose,
  PanelLeft
} from 'lucide-react';
import { getPdfUrl } from '../../lib/api';

interface SplitPdfViewerProps {
  contractId: string;
  filename: string;
  totalPages: number;
  activeCitationPage: number | null;
  activeCitationSnippet: string | null;
  cloudinaryUrl?: string;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
}

export const SplitPdfViewer: React.FC<SplitPdfViewerProps> = ({
  contractId,
  filename,
  totalPages,
  activeCitationPage,
  activeCitationSnippet,
  cloudinaryUrl,
  isExpanded = false,
  onToggleExpand,
}) => {
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageInput, setPageInput] = useState<string>('1');
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [fitMode, setFitMode] = useState<'FitH' | 'Fit' | null>('FitH'); // Default FitH fills full width
  const [showThumbnails, setShowThumbnails] = useState<boolean>(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Sync external citation jumps
  useEffect(() => {
    if (activeCitationPage) {
      setCurrentPage(activeCitationPage);
      setPageInput(String(activeCitationPage));
      if (iframeRef.current && iframeRef.current.contentWindow) {
        try {
          iframeRef.current.contentWindow.location.hash = `#page=${activeCitationPage}&view=FitH&navpanes=0`;
        } catch {
          // Cross-origin fallback
        }
      }
    }
  }, [activeCitationPage]);

  // Construct PDF URL with standard RFC 3778 Open Parameters:
  // - navpanes=0: Hides sidebar thumbnail panel to utilize 100% horizontal width
  // - view=FitH: Forces 100% full-width horizontal fit across all browser PDF engines
  // - page: Target page number
  const baseUrl = getPdfUrl(contractId);
  const pdfParams = React.useMemo(() => {
    const params: string[] = [`page=${currentPage}`];

    if (!showThumbnails) {
      params.push('navpanes=0');
    } else {
      params.push('navpanes=1');
    }

    if (fitMode === 'FitH') {
      params.push('view=FitH');
    } else if (fitMode === 'Fit') {
      params.push('view=Fit');
    } else {
      params.push(`zoom=${zoomLevel}`);
    }

    return params.join('&');
  }, [currentPage, showThumbnails, fitMode, zoomLevel]);

  const pdfUrlWithPage = `${baseUrl}#${pdfParams}`;

  const handlePageChange = (newPage: number) => {
    const valid = Math.max(1, Math.min(totalPages || 1, newPage));
    setCurrentPage(valid);
    setPageInput(String(valid));
    if (iframeRef.current && iframeRef.current.contentWindow) {
      try {
        iframeRef.current.contentWindow.location.hash = `#page=${valid}&view=FitH&navpanes=0`;
      } catch {
        // Cross-origin fallback
      }
    }
  };

  const handlePageInputSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const p = parseInt(pageInput, 10);
    if (!isNaN(p)) {
      handlePageChange(p);
    }
  };

  const handleZoomIn = () => {
    setFitMode(null);
    setZoomLevel((z) => Math.min(250, z + 25));
  };

  const handleZoomOut = () => {
    setFitMode(null);
    setZoomLevel((z) => Math.max(50, z - 25));
  };

  const handleFitWidth = () => {
    setFitMode('FitH');
    setZoomLevel(100);
  };

  const handleFitPage = () => {
    setFitMode('Fit');
  };

  return (
    <div className="flex flex-col w-full h-full min-h-0 bg-[#0d0e12] text-neutral-200 border-r border-[#23252a] relative overflow-hidden select-none">
      {/* Enhanced Pro Toolbar */}
      <div className="h-12 border-b border-[#23252a] bg-[#14151a] px-3 sm:px-4 flex items-center justify-between shadow-xs shrink-0 gap-2">
        {/* Document Info */}
        <div className="flex items-center space-x-2 min-w-0">
          <span className="text-xs font-semibold text-neutral-100 truncate max-w-[120px] sm:max-w-[200px]" title={filename}>
            {filename}
          </span>
          <span className="text-[10px] bg-neutral-800 text-neutral-400 px-2 py-0.5 rounded border border-neutral-700/80 font-mono shrink-0">
            {totalPages || 1} {totalPages === 1 ? 'Page' : 'Pages'}
          </span>
          {cloudinaryUrl && (
            <a
              href={cloudinaryUrl}
              target="_blank"
              rel="noreferrer"
              className="hidden xl:inline-flex items-center space-x-1 text-[11px] bg-neutral-800/80 hover:bg-neutral-800 text-neutral-300 px-2 py-0.5 rounded border border-neutral-700 transition shrink-0"
              title="Cloud Backup on Cloudinary"
            >
              <Cloud className="w-3 h-3 text-neutral-400" />
              <span>Cloud Backup</span>
            </a>
          )}
        </div>

        {/* Center: Page Navigation & Zoom Controls */}
        <div className="flex items-center space-x-1 sm:space-x-3 shrink-0">
          {/* Page Navigator */}
          <div className="flex items-center space-x-1 bg-[#1a1b22] px-2 py-1 rounded border border-[#27272a]">
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage <= 1}
              className="p-0.5 rounded hover:bg-neutral-700 disabled:opacity-30 text-neutral-300 transition"
              title="Previous Page"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <form onSubmit={handlePageInputSubmit} className="flex items-center">
              <input
                type="text"
                value={pageInput}
                onChange={(e) => setPageInput(e.target.value)}
                onBlur={handlePageInputSubmit}
                className="w-8 text-center text-xs bg-neutral-900 border border-neutral-700 text-neutral-100 rounded px-1 py-0.5 font-mono focus:outline-hidden focus:border-neutral-500"
              />
              <span className="text-xs text-neutral-400 font-mono ml-1.5">
                / {totalPages || 1}
              </span>
            </form>
            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage >= (totalPages || 1)}
              className="p-0.5 rounded hover:bg-neutral-700 disabled:opacity-30 text-neutral-300 transition"
              title="Next Page"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Zoom Controls */}
          <div className="hidden md:flex items-center space-x-1 bg-[#1a1b22] px-1.5 py-1 rounded border border-[#27272a]">
            <button
              onClick={handleZoomOut}
              className="p-1 rounded hover:bg-neutral-700 text-neutral-400 hover:text-neutral-100 transition"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="text-[11px] font-mono text-neutral-300 w-10 text-center">
              {fitMode === 'FitH' ? 'Fit W' : fitMode === 'Fit' ? 'Fit P' : `${zoomLevel}%`}
            </span>
            <button
              onClick={handleZoomIn}
              className="p-1 rounded hover:bg-neutral-700 text-neutral-400 hover:text-neutral-100 transition"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <div className="w-[1px] h-3 bg-neutral-700 mx-0.5" />
            <button
              onClick={handleFitWidth}
              className={`px-1.5 py-0.5 text-[10px] rounded transition ${
                fitMode === 'FitH' ? 'bg-neutral-700 text-white font-semibold' : 'text-neutral-400 hover:text-neutral-200'
              }`}
              title="Fit to Width (Utilize 100% width)"
            >
              Fit Width
            </button>
            <button
              onClick={handleFitPage}
              className={`px-1.5 py-0.5 text-[10px] rounded transition ${
                fitMode === 'Fit' ? 'bg-neutral-700 text-white font-semibold' : 'text-neutral-400 hover:text-neutral-200'
              }`}
              title="Fit Entire Page"
            >
              Fit Page
            </button>
          </div>
        </div>

        {/* Right Actions: Thumbnails toggle, Fullscreen/Expand, Download, Popout */}
        <div className="flex items-center space-x-1 shrink-0">
          <button
            onClick={() => setShowThumbnails((v) => !v)}
            className={`p-1.5 rounded transition hidden sm:inline-flex ${
              showThumbnails ? 'bg-neutral-700 text-white' : 'hover:bg-neutral-800 text-neutral-400 hover:text-white'
            }`}
            title={showThumbnails ? 'Hide page thumbnails' : 'Show page thumbnails sidebar'}
          >
            {showThumbnails ? <PanelLeftClose className="w-3.5 h-3.5" /> : <PanelLeft className="w-3.5 h-3.5" />}
          </button>

          {onToggleExpand && (
            <button
              onClick={onToggleExpand}
              className="p-1.5 rounded hover:bg-neutral-800 text-neutral-400 hover:text-white transition"
              title={isExpanded ? 'Restore split view' : 'Expand document to full width'}
            >
              {isExpanded ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
            </button>
          )}

          <a
            href={baseUrl}
            download={filename}
            className="p-1.5 rounded hover:bg-neutral-800 text-neutral-400 hover:text-white transition"
            title="Download PDF document"
          >
            <Download className="w-3.5 h-3.5" />
          </a>

          <a
            href={baseUrl}
            target="_blank"
            rel="noreferrer"
            className="p-1.5 rounded hover:bg-neutral-800 text-neutral-400 hover:text-white transition"
            title="Open in new window"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>

      {/* Active Citation Focus Banner (Dark Neutral SaaS Styling) */}
      {activeCitationSnippet && (
        <div className="bg-neutral-950 border-b border-neutral-800 px-4 py-2 flex items-start space-x-2 text-xs text-neutral-200 shrink-0">
          <AlertTriangle className="w-4 h-4 shrink-0 text-neutral-400 mt-0.5" />
          <div className="flex-1 min-w-0">
            <span className="font-semibold text-white">
              Referenced in Document (Page {activeCitationPage}):
            </span>
            <p className="font-mono text-neutral-300 mt-0.5 italic line-clamp-2">
              "{activeCitationSnippet}"
            </p>
          </div>
        </div>
      )}

      {/* Embedded Document Frame: 100% Full Width and Height */}
      <div className="relative flex-1 w-full h-full min-h-0 flex flex-col bg-neutral-900 overflow-hidden">
        <iframe
          key={`pdf_frame_${contractId}`}
          ref={iframeRef}
          src={pdfUrlWithPage}
          title={filename}
          className="w-full h-full flex-1 border-0 block"
          style={{ width: '100%', height: '100%', minHeight: 0, border: 'none' }}
        />
      </div>
    </div>
  );
};
