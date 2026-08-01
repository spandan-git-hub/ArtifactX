import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import CaseWorkspacePage from './CaseWorkspacePage';
import correlationService from '../services/correlationService';
import { getEvidences } from '../services/evidenceService';
import {
  GitFork,
  Users,
  MessageSquare,
  Clock,
  Sparkles,
  RefreshCw,
  Search,
  Zap,
  ShieldCheck,
  Filter,
  Layers,
  Phone,
  FileImage,
  ArrowRight,
  CheckCircle2,
} from 'lucide-react';
import { format } from 'date-fns';

const TIME_WINDOWS = [
  { label: '1 Minute (60s)', value: 60 },
  { label: '5 Minutes (300s)', value: 300 },
  { label: '15 Minutes (900s)', value: 900 },
  { label: '30 Minutes (1800s)', value: 1800 },
  { label: '60 Minutes (3600s)', value: 3600 },
];

const CorrelationPage = () => {
  const { caseId } = useParams();

  const [loading, setLoading] = useState(true);
  const [correlateLoading, setCorrelateLoading] = useState(false);
  const [edges, setEdges] = useState([]);
  const [entities, setEntities] = useState([]);
  const [matrix, setMatrix] = useState([]);
  const [evidenceCount, setEvidenceCount] = useState(0);
  const [hasWa, setHasWa] = useState(false);
  const [hasTg, setHasTg] = useState(false);
  const [windowSeconds, setWindowSeconds] = useState(300);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('all'); // 'all', 'entities', 'matrix'

  // Fetch correlation data
  const loadCorrelationData = useCallback(async () => {
    if (!caseId) return;
    try {
      setLoading(true);
      const [edgesData, entitiesData, matrixData, statusData] = await Promise.all([
        correlationService.getCorrelationEdges(caseId).catch(() => []),
        correlationService.getEntityResolutions(caseId).catch(() => []),
        correlationService.getMessageMatrix(caseId, windowSeconds).catch(() => []),
        correlationService.getCorrelationStatus(caseId).catch(() => ({ has_whatsapp: false, has_telegram: false, evidence_count: 0 })),
      ]);
      setEdges(edgesData || []);
      setEntities(entitiesData || []);
      setMatrix(matrixData || []);

      const status = statusData || {};
      setEvidenceCount(status.evidence_count || 0);
      setHasWa(Boolean(status.has_whatsapp));
      setHasTg(Boolean(status.has_telegram));
    } catch (err) {
      console.error('Failed to load correlation data:', err);
    } finally {
      setLoading(false);
    }
  }, [caseId, windowSeconds]);


  useEffect(() => {
    loadCorrelationData();
  }, [loadCorrelationData]);


  const [statusNotification, setStatusNotification] = useState(null);

  // Trigger Correlation Engine
  const handleRunCorrelation = async () => {
    try {
      setCorrelateLoading(true);
      const res = await correlationService.triggerCorrelation(caseId);
      await loadCorrelationData();
      const count = res?.edges_created ?? 0;
      setStatusNotification({
        type: 'success',
        message: `Correlation analysis completed! Generated ${count} cross-app edges.`,
      });
      setTimeout(() => setStatusNotification(null), 6000);
    } catch (err) {
      console.error('Failed to run correlation:', err);
      setStatusNotification({
        type: 'error',
        message: 'Failed to run correlation engine. Check backend logs.',
      });
      setTimeout(() => setStatusNotification(null), 6000);
    } finally {
      setCorrelateLoading(false);
    }
  };

  // Filtered entities
  const filteredEntities = entities.filter((item) => {
    const term = searchTerm.toLowerCase();
    return (
      (item.phone_number && item.phone_number.toLowerCase().includes(term)) ||
      (item.wa_name && item.wa_name.toLowerCase().includes(term)) ||
      (item.wa_jid && item.wa_jid.toLowerCase().includes(term)) ||
      (item.tg_name && item.tg_name.toLowerCase().includes(term)) ||
      (item.tg_username && item.tg_username.toLowerCase().includes(term)) ||
      (item.match_reason && item.match_reason.toLowerCase().includes(term))
    );
  });

  // Filtered matrix
  const filteredMatrix = matrix.filter((item) => {
    const term = searchTerm.toLowerCase();
    return (
      (item.wa_body && item.wa_body.toLowerCase().includes(term)) ||
      (item.tg_body && item.tg_body.toLowerCase().includes(term)) ||
      (item.wa_sender_jid && item.wa_sender_jid.toLowerCase().includes(term)) ||
      (item.tg_sender_id && String(item.tg_sender_id).toLowerCase().includes(term))
    );
  });

  // Calculate statistics
  const mediaEdgesCount = edges.filter((e) => e.target_type === 'media_item').length;
  const exactPhoneMatchesCount = entities.filter((e) => e.confidence_score >= 1.0).length;

  const formatDate = (ts) => {
    if (!ts) return 'N/A';
    try {
      const date = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts);
      return format(date, 'MMM d, yyyy HH:mm:ss');
    } catch (e) {
      return String(ts);
    }
  };

  return (
    <CaseWorkspacePage>
      <div className="space-y-6">
        {/* Status Notification Toast */}
        {statusNotification && (
          <div
            className={`p-4 rounded-xl border flex items-center justify-between text-xs font-mono animate-in ${
              statusNotification.type === 'success'
                ? 'bg-accent-emerald/15 border-accent-emerald/40 text-accent-emerald'
                : 'bg-accent-rose/15 border-accent-rose/40 text-accent-rose'
            }`}
          >
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              <span>{statusNotification.message}</span>
            </div>
            <button onClick={() => setStatusNotification(null)} className="hover:opacity-80">
              ✕
            </button>
          </div>
        )}

        {/* Header Navigation */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-forensic-900/60 p-4 rounded-xl border border-forensic-800 backdrop-blur-sm">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <GitFork className="w-5 h-5 text-accent-cyan" />
              <h2 className="text-lg font-bold font-mono text-forensic-50">
                Evidence Correlation Engine & Identity Visualizer
              </h2>
            </div>
            <p className="text-xs text-forensic-400">
              Cross-platform entity resolution (WhatsApp ↔ Telegram) and message time-window correlation matrix.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleRunCorrelation}
              disabled={correlateLoading}
              className="btn-primary inline-flex items-center gap-2 text-xs font-mono py-2 px-3 whitespace-nowrap"
            >
              {correlateLoading ? (
                <RefreshCw className="w-4 h-4 animate-spin text-forensic-950" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
              {correlateLoading ? 'Correlating...' : 'Run Correlation Engine'}
            </button>
          </div>
        </div>


        {/* Metrics Summary Overview */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="card bg-forensic-900/40 border-forensic-800 p-4 flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-accent-cyan/15 border border-accent-cyan/30 flex items-center justify-center text-accent-cyan">
              <GitFork className="w-6 h-6" />
            </div>
            <div>
              <div className="text-2xl font-bold font-mono text-forensic-50">{edges.length}</div>
              <div className="text-xs text-forensic-400 font-mono">Total Correlation Edges</div>
            </div>
          </div>

          <div className="card bg-forensic-900/40 border-forensic-800 p-4 flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-accent-emerald/15 border border-accent-emerald/30 flex items-center justify-center text-accent-emerald">
              <Users className="w-6 h-6" />
            </div>
            <div>
              <div className="text-2xl font-bold font-mono text-forensic-50">{entities.length}</div>
              <div className="text-xs text-forensic-400 font-mono">
                Mapped Identities ({exactPhoneMatchesCount} E.164)
              </div>
            </div>
          </div>

          <div className="card bg-forensic-900/40 border-forensic-800 p-4 flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <MessageSquare className="w-6 h-6" />
            </div>
            <div>
              <div className="text-2xl font-bold font-mono text-forensic-50">{matrix.length}</div>
              <div className="text-xs text-forensic-400 font-mono">Cross-App Message Pairs</div>
            </div>
          </div>

          <div className="card bg-forensic-900/40 border-forensic-800 p-4 flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <FileImage className="w-6 h-6" />
            </div>
            <div>
              <div className="text-2xl font-bold font-mono text-forensic-50">{mediaEdgesCount}</div>
              <div className="text-xs text-forensic-400 font-mono">Linked Media Items</div>
            </div>
          </div>
        </div>

        {/* Toolbar & Filter Bar */}
        <div className="card bg-forensic-900/60 border-forensic-800 p-4 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
          <div className="flex items-center gap-2 flex-1">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-forensic-500" />
              <input
                type="text"
                placeholder="Search phone, name, handle, JID or message..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="input-search pl-9 text-xs w-full"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-accent-cyan" />
              <span className="text-xs text-forensic-400 font-mono">Time Window:</span>
              <select
                value={windowSeconds}
                onChange={(e) => setWindowSeconds(Number(e.target.value))}
                className="bg-forensic-950 border border-forensic-700 text-forensic-200 text-xs rounded-md px-2.5 py-1.5 focus:outline-none focus:border-accent-cyan font-mono"
              >
                {TIME_WINDOWS.map((tw) => (
                  <option key={tw.value} value={tw.value}>
                    {tw.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center bg-forensic-950 p-1 rounded-lg border border-forensic-800 text-xs font-mono">
              <button
                onClick={() => setActiveTab('all')}
                className={`px-3 py-1 rounded-md transition-colors ${
                  activeTab === 'all' ? 'bg-accent-cyan/20 text-accent-cyan font-semibold' : 'text-forensic-400 hover:text-forensic-200'
                }`}
              >
                All Views
              </button>
              <button
                onClick={() => setActiveTab('entities')}
                className={`px-3 py-1 rounded-md transition-colors ${
                  activeTab === 'entities' ? 'bg-accent-cyan/20 text-accent-cyan font-semibold' : 'text-forensic-400 hover:text-forensic-200'
                }`}
              >
                Entities ({filteredEntities.length})
              </button>
              <button
                onClick={() => setActiveTab('matrix')}
                className={`px-3 py-1 rounded-md transition-colors ${
                  activeTab === 'matrix' ? 'bg-accent-cyan/20 text-accent-cyan font-semibold' : 'text-forensic-400 hover:text-forensic-200'
                }`}
              >
                Matrix ({filteredMatrix.length})
              </button>
            </div>
          </div>
        </div>

        {/* Dynamic Contextual Banner - ONLY shown when edges and entities are zero */}
        {!loading && edges.length === 0 && entities.length === 0 && (
          <div className="card bg-accent-cyan/5 border-accent-cyan/30 p-5 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-accent-cyan/20 flex items-center justify-center text-accent-cyan shrink-0">
                <GitFork className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold font-mono text-forensic-100 mb-1">
                  {evidenceCount === 0
                    ? 'No Evidence Files Ingested'
                    : (!hasWa || !hasTg)
                    ? 'Cross-Platform Correlation Not Possible'
                    : `Both WhatsApp & Telegram Evidence Present — Analysis Required`}
                </h4>
                <p className="text-xs text-forensic-400">
                  {evidenceCount === 0
                    ? 'No evidence files have been uploaded for this case. Upload WhatsApp and Telegram evidence under Evidence & Artifacts, or create a Demo Case from the home screen.'
                    : (!hasWa || !hasTg)
                    ? `Cross-platform identity resolution and message matrix matching requires evidence files from BOTH WhatsApp and Telegram. Currently, ${
                        hasWa ? 'only WhatsApp' : 'only Telegram'
                      } evidence is present. Please upload ${hasWa ? 'Telegram' : 'WhatsApp'} evidence under Evidence & Artifacts.`
                    : 'Evidence files from both platforms are ingested. Click "Run Correlation Engine" in the header above to perform the analysis before expecting correlation results.'}
                </p>
              </div>
            </div>
            {evidenceCount === 0 ? (
              <Link to="/" className="btn-secondary text-xs font-mono whitespace-nowrap shrink-0">
                Home / Create Demo
              </Link>
            ) : (!hasWa || !hasTg) ? (
              <Link to={`/cases/${caseId}/evidence`} className="btn-secondary text-xs font-mono whitespace-nowrap shrink-0">
                Upload Missing Evidence
              </Link>
            ) : null}
          </div>
        )}




        {/* Loading Spinner */}
        {loading ? (
          <div className="card p-12 flex flex-col items-center justify-center text-center border-forensic-800">
            <RefreshCw className="w-8 h-8 animate-spin text-accent-cyan mb-3" />
            <p className="text-sm font-mono text-forensic-300">Processing Evidence Correlation Network...</p>
          </div>
        ) : (

          <div className="space-y-8">
            {/* Section 1: Entity Resolution Table */}
            {(activeTab === 'all' || activeTab === 'entities') && (
              <div className="card border-forensic-800 p-0 overflow-hidden">
                <div className="p-4 bg-forensic-900/80 border-b border-forensic-800 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Users className="w-4 h-4 text-accent-emerald" />
                    <h3 className="text-sm font-bold font-mono text-forensic-100">
                      Cross-Platform Entity Resolution Table
                    </h3>
                    <span className="badge badge-emerald text-[11px] font-mono">
                      {filteredEntities.length} Resolved Identities
                    </span>
                  </div>
                  <span className="text-xs text-forensic-400 font-mono">
                    Normalized Standard: E.164 International Format
                  </span>
                </div>

                {filteredEntities.length === 0 ? (
                  <div className="p-8 text-center text-forensic-400 text-xs font-mono">
                    No resolved entity matches found for current search.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="table-forensic text-xs">
                      <thead>
                        <tr>
                          <th>Normalized E.164 Phone</th>
                          <th>WhatsApp Identity</th>
                          <th>Telegram Identity</th>
                          <th>Match Logic</th>
                          <th>Confidence</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredEntities.map((item) => {
                          const waHasSeparateName = item.wa_name && item.wa_name !== item.wa_jid;
                          const tgHasSeparateUser = item.tg_username && item.tg_name !== item.tg_username && item.tg_name !== `@${item.tg_username}`;

                          return (
                            <tr key={item.id} className="hover:bg-forensic-900/40 transition-colors">
                              <td className="py-3 px-4">
                                <div className="flex items-center gap-2 font-mono text-accent-cyan font-semibold text-xs">
                                  <Phone className="w-3.5 h-3.5 shrink-0" />
                                  {item.phone_number || 'Unlinked Phone'}
                                </div>
                              </td>
                              <td className="py-3 px-4">
                                <div className="space-y-1">
                                  <div className="flex items-center gap-2 font-medium text-forensic-100 text-xs">
                                    <span className="w-2 h-2 rounded-full bg-accent-emerald shrink-0" />
                                    <span>{waHasSeparateName ? item.wa_name : item.wa_jid}</span>
                                  </div>
                                  {waHasSeparateName && (
                                    <div className="text-[11px] font-mono text-forensic-500 pl-4">{item.wa_jid}</div>
                                  )}
                                </div>
                              </td>
                              <td className="py-3 px-4">
                                <div className="space-y-1">
                                  <div className="flex items-center gap-2 font-medium text-forensic-100 text-xs">
                                    <span className="w-2 h-2 rounded-full bg-accent-blue shrink-0" />
                                    <span>{item.tg_name || (item.tg_username ? `@${item.tg_username}` : item.tg_user_id)}</span>
                                  </div>
                                  {tgHasSeparateUser && (
                                    <div className="text-[11px] font-mono text-accent-blue pl-4">@{item.tg_username}</div>
                                  )}
                                </div>
                              </td>
                              <td className="py-3 px-4">
                                <span className="text-xs text-forensic-300 font-mono bg-forensic-900/80 px-2.5 py-1 rounded border border-forensic-800">
                                  {item.match_reason}
                                </span>
                              </td>
                              <td className="py-3 px-4">
                                <span
                                  className={`badge text-[11px] font-mono ${
                                    item.confidence_score >= 1.0
                                      ? 'badge-emerald'
                                      : item.confidence_score >= 0.85
                                      ? 'badge-cyan'
                                      : 'badge-amber'
                                  }`}
                                >
                                  {Math.round(item.confidence_score * 100)}% Match
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* Section 2: Cross-App Message Exchange Matrix */}
            {(activeTab === 'all' || activeTab === 'matrix') && (
              <div className="card border-forensic-800 p-0 overflow-hidden">
                <div className="p-4 bg-forensic-900/80 border-b border-forensic-800 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <MessageSquare className="w-4 h-4 text-accent-cyan" />
                    <h3 className="text-sm font-bold font-mono text-forensic-100">
                      Cross-App Message Exchange Matrix
                    </h3>
                    <span className="badge badge-cyan text-[11px] font-mono">
                      Window: ≤ {windowSeconds}s
                    </span>
                  </div>
                  <span className="text-xs text-forensic-400 font-mono">
                    Showing {filteredMatrix.length} Correlated Pairs
                  </span>
                </div>

                {filteredMatrix.length === 0 ? (
                  <div className="p-8 text-center text-forensic-400 text-xs font-mono">
                    No cross-app message exchanges detected within the selected {windowSeconds}s time window. Try increasing the time window threshold.
                  </div>
                ) : (
                  <div className="p-4 space-y-4 bg-forensic-950">
                    {filteredMatrix.map((item) => (
                      <div
                        key={item.id}
                        className="card bg-forensic-900/40 border-forensic-800 p-4 hover:border-accent-cyan/40 transition-colors"
                      >
                        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">
                          {/* WhatsApp Left Side */}
                          <div className="flex-1 bg-forensic-950 p-3.5 rounded-lg border border-accent-emerald/30 relative">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-accent-emerald/15 text-accent-emerald border border-accent-emerald/30 font-semibold">
                                WhatsApp
                              </span>
                              <span className="text-[11px] font-mono text-forensic-400">
                                {formatDate(item.wa_timestamp)}
                              </span>
                            </div>
                            <div className="text-xs font-mono text-forensic-300 mb-1.5">
                              From: <span className="text-forensic-100">{item.wa_sender_jid}</span>
                            </div>
                            <div className="text-sm text-forensic-100 bg-forensic-900/60 p-2.5 rounded border border-forensic-800 font-sans">
                              {item.wa_body || <span className="italic text-forensic-500">[Media attachment / empty body]</span>}
                            </div>
                          </div>

                          {/* Time Delta Connector Badge */}
                          <div className="flex flex-col items-center justify-center px-2 py-1 lg:py-0">
                            <div className="flex items-center gap-1 text-xs font-mono text-amber-400 bg-amber-500/10 px-3 py-1 rounded-full border border-amber-500/20 whitespace-nowrap mb-1">
                              <Zap className="w-3.5 h-3.5" />
                              ⚡ {item.time_delta_seconds}s Delta
                            </div>
                            {item.same_entity_pair && (
                              <span className="text-[10px] font-mono text-accent-emerald flex items-center gap-1">
                                <CheckCircle2 className="w-3 h-3" />
                                Same Identity
                              </span>
                            )}
                            <span className="text-[10px] font-mono text-forensic-400">
                              {Math.round((item.confidence_score || 0.8) * 100)}% Confidence
                            </span>
                          </div>

                          {/* Telegram Right Side */}
                          <div className="flex-1 bg-forensic-950 p-3.5 rounded-lg border border-accent-blue/30 relative">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-accent-blue/15 text-accent-blue border border-accent-blue/30 font-semibold">
                                Telegram
                              </span>
                              <span className="text-[11px] font-mono text-forensic-400">
                                {formatDate(item.tg_timestamp)}
                              </span>
                            </div>
                            <div className="text-xs font-mono text-forensic-300 mb-1.5">
                              From User ID: <span className="text-forensic-100">{item.tg_sender_id}</span>
                            </div>
                            <div className="text-sm text-forensic-100 bg-forensic-900/60 p-2.5 rounded border border-forensic-800 font-sans">
                              {item.tg_body || <span className="italic text-forensic-500">[Media attachment / empty body]</span>}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </CaseWorkspacePage>
  );
};

export default CorrelationPage;
