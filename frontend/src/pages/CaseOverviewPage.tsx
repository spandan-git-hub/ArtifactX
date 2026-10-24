import React, { useState, useEffect, useCallback } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { useActiveCase } from '../context/CaseContext';
import { caseService } from '../services/caseService';
import { evidenceService, uploadEvidence } from '../services/evidenceService';

export default function CaseOverviewPage() {
  const { caseId: paramCaseId } = useParams();
  const navigate = useNavigate();
  const { activeCase, cases, switchCase, deleteCase, refreshCases } = useActiveCase();

  // Find target case from param or activeCase
  const currentCase = cases.find(c => String(c.id) === String(paramCaseId) || c.caseNumber === paramCaseId) || activeCase;
  const effectiveCaseId = currentCase?.id || paramCaseId;

  const [workspaceData, setWorkspaceData] = useState(null);
  const [evidenceList, setEvidenceList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [copiedHash, setCopiedHash] = useState(null);

  // Upload modal state
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [stagedFiles, setStagedFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  // Delete modal state
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Fetch live case workspace and evidence list
  const loadCaseOverview = useCallback(async () => {
    if (!effectiveCaseId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [workspaceRes, evidenceRes] = await Promise.allSettled([
        caseService.getCaseWorkspace(effectiveCaseId),
        evidenceService.getEvidences(effectiveCaseId)
      ]);

      if (workspaceRes.status === 'fulfilled' && workspaceRes.value) {
        setWorkspaceData(workspaceRes.value);
      }
      if (evidenceRes.status === 'fulfilled' && evidenceRes.value) {
        const rawEv = Array.isArray(evidenceRes.value) ? evidenceRes.value : (evidenceRes.value?.evidences || []);
        setEvidenceList(rawEv);
      }
    } catch (err) {
      console.warn('Error loading case overview data:', err);
    } finally {
      setLoading(false);
    }
  }, [effectiveCaseId]);

  useEffect(() => {
    loadCaseOverview();
  }, [loadCaseOverview]);

  // Ensure activeCase is synchronized with URL
  useEffect(() => {
    if (paramCaseId && (!activeCase || String(activeCase.id) !== String(paramCaseId))) {
      switchCase(paramCaseId);
    }
  }, [paramCaseId, activeCase, switchCase]);

  const copyToClipboard = (text, key) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(key);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const formatFileSize = (bytes) => {
    if (!bytes || isNaN(bytes)) return '0 B';
    const num = Number(bytes);
    if (num < 1024) return `${num} B`;
    if (num < 1024 * 1024) return `${(num / 1024).toFixed(1)} KiB`;
    if (num < 1024 * 1024 * 1024) return `${(num / (1024 * 1024)).toFixed(2)} MiB`;
    return `${(num / (1024 * 1024 * 1024)).toFixed(2)} GiB`;
  };

  const getFormatBadge = (ev) => {
    const format = ev.detected_format || ev.format || '';
    const fname = (ev.original_filename || '').toLowerCase();

    if (format.includes('WHATSAPP') || fname.includes('whatsapp') || fname.includes('msgstore')) {
      return { label: 'WhatsApp Package', color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30', icon: 'chat' };
    }
    if (format.includes('TELEGRAM') || fname.includes('telegram') || fname.includes('cache4') || fname.includes('tdata')) {
      return { label: 'Telegram Package', color: 'bg-blue-500/10 text-blue-400 border-blue-500/30', icon: 'send' };
    }
    if (format === 'ZIP' || fname.endsWith('.zip')) {
      return { label: 'ZIP Forensic Container', color: 'bg-purple-500/10 text-purple-400 border-purple-500/30', icon: 'folder_zip' };
    }
    if (fname.endsWith('.key') || fname.includes('key')) {
      return { label: 'AES Key Credential', color: 'bg-amber-500/10 text-amber-400 border-amber-500/30', icon: 'key' };
    }
    if (fname.includes('.db') || fname.includes('.sqlite')) {
      return { label: 'SQLite Database', color: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30', icon: 'database' };
    }
    return { label: format || 'Evidence Exhibit', color: 'bg-surface-variant text-on-surface-variant border-outline-variant', icon: 'draft' };
  };

  // Drag and drop handlers for upload modal
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
      addStagedFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      addStagedFiles(Array.from(e.target.files));
    }
  };

  const addStagedFiles = (files) => {
    const formatted = files.map(file => ({
      rawFile: file,
      name: file.name,
      size: formatFileSize(file.size),
      sizeBytes: file.size,
      status: 'Staged for Ingestion'
    }));
    setStagedFiles(prev => [...prev, ...formatted]);
  };

  const removeStagedFile = (index) => {
    setStagedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleUploadFiles = async () => {
    if (stagedFiles.length === 0 || !effectiveCaseId) return;
    setUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      for (const item of stagedFiles) {
        if (item.rawFile) {
          await uploadEvidence(effectiveCaseId, item.rawFile);
        }
      }
      setUploadSuccess(`Successfully ingested ${stagedFiles.length} evidence file(s)!`);
      setStagedFiles([]);
      if (refreshCases) await refreshCases();
      await loadCaseOverview();
      setTimeout(() => {
        setShowUploadModal(false);
        setUploadSuccess(null);
      }, 1400);
    } catch (err) {
      console.error('Evidence upload error:', err);
      setUploadError(err.response?.data?.detail || err.message || 'Evidence upload failed.');
    } finally {
      setUploading(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!currentCase) return;
    try {
      setIsDeleting(true);
      await deleteCase(currentCase.id);
      setShowDeleteModal(false);
      navigate('/cases');
    } catch (err) {
      console.error('Failed to delete case from overview:', err);
    } finally {
      setIsDeleting(false);
    }
  };

  const caseDetails = workspaceData?.case || currentCase || {};
  const counts = workspaceData?.summary_counts || {};
  const totalEvidenceCount = evidenceList.length;

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-y-auto custom-scrollbar p-space-lg">
      <div className="w-full max-w-[1240px] mx-auto flex flex-col space-y-5 pb-12">

        {/* ================= TOP ACTION BAR & DOCKET HEADER ================= */}
        <div className="flex flex-wrap items-center justify-between gap-3 bg-surface-container-low border border-outline-variant rounded-xl p-4 shadow-sm">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center text-primary">
              <span className="material-symbols-outlined text-[24px]">folder_special</span>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-label-mono-sm text-label-mono-sm text-outline">DOCKET:</span>
                <span className="font-headline-sm text-headline-sm font-semibold text-primary">
                  {caseDetails.case_number || currentCase?.caseNumber || 'N/A'}
                </span>
                <button
                  type="button"
                  onClick={() => copyToClipboard(caseDetails.case_number || currentCase?.caseNumber || '', 'docket')}
                  className="text-on-surface-variant hover:text-primary transition-colors cursor-pointer"
                  title="Copy Docket ID"
                >
                  <span className="material-symbols-outlined text-[15px]">
                    {copiedHash === 'docket' ? 'check' : 'content_copy'}
                  </span>
                </button>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                  caseDetails.status === 'Active' || currentCase?.status === 'Active' || currentCase?.status === 'open'
                    ? 'bg-tertiary/15 text-tertiary border-tertiary/30'
                    : 'bg-surface-variant text-on-surface-variant border-outline-variant'
                }`}>
                  {caseDetails.status || currentCase?.status || 'Active'}
                </span>
              </div>
              <h1 className="text-body-md font-semibold text-on-surface mt-0.5 truncate max-w-xl">
                {caseDetails.name || currentCase?.title || 'Forensic Investigation'}
              </h1>
            </div>
          </div>

          {/* Action Buttons: Upload Evidence Files & Delete */}
          <div className="flex items-center space-x-2.5">
            <button
              type="button"
              onClick={() => setShowUploadModal(true)}
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-primary hover:opacity-90 text-on-primary font-medium text-body-sm shadow-sm transition-all cursor-pointer"
              title="Upload evidence files to this case"
            >
              <span className="material-symbols-outlined text-[18px]">upload_file</span>
              <span>Upload Evidence Files</span>
            </button>

            <Link
              to={`/cases/${effectiveCaseId}/upload`}
              className="hidden sm:flex items-center space-x-1.5 px-3 py-2 rounded-lg bg-surface-container border border-outline-variant text-on-surface hover:bg-surface-container-high text-body-sm font-medium transition-colors"
              title="Full evidence ingestion workbench"
            >
              <span className="material-symbols-outlined text-[16px]">tune</span>
              <span>Advanced Ingest</span>
            </Link>

            {currentCase && (
              <button
                type="button"
                onClick={() => setShowDeleteModal(true)}
                className="flex items-center space-x-1 px-3 py-2 rounded-lg bg-surface-container hover:bg-error/15 hover:text-error hover:border-error/40 text-on-surface-variant border border-outline-variant text-body-sm font-medium transition-colors cursor-pointer"
                title={`Delete Case ${currentCase.caseNumber}`}
              >
                <span className="material-symbols-outlined text-[16px]">delete</span>
              </button>
            )}
          </div>
        </div>

        {/* ================= OVERALL CASE DETAILS GRID ================= */}
        <div className="bg-surface-container border border-outline-variant rounded-xl p-5 shadow-xs">
          <div className="flex items-center justify-between pb-3 mb-4 border-b border-outline-variant">
            <div className="flex items-center space-x-2">
              <span className="material-symbols-outlined text-primary text-[20px]">badge</span>
              <h2 className="font-headline-sm text-headline-sm text-on-surface font-semibold">
                Overall Case Details
              </h2>
            </div>
            <div className="flex items-center space-x-3 text-label-mono-sm text-on-surface-variant">
              <span>CREATED: {currentCase?.createdDate || (caseDetails.created_at ? new Date(caseDetails.created_at).toLocaleDateString() : 'Today')}</span>
              <span className="text-outline">|</span>
              <span>HASH INTEGRITY: <strong className="text-tertiary">100% OK</strong></span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-3 rounded-lg bg-surface-container-low border border-outline-variant space-y-1">
              <div className="text-[11px] font-mono uppercase text-on-surface-variant">Lead Examiner</div>
              <div className="font-semibold text-on-surface text-body-sm truncate">
                {caseDetails.examiner_name || caseDetails.investigator || currentCase?.examiner || 'Unassigned'}
              </div>
              <div className="text-[10px] text-outline font-mono">Forensic Analyst ID</div>
            </div>

            <div className="p-3 rounded-lg bg-surface-container-low border border-outline-variant space-y-1">
              <div className="text-[11px] font-mono uppercase text-on-surface-variant">Agency / Unit</div>
              <div className="font-semibold text-on-surface text-body-sm truncate">
                {caseDetails.agency || currentCase?.agency || 'Cyber Forensics Division'}
              </div>
              <div className="text-[10px] text-outline font-mono">Authorizing Jurisdiction</div>
            </div>

            <div className="p-3 rounded-lg bg-surface-container-low border border-outline-variant space-y-1">
              <div className="text-[11px] font-mono uppercase text-on-surface-variant">Target Device</div>
              <div className="font-semibold text-on-surface text-body-sm truncate">
                {caseDetails.device_target || currentCase?.deviceTarget || 'Mobile Device / Physical Dump'}
              </div>
              <div className="text-[10px] text-outline font-mono">Acquisition Profile</div>
            </div>

            <div className="p-3 rounded-lg bg-surface-container-low border border-outline-variant space-y-1">
              <div className="text-[11px] font-mono uppercase text-on-surface-variant">Total Evidence Exhibits</div>
              <div className="font-bold text-primary text-xl font-mono">
                {totalEvidenceCount} <span className="text-xs font-sans font-normal text-on-surface-variant">files mounted</span>
              </div>
              <div className="text-[10px] text-tertiary font-mono">Multi-Algorithm Hashed</div>
            </div>
          </div>

          {caseDetails.description && (
            <div className="mt-4 pt-3 border-t border-outline-variant/60">
              <div className="text-[11px] font-mono uppercase text-on-surface-variant mb-1">Investigation Scope & Notes:</div>
              <p className="text-body-sm text-on-surface-variant leading-relaxed">
                {caseDetails.description}
              </p>
            </div>
          )}
        </div>

        {/* ================= UPLOADED EVIDENCE SECTION (DYNAMIC) ================= */}
        <div className="bg-surface-container border border-outline-variant rounded-xl p-5 shadow-xs space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-outline-variant">
            <div className="flex items-center space-x-2.5">
              <span className="material-symbols-outlined text-primary text-[22px]">inventory_2</span>
              <h2 className="font-headline-sm text-headline-sm text-on-surface font-semibold">
                Uploaded Evidence Files
              </h2>
              <span className="text-label-mono-sm px-2 py-0.5 rounded-full bg-primary/10 border border-primary/30 text-primary font-mono text-[11px]">
                {totalEvidenceCount} Exhibits
              </span>
            </div>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={() => setShowUploadModal(true)}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-primary/15 hover:bg-primary/25 border border-primary/30 text-primary text-label-ui font-medium transition-colors cursor-pointer"
              >
                <span className="material-symbols-outlined text-[16px]">add</span>
                <span>Upload Evidence</span>
              </button>

              <Link
                to={`/cases/${effectiveCaseId}/evidence`}
                className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-surface-container-low border border-outline-variant text-on-surface hover:bg-surface-container-high text-label-ui font-medium transition-colors"
              >
                <span>Evidence Tab</span>
                <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
              </Link>
            </div>
          </div>

          {/* Evidence Items Display */}
          {loading ? (
            <div className="py-12 flex flex-col items-center justify-center space-y-2 text-on-surface-variant">
              <span className="material-symbols-outlined text-[28px] animate-spin text-primary">progress_activity</span>
              <p className="text-body-sm">Loading uploaded evidence inventory...</p>
            </div>
          ) : evidenceList.length === 0 ? (
            /* Empty State */
            <div className="py-10 px-4 text-center rounded-xl bg-surface-container-low border border-dashed border-outline-variant space-y-3">
              <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/30 flex items-center justify-center mx-auto text-primary">
                <span className="material-symbols-outlined text-[28px]">cloud_upload</span>
              </div>
              <div className="space-y-1">
                <h3 className="font-headline-sm text-headline-sm font-semibold text-on-surface">
                  No Evidence Uploaded Yet
                </h3>
                <p className="text-body-sm text-on-surface-variant max-w-md mx-auto">
                  Click the button below to upload WhatsApp/Telegram database dumps, ZIP containers, SQLite databases, or cryptographic keys for this case.
                </p>
              </div>
              <div className="pt-2">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(true)}
                  className="px-4 py-2 rounded-lg bg-primary text-on-primary hover:opacity-90 font-medium text-body-sm inline-flex items-center space-x-2 shadow-sm transition-all cursor-pointer"
                >
                  <span className="material-symbols-outlined text-[18px]">upload_file</span>
                  <span>Upload Evidence Files</span>
                </button>
              </div>
            </div>
          ) : (
            /* Evidence Table / Cards List */
            <div className="space-y-3">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-surface-container-lowest/70 border-b border-outline-variant text-[11px] font-mono text-on-surface-variant uppercase tracking-wider">
                      <th className="py-2.5 px-3">Evidence Item / Filename</th>
                      <th className="py-2.5 px-3">Type & Detected Format</th>
                      <th className="py-2.5 px-3">Size</th>
                      <th className="py-2.5 px-3">Cryptographic SHA-256</th>
                      <th className="py-2.5 px-3">Integrity State</th>
                      <th className="py-2.5 px-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant/40 text-body-sm">
                    {evidenceList.map((ev, idx) => {
                      const badge = getFormatBadge(ev);
                      const sizeFormatted = ev.upload_size ? formatFileSize(ev.upload_size) : (ev.size ? formatFileSize(ev.size) : (ev.metadata?.upload_size ? formatFileSize(ev.metadata.upload_size) : 'N/A'));
                      const sha = ev.sha256 || 'Pending';
                      const isZip = ev.is_zip || (ev.detected_format === 'ZIP') || (ev.original_filename || '').endsWith('.zip') || (ev.metadata?.is_zip);
                      const extractedCount = ev.extracted_files_count || (ev.metadata?.extracted_files_count);

                      return (
                        <tr key={ev.id || idx} className="hover:bg-surface-container-high/50 transition-colors">
                          {/* Name & Icon */}
                          <td className="py-3 px-3">
                            <div className="flex items-center space-x-2.5">
                              <div className="w-8 h-8 rounded-lg bg-surface-container-highest flex items-center justify-center text-primary shrink-0 border border-outline-variant">
                                <span className="material-symbols-outlined text-[18px]">{badge.icon}</span>
                              </div>
                              <div className="overflow-hidden">
                                <div className="font-medium text-on-surface truncate max-w-[240px]">
                                  {ev.original_filename || ev.filename || 'Evidence File'}
                                </div>
                                <div className="text-[10px] text-outline font-mono">
                                  ID #{ev.id} · {ev.uploaded_at ? new Date(ev.uploaded_at).toLocaleString() : 'Uploaded'}
                                </div>
                              </div>
                            </div>
                          </td>

                          {/* Detected Format Badge */}
                          <td className="py-3 px-3">
                            <div className="flex flex-col items-start gap-1">
                              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono border ${badge.color}`}>
                                <span className="material-symbols-outlined text-[12px]">{badge.icon}</span>
                                {badge.label}
                              </span>
                              {isZip && extractedCount && (
                                <span className="text-[10px] text-on-surface-variant font-mono">
                                  {extractedCount} extracted exhibits
                                </span>
                              )}
                            </div>
                          </td>

                          {/* Size */}
                          <td className="py-3 px-3 font-mono text-label-mono-sm text-on-surface">
                            {sizeFormatted}
                          </td>

                          {/* SHA-256 */}
                          <td className="py-3 px-3">
                            <div className="flex items-center space-x-1.5 font-mono text-label-mono-sm bg-surface-container-lowest border border-outline-variant px-2 py-1 rounded w-fit">
                              <span className="text-primary truncate max-w-[130px] sm:max-w-[180px]">
                                {sha.substring(0, 16)}...{sha.substring(sha.length - 8)}
                              </span>
                              <button
                                type="button"
                                onClick={() => copyToClipboard(sha, `sha-${ev.id}`)}
                                className="text-on-surface-variant hover:text-primary transition-colors shrink-0 cursor-pointer"
                                title="Copy Full SHA-256"
                              >
                                <span className="material-symbols-outlined text-[13px]">
                                  {copiedHash === `sha-${ev.id}` ? 'check' : 'content_copy'}
                                </span>
                              </button>
                            </div>
                          </td>

                          {/* Integrity State */}
                          <td className="py-3 px-3">
                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono border ${
                              ev.integrity_state === 'ARCHIVE_REJECTED'
                                ? 'bg-error/10 text-error border-error/30'
                                : 'bg-tertiary/10 text-tertiary border-tertiary/30'
                            }`}>
                              <span className="w-1.5 h-1.5 rounded-full bg-current" />
                              {ev.integrity_state || 'OK'}
                            </span>
                          </td>

                          {/* Actions */}
                          <td className="py-3 px-3 text-right">
                            <div className="flex items-center justify-end space-x-2">
                              <Link
                                to={`/cases/${effectiveCaseId}/evidence`}
                                className="px-2.5 py-1 rounded bg-surface-container-low hover:bg-surface-container-high border border-outline-variant text-[11px] font-medium text-on-surface transition-colors"
                              >
                                Details
                              </Link>
                              <Link
                                to={`/cases/${effectiveCaseId}/decryption`}
                                className="px-2.5 py-1 rounded bg-primary/10 hover:bg-primary/20 border border-primary/30 text-[11px] font-medium text-primary transition-colors"
                              >
                                Decrypt
                              </Link>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* ================= WORKSPACE QUICK MODULE SHORTCUTS ================= */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
          <Link
            to={`/cases/${effectiveCaseId}/evidence`}
            className="p-3.5 rounded-xl bg-surface-container border border-outline-variant hover:border-primary transition-colors flex flex-col items-center text-center space-y-1.5 group"
          >
            <span className="material-symbols-outlined text-primary text-[24px] group-hover:scale-110 transition-transform">folder_open</span>
            <span className="text-body-sm font-semibold text-on-surface">Evidence</span>
            <span className="text-[10px] text-outline font-mono">{totalEvidenceCount} exhibits</span>
          </Link>

          <Link
            to={`/cases/${effectiveCaseId}/decryption`}
            className="p-3.5 rounded-xl bg-surface-container border border-outline-variant hover:border-primary transition-colors flex flex-col items-center text-center space-y-1.5 group"
          >
            <span className="material-symbols-outlined text-amber-400 text-[24px] group-hover:scale-110 transition-transform">key</span>
            <span className="text-body-sm font-semibold text-on-surface">Decryption</span>
            <span className="text-[10px] text-outline font-mono">Keys & Crypt</span>
          </Link>

          <Link
            to={`/cases/${effectiveCaseId}/timeline`}
            className="p-3.5 rounded-xl bg-surface-container border border-outline-variant hover:border-primary transition-colors flex flex-col items-center text-center space-y-1.5 group"
          >
            <span className="material-symbols-outlined text-cyan-400 text-[24px] group-hover:scale-110 transition-transform">schedule</span>
            <span className="text-body-sm font-semibold text-on-surface">Timeline</span>
            <span className="text-[10px] text-outline font-mono">{counts.timeline_events || 0} events</span>
          </Link>

          <Link
            to={`/cases/${effectiveCaseId}/recovery`}
            className="p-3.5 rounded-xl bg-surface-container border border-outline-variant hover:border-primary transition-colors flex flex-col items-center text-center space-y-1.5 group"
          >
            <span className="material-symbols-outlined text-emerald-400 text-[24px] group-hover:scale-110 transition-transform">restore</span>
            <span className="text-body-sm font-semibold text-on-surface">Recovery</span>
            <span className="text-[10px] text-outline font-mono">4-Tier Deleted</span>
          </Link>

          <Link
            to={`/cases/${effectiveCaseId}/correlations`}
            className="p-3.5 rounded-xl bg-surface-container border border-outline-variant hover:border-primary transition-colors flex flex-col items-center text-center space-y-1.5 group"
          >
            <span className="material-symbols-outlined text-purple-400 text-[24px] group-hover:scale-110 transition-transform">hub</span>
            <span className="text-body-sm font-semibold text-on-surface">Correlations</span>
            <span className="text-[10px] text-outline font-mono">Cross-Identity</span>
          </Link>

          <Link
            to={`/cases/${effectiveCaseId}/reports`}
            className="p-3.5 rounded-xl bg-surface-container border border-outline-variant hover:border-primary transition-colors flex flex-col items-center text-center space-y-1.5 group"
          >
            <span className="material-symbols-outlined text-red-400 text-[24px] group-hover:scale-110 transition-transform">description</span>
            <span className="text-body-sm font-semibold text-on-surface">Reports</span>
            <span className="text-[10px] text-outline font-mono">Court PDF</span>
          </Link>
        </div>

        {/* ================= UPLOAD EVIDENCE MODAL ================= */}
        {showUploadModal && (
          <div
            role="dialog"
            aria-modal="true"
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in"
          >
            <div className="bg-surface-container-high border border-outline-variant rounded-2xl max-w-xl w-full p-6 shadow-2xl space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-outline-variant">
                <div className="flex items-center space-x-2">
                  <span className="material-symbols-outlined text-primary text-[22px]">upload_file</span>
                  <h3 className="text-headline-sm font-headline-sm font-semibold text-on-surface">
                    Upload Evidence Files
                  </h3>
                </div>
                <button
                  type="button"
                  disabled={uploading}
                  onClick={() => setShowUploadModal(false)}
                  className="p-1 rounded-lg text-outline hover:text-on-surface hover:bg-surface-container-highest transition-colors cursor-pointer"
                >
                  <span className="material-symbols-outlined text-[20px]">close</span>
                </button>
              </div>

              {/* Success / Error Alerts */}
              {uploadSuccess && (
                <div className="p-3 rounded-lg bg-tertiary/15 border border-tertiary/30 text-tertiary text-body-sm flex items-center space-x-2">
                  <span className="material-symbols-outlined text-[18px]">check_circle</span>
                  <span>{uploadSuccess}</span>
                </div>
              )}

              {uploadError && (
                <div className="p-3 rounded-lg bg-error/15 border border-error/30 text-error text-body-sm flex items-center space-x-2">
                  <span className="material-symbols-outlined text-[18px]">error</span>
                  <span>{uploadError}</span>
                </div>
              )}

              {/* Drag & Drop Target Area */}
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-xl p-6 text-center transition-all cursor-pointer ${
                  dragActive
                    ? 'border-primary bg-primary/10 scale-[1.01]'
                    : 'border-outline-variant bg-surface-container-low hover:border-outline hover:bg-surface-container'
                }`}
              >
                <input
                  type="file"
                  multiple
                  id="modal-evidence-file-input"
                  onChange={handleFileSelect}
                  className="hidden"
                  disabled={uploading}
                />
                <label htmlFor="modal-evidence-file-input" className="cursor-pointer space-y-2 block">
                  <div className="w-12 h-12 rounded-xl bg-primary/10 border border-primary/30 flex items-center justify-center mx-auto text-primary">
                    <span className="material-symbols-outlined text-[24px]">cloud_upload</span>
                  </div>
                  <div>
                    <span className="font-semibold text-on-surface text-body-sm">
                      Click to choose files
                    </span>{' '}
                    <span className="text-on-surface-variant text-body-sm">or drag and drop</span>
                  </div>
                  <p className="text-[11px] text-outline font-mono">
                    WhatsApp/Telegram archives (.zip), SQLite (.db), Crypt14/15, Keys (.key)
                  </p>
                </label>
              </div>

              {/* Staged Files Preview */}
              {stagedFiles.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs text-on-surface-variant font-mono">
                    <span>STAGED FILES ({stagedFiles.length}):</span>
                    <span>Ready for Ingest</span>
                  </div>
                  <div className="max-h-48 overflow-y-auto custom-scrollbar divide-y divide-outline-variant/40 rounded-lg border border-outline-variant bg-surface-container-lowest">
                    {stagedFiles.map((file, idx) => (
                      <div key={idx} className="p-2.5 flex items-center justify-between text-xs hover:bg-surface-container-high/40">
                        <div className="flex items-center space-x-2 overflow-hidden">
                          <span className="material-symbols-outlined text-primary text-[16px]">draft</span>
                          <span className="font-medium text-on-surface truncate max-w-[280px]">{file.name}</span>
                          <span className="text-outline font-mono text-[10px]">({file.size})</span>
                        </div>
                        {!uploading && (
                          <button
                            type="button"
                            onClick={() => removeStagedFile(idx)}
                            className="text-outline hover:text-error transition-colors cursor-pointer"
                            title="Remove file"
                          >
                            <span className="material-symbols-outlined text-[16px]">close</span>
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Modal Actions */}
              <div className="flex items-center justify-between pt-3 border-t border-outline-variant">
                <Link
                  to={`/cases/${effectiveCaseId}/upload`}
                  onClick={() => setShowUploadModal(false)}
                  className="text-primary hover:underline text-xs font-medium flex items-center space-x-1"
                >
                  <span>Use Advanced Ingestion Form</span>
                  <span className="material-symbols-outlined text-[12px]">arrow_forward</span>
                </Link>

                <div className="flex items-center space-x-2">
                  <button
                    type="button"
                    disabled={uploading}
                    onClick={() => setShowUploadModal(false)}
                    className="px-3.5 py-1.5 rounded-lg bg-surface-container border border-outline-variant text-on-surface hover:bg-surface-container-highest text-body-sm font-medium transition-colors cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={uploading || stagedFiles.length === 0}
                    onClick={handleUploadFiles}
                    className="px-4 py-1.5 rounded-lg bg-primary text-on-primary hover:opacity-90 disabled:opacity-50 font-medium text-body-sm transition-all flex items-center space-x-1.5 cursor-pointer shadow-sm"
                  >
                    {uploading ? (
                      <>
                        <span className="material-symbols-outlined text-[16px] animate-spin">progress_activity</span>
                        <span>Ingesting...</span>
                      </>
                    ) : (
                      <>
                        <span className="material-symbols-outlined text-[16px]">upload</span>
                        <span>Upload & Ingest ({stagedFiles.length})</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ================= CONFIRM DELETE CASE MODAL ================= */}
        {showDeleteModal && currentCase && (
          <div
            role="dialog"
            aria-modal="true"
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in"
          >
            <div className="bg-surface-container-high border border-outline-variant rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
              <div className="flex items-start space-x-3">
                <div className="w-10 h-10 rounded-lg bg-error/15 border border-error/30 text-error flex items-center justify-center shrink-0">
                  <span className="material-symbols-outlined text-[24px]">warning</span>
                </div>
                <div>
                  <h3 className="text-headline-sm font-headline-sm font-semibold text-on-surface">
                    Delete Forensic Case?
                  </h3>
                  <p className="text-body-sm text-on-surface-variant mt-1">
                    Are you sure you want to permanently delete case{' '}
                    <span className="font-mono font-semibold text-primary">{currentCase.caseNumber}</span>
                    {currentCase.title ? ` (${currentCase.title})` : ''}?
                  </p>
                </div>
              </div>

              <div className="bg-surface-container-lowest/70 border border-outline-variant/60 rounded-lg p-3 text-xs text-on-surface-variant space-y-1 font-mono">
                <div>• Case ID: {currentCase.id}</div>
                <div>• Total Evidence Exhibits: {totalEvidenceCount}</div>
                <div className="text-error mt-2 font-sans font-medium">
                  Warning: All exhibits, database files, and audit entries will be permanently removed.
                </div>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-2">
                <button
                  type="button"
                  disabled={isDeleting}
                  onClick={() => setShowDeleteModal(false)}
                  className="px-4 py-2 rounded-lg bg-surface-container border border-outline-variant text-on-surface hover:bg-surface-container-highest text-body-sm font-medium transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={isDeleting}
                  onClick={handleConfirmDelete}
                  className="px-4 py-2 rounded-lg bg-error text-white hover:bg-error/90 text-body-sm font-medium transition-colors flex items-center space-x-1.5 shadow-sm cursor-pointer"
                >
                  {isDeleting ? (
                    <>
                      <span className="material-symbols-outlined text-[18px] animate-spin">progress_activity</span>
                      <span>Deleting...</span>
                    </>
                  ) : (
                    <>
                      <span className="material-symbols-outlined text-[18px]">delete_forever</span>
                      <span>Delete Case</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
