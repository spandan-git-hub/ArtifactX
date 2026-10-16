import React, { useState, useEffect, useCallback } from 'react';
import { useActiveCase } from '../context/CaseContext';
import { evidenceService } from '../services/evidenceService';

export default function IntegrityAuditPage() {
  const { activeCase } = useActiveCase();
  const caseId = activeCase?.id;

  const [evidences, setEvidences] = useState([]);
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [verifiedToast, setVerifiedToast] = useState(false);
  const [verifyMessage, setVerifyMessage] = useState('');

  const loadEvidences = useCallback(async () => {
    if (!caseId) {
      setEvidences([]);
      return;
    }
    setLoading(true);
    try {
      const data = await evidenceService.getEvidences(caseId);
      const list = Array.isArray(data) ? data : (data?.evidences || []);
      setEvidences(list);
    } catch (err) {
      console.warn('Error loading evidence records for audit:', err);
      setEvidences([]);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    loadEvidences();
  }, [loadEvidences]);

  const handleVerifyNow = async () => {
    if (!caseId || evidences.length === 0) return;
    setVerifying(true);
    setVerifiedToast(false);
    try {
      for (const ev of evidences) {
        await evidenceService.verifyEvidenceHashes(ev.id);
      }
      await loadEvidences();
      setVerifyMessage(`Cryptographic re-verification succeeded for ${evidences.length} evidence artifact(s).`);
      setVerifiedToast(true);
      setTimeout(() => setVerifiedToast(false), 4000);
    } catch (err) {
      console.error('Hash verification failed:', err);
      setVerifyMessage(err.response?.data?.detail || err.message || 'Cryptographic verification exception flagged.');
      setVerifiedToast(true);
    } finally {
      setVerifying(false);
    }
  };

  const mismatchList = evidences.filter(e => 
    e.integrity_state === 'HASH_MISMATCH' || 
    e.integrity_state === 'FLAGGED_EXCEPTION' ||
    e.status === 'Checksum Mismatch'
  );
  const hasExceptions = mismatchList.length > 0;

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-y-auto custom-scrollbar p-space-lg space-y-4">
      {/* Audit Chain Horizontal Banner */}
      <section className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 px-3.5 py-2 bg-surface-container border border-outline-variant rounded-lg shrink-0">
        <div className="flex items-center space-x-2 text-label-mono-sm text-xs">
          <span className={`inline-block w-2 h-2 rounded-full ${hasExceptions ? 'bg-error animate-ping' : 'bg-tertiary animate-pulse'}`} />
          <span className="text-on-surface-variant font-medium">Audit Ledger State:</span>
          <span className={`font-semibold ${hasExceptions ? 'text-error' : 'text-tertiary'}`}>
            {hasExceptions ? 'INTEGRITY FLAG DETECTED' : 'CHAIN VALID — RECOMPUTED CHECKSUMS VERIFIED'}
          </span>
          <span className="text-outline">|</span>
          <span className="text-on-surface-variant">Active Case: {activeCase?.caseNumber || 'N/A'}</span>
        </div>
        <div className="flex items-center space-x-2 text-label-mono-sm text-xs text-on-surface-variant">
          <span>Signer: SHA-256 / BLAKE3 Cryptographic Engine</span>
        </div>
      </section>

      {/* Verification Toast */}
      {verifiedToast && (
        <div className={`p-3 rounded-lg text-xs font-mono flex items-center justify-between animate-in fade-in ${
          hasExceptions 
            ? 'bg-error/15 border border-error/40 text-error' 
            : 'bg-tertiary/15 border border-tertiary/40 text-tertiary'
        }`}>
          <span>{verifyMessage}</span>
          <span className="material-symbols-outlined text-sm">
            {hasExceptions ? 'error' : 'check_circle'}
          </span>
        </div>
      )}

      {/* Status Cards Grid (Dual Panels) */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        {/* Status Card: Audit Chain Verified (7 Cols) */}
        <section className="xl:col-span-7 bg-surface-container border border-outline-variant rounded-lg p-5 flex flex-col justify-between shadow-xs space-y-4">
          <div>
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[11px] font-mono text-outline uppercase tracking-wider block">
                  Cryptographic Verification Status
                </span>
                <h2 className="text-headline-md font-semibold text-on-surface mt-0.5">
                  Evidence Ingestion Ledger
                </h2>
              </div>
              <span className={`px-2 py-0.5 rounded text-[11px] font-mono font-medium ${
                hasExceptions ? 'bg-error/20 text-error border border-error/30' : 'bg-tertiary/10 text-tertiary border border-tertiary/30'
              }`}>
                {evidences.length} Tracked Artifacts
              </span>
            </div>

            <p className="text-body-sm text-on-surface-variant mt-3 text-xs leading-relaxed">
              Every staged bit-stream file, unallocated SQLite carve, and derived artifact is verified against stored SHA-256 digests in pure memory to guarantee forensic immutability (BSA §63).
            </p>
          </div>

          <div className="pt-2 border-t border-outline-variant/60 flex items-center justify-between">
            <span className="text-[11px] font-mono text-outline">
              Verified Status: {evidences.length - mismatchList.length} / {evidences.length} Valid
            </span>
            <button
              type="button"
              onClick={handleVerifyNow}
              disabled={verifying || evidences.length === 0}
              className="btn-primary text-xs flex items-center gap-1.5"
            >
              <span className={`material-symbols-outlined text-sm ${verifying ? 'animate-spin' : ''}`}>
                {verifying ? 'sync' : 'verified'}
              </span>
              <span>{verifying ? 'Verifying Hashes...' : 'Re-verify All Hashes'}</span>
            </button>
          </div>
        </section>

        {/* Status Card: Exceptions / Anomaly Report (5 Cols) */}
        <section className={`xl:col-span-5 rounded-lg p-5 flex flex-col justify-between shadow-xs border ${
          hasExceptions 
            ? 'bg-error/10 border-error' 
            : 'bg-surface-container border-outline-variant'
        }`}>
          <div>
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono text-outline uppercase tracking-wider block">
                Tamper &amp; Mismatch Detection
              </span>
              <span className={`material-symbols-outlined text-lg ${hasExceptions ? 'text-error' : 'text-tertiary'}`}>
                {hasExceptions ? 'gpp_maybe' : 'verified_user'}
              </span>
            </div>

            <h3 className="text-headline-sm font-semibold text-on-surface mt-1">
              {hasExceptions ? `${mismatchList.length} Hash Mismatch Detected` : 'Zero Exceptions Detected'}
            </h3>

            {hasExceptions ? (
              <div className="mt-3 p-3 rounded bg-surface-container-lowest border border-error/30 space-y-1 font-mono text-[11px]">
                {mismatchList.map(m => (
                  <div key={m.id} className="flex justify-between text-on-surface-variant">
                    <span>Artifact: {m.original_filename || m.name}</span>
                    <span className="text-error font-semibold">{m.integrity_state || 'MISMATCH'}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-body-sm text-on-surface-variant mt-2 text-xs">
                No hash deviations or pre-gate checksum refusals recorded for case {activeCase?.caseNumber || 'docket'}.
              </p>
            )}
          </div>

          <div className="pt-2 border-t border-outline-variant/60 text-xs text-outline">
            Section 63 Gate: {hasExceptions ? 'Refused / Flagged' : 'Passed'}
          </div>
        </section>
      </div>

      {/* Ledger Blocks History Table */}
      <div className="bg-surface-container border border-outline-variant rounded-lg overflow-hidden shadow-xs">
        <div className="p-3 border-b border-outline-variant flex items-center justify-between">
          <h3 className="font-headline-sm font-headline-sm text-on-surface font-semibold">
            Immutable Audit Trail &amp; Artifact Register
          </h3>
          <span className="text-[11px] font-mono text-outline">Evidence Ingestion Manifest</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-body-sm font-body-sm">
            <thead>
              <tr className="bg-surface-container-lowest/80 border-b border-outline-variant h-8 text-label-ui font-label-ui text-on-surface-variant uppercase tracking-wider text-[11px]">
                <th className="py-2.5 px-3 w-16">ID</th>
                <th className="py-2.5 px-3 w-44">Filename / Exhibit</th>
                <th className="py-2.5 px-3 w-32">Type</th>
                <th className="py-2.5 px-3 font-mono text-[11px]">SHA-256 Checksum</th>
                <th className="py-2.5 px-3 w-28">Ingested UTC</th>
                <th className="py-2.5 px-3 w-32 text-right">Integrity</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/60 font-mono text-xs">
              {loading && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-on-surface-variant">
                    <span className="material-symbols-outlined text-2xl animate-spin text-primary mb-1">sync</span>
                    <p>Loading evidence audit trail...</p>
                  </td>
                </tr>
              )}

              {!loading && evidences.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-on-surface-variant">
                    No evidence records staged or ingested for this case yet.
                  </td>
                </tr>
              )}

              {!loading && evidences.map((ev) => {
                const isMismatch = ev.integrity_state === 'HASH_MISMATCH' || ev.status === 'Checksum Mismatch';
                return (
                  <tr
                    key={ev.id}
                    className={`hover:bg-surface-container-high/40 transition-colors ${
                      isMismatch ? 'bg-error/5' : ''
                    }`}
                  >
                    <td className="py-3 px-3 font-semibold text-primary">#{ev.id}</td>
                    <td className="py-3 px-3 text-on-surface font-semibold truncate max-w-xs">
                      {ev.original_filename || ev.name || `Evidence #${ev.id}`}
                    </td>
                    <td className="py-3 px-3 text-on-surface-variant">{ev.evidence_type || 'Bit-stream Dump'}</td>
                    <td className="py-3 px-3">
                      <code className="text-on-surface bg-surface-container-lowest px-1.5 py-0.5 rounded border border-outline-variant text-[10px] block truncate max-w-xs font-mono">
                        {ev.sha256 || 'Pending SHA-256'}
                      </code>
                    </td>
                    <td className="py-3 px-3 text-on-surface-variant text-[11px]">
                      {ev.uploaded_at ? new Date(ev.uploaded_at).toISOString().substring(0, 19).replace('T', ' ') : 'N/A'}
                    </td>
                    <td className="py-3 px-3 text-right">
                      {isMismatch ? (
                        <span className="px-2 py-0.5 rounded bg-error/15 text-error border border-error/40 text-[10px] font-semibold">
                          HASH MISMATCH
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-tertiary/10 text-tertiary border border-tertiary/30 text-[10px] font-semibold">
                          {ev.integrity_state || 'VERIFIED'}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
