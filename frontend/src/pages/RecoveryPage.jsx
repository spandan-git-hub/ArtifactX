import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useActiveCase } from '../context/CaseContext';
import { recoveryService } from '../services/recoveryService';

export default function RecoveryPage() {
  const { activeCase } = useActiveCase();
  const caseId = activeCase?.id;

  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTier, setActiveTier] = useState(0); // 0 = All, 1, 2, 3, 4
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [search, setSearch] = useState('');
  const [appFilter, setAppFilter] = useState('all');
  const [strengthFilter, setStrengthFilter] = useState('all');
  const [carvingRunning, setCarvingRunning] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [statusMessage, setStatusMessage] = useState(null);

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

      const mapped = findings.map((f, i) => {
        const tier = f.tier || (f.kind in { revocation: 1, edit: 1 } ? 1 : (f.method === 'wal' ? 2 : (f.kind === 'id_gap' ? 4 : 3)));
        const tierNames = {
          1: 'Tier 1: Explicit Deletion',
          2: 'Tier 2: WAL History',
          3: 'Tier 3: Freelist & Slack Carving',
          4: 'Tier 4: Sequence Gap Indicator',
        };
        const strength = f.strength || 'unassessed';
        const confidence = f.confidence_score !== undefined && f.confidence_score !== null
          ? f.confidence_score
          : null;

        return {
          id: f.id || `rec-${i}`,
          tier,
          tierName: tierNames[tier] || `Tier ${tier}`,
          kind: f.kind || f.method || 'carved',
          sourceApp: f.source_app || (f.table_name?.includes('tg') ? 'telegram' : 'whatsapp'),
          sourceTable: f.table_name || 'SQLite Table',
          mechanism: f.method || (tier === 1 ? 'Message Revocation' : (tier === 2 ? 'WAL Pre-Checkpoint Frame' : (tier === 3 ? 'Unallocated Slack Carving' : 'Sequence Continuity Gap'))),
          confidence,
          strength,
          timestamp: f.timestamp ? (new Date(typeof f.timestamp === 'number' && f.timestamp > 100000000000 ? f.timestamp : f.timestamp * 1000).toISOString().replace('T', ' ').substring(0, 19) + ' UTC') : 'Recorded in artifact',
          sender: f.sender_id || f.chat_id || 'Recovered Fragment',
          chatId: f.chat_id || '—',
          snippet: f.candidate_original_text || f.body || f.raw_payload_preview || '[Carved cell payload]',
          hexDump: f.raw_payload_preview || f.hex_dump || '',
          walFrameNumber: f.frame_index ? `Frame #${f.frame_index}` : (f.page_number ? `Page #${f.page_number}` : 'Slack Cell'),
          offset: f.byte_offset ? `0x${f.byte_offset.toString(16).toUpperCase()}` : '0x0000',
          hash: f.raw_payload_hash || '',
          validationStatus: f.validation_status || 'CANDIDATE',
          limitations: Array.isArray(f.limitations) ? f.limitations : [],
        };
      });

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
    setStatusMessage(null);
    try {
      const res = await recoveryService.runRecovery(caseId);
      await loadFindings();
      setStatusMessage(`Physical carving completed! Analyzed WAL pages, freelist blocks, and slack spans. Recovered findings populated.`);
      setTimeout(() => setStatusMessage(null), 6000);
    } catch (err) {
      console.error('Carving execution error:', err);
      setErrorMessage(err.response?.data?.detail || err.message || 'SQLite physical carving run failed.');
    } finally {
      setCarvingRunning(false);
    }
  };

  // Tier Counts
  const tier1Count = useMemo(() => records.filter(r => r.tier === 1).length, [records]);
  const tier2Count = useMemo(() => records.filter(r => r.tier === 2).length, [records]);
  const tier3Count = useMemo(() => records.filter(r => r.tier === 3).length, [records]);
  const tier4Count = useMemo(() => records.filter(r => r.tier === 4).length, [records]);

  // Filtered records
  const filtered = useMemo(() => {
    return records.filter(r => {
      if (activeTier !== 0 && r.tier !== activeTier) return false;
      if (appFilter !== 'all' && r.sourceApp.toLowerCase() !== appFilter.toLowerCase()) return false;
      if (strengthFilter !== 'all' && r.strength.toLowerCase() !== strengthFilter.toLowerCase()) return false;
      if (search.trim()) {
        const term = search.toLowerCase();
        const snippet = r.snippet.toLowerCase();
        const sender = r.sender.toLowerCase();
        const table = r.sourceTable.toLowerCase();
        const hash = r.hash.toLowerCase();
        if (!snippet.includes(term) && !sender.includes(term) && !table.includes(term) && !hash.includes(term)) {
          return false;
        }
      }
      return true;
    });
  }, [records, activeTier, appFilter, strengthFilter, search]);

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden">
      {/* Top Section Header */}
      <div className="p-space-lg border-b border-outline-variant bg-surface-container space-y-3 shrink-0">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-headline-lg font-headline-lg font-semibold text-on-surface flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-2xl">restore</span>
                Deleted Data Recovery &amp; Physical Carving
              </h1>
              {records.length > 0 && (
                <span className="px-2 py-0.5 rounded text-xs font-mono font-medium bg-tertiary/10 text-tertiary border border-tertiary/30">
                  {records.length} Residual Findings
                </span>
              )}
            </div>
            <p className="text-body-sm font-body-sm text-on-surface-variant mt-0.5">
              Excavation and 4-tier classification of deleted messages, uncheckpointed WAL frames, and unallocated SQLite cells for Case {activeCase?.caseNumber || 'N/A'}.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={handleExecuteCarve}
              disabled={carvingRunning || !caseId}
              className="btn-primary flex items-center gap-1.5 text-xs h-8"
            >
              <span className={`material-symbols-outlined text-sm ${carvingRunning ? 'animate-spin' : ''}`}>
                {carvingRunning ? 'sync' : 'search_check'}
              </span>
              <span>{carvingRunning ? 'Carving Unallocated Cells...' : 'Execute Deep Carve'}</span>
            </button>
          </div>
        </div>

        {statusMessage && (
          <div className="p-2.5 bg-emerald-500/15 border border-emerald-500/40 rounded text-emerald-300 text-xs font-mono flex items-center justify-between">
            <span>{statusMessage}</span>
            <button type="button" onClick={() => setStatusMessage(null)} className="hover:underline">✕</button>
          </div>
        )}

        {errorMessage && (
          <div className="p-2.5 bg-error/15 border border-error/40 rounded text-error text-xs font-mono">
            {errorMessage}
          </div>
        )}

        {/* 4 Different Tiers Classification Dashboard */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 pt-1 text-xs">
          {/* Tier 1: Explicit Deletion */}
          <button
            type="button"
            onClick={() => setActiveTier(activeTier === 1 ? 0 : 1)}
            className={`flex flex-col p-3 rounded-lg border text-left transition-all cursor-pointer ${
              activeTier === 1
                ? 'border-emerald-500 bg-emerald-500/15 shadow-sm'
                : 'border-outline-variant bg-surface-container-low hover:bg-surface-container-high'
            }`}
          >
            <div className="flex items-center justify-between w-full">
              <span className="font-label-ui font-bold text-emerald-400 flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px]">verified</span>
                Tier 1: Explicit Deletion
              </span>
              <span className="px-2 py-0.5 rounded font-mono text-[11px] font-bold bg-surface-container border border-emerald-500/50 text-emerald-300">
                {tier1Count}
              </span>
            </div>
            <span className="text-[11px] text-on-surface-variant mt-1">
              Revocations, tombstones &amp; edit history
            </span>
            <span className="text-[10px] font-mono text-emerald-400 font-medium mt-0.5">
              Deterministic 100% Certainty
            </span>
          </button>

          {/* Tier 2: WAL History */}
          <button
            type="button"
            onClick={() => setActiveTier(activeTier === 2 ? 0 : 2)}
            className={`flex flex-col p-3 rounded-lg border text-left transition-all cursor-pointer ${
              activeTier === 2
                ? 'border-cyan-500 bg-cyan-500/15 shadow-sm'
                : 'border-outline-variant bg-surface-container-low hover:bg-surface-container-high'
            }`}
          >
            <div className="flex items-center justify-between w-full">
              <span className="font-label-ui font-bold text-cyan-400 flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px]">history</span>
                Tier 2: WAL History
              </span>
              <span className="px-2 py-0.5 rounded font-mono text-[11px] font-bold bg-surface-container border border-cyan-500/50 text-cyan-300">
                {tier2Count}
              </span>
            </div>
            <span className="text-[11px] text-on-surface-variant mt-1">
              Uncheckpointed write-ahead frames
            </span>
            <span className="text-[10px] font-mono text-cyan-400 font-medium mt-0.5">
              High Confidence (90% - 99%)
            </span>
          </button>

          {/* Tier 3: Freelist & Slack Carving */}
          <button
            type="button"
            onClick={() => setActiveTier(activeTier === 3 ? 0 : 3)}
            className={`flex flex-col p-3 rounded-lg border text-left transition-all cursor-pointer ${
              activeTier === 3
                ? 'border-amber-500 bg-amber-500/15 shadow-sm'
                : 'border-outline-variant bg-surface-container-low hover:bg-surface-container-high'
            }`}
          >
            <div className="flex items-center justify-between w-full">
              <span className="font-label-ui font-bold text-amber-400 flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px]">memory</span>
                Tier 3: Freelist Carving
              </span>
              <span className="px-2 py-0.5 rounded font-mono text-[11px] font-bold bg-surface-container border border-amber-500/50 text-amber-300">
                {tier3Count}
              </span>
            </div>
            <span className="text-[11px] text-on-surface-variant mt-1">
              Unallocated B-Tree cells &amp; slack space
            </span>
            <span className="text-[10px] font-mono text-amber-400 font-medium mt-0.5">
              Strong Carved (75% - 90%)
            </span>
          </button>

          {/* Tier 4: Sequence Gap Indicators */}
          <button
            type="button"
            onClick={() => setActiveTier(activeTier === 4 ? 0 : 4)}
            className={`flex flex-col p-3 rounded-lg border text-left transition-all cursor-pointer ${
              activeTier === 4
                ? 'border-rose-500 bg-rose-500/15 shadow-sm'
                : 'border-outline-variant bg-surface-container-low hover:bg-surface-container-high'
            }`}
          >
            <div className="flex items-center justify-between w-full">
              <span className="font-label-ui font-bold text-rose-400 flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px]">timelapse</span>
                Tier 4: Sequence Gaps
              </span>
              <span className="px-2 py-0.5 rounded font-mono text-[11px] font-bold bg-surface-container border border-rose-500/50 text-rose-300">
                {tier4Count}
              </span>
            </div>
            <span className="text-[11px] text-on-surface-variant mt-1">
              Primary key &amp; RowID discontinuities
            </span>
            <span className="text-[10px] font-mono text-rose-400 font-medium mt-0.5">
              Heuristic Hint Indicator
            </span>
          </button>
        </div>
      </div>

      {/* Filter Row */}
      <div className="px-space-lg py-2 bg-surface-container-low border-b border-outline-variant flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-2.5 flex-wrap flex-1 max-w-2xl">
          <div className="relative flex-1 min-w-[200px]">
            <span className="material-symbols-outlined absolute left-2.5 top-1.5 text-outline text-[16px]">
              search
            </span>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search recovered string, sender, table, or hash..."
              className="w-full pl-8 pr-3 py-1 bg-surface-container-lowest border border-outline-variant rounded text-xs text-on-surface focus:outline-none focus:border-primary placeholder:text-outline"
            />
          </div>

          <select
            value={appFilter}
            onChange={(e) => setAppFilter(e.target.value)}
            className="h-7 px-2.5 rounded bg-surface-container-lowest border border-outline-variant text-[11px] text-on-surface focus:outline-none focus:border-primary cursor-pointer"
          >
            <option value="all">App: All Apps</option>
            <option value="whatsapp">WhatsApp</option>
            <option value="telegram">Telegram</option>
          </select>

          <select
            value={strengthFilter}
            onChange={(e) => setStrengthFilter(e.target.value)}
            className="h-7 px-2.5 rounded bg-surface-container-lowest border border-outline-variant text-[11px] text-on-surface focus:outline-none focus:border-primary cursor-pointer"
          >
            <option value="all">Strength: All</option>
            <option value="deterministic">Deterministic</option>
            <option value="strong">Strong</option>
            <option value="moderate">Moderate</option>
            <option value="heuristic">Heuristic</option>
          </select>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-on-surface-variant">Classified Findings:</span>
          <span className="font-mono text-primary font-semibold">{filtered.length} records</span>
          {activeTier !== 0 && (
            <button
              type="button"
              onClick={() => setActiveTier(0)}
              className="text-primary hover:underline text-xs"
            >
              (Clear Tier filter)
            </button>
          )}
        </div>
      </div>

      {/* Main Split Layout: Records List & Detail Inspector */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left List */}
        <div className="w-1/2 border-r border-outline-variant overflow-y-auto custom-scrollbar p-3 space-y-2">
          {loading && (
            <div className="py-16 text-center text-on-surface-variant font-mono text-xs">
              <span className="material-symbols-outlined text-2xl animate-spin text-primary mb-1">sync</span>
              <p>Scanning unallocated space, WAL frames, and freelists...</p>
            </div>
          )}

          {!loading && filtered.length === 0 && (
            <div className="py-16 text-center text-on-surface-variant border border-dashed border-outline-variant rounded-lg bg-surface-container-low p-6">
              <span className="material-symbols-outlined text-3xl text-outline mb-2">restore</span>
              <p className="text-body-sm font-medium text-on-surface">No Recovered Records Found</p>
              <p className="text-[11px] text-outline mt-1 mb-3">
                Execute deep carving to scan unallocated cells, pre-checkpoint WAL frames, and tombstone records.
              </p>
              {caseId && (
                <button
                  type="button"
                  onClick={handleExecuteCarve}
                  disabled={carvingRunning}
                  className="btn-primary text-xs"
                >
                  Carve Database Cells Now
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
                className={`p-3 rounded-lg border text-left transition-all cursor-pointer space-y-1.5 ${
                  isSelected
                    ? 'border-primary bg-primary/10 shadow-sm'
                    : 'border-outline-variant bg-surface-container hover:bg-surface-container-high'
                }`}
              >
                <div className="flex items-center justify-between text-[11px]">
                  <span className={`px-2 py-0.5 rounded font-mono font-medium text-[10px] ${
                    r.tier === 1 ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' :
                    r.tier === 2 ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' :
                    r.tier === 3 ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' :
                    'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                  }`}>
                    {r.tierName}
                  </span>
                  <span className="font-mono text-outline text-[10px]">{r.timestamp}</span>
                </div>

                <div className="text-body-sm font-semibold text-on-surface truncate flex items-center justify-between">
                  <span>{r.sender}</span>
                  <span className="text-[10px] font-mono text-outline">{r.sourceApp.toUpperCase()}</span>
                </div>

                <p className="text-body-sm text-on-surface-variant line-clamp-2 select-text font-sans text-xs">
                  {r.snippet}
                </p>

                <div className="pt-1 flex items-center justify-between text-[10px] font-mono text-outline border-t border-outline-variant/40">
                  <span>{r.sourceTable} • {r.offset}</span>
                  <span className="font-semibold text-on-surface">{r.confidence == null ? 'Not assessed' : `${(r.confidence * 100).toFixed(0)}% score`}</span>
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
                  <span className={`px-2 py-0.5 rounded text-xs font-mono font-semibold ${
                    selectedRecord.tier === 1 ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' :
                    selectedRecord.tier === 2 ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' :
                    selectedRecord.tier === 3 ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' :
                    'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                  }`}>
                    {selectedRecord.tierName}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-surface-container border border-outline-variant text-on-surface font-medium">
                    Confidence: {selectedRecord.confidence == null ? 'Not assessed' : `${(selectedRecord.confidence * 100).toFixed(1)}%`} ({selectedRecord.strength})
                  </span>
                </div>
                <h3 className="text-headline-md font-semibold text-on-surface mt-2">
                  {selectedRecord.sender}
                </h3>
              </div>

              {/* Reconstructed Payload Box */}
              <div className="p-3 bg-surface-container rounded-lg border border-outline-variant space-y-1">
                <div className="text-[10px] font-mono text-outline uppercase tracking-wider">RECONSTRUCTED PAYLOAD CONTENT</div>
                <div className="text-body-sm text-on-surface select-text whitespace-pre-wrap">{selectedRecord.snippet}</div>
              </div>

              {/* Technical Provenance Grid */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 rounded bg-surface-container border border-outline-variant">
                  <span className="text-outline uppercase text-[10px] block font-mono">Mechanism</span>
                  <span className="font-mono text-on-surface font-medium">{selectedRecord.mechanism}</span>
                </div>
                <div className="p-2.5 rounded bg-surface-container border border-outline-variant">
                  <span className="text-outline uppercase text-[10px] block font-mono">Source Table</span>
                  <span className="font-mono text-on-surface font-medium">{selectedRecord.sourceTable}</span>
                </div>
                <div className="p-2.5 rounded bg-surface-container border border-outline-variant">
                  <span className="text-outline uppercase text-[10px] block font-mono">Frame / Offset</span>
                  <span className="font-mono text-on-surface font-medium">{selectedRecord.walFrameNumber} ({selectedRecord.offset})</span>
                </div>
                <div className="p-2.5 rounded bg-surface-container border border-outline-variant">
                  <span className="text-outline uppercase text-[10px] block font-mono">Timestamp</span>
                  <span className="font-mono text-on-surface font-medium">{selectedRecord.timestamp}</span>
                </div>
              </div>

              {/* SHA-256 Provenance Hash */}
              {selectedRecord.hash && (
                <div className="p-2.5 bg-surface-container rounded border border-outline-variant space-y-1">
                  <span className="text-outline uppercase text-[10px] block font-mono">Cryptographic Payload Hash</span>
                  <span className="font-mono text-[11px] text-primary break-all select-all font-semibold">
                    {selectedRecord.hash}
                  </span>
                </div>
              )}

              {/* Limitations Disclosures */}
              {selectedRecord.limitations.length > 0 && (
                <div className="p-2.5 bg-amber-950/20 border border-amber-600/40 rounded space-y-1 text-xs">
                  <span className="text-amber-400 font-mono text-[10px] uppercase font-bold block">Forensic Limitations &amp; Caveats</span>
                  <ul className="list-disc list-inside text-amber-200 text-[11px] space-y-0.5">
                    {selectedRecord.limitations.map((lim, idx) => (
                      <li key={idx}>{lim}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Hex Dump Inspector */}
              {selectedRecord.hexDump && (
                <div className="space-y-1.5">
                  <div className="text-[10px] font-mono text-outline uppercase tracking-wider">HEX PAYLOAD PREVIEW</div>
                  <pre className="p-3 bg-surface-container-lowest border border-outline-variant rounded font-mono text-[11px] text-tertiary overflow-x-auto whitespace-pre-wrap">
                    {selectedRecord.hexDump}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-on-surface-variant font-mono text-xs">
              Select any recovered record from the 4-tier list to inspect reconstructed payload, confidence metrics, and physical offsets.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
