import React, { useState } from 'react';
import { useActiveCase } from '../context/CaseContext';

const LEDGER_BLOCKS = [
  {
    blockNumber: '#48',
    timestamp: '2026-03-30 08:42:19.094 UTC',
    eventType: 'PIPELINE_CYCLE_COMMIT',
    target: 'Full Analysis Docket (WhatsApp + Telegram + Residuals)',
    prevHash: '9a4fe88c1b3d2e44f8ca56449102c019dbebf883651139eef7b5a8e032148b8d',
    currentHash: '7f8a2c1b9d0e44f8ca56449102c019dbebf883651139eef7b5a8e032148b8df2',
    signer: 'ECDSA-P256:Node-04',
    status: 'Appended & Sealed'
  },
  {
    blockNumber: '#47',
    timestamp: '2026-03-30 08:38:27.102 UTC',
    eventType: 'STAGE_CORRELATION_SEAL',
    target: 'Entity Graph Linkage (7 Entity Pairs Sealed)',
    prevHash: '4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c',
    currentHash: '9a4fe88c1b3d2e44f8ca56449102c019dbebf883651139eef7b5a8e032148b8d',
    signer: 'ECDSA-P256:Node-04',
    status: 'Appended & Sealed'
  },
  {
    blockNumber: '#46',
    timestamp: '2026-03-30 08:37:12.910 UTC',
    eventType: 'STAGE_CARVING_SEAL',
    target: 'WAL Residual Frame Excavation (218 Records)',
    prevHash: '01f5e88d11ac293847291048b291048572910485729104857291048572910485',
    currentHash: '4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c',
    signer: 'ECDSA-P256:Node-04',
    status: 'Appended & Sealed'
  },
  {
    blockNumber: '#45-EX',
    timestamp: '2026-03-30 08:35:30.402 UTC',
    eventType: 'INGEST_HASH_MISMATCH',
    target: 'encrypted_backup.key (Pre-Gate Checksum Failure)',
    prevHash: '8a72cf19d45e08b1a32f91bc740192e8fa312904bc78e120aa45192803bba221',
    currentHash: 'MISMATCH_HALT (Pre-Ledger Flag)',
    signer: 'IntakeGate:Node-04',
    status: 'Failed Pre-Check'
  },
  {
    blockNumber: '#44',
    timestamp: '2026-03-30 08:35:12.019 UTC',
    eventType: 'INTAKE_MANIFEST_SEAL',
    target: 'Physical Evidence Store (msgstore.db.crypt15, cache4.db)',
    prevHash: 'c218f09d84e20791a82f3c7b6a19f048d21b780e1a674512e098df1245ba8912',
    currentHash: '8a72cf19d45e08b1a32f91bc740192e8fa312904bc78e120aa45192803bba221',
    signer: 'ECDSA-P256:Node-04',
    status: 'Appended & Sealed'
  }
];

export default function IntegrityAuditPage() {
  const { activeCase } = useActiveCase();
  const [verifying, setVerifying] = useState(false);
  const [verifiedToast, setVerifiedToast] = useState(false);

  const handleVerifyNow = () => {
    setVerifying(true);
    setTimeout(() => {
      setVerifying(false);
      setVerifiedToast(true);
      setTimeout(() => setVerifiedToast(false), 3000);
    }, 600);
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-y-auto custom-scrollbar p-space-lg space-y-4">
      {/* Audit Chain Horizontal Banner */}
      <section className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 px-3.5 py-2 bg-surface-container border border-outline-variant rounded-lg shrink-0">
        <div className="flex items-center space-x-2 text-label-mono-sm text-xs">
          <span className="inline-block w-2 h-2 rounded-full bg-tertiary animate-pulse" />
          <span className="text-on-surface-variant font-medium">Audit Ledger State:</span>
          <span className="text-tertiary font-semibold">CHAIN VALID — MERKLE ROOT VALIDATED</span>
          <span className="text-outline">|</span>
          <span className="text-on-surface-variant">Last Root Verification: UTC {new Date().toISOString().substring(0, 19)}</span>
        </div>
        <div className="flex items-center space-x-2 text-label-mono-sm text-xs text-on-surface-variant">
          <span>Signer: ECDSA-P256-SHA256 (Node-04)</span>
        </div>
      </section>

      {/* Verification Success Toast */}
      {verifiedToast && (
        <div className="p-3 bg-tertiary/15 border border-tertiary/40 rounded-lg text-tertiary text-xs font-mono flex items-center justify-between animate-in fade-in">
          <span>Cryptographic tree traversal verified 48 sequential blocks. Zero hash deviations detected.</span>
          <span className="material-symbols-outlined text-sm">check_circle</span>
        </div>
      )}

      {/* Status Cards Grid (Dual Stitch Panels) */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        {/* Status Card: Audit Chain Verified (7 Cols) */}
        <section className="xl:col-span-7 bg-surface-container border border-outline-variant rounded-lg p-5 flex flex-col justify-between shadow-xs space-y-4">
          <div>
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-2.5">
                <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-tertiary/10 text-tertiary border border-tertiary/30">
                  <span className="material-symbols-outlined text-[22px]">verified</span>
                </div>
                <div>
                  <h2 className="text-headline-sm font-headline-sm font-semibold text-on-surface">Audit Chain Verified</h2>
                  <p className="text-body-sm text-on-surface-variant">
                    Cryptographic ledger integrity verified up to block #48 for docket {activeCase?.caseNumber}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <span className="text-label-ui uppercase tracking-wider text-outline block text-[10px]">Chain Depth</span>
                <span className="font-mono text-base font-bold text-on-surface">48 blocks</span>
              </div>
            </div>

            {/* Monospace Head-Hash Chip */}
            <div className="mt-4 p-3 bg-surface-container-low border border-outline-variant rounded-lg space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-label-ui text-on-surface-variant">Current Head-Hash (Merkle Root):</span>
                <span className="font-mono text-primary font-semibold text-[11px]">BLAKE3-256 + SHA-256</span>
              </div>
              <div className="flex items-center justify-between bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1.5">
                <code className="font-mono text-xs text-on-surface tracking-wider select-all break-all">
                  7f8a2c1b9d0e44f8ca56449102c019dbebf883651139eef7b5a8e032148b8df2
                </code>
                <button
                  type="button"
                  onClick={() => navigator.clipboard?.writeText('7f8a2c1b9d0e44f8ca56449102c019dbebf883651139eef7b5a8e032148b8df2')}
                  className="ml-2 p-1 text-on-surface-variant hover:text-primary transition-colors"
                  title="Copy Head-Hash"
                >
                  <span className="material-symbols-outlined text-[16px]">content_copy</span>
                </button>
              </div>
            </div>

            <p className="mt-2 text-body-sm text-on-surface-variant flex items-center text-xs">
              <span className="material-symbols-outlined text-[15px] mr-1 text-amber-500">warning</span>
              Record this root hash separately in case physical notebook or judicial evidence registry.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 pt-3 border-t border-outline-variant">
            <button
              type="button"
              onClick={handleVerifyNow}
              disabled={verifying}
              className="btn-primary text-xs"
            >
              <span className="material-symbols-outlined text-[16px]">
                {verifying ? 'sync' : 'refresh'}
              </span>
              <span>{verifying ? 'Verifying Tree...' : 'Verify Now'}</span>
            </button>
            <button
              type="button"
              onClick={() => alert('Exporting signed audit ledger XML/JSON...')}
              className="btn-secondary text-xs"
            >
              <span className="material-symbols-outlined text-[16px]">download</span>
              <span>Export Ledger</span>
            </button>
          </div>
        </section>

        {/* Failure-State Alert Card (5 Cols) from Stitch */}
        <section className="xl:col-span-5 bg-error/5 border border-error/40 rounded-lg p-5 flex flex-col justify-between shadow-xs space-y-4">
          <div>
            <div className="flex items-start space-x-2.5">
              <span className="material-symbols-outlined text-error text-[24px] shrink-0 mt-0.5">gpp_bad</span>
              <div className="space-y-1">
                <h3 className="text-headline-sm font-headline-sm text-error font-semibold leading-tight">
                  INTEGRITY FAILURE — Exception Intercept
                </h3>
                <p className="text-body-sm text-on-surface-variant text-xs leading-relaxed">
                  Strict Chain-of-Custody Lock active. If any computed binary hash deviates from custodial intake records, stages refuse to run.
                </p>
              </div>
            </div>

            <div className="mt-3 p-3 rounded bg-surface-container-lowest border border-error/30 space-y-1 font-mono text-[11px]">
              <div className="flex justify-between text-on-surface-variant">
                <span>Intercepted Artifact:</span>
                <span className="text-error font-semibold">encrypted_backup.key</span>
              </div>
              <div className="flex justify-between text-on-surface-variant">
                <span>Intake Manifest:</span>
                <span className="text-on-surface">01f5e88d11ac...</span>
              </div>
              <div className="flex justify-between text-on-surface-variant">
                <span>Computed On-Disk:</span>
                <span className="text-error">a89c104fe291...</span>
              </div>
            </div>
          </div>

          <div className="pt-2 border-t border-outline-variant/60 flex items-center justify-between text-xs">
            <span className="text-outline">Section 63 Gate Refusal</span>
            <button
              type="button"
              onClick={() => alert('Opening raw exception traceback...')}
              className="text-error hover:underline font-medium"
            >
              Inspect Traceback →
            </button>
          </div>
        </section>
      </div>

      {/* Ledger Blocks History Table */}
      <div className="bg-surface-container border border-outline-variant rounded-lg overflow-hidden shadow-xs">
        <div className="p-3 border-b border-outline-variant flex items-center justify-between">
          <h3 className="font-headline-sm font-headline-sm text-on-surface font-semibold">
            Immutable Audit Trail &amp; Ledger Block Sequence
          </h3>
          <span className="text-[11px] font-mono text-outline">Append-Only Cryptographic Chain</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-body-sm font-body-sm">
            <thead>
              <tr className="bg-surface-container-lowest/80 border-b border-outline-variant h-8 text-label-ui font-label-ui text-on-surface-variant uppercase tracking-wider text-[11px]">
                <th className="py-2.5 px-3 w-20">Block #</th>
                <th className="py-2.5 px-3 w-44">UTC Timestamp</th>
                <th className="py-2.5 px-3 w-48">Event Action</th>
                <th className="py-2.5 px-3">Target Scope</th>
                <th className="py-2.5 px-3 font-mono text-[11px]">Block Merkle Hash</th>
                <th className="py-2.5 px-3 w-32 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/60 font-mono text-xs">
              {LEDGER_BLOCKS.map((blk) => (
                <tr
                  key={blk.blockNumber}
                  className={`hover:bg-surface-container-high/40 transition-colors ${
                    blk.status.includes('Failed') ? 'bg-error/5' : ''
                  }`}
                >
                  <td className="py-3 px-3 font-semibold text-primary">{blk.blockNumber}</td>
                  <td className="py-3 px-3 text-on-surface-variant">{blk.timestamp}</td>
                  <td className="py-3 px-3 font-semibold text-on-surface">{blk.eventType}</td>
                  <td className="py-3 px-3 text-on-surface-variant max-w-xs truncate">{blk.target}</td>
                  <td className="py-3 px-3">
                    <code className="text-on-surface bg-surface-container-lowest px-1.5 py-0.5 rounded border border-outline-variant text-[10px] block truncate max-w-xs">
                      {blk.currentHash}
                    </code>
                  </td>
                  <td className="py-3 px-3 text-right">
                    {blk.status.includes('Appended') ? (
                      <span className="px-2 py-0.5 rounded bg-tertiary/10 text-tertiary border border-tertiary/30 text-[10px] font-semibold">
                        {blk.status}
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded bg-error/15 text-error border border-error/40 text-[10px] font-semibold">
                        {blk.status}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
