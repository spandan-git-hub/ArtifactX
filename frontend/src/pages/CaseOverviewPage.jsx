import React, { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useActiveCase } from '../context/CaseContext';

export default function CaseOverviewPage() {
  const { caseId } = useParams();
  const { activeCase, cases } = useActiveCase();

  // Display case can be matched by URL param or context activeCase
  const currentCase = cases.find(c => c.id === caseId || c.caseNumber === caseId) || activeCase;

  // View state dynamically determined by actual case status and evidence count
  const viewState = !currentCase || currentCase.evidenceCount === 0
    ? 'empty'
    : (currentCase.integrityState === 'Flagged Exception' || currentCase.integrityState === 'HASH_MISMATCH' ? 'failure' : 'normal');

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-y-auto custom-scrollbar p-space-lg">
      <div className="w-full max-w-[1200px] mx-auto flex flex-col space-y-4 pb-12">
        {/* ================= CASE STATUS TOOLBAR ================= */}
        <div className="flex flex-wrap items-center justify-between gap-3 bg-surface-container-low border border-outline-variant rounded-lg px-4 py-2.5">
          <div className="flex items-center space-x-2">
            <span className="font-label-mono-sm text-label-mono-sm text-outline">DOCKET:</span>
            <span className="font-headline-sm text-headline-sm font-semibold text-primary">
              {currentCase?.caseNumber || 'N/A'}
            </span>
            <span className="text-outline text-xs">•</span>
            <span className="text-body-sm text-on-surface truncate max-w-md">{currentCase?.title || 'No Active Case'}</span>
          </div>

          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-surface-container border border-outline-variant text-[11px] font-label-mono-sm">
              <span className="text-outline uppercase">EVIDENCE:</span>
              <span className="text-on-surface font-semibold">{currentCase?.evidenceCount ?? 0} ITEMS</span>
            </div>
            <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-surface-container border border-outline-variant text-[11px] font-label-mono-sm">
              <span className="text-outline uppercase">INTEGRITY:</span>
              <span className={`font-semibold ${
                currentCase?.integrityState === 'Flagged Exception' || currentCase?.integrityState === 'HASH_MISMATCH'
                  ? 'text-error'
                  : currentCase?.integrityState === 'Pending Ingestion'
                    ? 'text-on-surface-variant'
                    : 'text-tertiary'
              }`}>
                {currentCase?.integrityState || 'Pending Ingestion'}
              </span>
            </div>
          </div>
        </div>

        {/* ================= VARIANT 1: INTEGRITY FAILURE STATE ================= */}
        {viewState === 'failure' && (
          <div className="space-y-4 animate-in fade-in">
            {/* Top Critical Alert Banner */}
            <div className="bg-error/10 border-2 border-error rounded-lg p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-lg">
              <div className="flex items-start space-x-3">
                <div className="w-10 h-10 rounded-lg bg-error/20 border border-error/40 flex items-center justify-center shrink-0 text-error">
                  <span className="material-symbols-outlined text-[24px]">gpp_bad</span>
                </div>
                <div>
                  <h2 className="text-headline-md font-headline-md font-semibold text-error">
                    CRITICAL INTEGRITY FAILURE — Chain of Custody Lock Engaged
                  </h2>
                  <p className="text-body-sm text-on-surface mt-1">
                    Computed SHA-256 for artifact <code className="text-error bg-surface-container-lowest px-1.5 py-0.5 rounded border border-error/30 font-mono">encrypted_backup.key</code> deviates from acquisition manifest. Pipeline execution refused to prevent evidentiary contamination.
                  </p>
                  <div className="mt-2 flex items-center space-x-4 text-label-mono-sm text-[11px] text-error">
                    <span>Claimed: 01f5e88d11ac293...</span>
                    <span>Actual: a89c104fe291b84...</span>
                    <span className="underline cursor-pointer">View Forensic Exception Block #40921-E</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-2 shrink-0">
                <Link
                  to={`/cases/${currentCase?.id}/integrity`}
                  className="px-3.5 py-2 rounded bg-error text-white font-semibold text-label-ui hover:bg-error/90 transition-colors shadow-sm"
                >
                  Inspect Exception Ledger
                </Link>
                <button
                  type="button"
                  onClick={() => setViewState('normal')}
                  className="px-3 py-2 rounded bg-surface-container border border-outline-variant text-on-surface text-label-ui hover:bg-surface-container-high transition-colors"
                >
                  Override (Test Mode)
                </button>
              </div>
            </div>

            {/* Locked Pipeline Notice */}
            <div className="bg-surface-container border border-outline-variant rounded-lg p-5 text-center space-y-3">
              <span className="material-symbols-outlined text-outline text-4xl">lock_clock</span>
              <h3 className="text-headline-sm font-headline-sm text-on-surface">Analysis Stages Locked</h3>
              <p className="text-body-sm text-on-surface-variant max-w-lg mx-auto">
                Under Section 63 BSA protocols, automated parsing, entity resolution, and report generation are suspended until the custodial officer verifies the physical disk intake hash.
              </p>
              <div className="pt-2">
                <Link
                  to={`/cases/${currentCase?.id}/evidence`}
                  className="btn-primary"
                >
                  Review Evidence Manifest &amp; Re-verify Hashes
                </Link>
              </div>
            </div>
          </div>
        )}

        {/* ================= VARIANT 2: EMPTY CASE STATE ================= */}
        {viewState === 'empty' && (
          <div className="space-y-4 animate-in fade-in">
            <div className="bg-surface-container border border-outline-variant rounded-lg p-8 text-center space-y-4 shadow-sm">
              <div className="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/30 flex items-center justify-center mx-auto text-primary">
                <span className="material-symbols-outlined text-[32px]">folder_open</span>
              </div>
              <div className="space-y-1">
                <h2 className="text-headline-md font-headline-md font-semibold text-on-surface">
                  Case Repository Initialized: Zero Artifacts Mounted
                </h2>
                <p className="text-body-sm text-on-surface-variant max-w-xl mx-auto">
                  This forensic container has been staged. Ingest WhatsApp/Telegram database dumps (.crypt14, .crypt15, SQLite), WAL frames, media archives, or encryption keys to begin parsing.
                </p>
              </div>

              {/* Step Flow */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl mx-auto pt-4 text-left">
                <div className="p-3.5 rounded bg-surface-container-low border border-outline-variant space-y-2">
                  <div className="flex items-center space-x-2 text-primary font-semibold text-body-sm">
                    <span className="w-5 h-5 rounded-full bg-primary/20 text-primary flex items-center justify-center text-xs">1</span>
                    <span>Upload Artifacts</span>
                  </div>
                  <p className="text-on-surface-variant text-[12px]">
                    Mount physical extractions, plain SQLite files, or crypt15 WhatsApp databases.
                  </p>
                </div>

                <div className="p-3.5 rounded bg-surface-container-low border border-outline-variant space-y-2">
                  <div className="flex items-center space-x-2 text-primary font-semibold text-body-sm">
                    <span className="w-5 h-5 rounded-full bg-primary/20 text-primary flex items-center justify-center text-xs">2</span>
                    <span>Bind Keystore</span>
                  </div>
                  <p className="text-on-surface-variant text-[12px]">
                    Provide encrypted_backup.key or hex AES-256 derivation tokens for decryption.
                  </p>
                </div>

                <div className="p-3.5 rounded bg-surface-container-low border border-outline-variant space-y-2">
                  <div className="flex items-center space-x-2 text-primary font-semibold text-body-sm">
                    <span className="w-5 h-5 rounded-full bg-primary/20 text-primary flex items-center justify-center text-xs">3</span>
                    <span>Run Pipeline</span>
                  </div>
                  <p className="text-on-surface-variant text-[12px]">
                    Trigger multi-source parsing, WAL residual carving, and Section 63 schedule generation.
                  </p>
                </div>
              </div>

              <div className="pt-4 flex items-center justify-center gap-3">
                <Link
                  to={`/cases/${currentCase?.id}/upload`}
                  className="btn-primary"
                >
                  <span className="material-symbols-outlined text-[16px]">upload_file</span>
                  <span>Upload Evidence Files</span>
                </Link>
                <Link
                  to={`/cases/${currentCase?.id}/decryption`}
                  className="btn-secondary"
                >
                  <span className="material-symbols-outlined text-[16px]">key</span>
                  <span>Manage Keys</span>
                </Link>
              </div>
            </div>
          </div>
        )}

        {/* ================= VARIANT 3: NORMAL LIVE CASE STATE ================= */}
        {viewState === 'normal' && (
          <div className="space-y-4 animate-in fade-in">
            {/* Top Banner (Audit Chain Verified Ribbon) */}
            <section className="w-full bg-surface-container border border-outline-variant rounded-lg px-4 py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
              <div className="flex items-center space-x-3">
                <div className="flex items-center space-x-1.5 text-tertiary">
                  <span className="material-symbols-outlined text-[18px]">verified</span>
                  <span className="font-headline-sm text-headline-sm font-semibold tracking-tight">Audit chain verified</span>
                </div>
                <div className="h-3.5 w-[1px] bg-outline-variant" />
                <div className="flex items-center space-x-1 text-label-mono-sm text-on-surface-variant">
                  <span>Length:</span>
                  <span className="text-on-surface font-semibold">48 blocks</span>
                </div>
                <div className="h-3.5 w-[1px] bg-outline-variant" />
                <div className="flex items-center space-x-1.5 bg-surface-container-highest border border-outline-variant px-2 py-0.5 rounded text-label-mono-sm">
                  <span className="text-on-surface-variant text-[10px]">HEAD:</span>
                  <span className="text-primary font-medium tracking-tight">7f8a2c1b9d0e...34cf81</span>
                  <button className="text-on-surface-variant hover:text-primary ml-1" title="Copy Root SHA-256">
                    <span className="material-symbols-outlined text-[12px]">content_copy</span>
                  </button>
                </div>
              </div>

              <div className="flex items-center space-x-3 text-label-mono-sm text-on-surface-variant">
                <div className="flex items-center space-x-1">
                  <span className="material-symbols-outlined text-[14px]">schedule</span>
                  <span>2026-03-30 08:42:19 UTC</span>
                </div>
                <span className="px-2 py-0.5 rounded border border-tertiary/30 bg-tertiary/10 text-tertiary text-label-ui">
                  SIGNATURE ED25519 VALID
                </span>
              </div>
            </section>

            {/* Bento Grid */}
            <div className="grid grid-cols-12 gap-4">
              {/* Evidence Repository Card */}
              <div className="col-span-12 lg:col-span-6 bg-surface-container border border-outline-variant rounded-lg p-4 flex flex-col justify-between shadow-xs">
                <div>
                  <div className="flex items-center justify-between pb-2 mb-3 border-b border-outline-variant">
                    <div className="flex items-center space-x-2">
                      <span className="material-symbols-outlined text-primary">inventory_2</span>
                      <h3 className="font-headline-sm text-headline-sm text-on-surface">Evidence Items</h3>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-label-mono-sm px-1.5 py-0.5 rounded bg-tertiary/10 text-tertiary border border-tertiary/30">
                        3 VERIFIED
                      </span>
                      <span className="text-label-mono-sm px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-500 border border-amber-500/30">
                        1 KEY NEEDED
                      </span>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between p-2 rounded bg-surface-container-highest/60 border border-outline-variant text-label-mono-sm">
                      <div className="flex items-center space-x-2 overflow-hidden">
                        <span className="material-symbols-outlined text-tertiary text-[14px]">check_circle</span>
                        <span className="text-on-surface font-medium truncate">phys_dump_sdcard0.bin</span>
                        <span className="text-on-surface-variant text-[10px]">14.2 GB</span>
                      </div>
                      <div className="flex items-center space-x-1.5 shrink-0 bg-surface-container-lowest px-1.5 py-0.5 rounded border border-outline-variant">
                        <span className="text-outline text-[10px]">SHA256:</span>
                        <span className="text-primary text-[10px]">e3b0c442...8b04</span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between p-2 rounded bg-surface-container-highest/60 border border-outline-variant text-label-mono-sm">
                      <div className="flex items-center space-x-2 overflow-hidden">
                        <span className="material-symbols-outlined text-tertiary text-[14px]">check_circle</span>
                        <span className="text-on-surface font-medium truncate">msgstore.db.crypt15</span>
                        <span className="text-on-surface-variant text-[10px]">182.4 MB</span>
                      </div>
                      <div className="flex items-center space-x-1.5 shrink-0 bg-surface-container-lowest px-1.5 py-0.5 rounded border border-outline-variant">
                        <span className="text-outline text-[10px]">SHA256:</span>
                        <span className="text-primary text-[10px]">8a72cf19...2201</span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between p-2 rounded bg-surface-container-highest/60 border border-outline-variant text-label-mono-sm">
                      <div className="flex items-center space-x-2 overflow-hidden">
                        <span className="material-symbols-outlined text-tertiary text-[14px]">check_circle</span>
                        <span className="text-on-surface font-medium truncate">cache4.db (+wal)</span>
                        <span className="text-on-surface-variant text-[10px]">48.2 MB</span>
                      </div>
                      <div className="flex items-center space-x-1.5 shrink-0 bg-surface-container-lowest px-1.5 py-0.5 rounded border border-outline-variant">
                        <span className="text-outline text-[10px]">SHA256:</span>
                        <span className="text-primary text-[10px]">01f5e88d...11ac</span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between p-2 rounded bg-amber-500/10 border border-amber-500/30 text-label-mono-sm">
                      <div className="flex items-center space-x-2 overflow-hidden">
                        <span className="material-symbols-outlined text-amber-500 text-[14px]">key</span>
                        <span className="text-amber-400 font-medium truncate">encrypted_backup.key</span>
                        <span className="text-on-surface-variant text-[10px]">128 B</span>
                      </div>
                      <div className="flex items-center space-x-1 shrink-0 text-amber-400 text-[10px]">
                        <span>PENDING KEY DERIVATION</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-3 pt-2 border-t border-outline-variant flex items-center justify-between text-label-mono-sm text-on-surface-variant">
                  <span>Custodian: Detective H. Wright</span>
                  <Link to={`/cases/${currentCase?.id}/evidence`} className="text-primary hover:underline flex items-center space-x-1">
                    <span>Inspect all artifacts</span>
                    <span className="material-symbols-outlined text-[12px]">arrow_forward</span>
                  </Link>
                </div>
              </div>

              {/* Last Pipeline Run Card (Compact Stepper) */}
              <div className="col-span-12 lg:col-span-6 bg-surface-container border border-outline-variant rounded-lg p-4 flex flex-col justify-between shadow-xs">
                <div>
                  <div className="flex items-center justify-between pb-2 mb-3 border-b border-outline-variant">
                    <div className="flex items-center space-x-2">
                      <span className="material-symbols-outlined text-primary">play_circle</span>
                      <h3 className="font-headline-sm text-headline-sm text-on-surface">Last Pipeline Run</h3>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-label-mono-sm text-on-surface-variant">Run #042 · 3m 14s elapsed</span>
                      <span className="px-2 py-0.5 rounded bg-tertiary/10 text-tertiary border border-tertiary/30 text-label-ui">
                        COMPLETED
                      </span>
                    </div>
                  </div>

                  {/* Stage Stepper across all 6 stages */}
                  <div className="py-2">
                    <div className="relative flex items-center justify-between">
                      <div className="absolute left-3 right-3 top-3.5 h-[1px] bg-outline-variant -z-0" />

                      <div className="flex flex-col items-center relative z-10">
                        <div className="w-7 h-7 rounded-full bg-tertiary text-on-tertiary flex items-center justify-center text-label-ui font-bold">
                          <span className="material-symbols-outlined text-[14px]">check</span>
                        </div>
                        <span className="text-[10px] font-label-ui text-on-surface mt-1.5 uppercase">Ingest</span>
                        <span className="text-label-mono-sm text-on-surface-variant text-[9px]">0.2s</span>
                      </div>

                      <div className="flex flex-col items-center relative z-10">
                        <div className="w-7 h-7 rounded-full bg-tertiary text-on-tertiary flex items-center justify-center text-label-ui font-bold">
                          <span className="material-symbols-outlined text-[14px]">check</span>
                        </div>
                        <span className="text-[10px] font-label-ui text-on-surface mt-1.5 uppercase">Mount</span>
                        <span className="text-label-mono-sm text-on-surface-variant text-[9px]">1.4s</span>
                      </div>

                      <div className="flex flex-col items-center relative z-10">
                        <div className="w-7 h-7 rounded-full bg-tertiary text-on-tertiary flex items-center justify-center text-label-ui font-bold">
                          <span className="material-symbols-outlined text-[14px]">check</span>
                        </div>
                        <span className="text-[10px] font-label-ui text-on-surface mt-1.5 uppercase">Decrypt</span>
                        <span className="text-label-mono-sm text-on-surface-variant text-[9px]">4.1s</span>
                      </div>

                      <div className="flex flex-col items-center relative z-10">
                        <div className="w-7 h-7 rounded-full bg-tertiary text-on-tertiary flex items-center justify-center text-label-ui font-bold">
                          <span className="material-symbols-outlined text-[14px]">check</span>
                        </div>
                        <span className="text-[10px] font-label-ui text-on-surface mt-1.5 uppercase">Parse</span>
                        <span className="text-label-mono-sm text-on-surface-variant text-[9px]">42.8s</span>
                      </div>

                      <div className="flex flex-col items-center relative z-10">
                        <div className="w-7 h-7 rounded-full bg-tertiary text-on-tertiary flex items-center justify-center text-label-ui font-bold">
                          <span className="material-symbols-outlined text-[14px]">check</span>
                        </div>
                        <span className="text-[10px] font-label-ui text-on-surface mt-1.5 uppercase">Carve</span>
                        <span className="text-label-mono-sm text-on-surface-variant text-[9px]">1m 12s</span>
                      </div>

                      <div className="flex flex-col items-center relative z-10">
                        <div className="w-7 h-7 rounded-full bg-tertiary text-on-tertiary flex items-center justify-center text-label-ui font-bold">
                          <span className="material-symbols-outlined text-[14px]">check</span>
                        </div>
                        <span className="text-[10px] font-label-ui text-on-surface mt-1.5 uppercase">Correlate</span>
                        <span className="text-label-mono-sm text-on-surface-variant text-[9px]">1m 14s</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-2 p-2 bg-surface-container-low rounded border border-outline-variant flex items-center justify-between text-body-sm">
                    <span className="text-on-surface-variant text-xs">Extraction Yield: 12,842 messages, 218 recovered records</span>
                    <span className="text-primary font-mono text-xs font-semibold">98.4% yield</span>
                  </div>
                </div>

                <div className="mt-3 pt-2 border-t border-outline-variant flex items-center justify-between text-label-mono-sm">
                  <span className="text-on-surface-variant">Engine: v4.8.2-rev9 (Deterministic)</span>
                  <Link to={`/cases/${currentCase?.id}/pipeline`} className="text-primary hover:underline flex items-center space-x-1">
                    <span>Manage Pipeline</span>
                    <span className="material-symbols-outlined text-[12px]">arrow_forward</span>
                  </Link>
                </div>
              </div>

              {/* Extracted Artifacts & Volume Telemetry */}
              <div className="col-span-12 lg:col-span-7 bg-surface-container border border-outline-variant rounded-lg p-4 shadow-xs space-y-3">
                <div className="flex items-center justify-between border-b border-outline-variant pb-2">
                  <div className="flex items-center space-x-2">
                    <span className="material-symbols-outlined text-primary">analytics</span>
                    <h3 className="font-headline-sm text-headline-sm text-on-surface">Forensic Yield by App</h3>
                  </div>
                  <Link to={`/cases/${currentCase?.id}/metrics`} className="text-primary text-xs hover:underline">
                    View Full Metrics →
                  </Link>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="p-3 rounded bg-surface-container-low border border-outline-variant">
                    <div className="flex items-center justify-between text-xs text-on-surface-variant mb-1">
                      <span>WhatsApp</span>
                      <span className="material-symbols-outlined text-emerald-400 text-sm">chat</span>
                    </div>
                    <div className="text-xl font-bold font-mono text-on-surface">12,842</div>
                    <span className="text-[10px] text-tertiary">98.4% parsed · 208 corrupt</span>
                  </div>

                  <div className="p-3 rounded bg-surface-container-low border border-outline-variant">
                    <div className="flex items-center justify-between text-xs text-on-surface-variant mb-1">
                      <span>Telegram</span>
                      <span className="material-symbols-outlined text-blue-400 text-sm">send</span>
                    </div>
                    <div className="text-xl font-bold font-mono text-on-surface">7,893</div>
                    <span className="text-[10px] text-primary">cache4.db · 44 channels</span>
                  </div>

                  <div className="p-3 rounded bg-surface-container-low border border-outline-variant">
                    <div className="flex items-center justify-between text-xs text-on-surface-variant mb-1">
                      <span>Carved Residuals</span>
                      <span className="material-symbols-outlined text-amber-400 text-sm">restore</span>
                    </div>
                    <div className="text-xl font-bold font-mono text-amber-400">218</div>
                    <span className="text-[10px] text-on-surface-variant">Tier 1-3 · WAL frames</span>
                  </div>
                </div>

                {/* Quick Shortcuts to Case Modules */}
                <div className="pt-2 flex flex-wrap items-center gap-2">
                  <Link to={`/cases/${currentCase?.id}/messages`} className="btn-secondary text-xs">
                    <span className="material-symbols-outlined text-sm">chat</span>
                    <span>Messages</span>
                  </Link>
                  <Link to={`/cases/${currentCase?.id}/timeline`} className="btn-secondary text-xs">
                    <span className="material-symbols-outlined text-sm">schedule</span>
                    <span>Timeline</span>
                  </Link>
                  <Link to={`/cases/${currentCase?.id}/recovery`} className="btn-secondary text-xs">
                    <span className="material-symbols-outlined text-sm">restore</span>
                    <span>Recovery</span>
                  </Link>
                  <Link to={`/cases/${currentCase?.id}/correlations`} className="btn-secondary text-xs">
                    <span className="material-symbols-outlined text-sm">hub</span>
                    <span>Correlations</span>
                  </Link>
                  <Link to={`/cases/${currentCase?.id}/section63`} className="btn-secondary text-xs">
                    <span className="material-symbols-outlined text-sm">gavel</span>
                    <span>Section 63</span>
                  </Link>
                  <Link to={`/cases/${currentCase?.id}/reports`} className="btn-primary text-xs ml-auto">
                    <span className="material-symbols-outlined text-sm">description</span>
                    <span>Generate Court Report</span>
                  </Link>
                </div>
              </div>

              {/* Custodial Chain of Custody Log Card */}
              <div className="col-span-12 lg:col-span-5 bg-surface-container border border-outline-variant rounded-lg p-4 shadow-xs space-y-3">
                <div className="flex items-center justify-between border-b border-outline-variant pb-2">
                  <div className="flex items-center space-x-2">
                    <span className="material-symbols-outlined text-primary">history_edu</span>
                    <h3 className="font-headline-sm text-headline-sm text-on-surface">Recent Custody Events</h3>
                  </div>
                  <span className="text-[10px] font-mono text-outline">SEC-LEDGER</span>
                </div>

                <div className="space-y-2 max-h-[190px] overflow-y-auto custom-scrollbar pr-1 text-xs">
                  <div className="p-2 rounded bg-surface-container-low border border-outline-variant flex items-start space-x-2">
                    <span className="material-symbols-outlined text-tertiary text-sm mt-0.5">verified</span>
                    <div className="flex-1">
                      <div className="font-semibold text-on-surface flex justify-between">
                        <span>Re-verification passed</span>
                        <span className="text-[10px] font-mono text-outline">10:14 UTC</span>
                      </div>
                      <p className="text-on-surface-variant text-[11px]">All 7 physical blocks matched Merkle root.</p>
                    </div>
                  </div>

                  <div className="p-2 rounded bg-surface-container-low border border-outline-variant flex items-start space-x-2">
                    <span className="material-symbols-outlined text-primary text-sm mt-0.5">alt_route</span>
                    <div className="flex-1">
                      <div className="font-semibold text-on-surface flex justify-between">
                        <span>Pipeline completed</span>
                        <span className="text-[10px] font-mono text-outline">08:42 UTC</span>
                      </div>
                      <p className="text-on-surface-variant text-[11px]">Stage 1-6 finished with 98.4% parse rate.</p>
                    </div>
                  </div>

                  <div className="p-2 rounded bg-surface-container-low border border-outline-variant flex items-start space-x-2">
                    <span className="material-symbols-outlined text-blue-400 text-sm mt-0.5">upload</span>
                    <div className="flex-1">
                      <div className="font-semibold text-on-surface flex justify-between">
                        <span>Artifact ingested</span>
                        <span className="text-[10px] font-mono text-outline">08:35 UTC</span>
                      </div>
                      <p className="text-on-surface-variant text-[11px]">msgstore.db.crypt15 intake sealed.</p>
                    </div>
                  </div>
                </div>

                <div className="pt-1 border-t border-outline-variant flex justify-between items-center text-[11px]">
                  <span className="text-on-surface-variant font-mono">Signer: Node-04 ECDSA-P256</span>
                  <Link to={`/cases/${currentCase?.id}/integrity`} className="text-primary hover:underline">
                    View Ledger →
                  </Link>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
