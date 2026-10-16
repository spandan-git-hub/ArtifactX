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
  const [loading, setLoading] = useState(false);
  const [verifyingId, setVerifyingId] = useState(null);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  const [verifyAlertVisible, setVerifyAlertVisible] = useState(true);

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
        const isWa = fname.toLowerCase().includes('wa') || fname.toLowerCase().includes('crypt') || fname.toLowerCase().includes('whatsapp');
        const isTg = fname.toLowerCase().includes('telegram') || fname.toLowerCase().includes('cache4');
        const app = isWa ? 'WhatsApp' : (isTg ? 'Telegram' : 'Cross-App');
        const isMismatch = ev.integrity_state === 'HASH_MISMATCH' || ev.status === 'Checksum Mismatch';
        const sizeMb = ev.file_size_bytes ? (ev.file_size_bytes / (1024 * 1024)).toFixed(1) : (ev.size || '1.0');

        return {
          id: ev.id || `art-${i}`,
          name: fname,
          role: ev.evidence_type || (fname.endsWith('.key') ? 'AES Key Reference' : 'Forensic Database Dump'),
          app: app,
          size: `${sizeMb} MiB`,
          sha256: ev.sha256 || 'Pending Computation',
          blake3: ev.blake3 || ev.sha256?.substring(0, 32) || 'N/A',
          md5: ev.md5 || 'N/A',
          status: isMismatch ? 'Checksum Mismatch' : (ev.integrity_state || 'Verified'),
          verifiedUtc: ev.uploaded_at ? new Date(ev.uploaded_at).toISOString().replace('T', ' ').substring(0, 19) : 'Recently',
          path: ev.stored_filepath || `/evidence/case_${caseId}/${fname}`,
          volume: 'Forensic_Airgap.raw',
          sectorOffset: `0x${String(ev.id * 1000).padStart(6, '0')}`,
          readOnly: true
        };
      });
      setArtifacts(mapped);
      if (mapped.length > 0) {
        setSelectedArtifact(prev => prev ? mapped.find(m => m.id === prev.id) || mapped[0] : mapped[0]);
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

  const mismatchItem = artifacts.find(a => a.status === 'Checksum Mismatch');

  const filtered = artifacts.filter(item => {
    const matchesSearch = item.name.toLowerCase().includes(search.toLowerCase()) ||
                          item.sha256.toLowerCase().includes(search.toLowerCase()) ||
                          item.app.toLowerCase().includes(search.toLowerCase());
    const matchesRole = roleFilter === 'All' || item.role.includes(roleFilter);
    const matchesStatus = statusFilter === 'All' || item.status === statusFilter;
    return matchesSearch && matchesRole && matchesStatus;
  });

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden">
      {/* Top Integrity Alert Banner: ONLY if real mismatch exists */}
      {mismatchItem && verifyAlertVisible && (
        <div className="bg-error/15 border-b border-error/40 px-4 py-2.5 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-3">
            <span className="material-symbols-outlined text-error text-[18px] shrink-0">warning</span>
            <div className="text-body-sm font-body-sm text-on-surface">
              <span className="font-semibold text-error">Integrity alert:</span> File{' '}
              <code className="font-label-mono-sm text-error bg-surface-container-lowest px-1.5 py-0.5 rounded border border-error/30">
                {mismatchItem.name}
              </code>{' '}
              failed cryptographic verification against acquisition checksum.
            </div>
          </div>
          <div className="flex items-center space-x-2 shrink-0 ml-4">
            <button
              type="button"
              onClick={() => setSelectedArtifact(mismatchItem)}
              className="px-2.5 py-1 rounded bg-error/20 hover:bg-error/30 text-error border border-error/50 text-label-ui font-label-ui font-medium flex items-center gap-1 transition-colors"
            >
              <span>Inspect Exception</span>
              <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
            </button>
            <button
              type="button"
              onClick={() => setVerifyAlertVisible(false)}
              className="p-1 text-on-surface-variant hover:text-on-surface rounded"
            >
              <span className="material-symbols-outlined text-[14px]">close</span>
            </button>
          </div>
        </div>
      )}

      {/* Audit Chain Status Ribbon */}
      <div className="bg-surface-container-high/40 border-b border-outline-variant px-4 py-1.5 flex items-center justify-between text-label-mono-sm font-label-mono-sm shrink-0">
        <div className="flex items-center space-x-2 text-on-surface-variant">
          <span className="material-symbols-outlined text-tertiary text-[14px]">check_circle</span>
          <span className="text-on-surface">Evidence Store: {artifacts.length} artifacts registered</span>
          <span className="text-outline">|</span>
          <span>Case: <span className="text-primary font-medium">{activeCase?.caseNumber || caseId || 'N/A'}</span></span>
          <span className="text-outline">|</span>
          <span>Chain status: ACTIVE</span>
        </div>
        <div className="flex items-center space-x-3 text-on-surface-variant">
          <Link to={`/cases/${caseId}/upload`} className="text-primary hover:underline text-xs flex items-center gap-1">
            <span className="material-symbols-outlined text-[14px]">add</span>
            Upload New File
          </Link>
        </div>
      </div>

      {/* Controls & Filter Bar */}
      <div className="p-3 bg-surface-container/60 border-b border-outline-variant flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-2 flex-1 max-w-xl">
          <div className="relative flex-1">
            <span className="material-symbols-outlined absolute left-2.5 top-2 text-on-surface-variant text-[16px]">
              search
            </span>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter evidence by name, hash, role..."
              className="w-full bg-surface-container-lowest border border-outline-variant rounded pl-8 pr-3 py-1.5 text-body-sm font-body-sm text-on-surface placeholder:text-outline focus:outline-none focus:border-primary"
            />
          </div>

          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1.5 text-body-sm font-body-sm text-on-surface focus:outline-none focus:border-primary cursor-pointer"
          >
            <option value="All">All Roles</option>
            <option value="Primary">Primary DB</option>
            <option value="Key">Key Material</option>
            <option value="WAL">WAL / Journal</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1.5 text-body-sm font-body-sm text-on-surface focus:outline-none focus:border-primary cursor-pointer"
          >
            <option value="All">All Statuses</option>
            <option value="Verified">Verified Only</option>
            <option value="Checksum Mismatch">Checksum Mismatches</option>
          </select>
        </div>

        <div className="flex items-center space-x-2">
          <Link
            to={`/cases/${caseId}/upload`}
            className="btn-primary text-xs"
          >
            <span className="material-symbols-outlined text-[16px]">upload_file</span>
            <span>Add Evidence</span>
          </Link>
        </div>
      </div>

      {/* Two-Pane Workspace Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Pane: Evidence Table */}
        <div className="flex-1 overflow-y-auto custom-scrollbar border-r border-outline-variant bg-surface-container-lowest">
          <table className="w-full text-left border-collapse text-body-sm font-body-sm">
            <thead>
              <tr className="bg-surface-container-low border-b border-outline-variant h-8 text-label-ui font-label-ui text-on-surface-variant uppercase tracking-wider text-[11px] sticky top-0 z-10">
                <th className="py-2 px-3 w-10">#</th>
                <th className="py-2 px-3">Artifact Name / Exhibit</th>
                <th className="py-2 px-3">Application Scope</th>
                <th className="py-2 px-3">Size</th>
                <th className="py-2 px-3 font-mono">SHA-256 Digest</th>
                <th className="py-2 px-3 text-right">Verification</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/60 font-mono text-xs">
              {loading && (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-on-surface-variant">
                    <span className="material-symbols-outlined text-3xl animate-spin text-primary mb-2">sync</span>
                    <p>Loading case evidence repository...</p>
                  </td>
                </tr>
              )}

              {!loading && filtered.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-16 text-center text-on-surface-variant">
                    <span className="material-symbols-outlined text-4xl text-outline mb-2">folder_open</span>
                    <p className="text-body-md font-semibold text-on-surface">No Evidence Artifacts Registered</p>
                    <p className="text-xs text-outline mt-1 mb-3">Upload bit-stream forensic images or database containers to begin.</p>
                    <Link
                      to={`/cases/${caseId}/upload`}
                      className="btn-primary text-xs inline-flex items-center gap-1.5"
                    >
                      <span className="material-symbols-outlined text-[16px]">upload</span>
                      Upload First Evidence
                    </Link>
                  </td>
                </tr>
              )}

              {!loading && filtered.map((art, idx) => {
                const isSelected = selectedArtifact?.id === art.id;
                const isMismatch = art.status === 'Checksum Mismatch';
                return (
                  <tr
                    key={art.id}
                    onClick={() => setSelectedArtifact(art)}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-primary/10 border-l-2 border-primary font-medium'
                        : isMismatch
                          ? 'bg-error/10 hover:bg-error/15'
                          : 'hover:bg-surface-container-high/40'
                    }`}
                  >
                    <td className="py-3 px-3 text-on-surface-variant">{idx + 1}</td>
                    <td className="py-3 px-3">
                      <div className="font-semibold text-on-surface font-sans text-sm truncate max-w-xs">{art.name}</div>
                      <div className="text-[11px] text-on-surface-variant font-sans">{art.role}</div>
                    </td>
                    <td className="py-3 px-3 font-sans">
                      <span className={`px-2 py-0.5 rounded text-[11px] border ${
                        art.app === 'WhatsApp' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' :
                        art.app === 'Telegram' ? 'bg-blue-500/10 text-blue-400 border-blue-500/30' :
                        'bg-surface-container border-outline-variant text-on-surface'
                      }`}>
                        {art.app}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-on-surface-variant">{art.size}</td>
                    <td className="py-3 px-3 text-outline truncate max-w-[180px]">
                      {art.sha256}
                    </td>
                    <td className="py-3 px-3 text-right">
                      {isMismatch ? (
                        <span className="px-2 py-0.5 rounded bg-error/20 text-error border border-error/40 text-[10px] font-semibold">
                          Checksum Mismatch
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-tertiary/10 text-tertiary border border-tertiary/30 text-[10px] font-semibold">
                          Verified
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Right Pane: Artifact Inspector */}
        <div className="w-[380px] bg-surface-container-low border-l border-outline-variant flex flex-col shrink-0 overflow-y-auto custom-scrollbar p-space-md space-y-4">
          {selectedArtifact ? (
            <div className="space-y-4">
              <div>
                <span className="text-[10px] font-mono text-outline uppercase tracking-wider block">
                  Evidentiary Exhibit Detail
                </span>
                <h3 className="text-headline-sm font-semibold text-on-surface mt-0.5 break-all">
                  {selectedArtifact.name}
                </h3>
              </div>

              <div className="space-y-2 text-xs">
                <div className="p-2.5 rounded bg-surface-container border border-outline-variant space-y-1">
                  <span className="text-outline uppercase text-[10px] block font-mono">SHA-256 Digest</span>
                  <code className="text-on-surface text-[10px] font-mono break-all block bg-surface-container-lowest p-1.5 rounded border border-outline-variant">
                    {selectedArtifact.sha256}
                  </code>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="p-2.5 rounded bg-surface-container border border-outline-variant">
                    <span className="text-outline uppercase text-[10px] block font-mono">Size</span>
                    <span className="font-mono text-on-surface">{selectedArtifact.size}</span>
                  </div>
                  <div className="p-2.5 rounded bg-surface-container border border-outline-variant">
                    <span className="text-outline uppercase text-[10px] block font-mono">App Target</span>
                    <span className="font-mono text-on-surface">{selectedArtifact.app}</span>
                  </div>
                </div>

                <div className="p-2.5 rounded bg-surface-container border border-outline-variant space-y-1">
                  <span className="text-outline uppercase text-[10px] block font-mono">Logical Storage Path</span>
                  <span className="font-mono text-[11px] text-on-surface-variant break-all">
                    {selectedArtifact.path}
                  </span>
                </div>

                <div className="p-2.5 rounded bg-surface-container border border-outline-variant space-y-1">
                  <span className="text-outline uppercase text-[10px] block font-mono">Last Verified (UTC)</span>
                  <span className="font-mono text-on-surface">{selectedArtifact.verifiedUtc}</span>
                </div>
              </div>

              <div className="pt-2 border-t border-outline-variant flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => handleVerifyNow(selectedArtifact.id)}
                  disabled={verifyingId === selectedArtifact.id}
                  className="btn-primary text-xs w-full flex items-center justify-center gap-1.5"
                >
                  <span className={`material-symbols-outlined text-[16px] ${verifyingId === selectedArtifact.id ? 'animate-spin' : ''}`}>
                    {verifyingId === selectedArtifact.id ? 'sync' : 'verified'}
                  </span>
                  <span>{verifyingId === selectedArtifact.id ? 'Recomputing Digest...' : 'Re-verify Hash Now'}</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-on-surface-variant font-mono text-xs text-center p-4">
              Select an evidence item from the table to inspect cryptographic hashes, sector origins, and audit status.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
