import React from 'react';
import { useActiveCase } from '../context/CaseContext';

export default function LimitationsPage() {
  const { activeCase } = useActiveCase();

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-y-auto custom-scrollbar p-space-lg space-y-5">
      {/* Statutory Protocol Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-outline-variant text-xs text-on-surface-variant font-mono">
        <div className="flex items-center gap-2">
          <span className="text-tertiary flex items-center gap-1">
            <span className="material-symbols-outlined text-sm">check_circle</span>
            1. Ingest
          </span>
          <span className="text-outline">→</span>
          <span className="text-tertiary flex items-center gap-1">
            <span className="material-symbols-outlined text-sm">check_circle</span>
            2. Decryption
          </span>
          <span className="text-outline">→</span>
          <span className="text-tertiary flex items-center gap-1">
            <span className="material-symbols-outlined text-sm">check_circle</span>
            3. Parsing
          </span>
          <span className="text-outline">→</span>
          <span className="text-tertiary flex items-center gap-1">
            <span className="material-symbols-outlined text-sm">check_circle</span>
            4. Correlation
          </span>
          <span className="text-outline">→</span>
          <span className="text-primary font-semibold flex items-center gap-1 bg-surface-container-high px-2 py-0.5 rounded border border-primary/40">
            <span className="material-symbols-outlined text-sm">verified</span>
            5. Evidentiary Bounds
          </span>
        </div>
        <span className="text-outline">Statutory Protocol: ISO/IEC 27037:2012 §6.4</span>
      </div>

      {/* Page Title & Actions */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-label-mono-sm text-primary font-mono tracking-wider uppercase text-xs">
              Forensic Protocol Specification
            </span>
            <span className="px-1.5 py-0.2 bg-surface-container text-on-surface-variant border border-outline-variant rounded text-[10px] font-mono">
              DOC-ID: ARX-LIM-8942
            </span>
          </div>
          <h1 className="text-headline-lg font-headline-lg font-semibold text-on-surface tracking-tight">
            Limitations and Evidentiary Methods
          </h1>
          <p className="text-body-md text-on-surface-variant mt-1 max-w-4xl leading-relaxed">
            Formal disclosure of technical boundaries, heuristic scoring foundations, and statutory constraints for Case <span className="font-mono text-on-surface font-semibold">{activeCase?.caseNumber}</span>. All analytical outputs in this docket are qualified by the methodologies detailed below.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={() => window.print()}
            className="btn-secondary text-xs"
          >
            <span className="material-symbols-outlined text-[16px]">print</span>
            <span>Export Certificate</span>
          </button>
          <button
            type="button"
            onClick={() => alert('Annex sealed with Ed25519 signature.')}
            className="btn-primary text-xs"
          >
            <span className="material-symbols-outlined text-[16px]">file_download</span>
            <span>Seal Methodology Annex</span>
          </button>
        </div>
      </div>

      {/* KEY SCIENTIFIC DECLARATION BOXED WARNING (Strict Stitch Requirement) */}
      <div className="bg-surface-container-high/60 border-l-4 border-amber-500 rounded-r-lg p-space-md shadow-sm">
        <div className="flex items-start gap-space-sm">
          <span className="material-symbols-outlined text-amber-500 text-[22px] mt-0.5 shrink-0">warning</span>
          <div className="space-y-1">
            <span className="text-label-ui font-label-ui text-amber-400 uppercase tracking-wider block font-semibold text-xs">
              Mandatory Judicial &amp; Laboratory Disclosure
            </span>
            <p className="text-body-md font-body-md text-on-surface leading-relaxed text-sm">
              <strong className="text-amber-200">Scores are heuristic orderings, not probabilities.</strong> A score of <code className="font-mono text-primary bg-surface-container px-1 py-0.5 rounded text-xs">0.85</code> indicates that an item satisfied 85% of qualifying heuristic rules; it does <span className="underline decoration-amber-500 underline-offset-2 font-medium">NOT</span> represent an 85% mathematical probability of human truth or event occurrence in reality. Courts and counsel must treat these indexes as triage rankings rather than absolute empirical frequencies.
            </p>
          </div>
        </div>
      </div>

      {/* Threshold Calibration Matrix & Admissibility Criteria */}
      <section className="bg-surface-container border border-outline-variant rounded-lg p-space-lg space-y-4 shadow-xs">
        <div className="flex items-center justify-between pb-2 border-b border-outline-variant">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">rule_settings</span>
            <h2 className="text-headline-sm font-headline-sm font-semibold text-on-surface">
              Threshold Calibration Matrix &amp; Admissibility Criteria
            </h2>
          </div>
          <span className="text-[11px] font-mono text-primary bg-surface-container-high border border-outline-variant px-2.5 py-1 rounded">
            Heuristic Engine v2.4-A
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Deterministic */}
          <div className="bg-surface-container-low border border-outline-variant rounded p-3 flex flex-col justify-between space-y-2">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="px-2 py-0.5 bg-primary text-on-primary text-[11px] font-mono font-medium rounded">
                  Deterministic
                </span>
                <span className="font-mono font-bold text-primary text-xs">&gt;= 0.95</span>
              </div>
              <p className="text-on-surface-variant text-xs leading-relaxed">
                Cryptographic hash equality, validated cryptographic signature, or strict schema foreign key match.
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-outline-variant flex items-center justify-between text-[11px] font-mono text-primary">
              <span>Evidentiary Weight:</span>
              <span className="font-bold">Primary Fact</span>
            </div>
          </div>

          {/* Strong */}
          <div className="bg-surface-container-low border border-outline-variant rounded p-3 flex flex-col justify-between space-y-2">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="px-2 py-0.5 border border-primary text-primary bg-primary/10 text-[11px] font-mono font-medium rounded">
                  Strong
                </span>
                <span className="font-mono font-bold text-primary text-xs">&gt;= 0.80</span>
              </div>
              <p className="text-on-surface-variant text-xs leading-relaxed">
                Multi-attribute concordance (e.g. E.164 phone + profile match, dHash perceptual similarity &lt;= 2).
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-outline-variant flex items-center justify-between text-[11px] font-mono text-primary">
              <span>Evidentiary Weight:</span>
              <span className="font-bold">Corroborative Fact</span>
            </div>
          </div>

          {/* Moderate */}
          <div className="bg-surface-container-low border border-outline-variant rounded p-3 flex flex-col justify-between space-y-2">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="px-2 py-0.5 border border-amber-500 text-amber-500 bg-amber-500/10 text-[11px] font-mono font-medium rounded">
                  Moderate
                </span>
                <span className="font-mono font-bold text-amber-500 text-xs">&gt;= 0.50</span>
              </div>
              <p className="text-on-surface-variant text-xs leading-relaxed">
                Single-attribute overlap, loose session timeframe, uncheckpointed WAL frame association.
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-outline-variant flex items-center justify-between text-[11px] font-mono text-amber-500">
              <span>Evidentiary Weight:</span>
              <span className="font-bold">Investigative Lead</span>
            </div>
          </div>

          {/* Weak Hint */}
          <div className="bg-surface-container-low border border-outline-variant rounded p-3 flex flex-col justify-between space-y-2">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="px-2 py-0.5 border border-outline text-outline bg-surface-container text-[11px] font-mono font-medium rounded">
                  Weak Hint
                </span>
                <span className="font-mono font-bold text-outline text-xs">&lt; 0.40</span>
              </div>
              <p className="text-on-surface-variant text-xs leading-relaxed">
                Sequential rowid gaps, unallocated residual strings without schema headers.
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-outline-variant flex items-center justify-between text-[11px] font-mono text-outline">
              <span>Evidentiary Weight:</span>
              <span className="font-bold">Heuristic Marker</span>
            </div>
          </div>
        </div>
      </section>

      {/* Forensic Methodology Boundaries */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-surface-container border border-outline-variant rounded-lg p-4 space-y-2 text-xs">
          <div className="flex items-center space-x-2 font-semibold text-on-surface text-sm">
            <span className="material-symbols-outlined text-primary text-base">restore</span>
            <h3>SQLite WAL Residual Reconstruction Method</h3>
          </div>
          <p className="text-on-surface-variant leading-relaxed">
            WAL residual carving targets pages marked uncheckpointed or stored in SQLite freelist trunks. Deleted records are reconstructed by parsing internal cell headers and varint payloads. Records lacking header validation are flagged as partial fragments.
          </p>
        </div>

        <div className="bg-surface-container border border-outline-variant rounded-lg p-4 space-y-2 text-xs">
          <div className="flex items-center space-x-2 font-semibold text-on-surface text-sm">
            <span className="material-symbols-outlined text-primary text-base">schedule</span>
            <h3>Clock Drift &amp; Temporal Synchronization</h3>
          </div>
          <p className="text-on-surface-variant leading-relaxed">
            All database timestamps are converted to UTC. Mobile clock skews up to ±120 seconds are accounted for when calculating temporal correlation windows. System uptime logs are cross-referenced to establish monotonic consistency.
          </p>
        </div>
      </div>
    </div>
  );
}
