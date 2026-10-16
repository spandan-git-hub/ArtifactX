import React, { useState } from 'react';
import { useActiveCase } from '../context/CaseContext';

export default function PipelinePage() {
  const { activeCase } = useActiveCase();

  // Subnav tabs: 'pipeline' | 'history' | 'quality'
  const [activeTab, setActiveTab] = useState('pipeline');
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [terminalLogs, setTerminalLogs] = useState([
    '[08:35:12.019 UTC] [INGEST] Stage 1 initialized. Verifying Merkle tree root for 7 artifacts...',
    '[08:35:12.230 UTC] [INGEST] SHA-256 root verified: c218f09d84e20791... [OK]',
    '[08:35:13.670 UTC] [MOUNT] ext4 volume Target_01.raw mounted loopback read-only at offset 0x0041F800 [OK]',
    '[08:35:17.801 UTC] [DECRYPT] WhatsApp crypt15 key derived via HKDF-SHA256 from KREF-WA-2026-01 [OK]',
    '[08:35:18.002 UTC] [DECRYPT] 182.4 MiB decrypted -> msgstore.decrypted.db [OK]',
    '[08:36:00.820 UTC] [PARSE] WhatsApp schema v15 initialized. 12,842 message rows indexed [OK]',
    '[08:37:12.910 UTC] [CARVE] SQLite WAL residual carver executed on unallocated space. 218 frames extracted [OK]',
    '[08:38:26.915 UTC] [CORRELATE] Cross-platform identity graph linked 28 phone numbers, 14 crypto wallets, 6 IBANs [OK]',
    '[08:38:27.102 UTC] [PIPELINE] Execution cycle completed in 3m 14s. Ledger Block #40921-X9 committed.'
  ]);

  const handleRunFullPipeline = () => {
    setPipelineRunning(true);
    setTerminalLogs(prev => [
      ...prev,
      `[${new Date().toISOString().substring(11, 23)} UTC] [START] Initiating full pipeline re-run for ${activeCase?.caseNumber}...`
    ]);

    setTimeout(() => {
      setTerminalLogs(prev => [
        ...prev,
        `[${new Date().toISOString().substring(11, 23)} UTC] [STAGE 1] Ingest integrity verified.`,
        `[${new Date().toISOString().substring(11, 23)} UTC] [STAGE 2] Enclave keys verified.`,
        `[${new Date().toISOString().substring(11, 23)} UTC] [STAGE 3] Re-parsed 20,735 database records (100%).`,
        `[${new Date().toISOString().substring(11, 23)} UTC] [SUCCESS] Pipeline cycle completed successfully.`
      ]);
      setPipelineRunning(false);
    }, 1200);
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden">
      {/* ================= SUB-NAVIGATION HEADER ================= */}
      <div className="h-10 px-6 border-b border-outline-variant bg-surface-container-low flex items-center justify-between shrink-0">
        <div className="flex items-center gap-6 h-full text-label-ui font-label-ui">
          <button
            type="button"
            onClick={() => setActiveTab('pipeline')}
            className={`h-full px-1 border-b-2 flex items-center gap-1.5 transition-colors ${
              activeTab === 'pipeline'
                ? 'border-primary text-primary font-semibold'
                : 'border-transparent text-on-surface-variant hover:text-on-surface'
            }`}
          >
            <span>Run Pipeline</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('history')}
            className={`h-full px-1 border-b-2 flex items-center gap-1.5 transition-colors ${
              activeTab === 'history'
                ? 'border-primary text-primary font-semibold'
                : 'border-transparent text-on-surface-variant hover:text-on-surface'
            }`}
          >
            <span>Run History</span>
            <span className="px-1.5 py-0.2 rounded text-[10px] font-label-mono-sm bg-primary/10 text-primary border border-primary/30">
              4 Active
            </span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('quality')}
            className={`h-full px-1 border-b-2 flex items-center gap-1.5 transition-colors ${
              activeTab === 'quality'
                ? 'border-primary text-primary font-semibold'
                : 'border-transparent text-on-surface-variant hover:text-on-surface'
            }`}
          >
            <span>Parse Quality</span>
            <span className="px-1.5 py-0.2 rounded-full bg-primary/20 text-primary text-[10px] border border-primary/40 font-mono">
              96.5%
            </span>
          </button>
        </div>

        <div className="hidden sm:flex items-center gap-3 text-label-mono-sm font-label-mono-sm text-on-surface-variant text-xs">
          <span>ENGINE: v4.8.2-rev9</span>
          <span className="w-2 h-2 rounded-full bg-tertiary" title="Online" />
          <span className="text-outline">|</span>
          <span>DURATION: 3m 42s</span>
          <span className="text-outline">|</span>
          <span className="text-primary font-semibold">SEC. 63 BSA COMPLIANT</span>
        </div>
      </div>

      {/* ================= TAB 1: RUN PIPELINE ================= */}
      {activeTab === 'pipeline' && (
        <div className="flex-1 flex overflow-hidden p-space-sm gap-space-sm">
          {/* LEFT COLUMN: CONFIGURATION & EVIDENCE MOUNT (340px) */}
          <div className="w-[340px] flex flex-col gap-space-sm shrink-0 overflow-y-auto custom-scrollbar pr-0.5">
            {/* Evidence Checklist Card */}
            <div className="bg-surface-container border border-outline-variant rounded-lg p-space-md flex flex-col gap-2.5 shadow-xs">
              <div className="flex items-center justify-between border-b border-outline-variant pb-2">
                <div className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-primary text-[16px]">checklist</span>
                  <span className="font-headline-sm text-headline-sm text-on-surface">Evidence Checklist</span>
                </div>
                <span className="text-[11px] font-label-mono-sm text-on-surface-variant">4/5 Mounted</span>
              </div>

              <div className="space-y-1.5 text-xs">
                <div className="flex items-center justify-between p-1.5 rounded bg-surface-container-low border border-outline-variant">
                  <label className="flex items-center gap-2 cursor-pointer truncate">
                    <input type="checkbox" defaultChecked className="rounded border-outline-variant text-primary" />
                    <span className="font-mono text-on-surface truncate">msgstore.db.crypt15</span>
                  </label>
                  <span className="text-[10px] font-mono text-tertiary">Verified</span>
                </div>

                <div className="flex items-center justify-between p-1.5 rounded bg-surface-container-low border border-outline-variant">
                  <label className="flex items-center gap-2 cursor-pointer truncate">
                    <input type="checkbox" defaultChecked className="rounded border-outline-variant text-primary" />
                    <span className="font-mono text-on-surface truncate">wa_unencrypted_dump</span>
                  </label>
                  <span className="text-[10px] font-mono text-tertiary">Verified</span>
                </div>

                <div className="flex items-center justify-between p-1.5 rounded bg-surface-container-low border border-outline-variant">
                  <label className="flex items-center gap-2 cursor-pointer truncate">
                    <input type="checkbox" defaultChecked className="rounded border-outline-variant text-primary" />
                    <span className="font-mono text-on-surface truncate">cache4.db (+wal)</span>
                  </label>
                  <span className="text-[10px] font-mono text-tertiary">Verified</span>
                </div>

                <div className="flex items-center justify-between p-1.5 rounded bg-surface-container-low border border-outline-variant">
                  <label className="flex items-center gap-2 cursor-pointer truncate">
                    <input type="checkbox" defaultChecked className="rounded border-outline-variant text-primary" />
                    <span className="font-mono text-on-surface truncate">media_attachments.zip</span>
                  </label>
                  <span className="text-[10px] font-mono text-tertiary">Verified</span>
                </div>

                <div className="flex items-center justify-between p-1.5 rounded bg-error/10 border border-error/30 text-error">
                  <label className="flex items-center gap-2 cursor-not-allowed truncate opacity-70">
                    <input type="checkbox" disabled className="rounded border-error text-error" />
                    <span className="font-mono line-through truncate">encrypted_backup.key</span>
                  </label>
                  <span className="text-[10px] font-mono">Mismatch</span>
                </div>
              </div>
            </div>

            {/* Keystore Binding Card */}
            <div className="bg-surface-container border border-outline-variant rounded-lg p-space-md flex flex-col gap-2 shadow-xs">
              <div className="flex items-center justify-between border-b border-outline-variant pb-1.5">
                <span className="text-label-ui font-label-ui text-on-surface uppercase tracking-wider text-xs">
                  Key Reference Binding
                </span>
                <span className="px-1.5 py-0.2 rounded text-[10px] font-label-mono-sm bg-primary/10 text-primary border border-primary/30">
                  Enclave Bound
                </span>
              </div>
              <div className="space-y-1">
                <label className="text-[11px] font-label-ui text-on-surface-variant">Active Keystore Reference</label>
                <select className="w-full bg-surface-container-low border border-outline-variant rounded px-2 py-1.5 font-label-mono-sm text-[11px] text-on-surface focus:outline-none focus:border-primary">
                  <option>KREF-WA-2026-01 (64-hex AES-256 deriv: 0x98A1...E41F)</option>
                  <option>KREF-TG-SYSTEM-2025-04 (Local Telegram KEK)</option>
                </select>
              </div>
              <div className="flex items-center gap-1.5 text-[11px] text-on-surface-variant bg-surface-container-high/40 p-1.5 rounded border border-outline-variant/50">
                <span className="material-symbols-outlined text-primary text-[14px]">lock</span>
                <span>Ephemeral RAM keys only. Wiped on exit.</span>
              </div>
            </div>

            {/* Rules & Thresholds */}
            <div className="bg-surface-container border border-outline-variant rounded-lg p-space-md flex flex-col gap-2 shadow-xs">
              <div className="border-b border-outline-variant pb-1.5 flex items-center justify-between">
                <span className="text-label-ui font-label-ui text-on-surface uppercase tracking-wider text-xs">
                  Confidence Thresholds
                </span>
                <span className="font-mono text-[10px] text-primary">v2.4-A</span>
              </div>
              <div className="grid grid-cols-2 gap-1.5 font-label-mono-sm text-[11px]">
                <div className="bg-surface-container-low p-1.5 rounded border border-outline-variant flex justify-between">
                  <span className="text-on-surface-variant">Deterministic:</span>
                  <span className="text-primary font-semibold">&gt;= 0.95</span>
                </div>
                <div className="bg-surface-container-low p-1.5 rounded border border-outline-variant flex justify-between">
                  <span className="text-on-surface-variant">Strong:</span>
                  <span className="text-primary font-semibold">&gt;= 0.80</span>
                </div>
                <div className="bg-surface-container-low p-1.5 rounded border border-outline-variant flex justify-between">
                  <span className="text-on-surface-variant">Moderate:</span>
                  <span className="text-amber-500 font-semibold">&gt;= 0.50</span>
                </div>
                <div className="bg-surface-container-low p-1.5 rounded border border-outline-variant flex justify-between">
                  <span className="text-on-surface-variant">Weak Hint:</span>
                  <span className="text-outline">&lt; 0.40</span>
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT COLUMN: STAGE CONTROLS & LIVE TERMINAL LOGS */}
          <div className="flex-1 flex flex-col min-w-0 bg-surface-container border border-outline-variant rounded-lg overflow-hidden shadow-xs">
            {/* Top Stepper Banner */}
            <div className="p-4 border-b border-outline-variant bg-surface-container-low flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h2 className="text-headline-sm font-headline-sm text-on-surface font-semibold">
                  Forensic Pipeline Stage Runner
                </h2>
                <p className="text-body-sm text-on-surface-variant">
                  Sequential deterministic evidence transformation, parsing, carving &amp; entity correlation.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleRunFullPipeline}
                  disabled={pipelineRunning}
                  className="btn-primary"
                >
                  <span className="material-symbols-outlined text-[16px]">
                    {pipelineRunning ? 'sync' : 'play_arrow'}
                  </span>
                  <span>{pipelineRunning ? 'Executing Stage...' : 'Execute Full Pipeline'}</span>
                </button>
              </div>
            </div>

            {/* Stepper Progress Visualizer */}
            <div className="p-4 border-b border-outline-variant bg-surface-container/50">
              <div className="grid grid-cols-2 md:grid-cols-6 gap-2 text-center text-xs">
                <div className="p-2 rounded bg-tertiary/10 border border-tertiary/30">
                  <div className="font-semibold text-tertiary flex items-center justify-center gap-1">
                    <span className="material-symbols-outlined text-sm">check_circle</span>
                    <span>1. Ingest</span>
                  </div>
                  <span className="text-[10px] text-on-surface-variant">0.2s · 7 Files</span>
                </div>

                <div className="p-2 rounded bg-tertiary/10 border border-tertiary/30">
                  <div className="font-semibold text-tertiary flex items-center justify-center gap-1">
                    <span className="material-symbols-outlined text-sm">check_circle</span>
                    <span>2. Mount</span>
                  </div>
                  <span className="text-[10px] text-on-surface-variant">1.4s · ext4 RO</span>
                </div>

                <div className="p-2 rounded bg-tertiary/10 border border-tertiary/30">
                  <div className="font-semibold text-tertiary flex items-center justify-center gap-1">
                    <span className="material-symbols-outlined text-sm">check_circle</span>
                    <span>3. Decrypt</span>
                  </div>
                  <span className="text-[10px] text-on-surface-variant">4.1s · AES-GCM</span>
                </div>

                <div className="p-2 rounded bg-tertiary/10 border border-tertiary/30">
                  <div className="font-semibold text-tertiary flex items-center justify-center gap-1">
                    <span className="material-symbols-outlined text-sm">check_circle</span>
                    <span>4. Parse</span>
                  </div>
                  <span className="text-[10px] text-on-surface-variant">42.8s · 20.7k rec</span>
                </div>

                <div className="p-2 rounded bg-tertiary/10 border border-tertiary/30">
                  <div className="font-semibold text-tertiary flex items-center justify-center gap-1">
                    <span className="material-symbols-outlined text-sm">check_circle</span>
                    <span>5. Carve</span>
                  </div>
                  <span className="text-[10px] text-on-surface-variant">1m 12s · WAL 218</span>
                </div>

                <div className="p-2 rounded bg-tertiary/10 border border-tertiary/30">
                  <div className="font-semibold text-tertiary flex items-center justify-center gap-1">
                    <span className="material-symbols-outlined text-sm">check_circle</span>
                    <span>6. Correlate</span>
                  </div>
                  <span className="text-[10px] text-on-surface-variant">1m 14s · 7 Entities</span>
                </div>
              </div>
            </div>

            {/* Live Terminal Stream */}
            <div className="flex-1 flex flex-col min-h-0 bg-surface-container-lowest p-3 font-mono text-xs overflow-hidden">
              <div className="flex items-center justify-between pb-2 border-b border-outline-variant text-[11px] text-outline mb-2">
                <span className="flex items-center gap-1.5 text-primary">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                  LIVE EXECUTION OUTPUT STREAM
                </span>
                <button
                  type="button"
                  onClick={() => setTerminalLogs([])}
                  className="hover:underline"
                >
                  Clear Console
                </button>
              </div>

              <div className="flex-1 overflow-y-auto custom-scrollbar space-y-1 text-on-surface select-text">
                {terminalLogs.map((line, idx) => (
                  <div key={idx} className="leading-relaxed">
                    {line.includes('[OK]') ? (
                      <span className="text-tertiary">{line}</span>
                    ) : line.includes('[ERROR]') || line.includes('Mismatch') ? (
                      <span className="text-error">{line}</span>
                    ) : (
                      <span className="text-on-surface-variant">{line}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ================= TAB 2: RUN HISTORY ================= */}
      {activeTab === 'history' && (
        <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-4">
          {/* Prominent Refused Run Banner */}
          <div className="bg-surface-container border border-error rounded-lg p-4 relative overflow-hidden bg-gradient-to-r from-error/15 via-surface-container to-surface-container">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded bg-error/20 border border-error/40 flex items-center justify-center shrink-0 text-error">
                  <span className="material-symbols-outlined text-[20px]">block</span>
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-headline-sm font-headline-sm text-on-surface font-semibold">
                      PIPELINE RUN REFUSED (Run #RUN-2026-042) — Evidence Integrity Failure
                    </h3>
                    <span className="px-2 py-0.5 rounded text-[11px] font-label-ui font-semibold bg-error/20 text-error border border-error">
                      CRITICAL REFUSAL
                    </span>
                  </div>
                  <p className="text-body-sm text-on-surface-variant max-w-4xl leading-relaxed">
                    Pre-execution integrity gate failed. Artifact <span className="font-mono text-on-surface bg-surface-container-lowest px-1 py-0.5 rounded border border-outline-variant">encrypted_backup.key</span> did not match acquisition manifest hash. Execution halted to prevent unverified contamination of Section 63 forensic ledger. Zero derived artifacts staged.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button type="button" className="btn-secondary text-xs">
                  Inspect Refusal Log
                </button>
              </div>
            </div>
          </div>

          {/* Historical Runs Table */}
          <div className="bg-surface-container border border-outline-variant rounded-lg overflow-hidden shadow-xs">
            <div className="p-3 border-b border-outline-variant flex items-center justify-between">
              <h3 className="font-headline-sm text-headline-sm text-on-surface font-semibold">
                Historical Execution Cycles
              </h3>
              <span className="text-[11px] font-mono text-outline">4 Runs Recorded</span>
            </div>

            <table className="w-full text-left border-collapse text-body-sm font-body-sm">
              <thead>
                <tr className="bg-surface-container-lowest/80 border-b border-outline-variant h-8 text-label-ui font-label-ui text-on-surface-variant uppercase tracking-wider text-[11px]">
                  <th className="py-2.5 px-3">Run ID</th>
                  <th className="py-2.5 px-3">Trigger / Operator</th>
                  <th className="py-2.5 px-3">Duration</th>
                  <th className="py-2.5 px-3">Stages Completed</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Ledger Commit</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/60 font-label-mono-sm text-xs">
                <tr className="hover:bg-surface-container-high/40">
                  <td className="py-3 px-3 font-semibold text-primary">RUN-2026-041</td>
                  <td className="py-3 px-3 text-on-surface">A. Verma (Manual Re-run)</td>
                  <td className="py-3 px-3 text-on-surface-variant">3m 14s</td>
                  <td className="py-3 px-3 text-on-surface">6/6 Stages (Complete)</td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded bg-tertiary/10 text-tertiary border border-tertiary/30">
                      SUCCESS
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right text-outline">Block #40921-X9</td>
                </tr>

                <tr className="hover:bg-surface-container-high/40 bg-error/5">
                  <td className="py-3 px-3 font-semibold text-error">RUN-2026-042</td>
                  <td className="py-3 px-3 text-on-surface">System Intake Auto-Gate</td>
                  <td className="py-3 px-3 text-on-surface-variant">0.12s</td>
                  <td className="py-3 px-3 text-error">0/6 Stages (Halted at Ingest)</td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded bg-error/20 text-error border border-error">
                      REFUSED
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right text-error font-medium">Exception #40921-E</td>
                </tr>

                <tr className="hover:bg-surface-container-high/40">
                  <td className="py-3 px-3 font-semibold text-primary">RUN-2026-040</td>
                  <td className="py-3 px-3 text-on-surface">A. Verma (Decryption Test)</td>
                  <td className="py-3 px-3 text-on-surface-variant">42.1s</td>
                  <td className="py-3 px-3 text-on-surface">3/6 Stages (Decrypted)</td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded bg-tertiary/10 text-tertiary border border-tertiary/30">
                      SUCCESS
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right text-outline">Block #40918-A2</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ================= TAB 3: PARSE QUALITY ================= */}
      {activeTab === 'quality' && (
        <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-5">
          <div className="bg-surface-container border border-outline-variant rounded-lg p-5 shadow-xs space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary">query_stats</span>
                  <h2 className="text-headline-sm font-headline-sm text-on-surface font-semibold">
                    Table Extraction &amp; Parsing Quality
                  </h2>
                </div>
                <p className="text-body-sm text-on-surface-variant mt-0.5">
                  Heuristic comparison of discovered database rows versus fully parsed forensic indicators across mounted partitions.
                </p>
              </div>

              <div className="flex items-center gap-2 px-3 py-1 bg-primary/10 border border-primary/30 rounded text-primary text-label-ui">
                <span className="w-2 h-2 rounded-full bg-primary" />
                <span>GLOBAL PARSE RATE: 96.5%</span>
              </div>
            </div>

            {/* Stacked Bars */}
            <div className="space-y-4 pt-2">
              <div className="space-y-1">
                <div className="flex items-center justify-between text-body-sm font-mono text-xs">
                  <span className="text-on-surface font-semibold">messages (WhatsApp msgstore.db)</span>
                  <span className="text-primary">12,842 parsed (98.4%) / 208 unparsed (1.6%)</span>
                </div>
                <div className="w-full h-3 rounded bg-surface-container-lowest overflow-hidden flex border border-outline-variant">
                  <div className="h-full bg-primary" style={{ width: '98.4%' }} />
                  <div className="h-full bg-amber-500" style={{ width: '1.6%' }} />
                </div>
              </div>

              <div className="space-y-1">
                <div className="flex items-center justify-between text-body-sm font-mono text-xs">
                  <span className="text-on-surface font-semibold">dialogs / channels (Telegram cache4.db)</span>
                  <span className="text-primary">7,893 parsed (97.8%) / 178 unparsed (2.2%)</span>
                </div>
                <div className="w-full h-3 rounded bg-surface-container-lowest overflow-hidden flex border border-outline-variant">
                  <div className="h-full bg-primary" style={{ width: '97.8%' }} />
                  <div className="h-full bg-amber-500" style={{ width: '2.2%' }} />
                </div>
              </div>

              <div className="space-y-1">
                <div className="flex items-center justify-between text-body-sm font-mono text-xs">
                  <span className="text-on-surface font-semibold">messages_quotes (Quoted context)</span>
                  <span className="text-primary">3,410 parsed (95.1%) / 176 unparsed (4.9%)</span>
                </div>
                <div className="w-full h-3 rounded bg-surface-container-lowest overflow-hidden flex border border-outline-variant">
                  <div className="h-full bg-primary" style={{ width: '95.1%' }} />
                  <div className="h-full bg-amber-500" style={{ width: '4.9%' }} />
                </div>
              </div>

              <div className="space-y-1">
                <div className="flex items-center justify-between text-body-sm font-mono text-xs">
                  <span className="text-on-surface font-semibold">wa_vnames (Contact Display Names)</span>
                  <span className="text-primary">1,120 parsed (99.2%) / 9 unparsed (0.8%)</span>
                </div>
                <div className="w-full h-3 rounded bg-surface-container-lowest overflow-hidden flex border border-outline-variant">
                  <div className="h-full bg-primary" style={{ width: '99.2%' }} />
                  <div className="h-full bg-amber-500" style={{ width: '0.8%' }} />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
