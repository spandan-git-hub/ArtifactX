import React from 'react';
import { useActiveCase } from '../context/CaseContext';

export default function CaseMetricsPage() {
  const { activeCase } = useActiveCase();

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-y-auto custom-scrollbar p-space-lg space-y-4">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-outline-variant">
        <div>
          <div className="flex items-center space-x-2.5 mb-1">
            <h1 className="text-headline-md font-headline-md font-semibold text-on-surface">
              Case Metrics &amp; Evidentiary Health Telemetry
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-surface-container-high border border-outline-variant text-on-surface-variant uppercase tracking-wider">
              LIVE TELEMETRY
            </span>
          </div>
          <p className="text-body-sm font-body-sm text-on-surface-variant">
            Statistical extraction yield, cryptographic health indicators, and pipeline performance metrics for case {activeCase?.caseNumber}.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={() => alert('Ledger refreshed')}
            className="btn-secondary text-xs"
          >
            <span className="material-symbols-outlined text-[15px]">refresh</span>
            <span>Refresh Ledger</span>
          </button>
          <button
            type="button"
            onClick={() => alert('Exporting metrics attestation...')}
            className="btn-primary text-xs"
          >
            <span className="material-symbols-outlined text-[15px]">print</span>
            <span>Export Metrics Attestation</span>
          </button>
        </div>
      </div>

      {/* MANDATORY AMBER / YELLOW CALLOUT BANNER (Strict Stitch Requirement) */}
      <div className="bg-amber-950/30 border border-amber-600/40 rounded-lg p-3.5 flex items-start space-x-3 text-amber-200 shadow-sm">
        <span className="material-symbols-outlined text-amber-400 text-lg shrink-0 mt-0.5">warning</span>
        <div className="text-body-sm font-body-sm text-amber-100/90 leading-relaxed text-xs">
          <strong className="font-semibold text-amber-300">Methodological Disclosure:</strong> Accuracy is not measured for this case (no ground truth). Forensic metrics track deterministic cryptographic validation, extraction yields, and heuristic parsing thresholds; accuracy against external reality cannot be calculated in the absence of verified ground truth.
        </div>
      </div>

      {/* 1. TOP KPI TILES (4 Across) */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Tile 1 */}
        <div className="bg-surface-container border border-outline-variant rounded-lg p-3.5 flex flex-col justify-between shadow-xs">
          <div className="flex items-center justify-between text-outline text-[11px] font-label-ui uppercase tracking-wider">
            <span>Mounted Artifacts</span>
            <span className="material-symbols-outlined text-[16px] text-primary">dataset</span>
          </div>
          <div className="my-2">
            <div className="text-xl font-bold font-mono text-on-surface">5 Mounted Artifacts</div>
          </div>
          <div className="flex items-center space-x-2 pt-1 border-t border-outline-variant text-[11px] font-mono">
            <span className="text-tertiary font-medium">4 Verified Match</span>
            <span className="text-outline">•</span>
            <span className="text-error font-medium">1 Mismatch</span>
          </div>
        </div>

        {/* Tile 2 */}
        <div className="bg-surface-container border border-outline-variant rounded-lg p-3.5 flex flex-col justify-between shadow-xs">
          <div className="flex items-center justify-between text-outline text-[11px] font-label-ui uppercase tracking-wider">
            <span>Last Re-Verification</span>
            <span className="material-symbols-outlined text-[16px] text-primary">update</span>
          </div>
          <div className="my-2">
            <div className="text-xl font-bold font-mono text-on-surface">10:14:02 UTC</div>
          </div>
          <div className="flex items-center justify-between pt-1 border-t border-outline-variant text-[11px] font-mono text-on-surface-variant">
            <span>Ledger Depth: 48 blocks</span>
            <span className="text-primary">Cycle: 00:04:12 ago</span>
          </div>
        </div>

        {/* Tile 3 */}
        <div className="bg-surface-container border border-outline-variant rounded-lg p-3.5 flex flex-col justify-between shadow-xs">
          <div className="flex items-center justify-between text-outline text-[11px] font-label-ui uppercase tracking-wider">
            <span>Audit Chain Status</span>
            <span className="material-symbols-outlined text-[16px] text-tertiary">verified_user</span>
          </div>
          <div className="my-2">
            <div className="text-lg font-bold font-mono text-tertiary">Strict Append-Only</div>
          </div>
          <div className="flex items-center space-x-1 pt-1 border-t border-outline-variant text-[10.5px] font-mono text-on-surface-variant">
            <span className="text-outline">Root:</span>
            <code className="text-primary bg-surface-container-lowest px-1.5 py-0.2 rounded border border-outline-variant truncate">
              7f8a2c1b9d0e...
            </code>
          </div>
        </div>

        {/* Tile 4 */}
        <div className="bg-surface-container border border-outline-variant rounded-lg p-3.5 flex flex-col justify-between shadow-xs">
          <div className="flex items-center justify-between text-outline text-[11px] font-label-ui uppercase tracking-wider">
            <span>Global Parse Rate</span>
            <span className="material-symbols-outlined text-[16px] text-primary">analytics</span>
          </div>
          <div className="my-2">
            <div className="text-xl font-bold font-mono text-on-surface">98.4% Yield</div>
          </div>
          <div className="flex items-center justify-between pt-1 border-t border-outline-variant text-[11px] font-mono text-on-surface-variant">
            <span>Total: 20,735 Records</span>
            <span className="text-tertiary">386 Carved</span>
          </div>
        </div>
      </section>

      {/* Extraction Yields by Artifact Table */}
      <div className="bg-surface-container border border-outline-variant rounded-lg p-4 shadow-xs space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-outline-variant">
          <h2 className="text-headline-sm font-headline-sm text-on-surface font-semibold">
            Extraction Yield &amp; Anomaly Distribution
          </h2>
          <span className="text-[11px] font-mono text-outline">Partition Breakdown</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-3 rounded bg-surface-container-low border border-outline-variant space-y-2">
            <div className="flex justify-between items-center text-xs font-semibold">
              <span className="text-on-surface font-mono">WhatsApp (msgstore.db.crypt15)</span>
              <span className="text-primary font-mono">98.4% Parsed</span>
            </div>
            <div className="w-full h-2 rounded bg-surface-container-lowest overflow-hidden flex">
              <div className="h-full bg-primary" style={{ width: '98.4%' }} />
              <div className="h-full bg-amber-500" style={{ width: '1.6%' }} />
            </div>
            <div className="flex justify-between text-[11px] text-on-surface-variant font-mono">
              <span>12,842 clean records</span>
              <span className="text-amber-500">208 unparsed/tombstones</span>
            </div>
          </div>

          <div className="p-3 rounded bg-surface-container-low border border-outline-variant space-y-2">
            <div className="flex justify-between items-center text-xs font-semibold">
              <span className="text-on-surface font-mono">Telegram (cache4.db + wal)</span>
              <span className="text-primary font-mono">97.8% Parsed</span>
            </div>
            <div className="w-full h-2 rounded bg-surface-container-lowest overflow-hidden flex">
              <div className="h-full bg-primary" style={{ width: '97.8%' }} />
              <div className="h-full bg-amber-500" style={{ width: '2.2%' }} />
            </div>
            <div className="flex justify-between text-[11px] text-on-surface-variant font-mono">
              <span>7,893 clean records</span>
              <span className="text-amber-500">178 unparsed/corrupt</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
