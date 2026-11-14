import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useActiveCase } from '../context/CaseContext';
import { pipelineService, StageEventData } from '../services/pipelineService';

const formatStageLog = (stage: any): string => {
  const ts = stage.timestamp || new Date().toISOString();
  const timeStr = ts.substring(11, 23);
  const stageName = (stage.stage || 'STAGE').toUpperCase();
  const status = (stage.status || 'SUCCESS').toUpperCase();
  const dur = stage.duration_ms !== undefined && stage.duration_ms !== null
    ? ` (${Number(stage.duration_ms).toFixed(2)} ms)`
    : '';
  const hash = stage.output_hash
    ? ` [sha256:${stage.output_hash.substring(0, 12)}...]`
    : '';

  let countsStr = '';
  const rawCounts = stage.counts_json || stage.counts;
  if (rawCounts && typeof rawCounts === 'object') {
    const entries = Object.entries(rawCounts).map(([k, v]) => `${k}=${v}`);
    if (entries.length > 0) countsStr = ` {${entries.join(', ')}}`;
  }

  const rawErrors = stage.errors_json || stage.errors;
  const errs = Array.isArray(rawErrors) ? rawErrors : [];
  const errStr = errs.length > 0 ? ` [ERRORS: ${errs.join('; ')}]` : '';

  return `[${timeStr} UTC] [${stageName}] [${status}]${dur}${countsStr}${hash}${errStr}`;
};

export default function PipelinePage() {
  const { activeCase, refreshCases } = useActiveCase();
  const caseId = activeCase?.id;

  // Subnav tabs: 'pipeline' | 'history' | 'quality'
  const [activeTab, setActiveTab] = useState('pipeline');
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [historicalRuns, setHistoricalRuns] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [terminalLogs, setTerminalLogs] = useState([
    `[${new Date().toISOString().substring(11, 23)} UTC] [INIT] Pipeline console ready for case ${activeCase?.caseNumber || 'docket'}.`,
    `[${new Date().toISOString().substring(11, 23)} UTC] [STATUS] Awaiting execution trigger.`
  ]);

  const loadHistoricalRuns = useCallback(async () => {
    if (!caseId) {
      setHistoricalRuns([]);
      return;
    }
    setLoadingHistory(true);
    try {
      const response = await axios.get(`/api/cases/${caseId}/pipeline/runs`);
      const runs = Array.isArray(response.data) ? response.data : [];
      setHistoricalRuns(runs);
    } catch (err) {
      console.warn('Error fetching historical pipeline runs:', err);
      setHistoricalRuns([]);
    } finally {
      setLoadingHistory(false);
    }
  }, [caseId]);

  useEffect(() => {
    if (activeTab === 'history') {
      loadHistoricalRuns();
    }
  }, [activeTab, loadHistoricalRuns]);

  const handleRunFullPipeline = async () => {
    if (!caseId) return;
    setPipelineRunning(true);
    const now = () => new Date().toISOString().substring(11, 23);

    setTerminalLogs(prev => [
      ...prev,
      `[${now()} UTC] [INIT] Connecting to live SSE pipeline stream for case ${activeCase?.caseNumber || caseId}...`
    ]);

    let streamSucceeded = false;
    try {
      await pipelineService.streamPipeline(
        caseId,
        (event: StageEventData) => {
          streamSucceeded = true;
          setTerminalLogs(prev => [...prev, formatStageLog(event)]);
        },
        async (streamErr: any) => {
          console.warn('SSE streaming encountered error, attempting synchronous fallback:', streamErr);
          if (!streamSucceeded) {
            setTerminalLogs(prev => [
              ...prev,
              `[${now()} UTC] [FALLBACK] Direct streaming unavailable. Invoking synchronous pipeline execution...`
            ]);
            try {
              const res = await pipelineService.runPipeline(caseId);
              if (res?.stage_runs && Array.isArray(res.stage_runs)) {
                const logs = res.stage_runs.map((st: any) => formatStageLog(st));
                setTerminalLogs(p => [...p, ...logs]);
              }
              setTerminalLogs(p => [
                ...p,
                `[${now()} UTC] [SUMMARY] [${res.status || 'COMPLETED'}] Run #${res.id} finalized with content hash ${res.content_hash || 'N/A'}`
              ]);
            } catch (postErr: any) {
              const msg = postErr.response?.data?.detail || postErr.message || 'Execution error';
              setTerminalLogs(p => [...p, `[${now()} UTC] [ERROR] Pipeline execution halted: ${msg}`]);
            }
          }
        },
        async () => {
          setTerminalLogs(prev => [
            ...prev,
            `[${now()} UTC] [COMPLETE] Streaming execution finalized. Case telemetry synchronized.`
          ]);
          if (refreshCases) await refreshCases();
          if (activeTab === 'history') await loadHistoricalRuns();
        }
      );
      if (refreshCases) await refreshCases();
      if (activeTab === 'history') await loadHistoricalRuns();
    } catch (err: any) {
      console.error('Pipeline execution failed:', err);
      const errMsg = err.response?.data?.detail || err.message || 'Execution error encountered.';
      setTerminalLogs(prev => [
        ...prev,
        `[${now()} UTC] [ERROR] Pipeline execution halted: ${errMsg}`
      ]);
    } finally {
      setPipelineRunning(false);
    }
  };

  const handleInspectHistoricalRun = async (runId: string) => {
    try {
      setPipelineRunning(true);
      const data = await pipelineService.getRunDetails(runId);
      const now = () => new Date().toISOString().substring(11, 23);
      if (data?.stage_runs && Array.isArray(data.stage_runs)) {
        const parsedLogs = data.stage_runs.map((st: any) => formatStageLog(st));
        setTerminalLogs([
          `[${now()} UTC] [HISTORY] Loaded historical run RUN-#${data.id} (Status: ${data.status})`,
          ...parsedLogs,
          `[${now()} UTC] [DIGEST] Master Content Hash: ${data.content_hash || 'N/A'}`
        ]);
        setActiveTab('pipeline');
      }
    } catch (err) {
      console.error('Failed to load run details:', err);
    } finally {
      setPipelineRunning(false);
    }
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
            <span>Parsing Quality</span>
          </button>
        </div>

        <div className="flex items-center gap-2 text-label-mono-sm text-xs text-on-surface-variant">
          <span className="w-2 h-2 rounded-full bg-tertiary" />
          <span>Case: {activeCase?.caseNumber || 'N/A'}</span>
        </div>
      </div>

      {/* ================= TAB 1: RUN PIPELINE ================= */}
      {activeTab === 'pipeline' && (
        <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-5">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 bg-surface-container border border-outline-variant rounded-lg shadow-xs">
            <div>
              <h2 className="text-headline-md font-semibold text-on-surface">
                Automated Forensic Ingestion &amp; Analysis Pipeline
              </h2>
              <p className="text-body-sm text-on-surface-variant mt-1 max-w-2xl text-xs">
                Executes multi-stage sequence: Pre-Stage Integrity Check → Container Decryption → Schema Indexing → Residual SQLite Carving → Multi-Source Chronology → Entity Linkage.
              </p>
            </div>

            <button
              type="button"
              disabled={pipelineRunning || !caseId}
              onClick={handleRunFullPipeline}
              className="btn-primary flex items-center gap-2 shrink-0"
            >
              <span className={`material-symbols-outlined text-[18px] ${pipelineRunning ? 'animate-spin' : ''}`}>
                {pipelineRunning ? 'sync' : 'play_arrow'}
              </span>
              <span>{pipelineRunning ? 'Running Pipeline...' : 'Execute Full Pipeline'}</span>
            </button>
          </div>

          {/* Terminal Console Output */}
          <div className="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden shadow-md flex flex-col h-[400px]">
            <div className="bg-surface-container-low px-4 py-2 border-b border-outline-variant flex items-center justify-between text-xs font-mono text-on-surface-variant">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
                <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/80" />
                <span className="w-2.5 h-2.5 rounded-full bg-green-500/80" />
                <span className="ml-2 font-semibold text-on-surface">Pipeline Live Output Log</span>
              </div>
              <button
                type="button"
                onClick={() => setTerminalLogs([`[${new Date().toISOString().substring(11, 23)} UTC] [CLEAR] Terminal buffer cleared.`])}
                className="hover:text-primary transition-colors text-[11px]"
              >
                Clear Log
              </button>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar p-4 font-mono text-xs text-primary/90 space-y-1 bg-black/40">
              {terminalLogs.map((log, idx) => (
                <div key={idx} className="leading-relaxed select-text">
                  {log}
                </div>
              ))}
              {pipelineRunning && (
                <div className="animate-pulse text-tertiary">
                  &gt; Executing pipeline worker task...
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ================= TAB 2: RUN HISTORY ================= */}
      {activeTab === 'history' && (
        <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-5">
          <div className="bg-surface-container border border-outline-variant rounded-lg overflow-hidden shadow-xs">
            <div className="p-3 border-b border-outline-variant flex items-center justify-between">
              <h3 className="font-headline-sm font-semibold text-on-surface text-sm">
                Recorded Pipeline Executions ({historicalRuns.length})
              </h3>
              <button
                type="button"
                onClick={loadHistoricalRuns}
                className="text-primary hover:underline text-xs flex items-center gap-1"
              >
                <span className="material-symbols-outlined text-[14px]">refresh</span>
                Refresh
              </button>
            </div>

            <table className="w-full text-left border-collapse text-body-sm font-body-sm">
              <thead>
                <tr className="bg-surface-container-lowest/80 border-b border-outline-variant h-8 text-label-ui uppercase tracking-wider text-[11px] text-on-surface-variant">
                  <th className="py-2.5 px-3">Run ID</th>
                  <th className="py-2.5 px-3">Trigger / Operator</th>
                  <th className="py-2.5 px-3">Completed At</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Run Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/60 font-mono text-xs">
                {loadingHistory && (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-on-surface-variant">
                      <span className="material-symbols-outlined text-2xl animate-spin text-primary mb-1">sync</span>
                      <p>Loading historical execution runs...</p>
                    </td>
                  </tr>
                )}

                {!loadingHistory && historicalRuns.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-10 text-center text-on-surface-variant">
                      No previous pipeline runs recorded for this case. Execute the pipeline from the "Run Pipeline" tab.
                    </td>
                  </tr>
                )}

                {!loadingHistory && historicalRuns.map((run) => (
                  <tr key={run.id} className="hover:bg-surface-container-high/40">
                    <td className="py-3 px-3 font-semibold text-primary">RUN-#{run.id}</td>
                    <td className="py-3 px-3 text-on-surface">{run.trigger_source || 'Automated Orchestrator'}</td>
                    <td className="py-3 px-3 text-on-surface-variant">
                      {run.completed_at ? new Date(run.completed_at).toISOString().replace('T', ' ').substring(0, 19) : 'In Progress'}
                    </td>
                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                        run.status === 'SUCCESS' || run.status === 'COMPLETED'
                          ? 'bg-tertiary/10 text-tertiary border border-tertiary/30'
                          : run.status === 'FAILED'
                            ? 'bg-error/20 text-error border border-error'
                            : 'bg-primary/10 text-primary border border-primary/30'
                      }`}>
                        {run.status}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right">
                      <button
                        type="button"
                        onClick={() => handleInspectHistoricalRun(run.id)}
                        className="px-2 py-0.5 rounded bg-surface-container-high hover:bg-primary hover:text-on-primary text-primary border border-outline-variant text-[11px] transition-colors"
                        title="Load Run Telemetry in Terminal"
                      >
                        Inspect Telemetry
                      </button>
                    </td>
                  </tr>
                ))}
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
                  <h2 className="text-headline-sm font-semibold text-on-surface text-sm">
                    Extraction &amp; Parsing Metrics
                  </h2>
                </div>
                <p className="text-body-sm text-on-surface-variant mt-0.5 text-xs">
                  Evidence records parsed versus total ingested items for case {activeCase?.caseNumber || 'docket'}.
                </p>
              </div>

              <div className="flex items-center gap-2 px-3 py-1 bg-primary/10 border border-primary/30 rounded text-primary text-xs font-mono">
                <span>EVIDENCE COUNT: {activeCase?.evidenceCount ?? 0}</span>
              </div>
            </div>

            <div className="p-4 bg-surface-container-lowest border border-outline-variant rounded text-xs space-y-2">
              <div className="flex justify-between font-mono text-on-surface">
                <span>Total Indexed Message Records:</span>
                <span className="text-primary font-semibold">{activeCase?.recordCount || '0'}</span>
              </div>
              <div className="flex justify-between font-mono text-on-surface">
                <span>Integrity Status:</span>
                <span className="text-tertiary font-semibold">{activeCase?.integrityState || 'Pending Ingestion'}</span>
              </div>
              <div className="flex justify-between font-mono text-on-surface">
                <span>Last Pipeline Execution:</span>
                <span className="text-on-surface-variant">{activeCase?.lastPipeline || 'Not executed'}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
