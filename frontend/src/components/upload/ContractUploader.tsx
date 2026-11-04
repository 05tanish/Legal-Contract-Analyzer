import React, { useState } from 'react';
import { UploadCloud, X, AlertCircle, FileText, CheckCircle2, Scale } from 'lucide-react';
import { uploadContract } from '../../lib/api';
import { Contract } from '../../types';

interface ContractUploaderProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (contract: Contract) => void;
}

export const ContractUploader: React.FC<ContractUploaderProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStep, setUploadStep] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    else if (e.type === 'dragleave') setDragActive(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const selected = e.dataTransfer.files[0];
      if (selected.type === 'application/pdf' || selected.name.toLowerCase().endsWith('.pdf')) {
        setFile(selected);
        setError(null);
      } else {
        setError('Please select a valid PDF file. Other formats are not supported.');
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleSubmit = async () => {
    if (!file) return;
    setIsUploading(true);
    setError(null);
    setUploadStep('Reading and analyzing document pages...');

    const stepTimer1 = setTimeout(() => {
      setUploadStep('Checking clauses and detecting legal risks...');
    }, 1200);

    const stepTimer2 = setTimeout(() => {
      setUploadStep('Saving document and preparing your summary...');
    }, 2800);

    try {
      const contract = await uploadContract(file);
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      onUploadSuccess(contract);
      onClose();
    } catch (err: any) {
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      setError(err.message || 'We were unable to process this document. Please ensure it is a valid, readable PDF file.');
    } finally {
      setIsUploading(false);
      setUploadStep('');
    }
  };

  return (
    <div className="fixed inset-0 bg-black/75 backdrop-blur-xs z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-[#121316] text-neutral-900 dark:text-neutral-100 border border-neutral-200 dark:border-[#27272a] rounded-xl w-full max-w-lg p-6 sm:p-7 shadow-2xl relative animate-in fade-in duration-150">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded bg-neutral-900 dark:bg-neutral-800 flex items-center justify-center text-white">
              <Scale className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-serif font-bold text-lg text-neutral-900 dark:text-white">
                Upload Contract for Review
              </h3>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">
                Identifies risks, checks compliance with Indian law, and suggests safer wording.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isUploading}
            className="text-neutral-400 hover:text-neutral-700 dark:hover:text-white p-1 rounded-md transition"
            title="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Error notification */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/60 rounded-md flex items-center space-x-2 text-xs text-red-700 dark:text-red-300">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Minimalist dashed drop area */}
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg p-8 text-center transition cursor-pointer ${
            dragActive
              ? 'border-neutral-900 dark:border-white bg-neutral-50 dark:bg-neutral-800/40'
              : 'border-neutral-300 dark:border-[#2a2b30] hover:border-neutral-400 dark:hover:border-neutral-600 bg-neutral-50/50 dark:bg-[#18191e]/50'
          }`}
          onClick={() => document.getElementById('contract-file-input')?.click()}
        >
          <input
            id="contract-file-input"
            type="file"
            accept=".pdf,application/pdf"
            onChange={handleFileChange}
            className="hidden"
          />

          <div className="flex flex-col items-center">
            <div className="w-10 h-10 rounded-full bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center mb-3 text-neutral-600 dark:text-neutral-300">
              <UploadCloud className="w-5 h-5" />
            </div>

            {file ? (
              <div className="flex items-center space-x-2 text-xs font-semibold text-neutral-900 dark:text-white bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 px-3 py-1.5 rounded shadow-xs">
                <FileText className="w-4 h-4 text-neutral-600 dark:text-neutral-300" />
                <span className="truncate max-w-xs">{file.name}</span>
                <span className="text-neutral-400 font-mono">({(file.size / 1024 / 1024).toFixed(2)} MB)</span>
              </div>
            ) : (
              <>
                <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 mb-1">
                  Drag and drop contract PDF here, or <span className="underline">browse files</span>
                </p>
                <p className="text-[11px] text-neutral-500 dark:text-neutral-400">
                  Accepts standard PDF documents up to 50MB. Scanned and text PDFs supported.
                </p>
              </>
            )}
          </div>
        </div>

        {/* Upload progress indicator */}
        {isUploading && (
          <div className="mt-4 p-3 bg-neutral-50 dark:bg-[#18191e] border border-neutral-200 dark:border-[#27272a] rounded-md">
            <div className="flex items-center space-x-2.5">
              <div className="w-4 h-4 border-2 border-neutral-400 border-t-neutral-900 dark:border-t-white rounded-full animate-spin shrink-0" />
              <div className="flex-1">
                <p className="text-xs font-medium text-neutral-800 dark:text-neutral-200">{uploadStep}</p>
                <div className="w-full bg-neutral-200 dark:bg-neutral-800 h-1 rounded-full mt-2 overflow-hidden">
                  <div className="bg-neutral-900 dark:bg-white h-full animate-pulse w-3/4 rounded-full" />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="mt-6 flex items-center justify-end space-x-2.5">
          <button
            onClick={onClose}
            disabled={isUploading}
            className="px-3.5 py-1.5 text-xs font-medium text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white rounded-md transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!file || isUploading}
            className="bg-neutral-900 dark:bg-white hover:bg-neutral-800 dark:hover:bg-neutral-200 disabled:opacity-40 text-white dark:text-neutral-950 px-4 py-2 rounded-md text-xs font-semibold shadow-xs transition flex items-center space-x-1.5 cursor-pointer disabled:cursor-not-allowed"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{isUploading ? 'Uploading & Reviewing...' : 'Upload & Review'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
