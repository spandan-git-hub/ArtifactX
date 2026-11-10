import React, { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useActiveCase } from '../context/CaseContext';
import { uploadEvidence } from '../services/evidenceService';

export default function UploadEvidencePage() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const { activeCase, refreshCases } = useActiveCase();

  const activeId = caseId || activeCase?.id;

  const [dragActive, setDragActive] = useState(false);
  const [stagedFiles, setStagedFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      addFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      addFiles(Array.from(e.target.files));
    }
  };

  const addFiles = (files) => {
    const formatted = files.map(file => {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
      const isKey = file.name.endsWith('.key') || file.name.includes('key');
      const isDb = file.name.includes('.db') || file.name.includes('.crypt');
      const fileType = isKey ? 'AES-256 Key Derivation File' : (isDb ? 'Encrypted Forensic Database' : 'Raw Partition / Evidence File');
      return {
        rawFile: file,
        name: file.name,
        size: `${sizeMB} MiB`,
        type: fileType,
        hash: 'Pending SHA-256 Hash on Server',
        status: 'Staged for Ingestion',
        progress: 0
      };
    });
    setStagedFiles(prev => [...prev, ...formatted]);
  };

  const handleCommitIngest = async () => {
    if (stagedFiles.length === 0) return;
    if (!activeId) {
      setUploadError('No active case selected to associate this evidence with.');
      return;
    }

    setUploading(true);
    setUploadError(null);

    try {
      for (const item of stagedFiles) {
        if (item.rawFile) {
          await uploadEvidence(activeId, item.rawFile);
        }
      }
      if (refreshCases) await refreshCases();
      navigate(`/cases/${activeId}/overview`);
    } catch (err) {
      console.error('Evidence upload failed:', err);
      setUploadError(err.response?.data?.detail || err.message || 'Evidence ingestion failed.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-y-auto custom-scrollbar p-space-lg">
      <div className="max-w-[1100px] mx-auto w-full space-y-5 pb-12">
        {/* ================= HEADER ================= */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-outline-variant">
          <div>
            <h1 className="text-headline-lg font-headline-lg font-semibold text-on-surface">
              Upload Evidence
            </h1>
            <p className="text-body-sm text-on-surface-variant">
              Stage bit-stream physical dumps, encrypted databases, or key derivation material for {activeCase?.caseNumber || 'case'}.
            </p>
          </div>
        </div>

        {uploadError && (
          <div className="p-3 bg-error/15 border border-error/40 rounded-lg text-error text-xs font-mono">
            Error: {uploadError}
          </div>
        )}

        {/* ================= DROPZONE ================= */}
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-all ${
            dragActive
              ? 'border-primary bg-primary/10 scale-[0.99]'
              : 'border-outline-variant bg-surface-container-low hover:border-primary/50'
          }`}
        >
          <input
            type="file"
            id="evidence-file-input"
            multiple
            onChange={handleFileSelect}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          />

          <div className="max-w-md mx-auto space-y-3 pointer-events-none">
            <div className="w-12 h-12 rounded-full bg-surface-container-highest flex items-center justify-center mx-auto text-primary border border-outline-variant">
              <span className="material-symbols-outlined text-[30px]">upload_file</span>
            </div>

            <div>
              <p className="text-body-md font-semibold text-on-surface">
                Drag &amp; Drop forensic evidence files here, or <span className="text-primary underline">browse</span>
              </p>
              <p className="text-body-sm text-on-surface-variant mt-1 text-xs">
                Supports WhatsApp databases (<code className="text-primary font-mono">.crypt14/.crypt15</code>), Telegram caches (<code className="text-primary font-mono">cache4.db</code>), WAL frames, and key files.
              </p>
            </div>

            <div className="pt-2 flex items-center justify-center space-x-2 text-label-mono-sm text-on-surface-variant text-[11px]">
              <span className="material-symbols-outlined text-[16px]">fingerprint</span>
              <span>SHA-256, MD5, SHA-1, and SHA-512 computed on ingest</span>
            </div>
          </div>
        </div>

        {/* ================= STAGED FILES QUEUE ================= */}
        <div className="bg-surface-container border border-outline-variant rounded-lg p-space-lg space-y-4 shadow-sm">
          <div className="flex items-center justify-between pb-2 border-b border-outline-variant">
            <div className="flex items-center space-x-2">
              <span className="material-symbols-outlined text-primary text-[18px]">checklist</span>
              <h2 className="text-headline-sm font-headline-sm text-on-surface">
                Staged Ingestion Queue ({stagedFiles.length} files)
              </h2>
            </div>
            {stagedFiles.length > 0 && (
              <span className="text-[11px] font-label-mono-sm text-tertiary">Ready to Transfer to Secure Storage</span>
            )}
          </div>

          {stagedFiles.length === 0 ? (
            <div className="py-8 text-center text-on-surface-variant border border-dashed border-outline-variant/60 rounded bg-surface-container-low">
              <span className="material-symbols-outlined text-3xl text-outline mb-1">cloud_upload</span>
              <p className="text-body-sm font-medium">No evidence files staged yet.</p>
              <p className="text-[11px] text-outline">Select or drop raw forensic files into the dropzone above to stage them.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {stagedFiles.map((file, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded bg-surface-container-low border border-outline-variant flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                >
                  <div className="flex items-center space-x-3 min-w-0">
                    <span className="material-symbols-outlined text-primary text-[20px]">
                      {file.name.endsWith('.key') ? 'key' : 'database'}
                    </span>
                    <div className="min-w-0">
                      <div className="font-medium text-on-surface font-mono text-sm truncate">{file.name}</div>
                      <div className="text-[11px] text-on-surface-variant">
                        {file.type} · {file.size}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3 shrink-0">
                    <span className="px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/30 text-[10px] font-label-mono-sm font-medium">
                      {file.status}
                    </span>
                    <button
                      type="button"
                      disabled={uploading}
                      onClick={() => setStagedFiles(stagedFiles.filter((_, i) => i !== idx))}
                      className="text-on-surface-variant hover:text-error p-1"
                      title="Remove"
                    >
                      <span className="material-symbols-outlined text-[16px]">delete</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="pt-2 flex items-center justify-between">
            <Link
              to={`/cases/${activeId}/evidence`}
              className="text-body-sm text-on-surface-variant hover:text-on-surface"
            >
              ← Cancel and Return to Evidence List
            </Link>

            <button
              type="button"
              disabled={uploading || stagedFiles.length === 0}
              onClick={handleCommitIngest}
              className="btn-primary flex items-center space-x-1.5"
            >
              <span className={`material-symbols-outlined text-[18px] ${uploading ? 'animate-spin' : ''}`}>
                {uploading ? 'sync' : 'verified'}
              </span>
              <span>{uploading ? 'Ingesting Evidence...' : 'Upload & Ingest Evidence'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
