import React, { useState, useMemo } from 'react';
import {
  FileText,
  Search,
  UploadCloud,
  ArrowRight,
  Trash2,
  Cloud,
  CheckCircle2,
  Clock,
  Lock,
  ExternalLink,
  ShieldCheck,
  FolderOpen
} from 'lucide-react';
import { Contract, User } from '../../types';

interface HistoryPageProps {
  contracts: Contract[];
  currentUser: User | null;
  onSelectContract: (contract: Contract) => void;
  onOpenUpload: () => void;
  onOpenAuth: () => void;
  onDeleteContract: (contract: Contract) => void;
}

export const HistoryPage: React.FC<HistoryPageProps> = ({
  contracts,
  currentUser,
  onSelectContract,
  onOpenUpload,
  onOpenAuth,
  onDeleteContract,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterMode, setFilterMode] = useState<'ALL' | 'CLOUD' | 'GUEST'>('ALL');

  // Filter contracts by search query and storage mode
  const filteredContracts = useMemo(() => {
    return contracts.filter((c) => {
      const matchSearch =
        !searchQuery.trim() ||
        c.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.id.toLowerCase().includes(searchQuery.toLowerCase());

      const matchFilter =
        filterMode === 'ALL' ||
        (filterMode === 'CLOUD' && Boolean(c.cloudinary_url)) ||
        (filterMode === 'GUEST' && Boolean(c.is_guest));

      return matchSearch && matchFilter;
    });
  }, [contracts, searchQuery, filterMode]);

  // Aggregate stats
  const totalPages = useMemo(() => {
    return contracts.reduce((acc, c) => acc + (c.total_pages || 0), 0);
  }, [contracts]);

  const cloudBackedCount = useMemo(() => {
    return contracts.filter((c) => Boolean(c.cloudinary_url)).length;
  }, [contracts]);

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'N/A';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-8 max-w-7xl mx-auto w-full select-none">
      {/* 1. Header & Quick Actions */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-8 pb-6 border-b border-[#23252a]">
        <div>
          <div className="flex items-center space-x-2 text-xs text-neutral-400 mb-1">
            <FolderOpen className="w-4 h-4 text-neutral-400" />
            <span>Document Repository</span>
            <span>•</span>
            <span>{currentUser ? 'Authenticated History' : 'Temporary Session'}</span>
          </div>
          <h1 className="font-serif text-2xl sm:text-3xl font-bold text-neutral-100">
            Contract Analysis History
          </h1>
          <p className="text-xs text-neutral-400 mt-1">
            {currentUser
              ? `Manage and review all contracts permanently saved to your account (${contracts.length} total).`
              : 'Sign in to access your permanent contract history across devices.'}
          </p>
        </div>

        <div className="flex items-center space-x-2.5 shrink-0">
          {!currentUser && (
            <button
              onClick={onOpenAuth}
              className="bg-[#18191e] hover:bg-[#22232a] text-neutral-200 border border-[#27272a] px-3.5 py-2 rounded-lg text-xs font-semibold transition flex items-center space-x-1.5 shadow-xs"
            >
              <Lock className="w-3.5 h-3.5 text-neutral-400" />
              <span>Sign In to Save Permanently</span>
            </button>
          )}

          <button
            onClick={onOpenUpload}
            className="bg-white hover:bg-neutral-200 text-neutral-950 px-4 py-2 rounded-lg text-xs font-semibold transition flex items-center space-x-1.5 shadow-xs"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload New Contract</span>
          </button>
        </div>
      </div>

      {/* 2. Key Metrics Summary Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="p-4 rounded-lg bg-[#131418] border border-[#23252a]">
          <span className="text-[10px] text-neutral-400 uppercase tracking-wider font-semibold block">Total Documents</span>
          <span className="text-2xl font-bold text-neutral-100 mt-1 block font-mono">{contracts.length}</span>
          <span className="text-[11px] text-neutral-500 mt-0.5 block">Stored in your repository</span>
        </div>

        <div className="p-4 rounded-lg bg-[#131418] border border-[#23252a]">
          <span className="text-[10px] text-neutral-400 uppercase tracking-wider font-semibold block">Total Pages Ingested</span>
          <span className="text-2xl font-bold text-neutral-100 mt-1 block font-mono">{totalPages}</span>
          <span className="text-[11px] text-neutral-500 mt-0.5 block">Parsed & indexed for review</span>
        </div>

        <div className="p-4 rounded-lg bg-[#131418] border border-[#23252a]">
          <span className="text-[10px] text-neutral-400 uppercase tracking-wider font-semibold block">Cloud Storage</span>
          <span className="text-2xl font-bold text-neutral-100 mt-1 block font-mono">{cloudBackedCount}</span>
          <span className="text-[11px] text-neutral-500 mt-0.5 block">Backed up to Cloudinary</span>
        </div>

        <div className="p-4 rounded-lg bg-[#131418] border border-[#23252a]">
          <span className="text-[10px] text-neutral-400 uppercase tracking-wider font-semibold block">Account Tier</span>
          <span className="text-base font-bold text-neutral-200 mt-1 block flex items-center space-x-1.5">
            {currentUser ? (
              <>
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Enterprise Counsel</span>
              </>
            ) : (
              <>
                <Clock className="w-4 h-4 text-amber-400" />
                <span>Guest (Temporary)</span>
              </>
            )}
          </span>
          <span className="text-[11px] text-neutral-500 mt-0.5 block">
            {currentUser ? 'Persistent contract retention' : 'Auto-purged after 24 hours'}
          </span>
        </div>
      </div>

      {/* 3. Search & Filter Bar */}
      <div className="p-3 bg-[#131418] border border-[#23252a] rounded-lg mb-6 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-neutral-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by contract filename or document ID..."
            className="w-full bg-[#18191e] border border-[#27272a] rounded-md pl-9 pr-3 py-2 text-xs text-neutral-200 placeholder-neutral-500 focus:outline-hidden focus:border-neutral-500 font-sans"
          />
        </div>

        <div className="flex items-center space-x-1 overflow-x-auto shrink-0">
          <button
            onClick={() => setFilterMode('ALL')}
            className={`px-3 py-1.5 rounded text-xs font-medium transition ${
              filterMode === 'ALL'
                ? 'bg-neutral-800 text-white border border-neutral-700'
                : 'text-neutral-400 hover:text-neutral-200'
            }`}
          >
            All ({contracts.length})
          </button>
          <button
            onClick={() => setFilterMode('CLOUD')}
            className={`px-3 py-1.5 rounded text-xs font-medium transition ${
              filterMode === 'CLOUD'
                ? 'bg-neutral-800 text-white border border-neutral-700'
                : 'text-neutral-400 hover:text-neutral-200'
            }`}
          >
            Cloud Backed ({cloudBackedCount})
          </button>
          {!currentUser && (
            <button
              onClick={() => setFilterMode('GUEST')}
              className={`px-3 py-1.5 rounded text-xs font-medium transition ${
                filterMode === 'GUEST'
                  ? 'bg-neutral-800 text-white border border-neutral-700'
                  : 'text-neutral-400 hover:text-neutral-200'
              }`}
            >
              Temporary
            </button>
          )}
        </div>
      </div>

      {/* 4. Contracts Table */}
      <div className="bg-[#131418] border border-[#23252a] rounded-lg overflow-hidden shadow-xs">
        {filteredContracts.length === 0 ? (
          <div className="p-12 text-center flex flex-col items-center justify-center">
            <div className="w-12 h-12 rounded-full bg-neutral-900 border border-neutral-800 flex items-center justify-center text-neutral-500 mb-3">
              <FileText className="w-6 h-6" />
            </div>
            <h3 className="font-serif font-bold text-base text-neutral-200 mb-1">
              No contracts found
            </h3>
            <p className="text-xs text-neutral-400 max-w-sm mx-auto mb-6">
              {searchQuery
                ? 'No documents match your search criteria. Try a different term or clear the filter.'
                : currentUser
                ? 'You have not uploaded any contracts yet. Upload your first PDF to begin legal risk analysis.'
                : 'You have no active contracts in this temporary guest session. Upload a contract to begin.'}
            </p>
            <button
              onClick={onOpenUpload}
              className="bg-white hover:bg-neutral-200 text-neutral-950 font-semibold px-4 py-2 rounded-md text-xs transition inline-flex items-center space-x-1.5"
            >
              <UploadCloud className="w-3.5 h-3.5" />
              <span>Upload Document</span>
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[#23252a] bg-[#16171b] text-neutral-400 uppercase tracking-wider font-semibold text-[10px]">
                  <th className="py-3 px-4">Contract Document</th>
                  <th className="py-3 px-4">Pages & Size</th>
                  <th className="py-3 px-4">Ingested Date</th>
                  <th className="py-3 px-4">Retention Mode</th>
                  <th className="py-3 px-4">Storage Backup</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#23252a]">
                {filteredContracts.map((c) => (
                  <tr
                    key={c.id}
                    onClick={() => onSelectContract(c)}
                    className="hover:bg-[#18191f] transition cursor-pointer group"
                  >
                    {/* Filename & icon */}
                    <td className="py-3.5 px-4 font-medium text-neutral-200">
                      <div className="flex items-center space-x-3">
                        <div className="w-7 h-7 rounded bg-neutral-800 border border-neutral-700/80 flex items-center justify-center text-neutral-400 group-hover:text-white transition shrink-0">
                          <FileText className="w-3.5 h-3.5" />
                        </div>
                        <div className="min-w-0">
                          <span className="font-semibold text-neutral-100 truncate block max-w-xs sm:max-w-md group-hover:underline" title={c.filename}>
                            {c.filename}
                          </span>
                          <span className="text-[10px] text-neutral-500 font-mono block mt-0.5">
                            ID: {c.id.substring(0, 8)}...
                          </span>
                        </div>
                      </div>
                    </td>

                    {/* Pages & Size */}
                    <td className="py-3.5 px-4 font-mono text-neutral-300">
                      <div>{c.total_pages || 1} {c.total_pages === 1 ? 'Page' : 'Pages'}</div>
                      <div className="text-[10px] text-neutral-500">{formatFileSize(c.file_size_bytes)}</div>
                    </td>

                    {/* Ingestion Date */}
                    <td className="py-3.5 px-4 text-neutral-400 whitespace-nowrap">
                      {formatDate(c.created_at)}
                    </td>

                    {/* Retention Mode */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      {c.is_guest ? (
                        <span className="inline-flex items-center space-x-1 text-[10px] bg-amber-950/40 text-amber-300 px-2 py-0.5 rounded border border-amber-900/60 font-medium">
                          <Clock className="w-3 h-3 text-amber-400" />
                          <span>Guest (24h TTL)</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center space-x-1 text-[10px] bg-emerald-950/40 text-emerald-300 px-2 py-0.5 rounded border border-emerald-900/60 font-medium">
                          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                          <span>Permanent</span>
                        </span>
                      )}
                    </td>

                    {/* Cloud Storage */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      {c.cloudinary_url ? (
                        <a
                          href={c.cloudinary_url}
                          target="_blank"
                          rel="noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="inline-flex items-center space-x-1 text-[11px] text-neutral-300 bg-neutral-800/80 hover:bg-neutral-800 px-2.5 py-1 rounded border border-neutral-700 transition"
                          title="Open backup copy on Cloudinary"
                        >
                          <Cloud className="w-3 h-3 text-neutral-400" />
                          <span>Cloud Backup</span>
                          <ExternalLink className="w-2.5 h-2.5 text-neutral-500 ml-0.5" />
                        </a>
                      ) : (
                        <span className="text-neutral-500 text-[11px]">Local Temporary</span>
                      )}
                    </td>

                    {/* Actions */}
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <div className="inline-flex items-center space-x-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectContract(c);
                          }}
                          className="bg-neutral-800 hover:bg-neutral-700 text-neutral-100 px-2.5 py-1 rounded text-xs font-semibold transition inline-flex items-center space-x-1 border border-neutral-700 shadow-xs"
                          title="Open in Workspace"
                        >
                          <span>Review</span>
                          <ArrowRight className="w-3 h-3" />
                        </button>

                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteContract(c);
                          }}
                          className="p-1 rounded hover:bg-red-950/40 text-neutral-400 hover:text-red-400 border border-transparent hover:border-red-900/40 transition"
                          title="Delete contract permanently"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

