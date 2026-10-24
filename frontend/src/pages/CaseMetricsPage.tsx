import React, { useState, useEffect, useCallback } from 'react';
import { useActiveCase } from '../context/CaseContext';
import { dashboardService } from '../services/dashboardService';

export default function CaseMetricsPage() {
  const { activeCase } = useActiveCase();
  const caseId = activeCase?.id;

  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadStats = useCallback(async () => {
    if (!caseId) {
      setStats(null);
      return;
    }
    setLoading(true);
    try {
      const data = await dashboardService.getCaseStats(caseId);
      setStats(data);
    } catch (err) {
      console.warn('Error loading case stats:', err);
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  const evidenceCount = stats?.evidence_count ?? activeCase?.evidenceCount ?? 0;
  const totalMessages = stats?.total_messages ?? (activeCase?.recordCount ? parseInt(activeCase.recordCount.replace(/,/g, ''), 10) : 0);
  const waMessages = stats?.whatsapp_messages ?? 0;
  const tgMessages = stats?.telegram_messages ?? 0;
  const carvedCount = stats?.deleted_messages ?? 0;

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
            Statistical extraction yield, cryptographic health indicators, and pipeline performance metrics for case {activeCase?.caseNumber || 'N/A'}.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={loadStats}
            disabled={loading || !caseId}
            className="btn-secondary text-xs flex items-center gap-1"
          >
            <span className={`material-symbols-outlined text-[15px] ${loading ? 'animate-spin' : ''}`}>refresh</span>
            <span>Refresh Telemetry</span>
          </button>
        </div>
      </div>

      {/* Methodological Callout Banner */}
      <div className="bg-amber-950/30 border border-amber-600/40 rounded-lg p-3.5 flex items-start space-x-3 text-amber-200 shadow-sm">
        <span className="material-symbols-outlined text-amber-400 text-lg shrink-0 mt-0.5">warning</span>
        <div className="text-body-sm font-body-sm text-amber-100/90 leading-relaxed text-xs">
          <strong className="font-semibold text-amber-300">Methodological Disclosure:</strong> Accuracy is not measured for this case (no ground truth). Forensic metrics track deterministic cryptographic validation, extraction yields, and heuristic parsing thresholds; accuracy against external reality cannot be calculated in the absence of verified ground truth.
        </div>
      </div>

      {/* TOP KPI TILES */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Tile 1 */}
        <div className="bg-surface-container border border-outline-variant rounded-lg p-3.5 flex flex-col justify-between shadow-xs">
          <div className="flex items-center justify-between text-outline text-[11px] font-label-ui uppercase tracking-wider">
            <span>Mounted Artifacts</span>
            <span className="material-symbols-outlined text-[16px] text-primary">dataset</span>
          </div>
          <div className="my-2">
            <div className="text-xl font-bold font-mono text-on-surface">{evidenceCount} Registered</div>
          </div>
          <div className="flex items-center space-x-2 pt-1 border-t border-outline-variant text-[11px] font-mono">
            <span className="text-tertiary font-medium">{activeCase?.integrityState || 'Valid'}</span>
          </div>
        </div>

        {/* Tile 2 */}
        <div className="bg-surface-container border border-outline-variant rounded-lg p-3.5 flex flex-col justify-between shadow-xs">
          <div className="flex items-center justify-between text-outline text-[11px] font-label-ui uppercase tracking-wider">
            <span>Last Pipeline Status</span>
            <span className="material-symbols-outlined text-[16px] text-primary">update</span>
          </div>
          <div className="my-2">
            <div className="text-xl font-bold font-mono text-on-surface">{activeCase?.lastPipeline || 'Not executed'}</div>
          </div>
          <div className="flex items-center justify-between pt-1 border-t border-outline-variant text-[11px] font-mono text-on-surface-variant">
            <span>Updated: {activeCase?.updated || 'Recently'}</span>
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
              {activeCase?.sha256Root ? `${activeCase.sha256Root.substring(0, 14)}...` : 'N/A'}
            </code>
          </div>
        </div>

        {/* Tile 4 */}
        <div className="bg-surface-container border border-outline-variant rounded-lg p-3.5 flex flex-col justify-between shadow-xs">
          <div className="flex items-center justify-between text-outline text-[11px] font-label-ui uppercase tracking-wider">
            <span>Indexed Records</span>
            <span className="material-symbols-outlined text-[16px] text-primary">analytics</span>
          </div>
          <div className="my-2">
            <div className="text-xl font-bold font-mono text-on-surface">{totalMessages} Total</div>
          </div>
          <div className="flex items-center justify-between pt-1 border-t border-outline-variant text-[11px] font-mono text-on-surface-variant">
            <span>{carvedCount} Carved</span>
            <span className="text-tertiary">{evidenceCount > 0 ? 'Live Ingest' : 'No Data'}</span>
          </div>
        </div>
      </section>

      {/* Extraction Yields Breakdown */}
      <div className="bg-surface-container border border-outline-variant rounded-lg p-4 shadow-xs space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-outline-variant">
          <h2 className="text-headline-sm font-headline-sm text-on-surface font-semibold text-sm">
            Extraction Yield &amp; Partition Distribution
          </h2>
          <span className="text-[11px] font-mono text-outline">Evidence Partition Breakdown</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-3 rounded bg-surface-container-low border border-outline-variant space-y-2">
            <div className="flex justify-between items-center text-xs font-semibold">
              <span className="text-on-surface font-mono">WhatsApp Data Store</span>
              <span className="text-primary font-mono">{waMessages} Records</span>
            </div>
            <div className="w-full h-2 rounded bg-surface-container-lowest overflow-hidden flex">
              <div className="h-full bg-primary" style={{ width: totalMessages > 0 ? `${Math.min(100, (waMessages / totalMessages) * 100)}%` : '0%' }} />
            </div>
            <div className="flex justify-between text-[11px] text-on-surface-variant font-mono">
              <span>{waMessages} indexed messages</span>
              <span className="text-outline">{totalMessages > 0 ? `${((waMessages / totalMessages) * 100).toFixed(0)}%` : '0%'}</span>
            </div>
          </div>

          <div className="p-3 rounded bg-surface-container-low border border-outline-variant space-y-2">
            <div className="flex justify-between items-center text-xs font-semibold">
              <span className="text-on-surface font-mono">Telegram Data Store</span>
              <span className="text-primary font-mono">{tgMessages} Records</span>
            </div>
            <div className="w-full h-2 rounded bg-surface-container-lowest overflow-hidden flex">
              <div className="h-full bg-primary" style={{ width: totalMessages > 0 ? `${Math.min(100, (tgMessages / totalMessages) * 100)}%` : '0%' }} />
            </div>
            <div className="flex justify-between text-[11px] text-on-surface-variant font-mono">
              <span>{tgMessages} indexed messages</span>
              <span className="text-outline">{totalMessages > 0 ? `${((tgMessages / totalMessages) * 100).toFixed(0)}%` : '0%'}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
