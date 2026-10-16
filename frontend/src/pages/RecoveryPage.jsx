import React, { useState, useEffect, useCallback } from 'react';
import { useActiveCase } from '../context/CaseContext';
import { recoveryService } from '../services/recoveryService';

export default function RecoveryPage() {
  const { activeCase } = useActiveCase();
  const caseId = activeCase?.id;

  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTier, setActiveTier] = useState(0); // 0 = all, 1, 2, 3, 4
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [search, setSearch] = useState('');
  const [carvingRunning, setCarvingRunning] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const loadFindings = useCallback(async () => {
    if (!caseId) {
      setRecords([]);
      setSelectedRecord(null);
      return;
    }
    setLoading(true);
    setErrorMessage(null);
    try {
      const data = await recoveryService.getRecoveryFindings(caseId);
      const findings = Array.isArray(data) ? data : (data?.findings || []);
      // Map API fields if necessary to match display properties
      const mapped = findings.map((f, i) => ({
        id: f.id || `rec-${i}`,
        tier: f.tier || f.recovery_tier || 1,
        tierName: f.tier_name || `Tier ${f.tier || f.recovery_tier || 1}`,
        status: f.status || 'Carved Payload',
        sourceTable: f.source_table || f.source || 'SQLite Table',
        mechanism: f.mechanism || f.carving_method || 'Unallocated B-Tree Cell',
        confidence: f.confidence || f.confidence_score || 0.85,
        timestamp: f.timestamp || f.recovered_at || 'N/A',
        sender: f.sender || f.actor || 'Recovered Fragment',
        snippet: f.snippet || f.content || f.payload_text || '[Raw Carved Frame]',
        hexDump: f.hex_dump || f.hexDump || '',
        walFrameNumber: f.wal_frame_number || f.frame_id || 'Cell',
        offset: f.offset || f.byte_offset || '0x0000'
      }));
      setRecords(mapped);
      if (mapped.length > 0) {
        setSelectedRecord(prev => prev ? mapped.find(m => m.id === prev.id) || mapped[0] : mapped[0]);
      } else {
        setSelectedRecord(null);
      }
    } catch (err) {
      console.warn('Error fetching recovery findings:', err);
      setRecords([]);
      setSelectedRecord(null);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    loadFindings();
  }, [loadFindings]);

  const handleExecuteCarve = async () => {
    if (!caseId) return;
    setCarvingRunning(true);
    setErrorMessage(null);
    try {
      await recoveryService.runRecovery(caseId);
      await loadFindings();
    } catch (err) {
      console.error('Carving execution error:', err);
      setErrorMessage(err.response?.data?.detail || err.message || 'SQLite carving run failed.');
    } finally {
      setCarvingRunning(false);
    }
  };

  const tier1Count = records.filter(r => r.tier === 1).length;
  const tier2Count = records.filter(r => r.tier === 2).length;
  const tier3Count = records.filter(r => r.tier === 3).length;
  const tier4Count = records.filter(r => r.tier === 4).length;

  const filtered = records.filter(r => {
    if (activeTier !== 0 && r.tier !== activeTier) return false;
    if (search && !r.snippet.toLowerCase().includes(search.toLowerCase()) && !r.sender.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

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
              Excavation and reconstruction of deleted records, WAL uncheckpointed frames, and unallocated SQLite cells for case {activeCase?.caseNumber || 'N/A'}.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={handleExecuteCarve}
              disabled={carvingRunning || !caseId}
              className="btn-primary"
            >
              <span className={`material-symbols-outlined text-sm ${carvingRunning ? 'animate-spin' : ''}`}>
                {carvingRunning ? 'sync' : 'play_arrow'}
              </span>
              <span>{carvingRunning ? 'Carving Unallocated Cells...' : 'Execute Deep Carve'}</span>
            </button>
          </div>
        </div>

        {errorMessage && (
          <div className="p-2.5 bg-error/15 border border-error/40 rounded text-error text-xs font-mono">
            {errorMessage}
          </div>
        )}

        {/* Amber Callout Banner */}
        <div className="flex items-center space-x-2.5 px-3 py-2 rounded border border-amber-600/40 bg-amber-950/20 text-amber-200 text-body-sm">
          <span className="material-symbols-outlined text-base text-amber-400">warning</span>
          <span className="font-medium text-xs">
            Counts are derived from real carved database cells and are never summed across differing recovery mechanisms.
          </span>
        </div>

        {/* Four Tier Tabs with Real Dynamic Counts */}
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
                  {tier1Count}
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
                  {tier2Count}
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
                  {tier3Count}
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
                  {tier4Count}
                </span>
              </div>
              <span className="text-[11px] text-outline mt-0.5">(Weak Hint Heuristics)</span>
            </button>
          </div>
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

      {/* Main Split Layout: Records List & Detail Hex Dump Inspector */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left List */}
        <div className="w-1/2 border-r border-outline-variant overflow-y-auto custom-scrollbar p-3 space-y-2">
          {loading && (
            <div className="py-12 text-center text-on-surface-variant font-mono text-xs">
              <span className="material-symbols-outlined text-2xl animate-spin text-primary mb-1">sync</span>
              <p>Scanning unallocated space for carved structures...</p>
            </div>
          )}

          {!loading && filtered.length === 0 && (
            <div className="py-16 text-center text-on-surface-variant border border-dashed border-outline-variant rounded bg-surface-container-low p-6">
              <span className="material-symbols-outlined text-3xl text-outline mb-2">restore</span>
              <p className="text-body-sm font-medium">No Carved Records Found</p>
              <p className="text-[11px] text-outline mt-1 mb-3">
                Execute deep carving to scan WAL history, freelist blocks, and unallocated cells.
              </p>
              {caseId && (
                <button
                  type="button"
                  onClick={handleExecuteCarve}
                  disabled={carvingRunning}
                  className="btn-primary text-xs"
                >
                  Carve Cells Now
                </button>
              )}
            </div>
          )}

          {!loading && filtered.map((r) => {
            const isSelected = selectedRecord?.id === r.id;
            return (
              <div
                key={r.id}
                onClick={() => setSelectedRecord(r)}
                className={`p-3 rounded border text-left transition-all cursor-pointer space-y-1.5 ${
                  isSelected
                    ? 'border-primary bg-primary/10 shadow-sm'
                    : 'border-outline-variant bg-surface-container hover:bg-surface-container-high'
                }`}
              >
                <div className="flex items-center justify-between text-[11px]">
                  <span className={`px-1.5 py-0.2 rounded font-mono font-medium ${
                    r.tier === 1 ? 'bg-primary/20 text-primary border border-primary/30' :
                    r.tier === 2 ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
                    r.tier === 3 ? 'bg-orange-500/20 text-orange-300 border border-orange-500/30' :
                    'bg-surface-container-highest text-outline border border-outline-variant'
                  }`}>
                    {r.tierName}
                  </span>
                  <span className="font-mono text-outline">{r.timestamp}</span>
                </div>

                <div className="text-body-sm font-semibold text-on-surface truncate">
                  {r.sender}
                </div>

                <p className="text-body-sm text-on-surface-variant line-clamp-2 select-text font-sans">
                  {r.snippet}
                </p>

                <div className="pt-1 flex items-center justify-between text-[10px] font-mono text-outline border-t border-outline-variant/40">
                  <span>{r.sourceTable}</span>
                  <span>Confidence: {(r.confidence * 100).toFixed(0)}%</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right Detail & Hex Inspector */}
        <div className="w-1/2 overflow-y-auto custom-scrollbar p-space-lg bg-surface-container-low space-y-4">
          {selectedRecord ? (
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between">
                  <span className="font-label-mono-sm text-primary text-xs">{selectedRecord.tierName}</span>
                  <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-surface-container border border-outline-variant text-on-surface">
                    Confidence: {(selectedRecord.confidence * 100).toFixed(1)}%
                  </span>
                </div>
                <h3 className="text-headline-md font-semibold text-on-surface mt-1">
                  {selectedRecord.sender}
                </h3>
              </div>

              <div className="p-3 bg-surface-container rounded border border-outline-variant space-y-1">
                <div className="text-[10px] font-mono text-outline uppercase tracking-wider">RECONSTRUCTED PAYLOAD</div>
                <div className="text-body-sm text-on-surface select-text">{selectedRecord.snippet}</div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 rounded bg-surface-container border border-outline-variant">
                  <span className="text-outline uppercase text-[10px] block font-mono">Mechanism</span>
                  <span className="font-mono text-on-surface">{selectedRecord.mechanism}</span>
                </div>
                <div className="p-2.5 rounded bg-surface-container border border-outline-variant">
                  <span className="text-outline uppercase text-[10px] block font-mono">WAL / Frame</span>
                  <span className="font-mono text-on-surface">{selectedRecord.walFrameNumber}</span>
                </div>
                <div className="p-2.5 rounded bg-surface-container border border-outline-variant">
                  <span className="text-outline uppercase text-[10px] block font-mono">Offset</span>
                  <span className="font-mono text-on-surface">{selectedRecord.offset}</span>
                </div>
                <div className="p-2.5 rounded bg-surface-container border border-outline-variant">
                  <span className="text-outline uppercase text-[10px] block font-mono">Timestamp</span>
                  <span className="font-mono text-on-surface">{selectedRecord.timestamp}</span>
                </div>
              </div>

              {selectedRecord.hexDump && (
                <div className="space-y-1.5">
                  <div className="text-[10px] font-mono text-outline uppercase tracking-wider">HEX PAYLOAD DUMP</div>
                  <pre className="p-3 bg-surface-container-lowest border border-outline-variant rounded font-mono text-[11px] text-tertiary overflow-x-auto">
                    {selectedRecord.hexDump}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-on-surface-variant font-mono text-xs">
              Select a carved record from the left queue to inspect raw payload and provenance.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
