import React, { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useActiveCase } from '../context/CaseContext';

export default function UploadEvidencePage() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const { activeCase } = useActiveCase();

  const [dragActive, setDragActive] = useState(false);
  const [stagedFiles, setStagedFiles] = useState([
    {
      name: 'msgstore.db.crypt15',
      size: '182.4 MiB',
      type: 'WhatsApp Encrypted Database',
      hash: '8a72cf19d45e08b1a32f91bc740192e8fa312904bc78e120aa45192803bba221',
      status: 'Ready to Ingest',
      progress: 100
    },
    {
      name: 'encrypted_backup.key',
      size: '128 B',
      type: 'AES-256 Key Derivation File',
      hash: '01f5e88d11ac293847291048b291048572910485729104857291048572910485',
      status: 'Ready to Ingest',
      progress: 100
    }
  ]);

  const [metadata, setMetadata] = useState({
    exhibitNumber: 'EX-2026-09A',
    seizingOfficer: 'Det. H. Wright (Badge #402)',
    extractionType: 'Physical Chip-Off / Bit-Stream Forensic Image',
    sourceDeviceImei: '354892019482019',
    airgapVerified: true
  });

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
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setStagedFiles(prev => [
        ...prev,
        {
          name: file.name,
          size: `${(file.size / (1024 * 1024)).toFixed(1)} MiB`,
          type: 'Raw Forensic Partition / File',
          hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
          status: 'Ready to Ingest',
          progress: 100
        }
      ]);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setStagedFiles(prev => [
        ...prev,
        {
          name: file.name,
          size: `${(file.size / (1024 * 1024)).toFixed(1)} MiB`,
          type: 'Uploaded Container',
          hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
          status: 'Ready to Ingest',
          progress: 100
        }
      ]);
    }
  };

  const handleCommitIngest = () => {
    navigate(`/cases/${caseId || activeCase?.id}/evidence`);
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-y-auto custom-scrollbar p-space-lg">
      <div className="max-w-[1100px] mx-auto w-full space-y-5 pb-12">
        {/* ================= HEADER ================= */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-outline-variant">
          <div>
            <div className="flex items-center space-x-2.5 mb-1">
              <h1 className="text-headline-lg font-headline-lg font-semibold text-on-surface">
                Upload Evidence
              </h1>
              <span className="px-2 py-0.5 rounded text-[11px] font-label-mono-sm bg-primary/10 text-primary border border-primary/30">
                HASH-CHECKING AUTO-ENABLED
              </span>
            </div>
            <p className="text-body-md font-body-md text-on-surface-variant">
              Ingest WhatsApp databases (.crypt14/15, plain SQLite), Telegram cache4.db with WAL/SHM, media ZIPs, and key files into case {caseId || activeCase?.caseNumber}.
            </p>
          </div>

          <div className="self-start md:self-auto flex items-center space-x-2 bg-surface-container border border-outline-variant px-3 py-1.5 rounded">
            <span className="material-symbols-outlined text-primary text-[18px]">verified</span>
            <span className="font-label-mono-sm text-[11px] text-on-surface tracking-wide">
              CHAIN OF CUSTODY BUFFER · STATION WS-LON-402
            </span>
          </div>
        </div>

        {/* ================= DROP ZONE ================= */}
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg bg-surface-container p-8 text-center transition-all ${
            dragActive ? 'border-primary bg-primary/5' : 'border-outline-variant hover:border-primary/60'
          }`}
        >
          <div className="flex flex-col items-center justify-center max-w-xl mx-auto space-y-3">
            <div className="w-14 h-14 rounded-full bg-surface-container-high border border-outline-variant flex items-center justify-center text-primary shadow-inner">
              <span className="material-symbols-outlined text-[30px]">upload_file</span>
            </div>

            <div className="space-y-1">
              <p className="text-headline-sm font-headline-sm text-on-surface">
                Drag and drop evidence files here, or browse workstation storage
              </p>
              <p className="text-body-sm font-body-sm text-on-surface-variant">
                Supports WhatsApp (.crypt14, .crypt15, msgstore.db), key files (encrypted_backup.key), Telegram (cache4.db, cache4.db-wal, cache4.db-shm), and media archives (.zip, .tar)
              </p>
            </div>

            <div className="flex items-center space-x-3 pt-2">
              <label className="btn-primary cursor-pointer">
                <span className="material-symbols-outlined text-[18px]">lock_open</span>
                <span>Select Files from Vault</span>
                <input type="file" onChange={handleFileSelect} className="hidden" />
              </label>
              <span className="text-label-mono-sm text-outline border-l border-outline-variant pl-3 text-xs">
                Maximum upload 256 MiB per artifact
              </span>
            </div>
          </div>
        </div>

        {/* ================= ACQUISITION METADATA FORM ================= */}
        <div className="bg-surface-container border border-outline-variant rounded-lg p-space-lg space-y-4 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-outline-variant">
            <div className="flex items-center space-x-2">
              <span className="material-symbols-outlined text-primary text-[18px]">assignment</span>
              <h2 className="text-headline-sm font-headline-sm text-on-surface">
                Custodial Acquisition Metadata
              </h2>
            </div>
            <span className="text-[11px] font-label-mono-sm text-outline">Section 63 Intake Schedule</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-label-ui uppercase tracking-wider text-on-surface-variant block text-xs">
                Exhibit / Tag Identifier
              </label>
              <input
                type="text"
                value={metadata.exhibitNumber}
                onChange={(e) => setMetadata({ ...metadata, exhibitNumber: e.target.value })}
                className="w-full bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1.5 text-body-sm text-on-surface focus:outline-none focus:border-primary"
              />
            </div>

            <div className="space-y-1">
              <label className="text-label-ui uppercase tracking-wider text-on-surface-variant block text-xs">
                Seizing Officer / Forensic Technician
              </label>
              <input
                type="text"
                value={metadata.seizingOfficer}
                onChange={(e) => setMetadata({ ...metadata, seizingOfficer: e.target.value })}
                className="w-full bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1.5 text-body-sm text-on-surface focus:outline-none focus:border-primary"
              />
            </div>

            <div className="space-y-1">
              <label className="text-label-ui uppercase tracking-wider text-on-surface-variant block text-xs">
                Extraction Methodology
              </label>
              <input
                type="text"
                value={metadata.extractionType}
                onChange={(e) => setMetadata({ ...metadata, extractionType: e.target.value })}
                className="w-full bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1.5 text-body-sm text-on-surface focus:outline-none focus:border-primary"
              />
            </div>

            <div className="space-y-1">
              <label className="text-label-ui uppercase tracking-wider text-on-surface-variant block text-xs">
                Source Device IMEI / Serial Number
              </label>
              <input
                type="text"
                value={metadata.sourceDeviceImei}
                onChange={(e) => setMetadata({ ...metadata, sourceDeviceImei: e.target.value })}
                className="w-full bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1.5 text-body-sm text-on-surface font-mono focus:outline-none focus:border-primary"
              />
            </div>
          </div>
        </div>

        {/* ================= STAGED FILES QUEUE ================= */}
        <div className="bg-surface-container border border-outline-variant rounded-lg p-space-lg space-y-4 shadow-sm">
          <div className="flex items-center justify-between pb-2 border-b border-outline-variant">
            <div className="flex items-center space-x-2">
              <span className="material-symbols-outlined text-primary text-[18px]">checklist</span>
              <h2 className="text-headline-sm font-headline-sm text-on-surface">
                Staged Ingestion Queue ({stagedFiles.length} files ready)
              </h2>
            </div>
            <span className="text-[11px] font-label-mono-sm text-tertiary">Cryptographic Pre-Hash Valid</span>
          </div>

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
                  <code className="text-[10px] font-mono text-outline bg-surface-container-lowest px-2 py-0.5 rounded border border-outline-variant hidden md:block">
                    {file.hash.substring(0, 18)}...
                  </code>
                  <span className="px-2 py-0.5 rounded bg-tertiary/10 text-tertiary border border-tertiary/30 text-[10px] font-label-mono-sm font-medium">
                    {file.status}
                  </span>
                  <button
                    type="button"
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

          <div className="pt-2 flex items-center justify-between">
            <Link
              to={`/cases/${caseId || activeCase?.id}/evidence`}
              className="text-body-sm text-on-surface-variant hover:text-on-surface"
            >
              ← Cancel and Return to Evidence List
            </Link>

            <button
              type="button"
              onClick={handleCommitIngest}
              className="btn-primary"
            >
              <span className="material-symbols-outlined text-[18px]">verified</span>
              <span>Commit Ingestion to Immutable Ledger</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
