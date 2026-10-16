import React, { useState } from 'react';
import { useActiveCase } from '../context/CaseContext';

const RECOVERED_RECORDS = [
  {
    id: 'rec-01',
    tier: 1,
    tierName: 'Tier 1: Explicit Deletion',
    status: 'Complete Reconstruction',
    sourceTable: 'messages (WhatsApp)',
    mechanism: 'Revocation / Edit Tombstone',
    confidence: 0.96,
    timestamp: '2026-03-30 08:14:02 UTC',
    sender: '+91 98765 43210',
    snippet: 'Target shipment leaving via Sector 4 gateway at 11:00. Clear security.',
    hexDump: '54 61 72 67 65 74 20 73 68 69 70 6d 65 6e 74 20 6c 65 61 76 69 6e 67 20 76 69 61 20 53 65 63 74 6f 72 20 34',
    walFrameNumber: 'Frame #142',
    offset: '0x00418A0'
  },
  {
    id: 'rec-02',
    tier: 1,
    tierName: 'Tier 1: Explicit Deletion',
    status: 'Complete Reconstruction',
    sourceTable: 'messages (WhatsApp)',
    mechanism: 'Message Revocation (Remote Delete)',
    confidence: 0.94,
    timestamp: '2026-03-30 07:55:10 UTC',
    sender: 'Target Subject',
    snippet: 'Transfer completed to wallet 0x71C...49b2. Wipe all cache.',
    hexDump: '54 72 61 6e 73 66 65 72 20 63 6f 6d 70 6c 65 74 65 64 20 74 6f 20 77 61 6c 6c 65 74 20 30 78 37 31 43',
    walFrameNumber: 'Frame #189',
    offset: '0x00422B0'
  },
  {
    id: 'rec-03',
    tier: 2,
    tierName: 'Tier 2: WAL History',
    status: 'Pre-checkpoint Frame Restored',
    sourceTable: 'cache4.db (Telegram)',
    mechanism: 'WAL Uncheckpointed Page #410',
    confidence: 0.89,
    timestamp: '2026-03-30 06:21:44 UTC',
    sender: '@falcon_lead',
    snippet: 'Encrypted payload backup key file staged on SD card path.',
    hexDump: '45 6e 63 72 79 70 74 65 64 20 70 61 79 6c 6f 61 64 20 62 61 63 6b 75 70 20 6b 65 79 20 66 69 6c 65',
    walFrameNumber: 'Frame #410',
    offset: '0x00891C0'
  },
  {
    id: 'rec-04',
    tier: 3,
    tierName: 'Tier 3: Freelist & Page Carving',
    status: 'Partial Payload Carved',
    sourceTable: 'messages (WhatsApp)',
    mechanism: 'Unallocated B-Tree Cell Carving',
    confidence: 0.76,
    timestamp: '2026-03-29 23:40:01 UTC',
    sender: 'Unknown JID Fragment',
    snippet: '...meet at coordinates 28.6139, 77.2090 before sunrise...',
    hexDump: '2e 2e 2e 6d 65 65 74 20 61 74 20 63 6f 6f 72 64 69 6e 61 74 65 73 20 32 38 2e 36 31 33 39',
    walFrameNumber: 'Page #892 B-Tree Cell',
    offset: '0x00F8210'
  },
  {
    id: 'rec-05',
    tier: 4,
    tierName: 'Tier 4: ID-Gap Indicators',
    status: 'Gap Heuristic Indicator',
    sourceTable: 'messages (WhatsApp)',
    mechanism: 'RowID Gap [84901..84919] Missing',
    confidence: 0.38,
    timestamp: '2026-03-29 22:10:00 UTC',
    sender: 'Sequential ID Gap Detected',
    snippet: '18 missing sequential records identified between rowid 84901 and 84920 indicating selective database purging.',
    hexDump: '00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00',
    walFrameNumber: 'Gap Detection',
    offset: 'N/A'
  }
];

export default function RecoveryPage() {
  const { activeCase } = useActiveCase();

  const [activeTier, setActiveTier] = useState(0); // 0 = all, 1, 2, 3, 4
  const [selectedRecord, setSelectedRecord] = useState(RECOVERED_RECORDS[0]);
  const [search, setSearch] = useState('');
  const [carvingRunning, setCarvingRunning] = useState(false);

  const filtered = RECOVERED_RECORDS.filter(r => {
    if (activeTier !== 0 && r.tier !== activeTier) return false;
    if (search && !r.snippet.toLowerCase().includes(search.toLowerCase()) && !r.sender.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const handleExecuteCarve = () => {
    setCarvingRunning(true);
    setTimeout(() => {
      setCarvingRunning(false);
    }, 800);
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden">
      {/* Top Section Header */}
      <div className="p-space-lg border-b border-outline-variant bg-surface-container space-y-3 shrink-0">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <h1 className="text-headline-lg font-headline-lg font-semibold text-on-surface">
              Artifact Recovery &amp; Residual Carving
            </h1>
            <p className="text-body-sm font-body-sm text-on-surface-variant mt-0.5">
              Excavation and reconstruction of deleted records, WAL uncheckpointed frames, and unallocated SQLite cells for case {activeCase?.caseNumber}.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={handleExecuteCarve}
              disabled={carvingRunning}
              className="btn-primary"
            >
              <span className="material-symbols-outlined text-sm">
                {carvingRunning ? 'sync' : 'play_arrow'}
              </span>
              <span>{carvingRunning ? 'Carving Unallocated Cells...' : 'Execute Deep Carve'}</span>
            </button>
            <button
              type="button"
              onClick={() => alert('Exporting forensic carved manifest...')}
              className="btn-secondary"
            >
              <span className="material-symbols-outlined text-sm">download</span>
              <span>Export Full Manifest</span>
            </button>
          </div>
        </div>

        {/* Critical Amber Callout Banner per Stitch design */}
        <div className="flex items-center space-x-2.5 px-3 py-2 rounded border border-amber-600/40 bg-amber-950/20 text-amber-200 text-body-sm">
          <span className="material-symbols-outlined text-base text-amber-400">warning</span>
          <span className="font-medium text-xs">
            Counts are shown per tier and are never summed across recovery mechanisms.
          </span>
        </div>

        {/* Four Tier Tabs with Counts */}
        <div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-1 text-xs">
            {/* Tier 1 */}
            <button
              type="button"
              onClick={() => setActiveTier(activeTier === 1 ? 0 : 1)}
              className={`flex flex-col p-2.5 rounded border text-left transition-colors ${
                activeTier === 1
                  ? 'border-primary bg-primary/10'
                  : 'border-outline-variant bg-surface-container-low hover:bg-surface-container-high'
              }`}
            >
              <div className="flex items-center justify-between w-full">
                <span className="font-label-ui font-semibold text-primary">Tier 1: Explicit Deletion</span>
                <span className="px-1.5 py-0.2 rounded font-mono text-[11px] font-bold bg-surface-container border border-primary text-primary">
                  42
                </span>
              </div>
              <span className="text-[11px] text-on-surface-variant mt-0.5">(Revocations, Edits)</span>
            </button>

            {/* Tier 2 */}
            <button
              type="button"
              onClick={() => setActiveTier(activeTier === 2 ? 0 : 2)}
              className={`flex flex-col p-2.5 rounded border text-left transition-colors ${
                activeTier === 2
                  ? 'border-primary bg-primary/10'
                  : 'border-outline-variant bg-surface-container-low hover:bg-surface-container-high'
              }`}
            >
              <div className="flex items-center justify-between w-full">
                <span className="font-label-ui font-semibold text-on-surface">Tier 2: WAL History</span>
                <span className="px-1.5 py-0.2 rounded font-mono text-[11px] font-bold bg-surface-container-highest border border-outline-variant text-on-surface">
                  114
                </span>
              </div>
              <span className="text-[11px] text-on-surface-variant mt-0.5">(Pre-checkpoint Frames)</span>
            </button>

            {/* Tier 3 */}
            <button
              type="button"
              onClick={() => setActiveTier(activeTier === 3 ? 0 : 3)}
              className={`flex flex-col p-2.5 rounded border text-left transition-colors ${
                activeTier === 3
                  ? 'border-primary bg-primary/10'
                  : 'border-outline-variant bg-surface-container-low hover:bg-surface-container-high'
              }`}
            >
              <div className="flex items-center justify-between w-full">
                <span className="font-label-ui font-semibold text-on-surface">Tier 3: Freelist Carving</span>
                <span className="px-1.5 py-0.2 rounded font-mono text-[11px] font-bold bg-surface-container-highest border border-outline-variant text-on-surface">
                  62
                </span>
              </div>
              <span className="text-[11px] text-on-surface-variant mt-0.5">(Unallocated B-Tree Cells)</span>
            </button>

            {/* Tier 4 */}
            <button
              type="button"
              onClick={() => setActiveTier(activeTier === 4 ? 0 : 4)}
              className={`flex flex-col p-2.5 rounded border text-left transition-colors ${
                activeTier === 4
                  ? 'border-primary bg-primary/10'
                  : 'border-dashed border-outline-variant bg-transparent opacity-80 hover:opacity-100'
              }`}
            >
              <div className="flex items-center justify-between w-full">
                <span className="font-label-ui text-outline">Tier 4: ID-Gap Indicators</span>
                <span className="px-1.5 py-0.2 rounded font-mono text-[11px] bg-surface-container-highest border border-outline-variant text-outline">
                  19
                </span>
              </div>
              <span className="text-[11px] text-outline mt-0.5">(Weak Hint Heuristics)</span>
            </button>
          </div>

          <p className="text-[11px] text-outline italic mt-1.5">
            * Records identical to live rows are listed for audit but excluded from active recovery counts.
          </p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="p-3 bg-surface-container-low border-b border-outline-variant flex items-center justify-between gap-3 shrink-0">
        <div className="relative flex-1 max-w-md">
          <span className="material-symbols-outlined absolute left-2.5 top-2 text-outline text-[16px]">
            search
          </span>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search recovered strings, hash, or JID..."
            className="w-full pl-8 pr-3 py-1.5 bg-surface-container-lowest border border-outline-variant rounded text-body-sm text-on-surface focus:outline-none focus:border-primary placeholder:text-outline"
          />
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-on-surface-variant">Showing:</span>
          <span className="font-mono text-primary font-semibold">{filtered.length} records</span>
          {activeTier !== 0 && (
            <button
              type="button"
              onClick={() => setActiveTier(0)}
              className="text-primary hover:underline text-xs"
            >
              (Clear filter)
            </button>
          )}
        </div>
      </div>

      {/* Center Table & Right Hex Inspector Split */}
      <div className="flex-1 flex overflow-hidden">
        {/* Table Area */}
        <div className="flex-1 overflow-y-auto custom-scrollbar border-r border-outline-variant">
          <table className="w-full text-left border-collapse text-body-sm font-body-sm">
            <thead>
              <tr className="bg-surface-container-lowest/80 border-b border-outline-variant h-8 text-label-ui font-label-ui text-on-surface-variant uppercase tracking-wider text-[11px] sticky top-0 z-10">
                <th className="py-2 px-3 w-10 text-center">#</th>
                <th className="py-2 px-3">Reconstruction Status &amp; Tier</th>
                <th className="py-2 px-3 w-36">Source Table</th>
                <th className="py-2 px-3 w-28 text-center">Confidence</th>
                <th className="py-2 px-3">Reconstructed Text / Residual Snippet</th>
                <th className="py-2 px-3 w-36">Timestamp (UTC)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/60 text-xs">
              {filtered.map((item, idx) => {
                const isSelected = selectedRecord?.id === item.id;
                return (
                  <tr
                    key={item.id}
                    onClick={() => setSelectedRecord(item)}
                    className={`hover:bg-surface-container-high/60 transition-colors cursor-pointer ${
                      isSelected ? 'bg-primary/10 border-l-2 border-primary' : ''
                    }`}
                  >
                    <td className="py-2.5 px-3 text-center font-mono text-outline">
                      {String(idx + 1).padStart(2, '0')}
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="font-semibold text-on-surface">{item.status}</div>
                      <span className="text-[10px] text-primary font-mono">{item.mechanism}</span>
                    </td>
                    <td className="py-2.5 px-3 text-on-surface font-mono">
                      {item.sourceTable}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <span className={`px-2 py-0.5 rounded font-mono text-[11px] font-semibold ${
                        item.confidence >= 0.8
                          ? 'bg-tertiary/10 text-tertiary border border-tertiary/30'
                          : item.confidence >= 0.5
                          ? 'bg-amber-500/10 text-amber-500 border border-amber-500/30'
                          : 'bg-surface-container text-outline border border-outline-variant'
                      }`}>
                        {(item.confidence * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-on-surface max-w-md truncate">
                      "{item.snippet}"
                    </td>
                    <td className="py-2.5 px-3 font-mono text-outline text-[11px]">
                      {item.timestamp}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Right Hex & Cell Fragment Inspector */}
        {selectedRecord && (
          <aside className="w-[360px] bg-surface-container border-l border-outline-variant flex flex-col justify-between overflow-y-auto custom-scrollbar p-4 space-y-4 shrink-0">
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-outline-variant">
                <span className="font-label-ui uppercase tracking-wider text-xs font-semibold text-outline">
                  Carved Cell Inspector
                </span>
                <span className="px-1.5 py-0.2 rounded bg-primary/20 text-primary text-[10px] font-mono">
                  {selectedRecord.id}
                </span>
              </div>

              {/* Provenance Details */}
              <div className="space-y-2 text-xs">
                <div className="text-label-ui uppercase tracking-wider text-outline font-semibold">
                  Carving Provenance
                </div>
                <div className="p-2.5 rounded bg-surface-container-low border border-outline-variant space-y-1.5 font-mono text-[11px]">
                  <div className="flex justify-between">
                    <span className="text-on-surface-variant">Tier Category:</span>
                    <span className="text-primary font-semibold">{selectedRecord.tierName}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-on-surface-variant">Frame / Page:</span>
                    <span className="text-on-surface">{selectedRecord.walFrameNumber}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-on-surface-variant">Sector Offset:</span>
                    <span className="text-primary">{selectedRecord.offset}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-on-surface-variant">Confidence:</span>
                    <span className="text-tertiary font-semibold">{(selectedRecord.confidence * 100).toFixed(0)}% (Heuristic Order)</span>
                  </div>
                </div>
              </div>

              {/* Raw Hex Dump View */}
              <div className="space-y-2 text-xs">
                <div className="text-label-ui uppercase tracking-wider text-outline font-semibold flex items-center justify-between">
                  <span>Carved Byte Dump (Hex)</span>
                  <button
                    type="button"
                    onClick={() => navigator.clipboard?.writeText(selectedRecord.hexDump)}
                    className="text-primary hover:underline font-mono text-[10px]"
                  >
                    Copy Bytes
                  </button>
                </div>
                <div className="p-2.5 rounded bg-surface-container-lowest border border-outline-variant font-mono text-[11px] text-primary break-all leading-relaxed select-all">
                  {selectedRecord.hexDump}
                </div>
              </div>

              {/* Reconstructed ASCII Text */}
              <div className="space-y-2 text-xs">
                <div className="text-label-ui uppercase tracking-wider text-outline font-semibold">
                  Reconstructed String Content
                </div>
                <div className="p-2.5 rounded bg-surface-container-lowest border border-outline-variant text-on-surface text-sm select-all">
                  "{selectedRecord.snippet}"
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-outline-variant">
              <button
                type="button"
                onClick={() => navigator.clipboard?.writeText(JSON.stringify(selectedRecord, null, 2))}
                className="btn-secondary w-full text-xs"
              >
                <span className="material-symbols-outlined text-[15px]">content_copy</span>
                <span>Copy Carved Artifact Record</span>
              </button>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
