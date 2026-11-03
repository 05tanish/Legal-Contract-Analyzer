import React, { useState } from 'react';
import { UploadCloud, X, AlertCircle } from 'lucide-react';
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
      if (selected.type === 'application/pdf') {
        setFile(selected);
        setError(null);
      } else {
        setError('Please drop a valid PDF contract file.');
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
    try {
      const contract = await uploadContract(file);
      onUploadSuccess(contract);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Upload and indexing failed');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white transition"
        >
          <X className="w-5 h-5" />
        </button>

        <h3 className="text-xl font-bold text-white mb-2">Upload Legal Contract</h3>
        <p className="text-sm text-slate-400 mb-6">
          PDF will be parsed with layout-awareness (Docling), sliced into hierarchical parent-child chunks, and indexed into Qdrant.
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center space-x-2 text-sm text-red-400">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-xl p-8 text-center transition flex flex-col items-center justify-center ${
            dragActive
              ? 'border-indigo-500 bg-indigo-500/10'
              : 'border-slate-700 bg-slate-800/40 hover:bg-slate-800/70'
          }`}
        >
          <UploadCloud className="w-12 h-12 text-slate-400 mb-3" />
          <p className="text-sm font-medium text-slate-200 mb-1">
            {file ? file.name : 'Drag & drop contract PDF here'}
          </p>
          <p className="text-xs text-slate-500 mb-4">Max size 50MB (Standard PDF with selectable text)</p>

          <label className="bg-slate-800 hover:bg-slate-700 text-indigo-400 px-4 py-2 rounded-lg text-xs font-semibold border border-slate-700 cursor-pointer transition">
            Browse Computer
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              className="hidden"
            />
          </label>
        </div>

        <div className="mt-6 flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!file || isUploading}
            className="px-5 py-2 rounded-lg text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800/50 text-white transition flex items-center space-x-2"
          >
            {isUploading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Indexing to Qdrant...</span>
              </>
            ) : (
              <span>Start Ingestion</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

