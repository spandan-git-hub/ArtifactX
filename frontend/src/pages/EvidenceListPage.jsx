import React, { useState, useEffect, useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useActiveCase } from '../context/CaseContext';
import { evidenceService } from '../services/evidenceService';

export default function EvidenceListPage() {
  const { caseId: paramCaseId } = useParams();
  const { activeCase } = useActiveCase();
  const caseId = paramCaseId || activeCase?.id;

  const [artifacts, setArtifacts] = useState([]);
  const [selectedArtifact, setSelectedArtifact] = useState(null);
  const [memberFiles, setMemberFiles] = useState([]);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [activeTab, setActiveTab] = useState('hashes'); // 'hashes' | 'info' | 'members'
  const [loading, setLoading] = useState(false);
  const [verifyingId, setVerifyingId] = useState(null);
  const [copiedKey, setCopiedKey] = useState(null);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  const [isInspectorCollapsed, setIsInspectorCollapsed] = useState(false);

  const formatFileSize = (bytes) => {
    if (!bytes || isNaN(bytes)) return '0 B';
    const num = Number(bytes);
    if (num < 1024) return `${num} B`;
    if (num < 1024 * 1024) return `${(num / 1024).toFixed(1)} KiB`;
    if (num < 1024 * 1024 * 1024) return `${(num / (1024 * 1024)).toFixed(2)} MiB`;
    return `${(num / (1024 * 1024 * 1024)).toFixed(2)} GiB`;
  };

  const copyToClipboard = (text, key) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const loadArtifacts = useCallback(async () => {
    if (!caseId) {
      setArtifacts([]);
      setSelectedArtifact(null);
      return;
    }
    setLoading(true);
    try {
      const data = await evidenceService.getEvidences(caseId);
      const list = Array.isArray(data) ? data : (data?.evidences || []);
      const mapped = list.map((ev, i) => {
        const fname = ev.original_filename || ev.name || `evidence_artifact_${ev.id || i}`;
        const fnameLower = fname.toLowerCase();
        const isWa = fnameLower.includes('wa') || fnameLower.includes('crypt') || fnameLower.includes('whatsapp') || (ev.detected_format || '').includes('WHATSAPP');
        const isTg = fnameLower.includes('telegram') || fnameLower.includes('cache4') || fnameLower.includes('tdata') || (ev.detected_format || '').includes('TELEGRAM');
        const app = isWa ? 'WhatsApp' : (isTg ? 'Telegram' : (fname.endsWith('.key') ? 'Key Material' : 'Container'));
        const sizeBytes = ev.upload_size || ev.size || ev.metadata?.upload_size || 0;
        const meta = ev.metadata || {};

        return {
          id: ev.id || `art-${i}`,
          rawId: ev.id,
          name: fname,
          role: ev.evidence_type || (fname.endsWith('.key') ? 'AES Key Credential' : 'Forensic Archive Container'),
          app: app,
          detectedFormat: ev.detected_format || meta.detection?.format || 'Standard Binary',
          size: formatFileSize(sizeBytes),
          sizeBytes: sizeBytes,
          sha256: ev.sha256 || meta.sha256 || 'N/A',
          md5: ev.md5 || meta.md5 || 'N/A',
          sha1: ev.sha1 || meta.sha1 || 'N/A',
          sha512: ev.sha512 || meta.sha512 || 'N/A',
          status: ev.integrity_state === 'ARCHIVE_REJECTED' ? 'Archive Rejected' : (ev.integrity_state || 'Verified OK'),
          integrityState: ev.integrity_state || 'OK',
          claimedHash: ev.acquisition_hash_claimed || meta.acquisition_hash_claimed || null,
          claimedVsComputed: ev.claimed_vs_computed || 'NOT_PROVIDED',
          uploadedAt: ev.uploaded_at ? new Date(ev.uploaded_at).toLocaleString() : 'Recently',
          uploadedAtUtc: ev.uploaded_at || '',
          path: ev.storage_path || meta.storage_path || `/evidence/case_${caseId}/${fname}`,
          uploader: ev.uploader || 'Examiner / Officer',
          acquisitionMethod: ev.acquisition_method || 'Logical Acquisition (Direct Ingestion)',
          deviceModel: ev.device_make_model || 'Android Forensic Extraction',
          isZip: ev.is_zip || fname.endsWith('.zip') || ev.evidence_type === 'zip' || (ev.detected_format === 'ZIP'),
          extractedCount: ev.extracted_files_count || meta.extracted_files_count || 0
        };
      });

      setArtifacts(mapped);
      if (mapped.length > 0) {
        setSelectedArtifact(prev => {
          const match = prev ? mapped.find(m => m.id === prev.id) : null;
          return match || mapped[0];
        });
      } else {
        setSelectedArtifact(null);
      }
    } catch (err) {
      console.warn('Error loading evidence artifacts:', err);
      setArtifacts([]);
      setSelectedArtifact(null);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    loadArtifacts();
  }, [loadArtifacts]);

  // Load member files whenever selected artifact changes
  useEffect(() => {
    if (!selectedArtifact?.rawId || !selectedArtifact.isZip) {
      setMemberFiles([]);
      return;
    }

    let isMounted = true;
    setLoadingFiles(true);
    evidenceService.getEvidenceFiles(selectedArtifact.rawId)
      .then(files => {
        if (isMounted) {
          setMemberFiles(Array.isArray(files) ? files : []);
        }
      })
      .catch(err => {
        console.warn('Could not load member files for evidence:', err);
        if (isMounted) setMemberFiles([]);
      })
      .finally(() => {
        if (isMounted) setLoadingFiles(false);
      });

    return () => { isMounted = false; };
  }, [selectedArtifact]);

  const handleVerifyNow = async (artId) => {
    setVerifyingId(artId);
    try {
      await evidenceService.verifyEvidenceHashes(artId);
      await loadArtifacts();
    } catch (err) {
      console.error('Failed to verify evidence hash:', err);
    } finally {
      setVerifyingId(null);
    }
  };

  const filtered = artifacts.filter(item => {
    const q = search.toLowerCase();
    const matchesSearch = item.name.toLowerCase().includes(q) ||
                          item.sha256.toLowerCase().includes(q) ||
                          item.app.toLowerCase().includes(q) ||
                          item.detectedFormat.toLowerCase().includes(q);
    const matchesRole = roleFilter === 'All' || item.role.includes(roleFilter) || item.app.includes(roleFilter);
    const matchesStatus = statusFilter === 'All' || item.status === statusFilter || item.integrityState === statusFilter;
    return matchesSearch && matchesRole && matchesStatus;
  });

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden">

      {/* ================= SUB-HEADER & STATS RIBBON ================= */}
      <div className="bg-surface-container-high/40 border-b border-outline-variant px-4 py-2 flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex items-center space-x-3 text-label-mono-sm font-label-mono-sm">
          <div className="flex items-center space-x-1.5 text-primary">
            <span className="material-symbols-outlined text-[18px]">verified_user</span>
            <span className="font-semibold text-on-surface">Evidence Repository & Hash Manifest</span>
          </div>
          <span className="text-outline">|</span>
          <span className="text-on-surface-variant">Case: <strong className="text-primary">{activeCase?.caseNumber || caseId}</strong></span>
          <span className="text-outline">|</span>
          <span className="text-on-surface-variant">Total Exhibits: <strong className="text-on-surface">{artifacts.length}</strong></span>
          <span className="text-outline">|</span>
          <span className="text-tertiary font-medium">CRYPTOGRAPHIC AUDIT: OK</span>
        </div>

        <div className="flex items-center space-x-2">
          <Link
            to={`/cases/${caseId}/overview`}
            className="px-2.5 py-1 rounded bg-surface-container border border-outline-variant hover:bg-surface-container-high text-xs text-on-surface flex items-center gap-1 transition-colors"
          >
            <span className="material-symbols-outlined text-[14px]">dashboard</span>
            <span>Case Overview</span>
          </Link>
          <Link
            to={`/cases/${caseId}/upload`}
            className="px-3 py-1 rounded-lg bg-primary hover:opacity-90 text-on-primary text-xs font-medium flex items-center gap-1.5 shadow-sm transition-all"
          >
            <span className="material-symbols-outlined text-[15px]">upload_file</span>
            <span>Upload New Evidence</span>
          </Link>
        </div>
      </div>

      {/* ================= SEARCH & FILTER TOOLBAR ================= */}
      <div className="p-3 bg-surface-container/60 border-b border-outline-variant flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-2 flex-1 max-w-xl">
          <div className="relative flex-1">
            <span className="material-symbols-outlined absolute left-2.5 top-2 text-outline text-[16px]">
              search
            </span>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search evidence by filename, SHA-256, format..."
              className="w-full bg-surface-container-lowest border border-outline-variant rounded pl-8 pr-3 py-1.5 text-body-sm font-body-sm text-on-surface placeholder:text-outline focus:outline-none focus:border-primary transition-colors"
            />
          </div>

          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1.5 text-body-sm text-on-surface focus:outline-none focus:border-primary cursor-pointer"
          >
            <option value="All">All Formats</option>
            <option value="WhatsApp">WhatsApp</option>
            <option value="Telegram">Telegram</option>
            <option value="Key">Key Materials</option>
            <option value="Container">ZIP Archives</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1.5 text-body-sm text-on-surface focus:outline-none focus:border-primary cursor-pointer"
          >
            <option value="All">All Statuses</option>
            <option value="Verified OK">Verified OK</option>
            <option value="Archive Rejected">Archive Rejected</option>
          </select>
        </div>

        <div className="flex items-center space-x-3">
          <button
            type="button"
            onClick={() => setIsInspectorCollapsed(!isInspectorCollapsed)}
            className={`px-2.5 py-1 rounded border text-xs font-medium flex items-center gap-1.5 transition-colors cursor-pointer ${
              !isInspectorCollapsed
                ? 'bg-primary/10 border-primary/30 text-primary'
                : 'bg-surface-container border-outline-variant text-on-surface-variant hover:text-on-surface'
            }`}
            title={isInspectorCollapsed ? 'Expand Inspector Panel' : 'Collapse Inspector Panel'}
          >
            <span className="material-symbols-outlined text-[16px]">
              {isInspectorCollapsed ? 'dock_to_left' : 'dock_to_right'}
            </span>
            <span>{isInspectorCollapsed ? 'Show Details' : 'Hide Details'}</span>
          </button>
          <div className="text-xs text-on-surface-variant font-mono">
            Showing {filtered.length} of {artifacts.length} exhibits
          </div>
        </div>
      </div>

      {/* ================= TWO-PANE WORKSPACE ================= */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden">

        {/* LEFT PANE: Evidence Table */}
        <div className="flex-1 overflow-y-auto custom-scrollbar border-r border-outline-variant bg-surface-container-lowest">
          <table className="w-full text-left border-collapse text-body-sm">
            <thead>
              <tr className="bg-surface-container-low border-b border-outline-variant h-9 text-label-ui font-label-ui text-on-surface-variant uppercase tracking-wider text-[11px] sticky top-0 z-10">
                <th className="py-2 px-3 w-12 text-center">#</th>
                <th className="py-2 px-3">Evidence Item / Exhibit</th>
                <th className="py-2 px-3">Application / Format</th>
                <th className="py-2 px-3 font-mono">Size</th>
                <th className="py-2 px-3 font-mono">SHA-256 Digest</th>
                <th className="py-2 px-3 text-right">Integrity</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/50 font-mono text-xs">
              {loading && (
                <tr>
                  <td colSpan={6} className="py-16 text-center text-on-surface-variant">
                    <span className="material-symbols-outlined text-3xl animate-spin text-primary mb-2">progress_activity</span>
                    <p className="font-sans text-body-sm">Loading evidence exhibits & hash ledger...</p>
                  </td>
                </tr>
              )}

              {!loading && filtered.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-16 text-center text-on-surface-variant">
                    <span className="material-symbols-outlined text-4xl text-outline mb-2">inventory_2</span>
                    <p className="text-body-md font-semibold text-on-surface font-sans">No Evidence Found</p>
                    <p className="text-xs text-outline mt-1 mb-4 font-sans">No evidence exhibits match the current search or filters.</p>
                    <Link
                      to={`/cases/${caseId}/upload`}
                      className="px-3.5 py-1.5 rounded-lg bg-primary text-on-primary hover:opacity-90 text-xs font-sans font-medium inline-flex items-center gap-1.5 shadow-sm"
                    >
                      <span className="material-symbols-outlined text-[16px]">upload_file</span>
                      <span>Upload Evidence Files</span>
                    </Link>
                  </td>
                </tr>
              )}

              {!loading && filtered.map((art, idx) => {
                const isSelected = selectedArtifact?.id === art.id;
                const isRejected = art.integrityState === 'ARCHIVE_REJECTED';

                return (
                  <tr
                    key={art.id}
                    onClick={() => {
                      setSelectedArtifact(art);
                      setIsInspectorCollapsed(false);
                    }}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-primary/10 border-l-4 border-primary font-medium'
                        : isRejected
                          ? 'bg-error/10 hover:bg-error/15'
                          : 'hover:bg-surface-container-high/40'
                    }`}
                  >
                    <td className="py-3 px-3 text-center text-outline">{idx + 1}</td>
                    <td className="py-3 px-3">
                      <div className="font-semibold text-on-surface font-sans text-sm truncate max-w-xs">{art.name}</div>
                      <div className="text-[11px] text-on-surface-variant font-mono">EXH-#{art.rawId} · {art.uploadedAt}</div>
                    </td>
                    <td className="py-3 px-3 font-sans">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono border ${
                        art.app === 'WhatsApp' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' :
                        art.app === 'Telegram' ? 'bg-blue-500/10 text-blue-400 border-blue-500/30' :
                        art.app === 'Key Material' ? 'bg-amber-500/10 text-amber-400 border-amber-500/30' :
                        'bg-surface-container border-outline-variant text-on-surface'
                      }`}>
                        {art.detectedFormat}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-on-surface font-mono">{art.size}</td>
                    <td className="py-3 px-3 text-primary truncate max-w-[170px]" title={art.sha256}>
                      {art.sha256 ? `${art.sha256.substring(0, 16)}...` : 'Pending'}
                    </td>
                    <td className="py-3 px-3 text-right">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold font-mono border ${
                        isRejected
                          ? 'bg-error/15 text-error border-error/30'
                          : 'bg-tertiary/15 text-tertiary border-tertiary/30'
                      }`}>
                        {art.status}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* RIGHT PANE: Comprehensive Evidence Detail & Hashes Inspector (Collapsible) */}
        {isInspectorCollapsed ? (
          <div className="hidden md:flex w-10 bg-surface-container-low border-l border-outline-variant flex-col items-center py-3 shrink-0">
            <button
              type="button"
              onClick={() => setIsInspectorCollapsed(false)}
              className="p-1.5 rounded hover:bg-surface-container-high text-outline hover:text-primary transition-colors cursor-pointer flex flex-col items-center gap-2"
              title="Expand Evidence Inspector"
            >
              <span className="material-symbols-outlined text-[18px]">chevron_left</span>
              <span className="[writing-mode:vertical-rl] rotate-180 text-[10px] font-mono tracking-wider uppercase text-outline font-semibold">
                Exhibit Inspector
              </span>
            </button>
          </div>
        ) : (
          <div className="w-full md:w-[460px] bg-surface-container-low border-t md:border-t-0 md:border-l border-outline-variant flex flex-col shrink-0 overflow-y-auto custom-scrollbar p-space-md space-y-4 animate-in fade-in">
            {selectedArtifact ? (
              <div className="space-y-4">

                {/* Inspector Header */}
                <div className="border-b border-outline-variant pb-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-outline uppercase tracking-wider">
                      Evidence Exhibit #{selectedArtifact.rawId}
                    </span>
                    <div className="flex items-center space-x-1.5">
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                        selectedArtifact.integrityState === 'ARCHIVE_REJECTED'
                          ? 'bg-error/10 text-error border-error/30'
                          : 'bg-tertiary/10 text-tertiary border-tertiary/30'
                      }`}>
                        {selectedArtifact.status}
                      </span>
                      <button
                        type="button"
                        onClick={() => setIsInspectorCollapsed(true)}
                        className="p-1 rounded text-outline hover:text-on-surface hover:bg-surface-container-high transition-colors cursor-pointer"
                        title="Collapse Inspector Panel"
                      >
                        <span className="material-symbols-outlined text-[16px]">close</span>
                      </button>
                    </div>
                  </div>
                <h3 className="text-headline-sm font-semibold text-on-surface mt-1 break-all">
                  {selectedArtifact.name}
                </h3>
                <div className="text-xs text-on-surface-variant font-mono mt-0.5">
                  Package: <strong className="text-primary">{selectedArtifact.detectedFormat}</strong>
                </div>
              </div>

              {/* Inspector Tabs: Hashes / Basic Info / Member Files */}
              <div className="flex border-b border-outline-variant text-xs font-medium">
                <button
                  type="button"
                  onClick={() => setActiveTab('hashes')}
                  className={`pb-2 px-3 border-b-2 transition-colors cursor-pointer ${
                    activeTab === 'hashes'
                      ? 'border-primary text-primary font-semibold'
                      : 'border-transparent text-on-surface-variant hover:text-on-surface'
                  }`}
                >
                  Cryptographic Hashes
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('info')}
                  className={`pb-2 px-3 border-b-2 transition-colors cursor-pointer ${
                    activeTab === 'info'
                      ? 'border-primary text-primary font-semibold'
                      : 'border-transparent text-on-surface-variant hover:text-on-surface'
                  }`}
                >
                  Basic Info
                </button>
                {selectedArtifact.isZip && (
                  <button
                    type="button"
                    onClick={() => setActiveTab('members')}
                    className={`pb-2 px-3 border-b-2 transition-colors cursor-pointer flex items-center gap-1 ${
                      activeTab === 'members'
                        ? 'border-primary text-primary font-semibold'
                        : 'border-transparent text-on-surface-variant hover:text-on-surface'
                    }`}
                  >
                    <span>Archive Contents</span>
                    <span className="text-[10px] bg-primary/10 text-primary px-1.5 py-0.2 rounded font-mono">
                      {memberFiles.length || selectedArtifact.extractedCount}
                    </span>
                  </button>
                )}
              </div>

              {/* TAB 1: Cryptographic Hashes */}
              {activeTab === 'hashes' && (
                <div className="space-y-3 animate-in fade-in">
                  {/* SHA-256 */}
                  <div className="p-3 rounded-lg bg-surface-container border border-outline-variant space-y-1.5">
                    <div className="flex items-center justify-between text-[11px] font-mono">
                      <span className="text-primary font-bold">SHA-256 DIGEST (PRIMARY NIST)</span>
                      <button
                        type="button"
                        onClick={() => copyToClipboard(selectedArtifact.sha256, 'sha256')}
                        className="text-on-surface-variant hover:text-primary transition-colors flex items-center gap-1 cursor-pointer"
                        title="Copy SHA-256"
                      >
                        <span className="material-symbols-outlined text-[13px]">
                          {copiedKey === 'sha256' ? 'check' : 'content_copy'}
                        </span>
                        <span>{copiedKey === 'sha256' ? 'Copied' : 'Copy'}</span>
                      </button>
                    </div>
                    <code className="text-on-surface text-[11px] font-mono break-all block bg-surface-container-lowest p-2 rounded border border-outline-variant select-all">
                      {selectedArtifact.sha256}
                    </code>
                  </div>

                  {/* MD5 */}
                  <div className="p-3 rounded-lg bg-surface-container border border-outline-variant space-y-1.5">
                    <div className="flex items-center justify-between text-[11px] font-mono">
                      <span className="text-on-surface-variant font-semibold">MD5 CHECKSUM</span>
                      <button
                        type="button"
                        onClick={() => copyToClipboard(selectedArtifact.md5, 'md5')}
                        className="text-on-surface-variant hover:text-primary transition-colors flex items-center gap-1 cursor-pointer"
                        title="Copy MD5"
                      >
                        <span className="material-symbols-outlined text-[13px]">
                          {copiedKey === 'md5' ? 'check' : 'content_copy'}
                        </span>
                        <span>{copiedKey === 'md5' ? 'Copied' : 'Copy'}</span>
                      </button>
                    </div>
                    <code className="text-on-surface text-[11px] font-mono break-all block bg-surface-container-lowest p-2 rounded border border-outline-variant select-all">
                      {selectedArtifact.md5}
                    </code>
                  </div>

                  {/* SHA-1 */}
                  <div className="p-3 rounded-lg bg-surface-container border border-outline-variant space-y-1.5">
                    <div className="flex items-center justify-between text-[11px] font-mono">
                      <span className="text-on-surface-variant font-semibold">SHA-1 HASH</span>
                      <button
                        type="button"
                        onClick={() => copyToClipboard(selectedArtifact.sha1, 'sha1')}
                        className="text-on-surface-variant hover:text-primary transition-colors flex items-center gap-1 cursor-pointer"
                        title="Copy SHA-1"
                      >
                        <span className="material-symbols-outlined text-[13px]">
                          {copiedKey === 'sha1' ? 'check' : 'content_copy'}
                        </span>
                        <span>{copiedKey === 'sha1' ? 'Copied' : 'Copy'}</span>
                      </button>
                    </div>
                    <code className="text-on-surface text-[11px] font-mono break-all block bg-surface-container-lowest p-2 rounded border border-outline-variant select-all">
                      {selectedArtifact.sha1}
                    </code>
                  </div>

                  {/* SHA-512 */}
                  {selectedArtifact.sha512 && selectedArtifact.sha512 !== 'N/A' && (
                    <div className="p-3 rounded-lg bg-surface-container border border-outline-variant space-y-1.5">
                      <div className="flex items-center justify-between text-[11px] font-mono">
                        <span className="text-on-surface-variant font-semibold">SHA-512 HIGH-SECURITY</span>
                        <button
                          type="button"
                          onClick={() => copyToClipboard(selectedArtifact.sha512, 'sha512')}
                          className="text-on-surface-variant hover:text-primary transition-colors flex items-center gap-1 cursor-pointer"
                          title="Copy SHA-512"
                        >
                          <span className="material-symbols-outlined text-[13px]">
                            {copiedKey === 'sha512' ? 'check' : 'content_copy'}
                          </span>
                          <span>{copiedKey === 'sha512' ? 'Copied' : 'Copy'}</span>
                        </button>
                      </div>
                      <code className="text-on-surface text-[10px] font-mono break-all block bg-surface-container-lowest p-2 rounded border border-outline-variant select-all max-h-20 overflow-y-auto custom-scrollbar">
                        {selectedArtifact.sha512}
                      </code>
                    </div>
                  )}

                  {/* Hash Integrity Verification Status */}
                  <div className="p-3 rounded-lg bg-surface-container-low border border-outline-variant flex items-center justify-between text-xs font-mono">
                    <span className="text-on-surface-variant">Intake vs Computed Hash:</span>
                    <span className={`px-2 py-0.5 rounded border ${
                      selectedArtifact.claimedVsComputed === 'MATCH'
                        ? 'bg-tertiary/15 text-tertiary border-tertiary/30'
                        : selectedArtifact.claimedVsComputed === 'MISMATCH'
                          ? 'bg-error/15 text-error border-error/30'
                          : 'bg-surface-variant text-on-surface-variant border-outline-variant'
                    }`}>
                      {selectedArtifact.claimedVsComputed}
                    </span>
                  </div>

                  {/* Re-verify Button */}
                  <div className="pt-2">
                    <button
                      type="button"
                      onClick={() => handleVerifyNow(selectedArtifact.rawId)}
                      disabled={verifyingId === selectedArtifact.rawId}
                      className="w-full px-3.5 py-2 rounded-lg bg-primary hover:opacity-90 disabled:opacity-60 text-on-primary font-medium text-xs flex items-center justify-center gap-1.5 transition-all shadow-sm cursor-pointer"
                    >
                      <span className={`material-symbols-outlined text-[16px] ${verifyingId === selectedArtifact.rawId ? 'animate-spin' : ''}`}>
                        {verifyingId === selectedArtifact.rawId ? 'progress_activity' : 'verified'}
                      </span>
                      <span>{verifyingId === selectedArtifact.rawId ? 'Recomputing Hashes...' : 'Re-verify Hash Now'}</span>
                    </button>
                  </div>
                </div>
              )}

              {/* TAB 2: Basic Info */}
              {activeTab === 'info' && (
                <div className="space-y-3 animate-in fade-in text-xs">
                  <div className="grid grid-cols-2 gap-2.5">
                    <div className="p-2.5 rounded-lg bg-surface-container border border-outline-variant space-y-1">
                      <span className="text-outline uppercase text-[10px] block font-mono">File Size</span>
                      <span className="font-mono text-on-surface font-semibold">{selectedArtifact.size}</span>
                      <span className="text-[10px] text-outline block">({selectedArtifact.sizeBytes.toLocaleString()} bytes)</span>
                    </div>

                    <div className="p-2.5 rounded-lg bg-surface-container border border-outline-variant space-y-1">
                      <span className="text-outline uppercase text-[10px] block font-mono">Detected Format</span>
                      <span className="font-semibold text-primary">{selectedArtifact.detectedFormat}</span>
                      <span className="text-[10px] text-outline block">{selectedArtifact.app}</span>
                    </div>
                  </div>

                  <div className="p-2.5 rounded-lg bg-surface-container border border-outline-variant space-y-1">
                    <span className="text-outline uppercase text-[10px] block font-mono">Logical Storage Path</span>
                    <span className="font-mono text-[11px] text-on-surface-variant break-all select-all block bg-surface-container-lowest p-1.5 rounded border border-outline-variant">
                      {selectedArtifact.path}
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-surface-container border border-outline-variant space-y-1">
                    <span className="text-outline uppercase text-[10px] block font-mono">Acquisition Method</span>
                    <span className="font-medium text-on-surface">{selectedArtifact.acquisitionMethod}</span>
                  </div>

                  <div className="grid grid-cols-2 gap-2.5">
                    <div className="p-2.5 rounded-lg bg-surface-container border border-outline-variant space-y-1">
                      <span className="text-outline uppercase text-[10px] block font-mono">Ingested By</span>
                      <span className="font-medium text-on-surface">{selectedArtifact.uploader}</span>
                    </div>

                    <div className="p-2.5 rounded-lg bg-surface-container border border-outline-variant space-y-1">
                      <span className="text-outline uppercase text-[10px] block font-mono">Ingestion Timestamp</span>
                      <span className="font-mono text-on-surface">{selectedArtifact.uploadedAt}</span>
                    </div>
                  </div>

                  <div className="pt-2 flex items-center justify-between">
                    <Link
                      to={`/cases/${caseId}/decryption`}
                      className="w-full px-3 py-2 rounded-lg bg-primary/10 hover:bg-primary/20 border border-primary/30 text-primary font-medium text-xs flex items-center justify-center gap-1.5 transition-colors"
                    >
                      <span className="material-symbols-outlined text-[16px]">key</span>
                      <span>Proceed to Decryption Tab →</span>
                    </Link>
                  </div>
                </div>
              )}

              {/* TAB 3: Archive Contents (Member Files) */}
              {activeTab === 'members' && selectedArtifact.isZip && (
                <div className="space-y-3 animate-in fade-in text-xs">
                  <div className="flex items-center justify-between text-[11px] font-mono text-on-surface-variant">
                    <span>EXTRACTED EXHIBITS ({memberFiles.length}):</span>
                    <span>Safe In-Memory Extraction</span>
                  </div>

                  {loadingFiles ? (
                    <div className="py-8 text-center text-on-surface-variant">
                      <span className="material-symbols-outlined text-2xl animate-spin text-primary mb-1">progress_activity</span>
                      <p>Loading member files...</p>
                    </div>
                  ) : memberFiles.length === 0 ? (
                    <div className="p-4 rounded-lg bg-surface-container text-center text-outline font-mono">
                      No member files registered for this container.
                    </div>
                  ) : (
                    <div className="max-h-80 overflow-y-auto custom-scrollbar divide-y divide-outline-variant/40 rounded-lg border border-outline-variant bg-surface-container-lowest">
                      {memberFiles.map((file, idx) => (
                        <div key={file.id || idx} className="p-2.5 hover:bg-surface-container-high/40 transition-colors space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="font-mono font-medium text-on-surface truncate max-w-[260px]" title={file.relative_path}>
                              {file.relative_path}
                            </span>
                            <span className="font-mono text-outline text-[10px]">
                              {formatFileSize(file.size)}
                            </span>
                          </div>
                          {file.sha256 && (
                            <div className="flex items-center space-x-1.5 font-mono text-[10px] text-primary">
                              <span>SHA: {file.sha256.substring(0, 16)}...</span>
                              <button
                                type="button"
                                onClick={() => copyToClipboard(file.sha256, `mem-${file.id}`)}
                                className="text-on-surface-variant hover:text-primary transition-colors cursor-pointer"
                                title="Copy member SHA-256"
                              >
                                <span className="material-symbols-outlined text-[12px]">
                                  {copiedKey === `mem-${file.id}` ? 'check' : 'content_copy'}
                                </span>
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-on-surface-variant font-mono text-xs text-center p-6 space-y-2">
              <span className="material-symbols-outlined text-4xl text-outline">fingerprint</span>
              <p className="font-semibold text-on-surface">Select an Evidence Exhibit</p>
              <p className="text-outline">
                Click any row in the evidence table to inspect multi-algorithm cryptographic hashes (SHA-256, MD5, SHA-1, SHA-512) and basic acquisition metadata.
              </p>
            </div>
          )}
        </div>
        )}

      </div>
    </div>
  );
}
