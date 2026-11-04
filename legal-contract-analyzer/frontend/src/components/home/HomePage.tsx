import React from 'react';
import {
  Scale,
  UploadCloud,
  FileText,
  ShieldCheck,
  BookOpen,
  ArrowRight,
  ChevronRight,
  Lock,
  FileSearch,
  Cloud
} from 'lucide-react';
import { Contract } from '../../types';

interface HomePageProps {
  contracts: Contract[];
  onSelectContract: (contract: Contract) => void;
  onOpenUpload: () => void;
  onOpenLegalGuide: () => void;
  onOpenAuth: () => void;
  onNavigateHistory?: () => void;
  isLoggedIn: boolean;
}

export const HomePage: React.FC<HomePageProps> = ({
  contracts,
  onSelectContract,
  onOpenUpload,
  onOpenLegalGuide,
  onOpenAuth,
  onNavigateHistory,
  isLoggedIn,
}) => {
  return (
    <div className="flex-1 overflow-y-auto">
      {/* 1. Hero Section */}
      <section className="relative px-4 sm:px-6 lg:px-8 pt-16 pb-20 max-w-6xl mx-auto text-center">
        {/* Subtle pill badge */}
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-neutral-900 border border-neutral-800 text-neutral-300 text-xs font-medium mb-6">
          <Scale className="w-3.5 h-3.5 text-neutral-400" />
          <span>Indian Commercial Law Standards & Contract Review</span>
        </div>

        {/* Main Title */}
        <h1 className="font-serif text-3xl sm:text-5xl lg:text-6xl font-bold text-neutral-100 tracking-tight leading-[1.15] max-w-4xl mx-auto">
          Precision contract intelligence for legal teams.
        </h1>

        {/* Subtitle */}
        <p className="mt-5 text-sm sm:text-base text-neutral-400 max-w-2xl mx-auto leading-relaxed">
          Review agreements with absolute confidence. Automatically detect high-risk clauses against Indian statutory standards, view grounded evidence, and generate negotiation-ready redlines.
        </p>

        {/* Primary Call to Actions */}
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <button
            onClick={onOpenUpload}
            className="flex items-center space-x-2 bg-white hover:bg-neutral-200 text-neutral-950 font-semibold px-5 py-2.5 rounded-lg text-xs sm:text-sm transition shadow-sm cursor-pointer"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload Contract for Review</span>
          </button>

          {!isLoggedIn && (
            <button
              onClick={onOpenAuth}
              className="flex items-center space-x-2 bg-neutral-900 hover:bg-neutral-800 text-neutral-200 border border-neutral-800 px-5 py-2.5 rounded-lg text-xs sm:text-sm font-medium transition cursor-pointer"
            >
              <Lock className="w-4 h-4 text-neutral-400" />
              <span>Sign In</span>
            </button>
          )}

          <button
            onClick={onOpenLegalGuide}
            className="flex items-center space-x-2 bg-neutral-900 hover:bg-neutral-800 text-neutral-200 border border-neutral-800 px-5 py-2.5 rounded-lg text-xs sm:text-sm font-medium transition cursor-pointer"
          >
            <BookOpen className="w-4 h-4 text-neutral-400" />
            <span>Explore Indian Legal Guide</span>
          </button>
        </div>

        {/* Stat metrics banner */}
        <div className="mt-14 pt-8 border-t border-neutral-900 grid grid-cols-2 md:grid-cols-4 gap-4 text-left">
          <div className="p-4 rounded-lg bg-neutral-950/60 border border-neutral-900">
            <span className="text-[11px] uppercase tracking-wider text-neutral-500 font-semibold block">Indian Statutes</span>
            <span className="text-xl font-bold text-neutral-100 mt-0.5 block">Bare Acts & Cases</span>
            <span className="text-[11px] text-neutral-400 mt-1 block">Contract Act 1872, Arbitration 1996</span>
          </div>
          <div className="p-4 rounded-lg bg-neutral-950/60 border border-neutral-900">
            <span className="text-[11px] uppercase tracking-wider text-neutral-500 font-semibold block">Evidence Grounding</span>
            <span className="text-xl font-bold text-neutral-100 mt-0.5 block">100% Verbatim</span>
            <span className="text-[11px] text-neutral-400 mt-1 block">Every finding links to exact document page</span>
          </div>
          <div className="p-4 rounded-lg bg-neutral-950/60 border border-neutral-900">
            <span className="text-[11px] uppercase tracking-wider text-neutral-500 font-semibold block">Indexed Contracts</span>
            <span className="text-xl font-bold text-neutral-100 mt-0.5 block">
              {isLoggedIn ? `${contracts.length} Documents` : 'Sign in to save'}
            </span>
            <span className="text-[11px] text-neutral-400 mt-1 block">
              {isLoggedIn ? 'Available in your permanent archive' : 'Permanent encrypted archive'}
            </span>
          </div>
          <div className="p-4 rounded-lg bg-neutral-950/60 border border-neutral-900">
            <span className="text-[11px] uppercase tracking-wider text-neutral-500 font-semibold block">Security Standard</span>
            <span className="text-xl font-bold text-neutral-100 mt-0.5 block">Cloudflare & Cloud</span>
            <span className="text-[11px] text-neutral-400 mt-1 block">Encrypted document storage</span>
          </div>
        </div>
      </section>

      {/* 2. Embedded Upload Drop Zone */}
      <section className="px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto mb-16">
        <div
          onClick={onOpenUpload}
          className="border-2 border-dashed border-neutral-800 hover:border-neutral-600 bg-neutral-950/70 hover:bg-neutral-900/50 rounded-xl p-8 sm:p-12 text-center cursor-pointer transition"
        >
          <div className="w-12 h-12 rounded-full bg-neutral-900 border border-neutral-800 flex items-center justify-center mx-auto mb-3 text-neutral-300">
            <UploadCloud className="w-6 h-6" />
          </div>
          <h3 className="font-serif font-bold text-lg sm:text-xl text-neutral-100 mb-1">
            Drag & drop legal contract to start review
          </h3>
          <p className="text-xs text-neutral-400 max-w-md mx-auto mb-4">
            Supports standard PDF documents up to 50MB. Text contracts and scanned agreements supported.
          </p>
          <button
            type="button"
            className="bg-neutral-800 hover:bg-neutral-700 text-neutral-200 border border-neutral-700 px-4 py-2 rounded-md text-xs font-medium shadow-xs transition"
          >
            Select Contract PDF
          </button>
        </div>
      </section>

      {/* 3. Core Capabilities Grid */}
      <section className="px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto mb-20">
        <div className="text-center mb-10">
          <span className="text-[11px] uppercase tracking-wider font-semibold text-neutral-500">
            Engineered for Legal Accuracy
          </span>
          <h2 className="font-serif text-2xl sm:text-3xl font-bold text-neutral-100 mt-1">
            Comprehensive Contract Analysis
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div className="p-6 rounded-xl bg-neutral-950/80 border border-neutral-900 flex flex-col justify-between">
            <div>
              <div className="w-9 h-9 rounded-md bg-neutral-900 border border-neutral-800 flex items-center justify-center text-neutral-300 mb-4">
                <FileSearch className="w-5 h-5" />
              </div>
              <h3 className="font-serif font-bold text-base text-neutral-100 mb-2">
                Contract Risk Audit
              </h3>
              <p className="text-xs text-neutral-400 leading-relaxed">
                Flags one-sided indemnities, uncapped liabilities, non-standard termination windows, and onerous IP assignments.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-neutral-900 text-[11px] text-neutral-500 font-mono">
              Corporate Benchmark Rules
            </div>
          </div>

          <div className="p-6 rounded-xl bg-neutral-950/80 border border-neutral-900 flex flex-col justify-between">
            <div>
              <div className="w-9 h-9 rounded-md bg-neutral-900 border border-neutral-800 flex items-center justify-center text-neutral-300 mb-4">
                <Scale className="w-5 h-5" />
              </div>
              <h3 className="font-serif font-bold text-base text-neutral-100 mb-2">
                Indian Law Verification
              </h3>
              <p className="text-xs text-neutral-400 leading-relaxed">
                Cross-references Section 27 (Restraint of Trade), Section 73/74 (Liquidated Damages), and Supreme Court rulings on enforceability.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-neutral-900 text-[11px] text-neutral-500 font-mono">
              Bare Acts & Supreme Court Precedents
            </div>
          </div>

          <div className="p-6 rounded-xl bg-neutral-950/80 border border-neutral-900 flex flex-col justify-between">
            <div>
              <div className="w-9 h-9 rounded-md bg-neutral-900 border border-neutral-800 flex items-center justify-center text-neutral-300 mb-4">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h3 className="font-serif font-bold text-base text-neutral-100 mb-2">
                Suggested Redlines
              </h3>
              <p className="text-xs text-neutral-400 leading-relaxed">
                Generates balanced replacement wording side-by-side with original clauses, ready to copy into negotiation drafts.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-neutral-900 text-[11px] text-neutral-500 font-mono">
              One-Click Copy Amendments
            </div>
          </div>
        </div>
      </section>

      {/* 4. Active / Uploaded Contracts Section (Only visible for Authenticated Users) */}
      {isLoggedIn && contracts.length > 0 && (
        <section className="px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto mb-20">
          <div className="p-6 rounded-xl bg-neutral-950/80 border border-neutral-900">
            <div className="flex items-center justify-between pb-3 border-b border-neutral-900 mb-4">
              <div>
                <h3 className="font-serif font-bold text-base text-neutral-100">
                  Your Uploaded Contracts ({contracts.length})
                </h3>
                <p className="text-xs text-neutral-500">
                  Select any document to open the full interactive workspace
                </p>
              </div>
              <div className="flex items-center space-x-3">
                {onNavigateHistory && (
                  <button
                    onClick={onNavigateHistory}
                    className="text-xs text-neutral-400 hover:text-white font-medium flex items-center space-x-1 transition"
                  >
                    <span>View All History ({contracts.length})</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                )}
                <button
                  onClick={onOpenUpload}
                  className="text-xs text-neutral-200 hover:text-white font-medium flex items-center space-x-1 bg-neutral-900 px-2.5 py-1 rounded border border-neutral-800 transition"
                >
                  <span>Upload New</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-neutral-900 text-neutral-500 uppercase tracking-wider font-semibold text-[10px]">
                    <th className="py-2.5 px-3">Contract Document</th>
                    <th className="py-2.5 px-3">Pages</th>
                    <th className="py-2.5 px-3">Storage Status</th>
                    <th className="py-2.5 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-900">
                  {contracts.map((c) => (
                    <tr
                      key={c.id}
                      onClick={() => onSelectContract(c)}
                      className="hover:bg-neutral-900/60 transition cursor-pointer group"
                    >
                      <td className="py-3 px-3 font-medium text-neutral-200 flex items-center space-x-2.5">
                        <FileText className="w-4 h-4 text-neutral-500 group-hover:text-neutral-200 transition" />
                        <span className="truncate max-w-sm">{c.filename}</span>
                      </td>
                      <td className="py-3 px-3 text-neutral-400 font-mono">
                        {c.total_pages} {c.total_pages === 1 ? 'Page' : 'Pages'}
                      </td>
                      <td className="py-3 px-3">
                        {c.cloudinary_url ? (
                          <span className="inline-flex items-center space-x-1 text-[11px] text-neutral-300 bg-neutral-900 px-2 py-0.5 rounded border border-neutral-800">
                            <Cloud className="w-3 h-3 text-neutral-400" />
                            <span>Cloud Backup</span>
                          </span>
                        ) : (
                          <span className="text-neutral-500">Local Copy</span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectContract(c);
                          }}
                          className="text-xs font-semibold text-neutral-100 hover:text-white inline-flex items-center space-x-1"
                        >
                          <span>Open Review</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}

      {/* 5. Privacy & Legal Notice Footer */}
      <footer className="border-t border-neutral-900 py-10 px-4 text-center text-xs text-neutral-500 max-w-4xl mx-auto">
        <div className="flex items-center justify-center space-x-2 mb-2 text-neutral-400">
          <Scale className="w-4 h-4" />
          <span className="font-serif font-bold text-neutral-300">ContractIQ</span>
          <span>•</span>
          <span>Legal Risk Intelligence</span>
        </div>
        <p className="max-w-xl mx-auto leading-relaxed text-[11px] text-neutral-500">
          <strong>Confidentiality Notice:</strong> All uploaded contracts and review results are processed securely for your active session. ContractIQ does not sell or publicly store contract texts. Please handle confidential agreements in accordance with your organization's legal policies.
        </p>
      </footer>
    </div>
  );
};

