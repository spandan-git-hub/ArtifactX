import React, { useState, useEffect, useCallback } from 'react';
import { useActiveCase } from '../context/CaseContext';
import { evidenceService } from '../services/evidenceService';

export default function Section63Page() {
  const { activeCase } = useActiveCase();
  const caseId = activeCase?.id;

  const [artifacts, setArtifacts] = useState([]);
  const [loading, setLoading] = useState(false);

  const [certifier, setCertifier] = useState({
    name: activeCase?.examiner || '',
    designation: 'Forensic Examiner & Certifier',
    agency: activeCase?.agency || 'Special Cyber Forensics Division',
    station: 'Forensic Enclave Workstation',
    certificateRef: `BSA-2023-SEC63-${activeCase?.caseNumber || caseId || 'DRAFT'}`,
    date: new Date().toISOString().substring(0, 10),
    attested: false
  });

  useEffect(() => {
    if (activeCase) {
      setCertifier(prev => ({
        ...prev,
        name: prev.name || activeCase.examiner || '',
        agency: prev.agency || activeCase.agency || 'Special Cyber Forensics Division',
        certificateRef: `BSA-2023-SEC63-${activeCase.caseNumber || caseId || 'DRAFT'}`
      }));
    }
  }, [activeCase, caseId]);

  const loadArtifacts = useCallback(async () => {
    if (!caseId) {
      setArtifacts([]);
      return;
    }
    setLoading(true);
    try {
      const data = await evidenceService.getEvidences(caseId);
      const list = Array.isArray(data) ? data : (data?.evidences || []);
      const mapped = list.map((ev, i) => ({
        item: String(i + 1).padStart(2, '0'),
        id: ev.id,
        name: ev.original_filename || ev.name || `Evidence #${ev.id}`,
        size: ev.file_size_bytes ? `${(ev.file_size_bytes / (1024 * 1024)).toFixed(1)} MiB` : (ev.size || 'N/A'),
        algo: 'SHA-256',
        hash: ev.sha256 || 'Pending Calculation',
        role: ev.evidence_type || 'Primary Evidence Container',
        verifiedUtc: ev.uploaded_at ? new Date(ev.uploaded_at).toISOString().replace('T', ' ').substring(0, 19) : 'Recently',
        status: ev.integrity_state === 'HASH_MISMATCH' ? 'Mismatch' : (ev.integrity_state || 'Match')
      }));
      setArtifacts(mapped);
    } catch (err) {
      console.warn('Error loading artifacts for Section 63:', err);
      setArtifacts([]);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    loadArtifacts();
  }, [loadArtifacts]);

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden">
      {/* 1. Amber Warning Banner at Top */}
      <section className="bg-amber-950/30 border-b border-amber-600/40 px-space-lg py-2.5 flex items-start gap-3 shrink-0">
        <span className="material-symbols-outlined text-amber-400 text-lg shrink-0 mt-0.5">warning</span>
        <div className="flex flex-col">
          <p className="text-body-sm font-body-sm text-amber-200">
            <span className="font-semibold uppercase tracking-wider text-amber-400">
              ⚠ DRAFT FOR EXPERT REVIEW — not a certificate.
            </span>{' '}
            This tool prepares technical schedules for verification and signature by an authorized certifier under Section 63 of the Bharatiya Sakshya Adhiniyam, 2023. Do not submit unexamined output to court.
          </p>
          <div className="flex flex-wrap items-center gap-4 mt-1 text-label-mono-sm font-label-mono-sm text-amber-400 text-xs">
            <span>Statutory Reference: BSA 2023 s. 63(4)</span>
            <span>•</span>
            <span>Case Number: <code className="text-on-surface bg-surface-container-lowest px-1 py-0.2 rounded font-mono">{activeCase?.caseNumber || 'N/A'}</code></span>
            {activeCase?.sha256Root && (
              <>
                <span>•</span>
                <span>Master Case Root: <code className="text-on-surface bg-surface-container-lowest px-1 py-0.2 rounded font-mono">{activeCase.sha256Root.substring(0, 16)}...</code></span>
              </>
            )}
          </div>
        </div>
      </section>

      {/* Main Scrollable Canvas */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-space-lg space-y-5">
        {/* Section 1: Cryptographic Hash Report (Schedule of Artifacts) */}
        <div className="bg-surface-container border border-outline-variant rounded-lg overflow-hidden shadow-xs">
          <div className="flex flex-wrap items-center justify-between p-3 border-b border-outline-variant bg-surface-container-low gap-3">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-base">fingerprint</span>
              <h2 className="text-headline-sm font-headline-sm font-semibold text-on-surface">
                Cryptographic Hash Report (Schedule of Artifacts)
              </h2>
              <span className="text-label-mono-sm text-outline bg-surface-container-lowest border border-outline-variant px-2 py-0.5 rounded text-xs">
                {artifacts.length} Items Identified
              </span>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-label-mono-sm text-xs text-on-surface-variant font-mono">Algorithm: SHA-256 (Statutory Primary)</span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-body-sm font-body-sm">
              <thead>
                <tr className="bg-surface-container-lowest/80 border-b border-outline-variant h-8 text-label-ui font-label-ui text-on-surface-variant uppercase tracking-wider text-[11px]">
                  <th className="py-2.5 px-3 w-12 text-center">Item</th>
                  <th className="py-2.5 px-3">Filename / Container</th>
                  <th className="py-2.5 px-3 w-24">Size</th>
                  <th className="py-2.5 px-3 w-28">Algorithm</th>
                  <th className="py-2.5 px-3 font-mono">Cryptographic Hash Digest</th>
                  <th className="py-2.5 px-3">Evidentiary Role</th>
                  <th className="py-2.5 px-3 text-right">Integrity Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/60 text-xs">
                {loading && (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-on-surface-variant font-mono">
                      Loading evidence schedule for Section 63 certificate...
                    </td>
                  </tr>
                )}

                {!loading && artifacts.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-10 text-center text-on-surface-variant font-mono">
                      No evidence artifacts registered for this case docket.
                    </td>
                  </tr>
                )}

                {!loading && artifacts.map((a) => (
                  <tr key={a.item} className="hover:bg-surface-container-high/40 transition-colors">
                    <td className="py-2.5 px-3 text-center font-mono text-outline">{a.item}</td>
                    <td className="py-2.5 px-3 font-medium text-on-surface">
                      <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-sm text-primary">database</span>
                        <span>{a.name}</span>
                      </div>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-on-surface-variant">{a.size}</td>
                    <td className="py-2.5 px-3 font-mono text-outline">{a.algo}</td>
                    <td className="py-2.5 px-3 font-mono text-on-surface">
                      <code className="bg-surface-container-lowest px-1.5 py-0.5 rounded border border-outline-variant text-[11px] block truncate max-w-xs">
                        {a.hash}
                      </code>
                    </td>
                    <td className="py-2.5 px-3 text-on-surface-variant">{a.role}</td>
                    <td className="py-2.5 px-3 text-right">
                      <span className={`px-2 py-0.5 rounded font-mono text-[10px] font-medium border ${
                        a.status === 'Match'
                          ? 'bg-tertiary/10 text-tertiary border-tertiary/30'
                          : 'bg-error/15 text-error border-error/40'
                      }`}>
                        {a.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Section 2: Certifier Identification & Attestation Form */}
        <div className="bg-surface-container border border-outline-variant rounded-lg p-5 space-y-4 shadow-xs">
          <div className="border-b border-outline-variant pb-3 flex items-center justify-between">
            <h2 className="text-headline-sm font-headline-sm font-semibold text-on-surface">
              Certifier Identification &amp; Statutory Attestation (BSA §63(4))
            </h2>
            <span className="text-label-mono-sm text-[11px] text-outline">Form B Statutory Draft</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="space-y-1">
              <label className="text-label-ui uppercase tracking-wider text-on-surface-variant block">
                Full Legal Name of Certifier
              </label>
              <input
                type="text"
                placeholder="e.g. Abhishek Verma"
                value={certifier.name}
                onChange={(e) => setCertifier({ ...certifier, name: e.target.value })}
                className="w-full bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1.5 text-body-sm text-on-surface focus:outline-none focus:border-primary"
              />
            </div>

            <div className="space-y-1">
              <label className="text-label-ui uppercase tracking-wider text-on-surface-variant block">
                Official Designation / Cadre
              </label>
              <input
                type="text"
                placeholder="e.g. Senior Forensic Analyst"
                value={certifier.designation}
                onChange={(e) => setCertifier({ ...certifier, designation: e.target.value })}
                className="w-full bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1.5 text-body-sm text-on-surface focus:outline-none focus:border-primary"
              />
            </div>

            <div className="space-y-1">
              <label className="text-label-ui uppercase tracking-wider text-on-surface-variant block">
                Investigating Agency / Law Enforcement Unit
              </label>
              <input
                type="text"
                placeholder="e.g. Directorate of Enforcement"
                value={certifier.agency}
                onChange={(e) => setCertifier({ ...certifier, agency: e.target.value })}
                className="w-full bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1.5 text-body-sm text-on-surface focus:outline-none focus:border-primary"
              />
            </div>

            <div className="space-y-1">
              <label className="text-label-ui uppercase tracking-wider text-on-surface-variant block">
                Certificate Docket Reference
              </label>
              <input
                type="text"
                value={certifier.certificateRef}
                onChange={(e) => setCertifier({ ...certifier, certificateRef: e.target.value })}
                className="w-full bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1.5 font-mono text-body-sm text-on-surface focus:outline-none focus:border-primary"
              />
            </div>
          </div>

          <div className="pt-2 flex items-center justify-between">
            <label className="flex items-center space-x-2 cursor-pointer text-xs">
              <input
                type="checkbox"
                checked={certifier.attested}
                onChange={(e) => setCertifier({ ...certifier, attested: e.target.checked })}
                className="rounded border-outline-variant text-primary focus:ring-0"
              />
              <span className="text-on-surface-variant">
                I hereby attest that the evidence was processed under strict forensically sound conditions.
              </span>
            </label>

            <button
              type="button"
              onClick={() => window.print()}
              disabled={artifacts.length === 0}
              className="btn-primary text-xs"
            >
              Export Section 63 Schedule PDF
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
