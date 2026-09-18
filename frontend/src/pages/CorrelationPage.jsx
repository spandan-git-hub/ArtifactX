import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import CaseWorkspacePage from './CaseWorkspacePage';
import correlationService from '../services/correlationService';
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
  AlertTriangle,
  MapPin,
  Coins,
  CreditCard,
  Hash,
  Compass,
  Sliders,
  X,
  ExternalLink,
  ChevronRight,
  Eye,
  Info,
} from 'lucide-react';
import { format } from 'date-fns';

const TIME_WINDOWS = [
  { label: '1 Minute (60s)', value: 60 },
  { label: '3 Minutes (180s)', value: 180 },
  { label: '5 Minutes (300s)', value: 300 },
  { label: '15 Minutes (900s)', value: 900 },
  { label: '30 Minutes (1800s)', value: 1800 },
];

const CorrelationPage = () => {
  const { caseId } = useParams();

  const [loading, setLoading] = useState(true);
  const [correlateLoading, setCorrelateLoading] = useState(false);
  const [showConfigModal, setShowConfigModal] = useState(false);

  // Core Data States
  const [edges, setEdges] = useState([]);
  const [entities, setEntities] = useState([]);
  const [matrix, setMatrix] = useState([]);
  const [persons, setPersons] = useState([]);
  const [handovers, setHandovers] = useState([]);
  const [mediaMatches, setMediaMatches] = useState([]);
  const [artifacts, setArtifacts] = useState([]);
  const [rendezvous, setRendezvous] = useState([]);
  const [graphData, setGraphData] = useState({ nodes: [], edges: [], metadata: {} });

  // Status & Counts
  const [evidenceCount, setEvidenceCount] = useState(0);
  const [hasWa, setHasWa] = useState(false);
  const [hasTg, setHasTg] = useState(false);

  // Filter & Active Tab
  const [windowSeconds, setWindowSeconds] = useState(300);
  const [searchTerm, setSearchTerm] = useState('');
  const [artifactFilter, setArtifactFilter] = useState('ALL'); // ALL, CRYPTO, BANKING, LOGISTICS, CODEWORD
  const [activeTab, setActiveTab] = useState('entities'); // 'entities', 'handovers', 'media', 'artifacts', 'rendezvous', 'matrix'

  // Selected Item for Drill-Down Inspector
  const [selectedInspectorItem, setSelectedInspectorItem] = useState(null);

  // Configuration Parameters
  const [configParams, setConfigParams] = useState({
    handover_threshold_seconds: 180,
    media_hamming_distance: 4,
    rendezvous_distance_meters: 50.0,
    rendezvous_time_seconds: 1800,
    custom_keywords_input: 'secret, cash, transfer, drop, package',
  });

  const [statusNotification, setStatusNotification] = useState(null);

  // Load all correlation data
  const loadCorrelationData = useCallback(async () => {
    if (!caseId) return;
    try {
      setLoading(true);
      const [
        edgesData,
        entitiesData,
        matrixData,
        statusData,
        personsData,
        handoversData,
        mediaData,
        artifactsData,
        rendezvousData,
        graphRes,
      ] = await Promise.all([
        correlationService.getCorrelationEdges(caseId).catch(() => []),
        correlationService.getEntityResolutions(caseId).catch(() => []),
        correlationService.getMessageMatrix(caseId, windowSeconds).catch(() => []),
        correlationService.getCorrelationStatus(caseId).catch(() => ({ has_whatsapp: false, has_telegram: false, evidence_count: 0 })),
        correlationService.getResolvedPersons(caseId).catch(() => []),
        correlationService.getPlatformHandovers(caseId).catch(() => []),
        correlationService.getMediaCorrelations(caseId).catch(() => []),
        correlationService.getSharedArtifacts(caseId).catch(() => []),
        correlationService.getRendezvousEvents(caseId).catch(() => []),
        correlationService.getCorrelationGraph(caseId).catch(() => ({ nodes: [], edges: [], metadata: {} })),
      ]);

      setEdges(edgesData || []);
      setEntities(entitiesData || []);
      setMatrix(matrixData || []);
      setPersons(personsData || []);
      setHandovers(handoversData || []);
      setMediaMatches(mediaData || []);
      setArtifacts(artifactsData || []);
      setRendezvous(rendezvousData || []);
      setGraphData(graphRes || { nodes: [], edges: [], metadata: {} });

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

  // Run Deep Correlation Engine
  const handleRunDeepCorrelation = async () => {
    try {
      setCorrelateLoading(true);
      const keywords = configParams.custom_keywords_input
        ? configParams.custom_keywords_input.split(',').map((k) => k.trim()).filter(Boolean)
        : [];

      const payload = {
        handover_threshold_seconds: Number(configParams.handover_threshold_seconds),
        media_hamming_distance: Number(configParams.media_hamming_distance),
        rendezvous_distance_meters: Number(configParams.rendezvous_distance_meters),
        rendezvous_time_seconds: Number(configParams.rendezvous_time_seconds),
        custom_keywords: keywords,
      };

      const res = await correlationService.triggerDeepCorrelation(caseId, payload);
      await loadCorrelationData();

      setStatusNotification({
        type: 'success',
        message: `R4 Deep Correlation completed! Resolved ${res.persons_count} Persons, ${res.handovers_count} Handovers, ${res.media_matches_count} Media Links, ${res.artifacts_count} Artifacts, and ${res.rendezvous_count} Rendezvous Events.`,
      });
      setShowConfigModal(false);
      setTimeout(() => setStatusNotification(null), 8000);
    } catch (err) {
      console.error('Failed to run deep correlation:', err);
      setStatusNotification({
        type: 'error',
        message: 'Failed to run Deep Correlation Engine. Check backend logs.',
      });
      setTimeout(() => setStatusNotification(null), 8000);
    } finally {
      setCorrelateLoading(false);
    }
  };

  const formatDate = (ts) => {
    if (!ts) return 'N/A';
    try {
      const date = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts);
      return format(date, 'MMM d, yyyy HH:mm:ss');
    } catch (e) {
      return String(ts);
    }
  };

  // Filtered Persons & Entities
  const filteredPersons = persons.filter((p) => {
    const term = searchTerm.toLowerCase();
    return (
      (p.label && p.label.toLowerCase().includes(term)) ||
      (p.phone_numbers && p.phone_numbers.some((ph) => ph.toLowerCase().includes(term))) ||
      (p.handles && p.handles.some((h) => h.toLowerCase().includes(term))) ||
      (p.aliases && p.aliases.some((a) => a.toLowerCase().includes(term)))
    );
  });

  const ambiguousEdges = edges.filter((e) => (e.metadata || {}).is_ambiguous);

  // Filtered Handovers
  const filteredHandovers = handovers.filter((h) => {
    const term = searchTerm.toLowerCase();
    return (
      (h.from_body && h.from_body.toLowerCase().includes(term)) ||
      (h.to_body && h.to_body.toLowerCase().includes(term)) ||
      (h.transition_keywords && h.transition_keywords.some((k) => k.toLowerCase().includes(term))) ||
      (h.from_sender && h.from_sender.toLowerCase().includes(term))
    );
  });

  // Filtered Artifacts
  const filteredArtifacts = artifacts.filter((a) => {
    const term = searchTerm.toLowerCase();
    const matchesCategory = artifactFilter === 'ALL' || a.artifact_category === artifactFilter;
    const matchesTerm =
      (a.value && a.value.toLowerCase().includes(term)) ||
      (a.artifact_type && a.artifact_type.toLowerCase().includes(term)) ||
      (a.context_snippet && a.context_snippet.toLowerCase().includes(term));
    return matchesCategory && matchesTerm;
  });

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
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{statusNotification.message}</span>
            </div>
            <button onClick={() => setStatusNotification(null)} className="hover:opacity-80 ml-4">
              ✕
            </button>
          </div>
        )}

        {/* Header Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-forensic-900/60 p-4 rounded-xl border border-forensic-800 backdrop-blur-sm">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <GitFork className="w-5 h-5 text-accent-cyan" />
              <h2 className="text-lg font-bold font-mono text-forensic-50">
                R4 Deep Cross-Platform Correlation Engine
              </h2>
              <span className="badge badge-cyan text-[10px] font-mono">Judicial Admissibility Enforced</span>
            </div>
            <p className="text-xs text-forensic-400">
              Multi-entity identity resolution, platform handovers, perceptual media hashing, deterministic artifacts, and rendezvous analysis.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowConfigModal(true)}
              className="btn-secondary inline-flex items-center gap-2 text-xs font-mono py-2 px-3"
            >
              <Sliders className="w-3.5 h-3.5" />
              Tune Parameters
            </button>

            <button
              onClick={handleRunDeepCorrelation}
              disabled={correlateLoading}
              className="btn-primary inline-flex items-center gap-2 text-xs font-mono py-2 px-3 whitespace-nowrap"
            >
              {correlateLoading ? (
                <RefreshCw className="w-4 h-4 animate-spin text-forensic-950" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
              {correlateLoading ? 'Correlating Case...' : 'Run Deep Correlation'}
            </button>
          </div>
        </div>

        {/* Configuration Modal */}
        {showConfigModal && (
          <div className="fixed inset-0 bg-forensic-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-forensic-900 border border-forensic-700 rounded-2xl p-6 max-w-lg w-full space-y-4 shadow-2xl">
              <div className="flex items-center justify-between border-b border-forensic-800 pb-3">
                <div className="flex items-center gap-2 text-forensic-100 font-mono font-bold text-sm">
                  <Sliders className="w-4 h-4 text-accent-cyan" />
                  R4 Correlation Parameters
                </div>
                <button
                  onClick={() => setShowConfigModal(false)}
                  className="text-forensic-400 hover:text-forensic-200"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="space-y-3 text-xs font-mono text-forensic-300">
                <div>
                  <label className="block mb-1 text-forensic-200">
                    Platform Handover Threshold (Seconds)
                  </label>
                  <input
                    type="number"
                    value={configParams.handover_threshold_seconds}
                    onChange={(e) =>
                      setConfigParams({ ...configParams, handover_threshold_seconds: e.target.value })
                    }
                    className="w-full bg-forensic-950 border border-forensic-700 rounded-lg p-2 text-forensic-100"
                  />
                  <span className="text-[10px] text-forensic-500">
                    Max seconds between cross-app messages to qualify as candidate handover (Default: 180s).
                  </span>
                </div>

                <div>
                  <label className="block mb-1 text-forensic-200">
                    Perceptual Media Hamming Distance (Threshold)
                  </label>
                  <input
                    type="number"
                    value={configParams.media_hamming_distance}
                    onChange={(e) =>
                      setConfigParams({ ...configParams, media_hamming_distance: e.target.value })
                    }
                    className="w-full bg-forensic-950 border border-forensic-700 rounded-lg p-2 text-forensic-100"
                  />
                  <span className="text-[10px] text-forensic-500">
                    Max bitwise difference for pHash/dHash linkage (Default: 4).
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block mb-1 text-forensic-200">Rendezvous Distance (Meters)</label>
                    <input
                      type="number"
                      value={configParams.rendezvous_distance_meters}
                      onChange={(e) =>
                        setConfigParams({ ...configParams, rendezvous_distance_meters: e.target.value })
                      }
                      className="w-full bg-forensic-950 border border-forensic-700 rounded-lg p-2 text-forensic-100"
                    />
                  </div>
                  <div>
                    <label className="block mb-1 text-forensic-200">Rendezvous Time (Seconds)</label>
                    <input
                      type="number"
                      value={configParams.rendezvous_time_seconds}
                      onChange={(e) =>
                        setConfigParams({ ...configParams, rendezvous_time_seconds: e.target.value })
                      }
                      className="w-full bg-forensic-950 border border-forensic-700 rounded-lg p-2 text-forensic-100"
                    />
                  </div>
                </div>

                <div>
                  <label className="block mb-1 text-forensic-200">Custom Codewords (Comma Separated)</label>
                  <input
                    type="text"
                    value={configParams.custom_keywords_input}
                    onChange={(e) =>
                      setConfigParams({ ...configParams, custom_keywords_input: e.target.value })
                    }
                    placeholder="e.g. secret, cash, drop, package"
                    className="w-full bg-forensic-950 border border-forensic-700 rounded-lg p-2 text-forensic-100"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-forensic-800">
                <button
                  onClick={() => setShowConfigModal(false)}
                  className="btn-secondary text-xs font-mono py-1.5 px-3"
                >
                  Cancel
                </button>
                <button
                  onClick={handleRunDeepCorrelation}
                  disabled={correlateLoading}
                  className="btn-primary text-xs font-mono py-1.5 px-4"
                >
                  Save & Run
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Metrics Summary Overview */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div
            onClick={() => setActiveTab('entities')}
            className={`card bg-forensic-900/40 border-forensic-800 p-3 cursor-pointer transition-all ${
              activeTab === 'entities' ? 'ring-2 ring-accent-cyan/60 border-accent-cyan' : 'hover:border-forensic-700'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-mono text-forensic-400">Persons</span>
              <Users className="w-4 h-4 text-accent-cyan" />
            </div>
            <div className="text-xl font-bold font-mono text-forensic-50">{persons.length}</div>
            <div className="text-[10px] text-forensic-500 font-mono">Resolved Clusters</div>
          </div>

          <div
            onClick={() => setActiveTab('handovers')}
            className={`card bg-forensic-900/40 border-forensic-800 p-3 cursor-pointer transition-all ${
              activeTab === 'handovers' ? 'ring-2 ring-amber-500/60 border-amber-500' : 'hover:border-forensic-700'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-mono text-forensic-400">Handovers</span>
              <Zap className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-xl font-bold font-mono text-forensic-50">{handovers.length}</div>
            <div className="text-[10px] text-forensic-500 font-mono">Sequence Shifts</div>
          </div>

          <div
            onClick={() => setActiveTab('media')}
            className={`card bg-forensic-900/40 border-forensic-800 p-3 cursor-pointer transition-all ${
              activeTab === 'media' ? 'ring-2 ring-indigo-500/60 border-indigo-500' : 'hover:border-forensic-700'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-mono text-forensic-400">Media Hash</span>
              <FileImage className="w-4 h-4 text-indigo-400" />
            </div>
            <div className="text-xl font-bold font-mono text-forensic-50">{mediaMatches.length}</div>
            <div className="text-[10px] text-forensic-500 font-mono">dHash/pHash Links</div>
          </div>

          <div
            onClick={() => setActiveTab('artifacts')}
            className={`card bg-forensic-900/40 border-forensic-800 p-3 cursor-pointer transition-all ${
              activeTab === 'artifacts' ? 'ring-2 ring-accent-emerald/60 border-accent-emerald' : 'hover:border-forensic-700'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-mono text-forensic-400">Artifacts</span>
              <Coins className="w-4 h-4 text-accent-emerald" />
            </div>
            <div className="text-xl font-bold font-mono text-forensic-50">{artifacts.length}</div>
            <div className="text-[10px] text-forensic-500 font-mono">Crypto/Bank/Code</div>
          </div>

          <div
            onClick={() => setActiveTab('rendezvous')}
            className={`card bg-forensic-900/40 border-forensic-800 p-3 cursor-pointer transition-all ${
              activeTab === 'rendezvous' ? 'ring-2 ring-rose-500/60 border-rose-500' : 'hover:border-forensic-700'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-mono text-forensic-400">Rendezvous</span>
              <MapPin className="w-4 h-4 text-rose-400" />
            </div>
            <div className="text-xl font-bold font-mono text-forensic-50">{rendezvous.length}</div>
            <div className="text-[10px] text-forensic-500 font-mono">GPS Co-occurrences</div>
          </div>

          <div
            onClick={() => setActiveTab('matrix')}
            className={`card bg-forensic-900/40 border-forensic-800 p-3 cursor-pointer transition-all ${
              activeTab === 'matrix' ? 'ring-2 ring-cyan-500/60 border-cyan-500' : 'hover:border-forensic-700'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-mono text-forensic-400">Exchange Matrix</span>
              <MessageSquare className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="text-xl font-bold font-mono text-forensic-50">{matrix.length}</div>
            <div className="text-[10px] text-forensic-500 font-mono">Temporal Pairs</div>
          </div>
        </div>

        {/* Tab Selector Navigation Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 bg-forensic-900/60 p-2.5 rounded-xl border border-forensic-800">
          <div className="flex flex-wrap items-center gap-1.5 text-xs font-mono">
            <button
              onClick={() => setActiveTab('entities')}
              className={`px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 ${
                activeTab === 'entities'
                  ? 'bg-accent-cyan/20 text-accent-cyan font-semibold border border-accent-cyan/40'
                  : 'text-forensic-400 hover:text-forensic-200'
              }`}
            >
              <Users className="w-3.5 h-3.5" />
              Identity Graph ({persons.length})
            </button>

            <button
              onClick={() => setActiveTab('handovers')}
              className={`px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 ${
                activeTab === 'handovers'
                  ? 'bg-amber-500/20 text-amber-400 font-semibold border border-amber-500/40'
                  : 'text-forensic-400 hover:text-forensic-200'
              }`}
            >
              <Zap className="w-3.5 h-3.5" />
              Platform Handovers ({handovers.length})
            </button>

            <button
              onClick={() => setActiveTab('media')}
              className={`px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 ${
                activeTab === 'media'
                  ? 'bg-indigo-500/20 text-indigo-400 font-semibold border border-indigo-500/40'
                  : 'text-forensic-400 hover:text-forensic-200'
              }`}
            >
              <FileImage className="w-3.5 h-3.5" />
              Perceptual Media ({mediaMatches.length})
            </button>

            <button
              onClick={() => setActiveTab('artifacts')}
              className={`px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 ${
                activeTab === 'artifacts'
                  ? 'bg-accent-emerald/20 text-accent-emerald font-semibold border border-accent-emerald/40'
                  : 'text-forensic-400 hover:text-forensic-200'
              }`}
            >
              <Coins className="w-3.5 h-3.5" />
              Shared Artifacts ({artifacts.length})
            </button>

            <button
              onClick={() => setActiveTab('rendezvous')}
              className={`px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 ${
                activeTab === 'rendezvous'
                  ? 'bg-rose-500/20 text-rose-400 font-semibold border border-rose-500/40'
                  : 'text-forensic-400 hover:text-forensic-200'
              }`}
            >
              <MapPin className="w-3.5 h-3.5" />
              Rendezvous ({rendezvous.length})
            </button>

            <button
              onClick={() => setActiveTab('matrix')}
              className={`px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 ${
                activeTab === 'matrix'
                  ? 'bg-cyan-500/20 text-cyan-400 font-semibold border border-cyan-500/40'
                  : 'text-forensic-400 hover:text-forensic-200'
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              Message Matrix ({matrix.length})
            </button>
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-forensic-500" />
            <input
              type="text"
              placeholder="Search findings..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input-search pl-9 py-1 text-xs w-full font-mono"
            />
          </div>
        </div>

        {/* Loading State */}
        {loading ? (
          <div className="card p-12 flex flex-col items-center justify-center text-center border-forensic-800">
            <RefreshCw className="w-8 h-8 animate-spin text-accent-cyan mb-3" />
            <p className="text-sm font-mono text-forensic-300">Evaluating multi-entity forensic correlations...</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* TAB 1: IDENTITY RESOLUTION & PERSON CLUSTERS */}
            {activeTab === 'entities' && (
              <div className="space-y-4">
                {/* Ambiguous Match Warning Alert if any exist */}
                {ambiguousEdges.length > 0 && (
                  <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                    <div className="text-xs font-mono text-forensic-200">
                      <span className="font-bold text-amber-300">Forensic Rule Warning: </span>
                      {ambiguousEdges.length} ambiguous name match candidate(s) detected. Per judicial admissibility standards, individuals are NEVER merged into Person entities solely on display name similarity without E.164 phone or account corroboration.
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {filteredPersons.length === 0 ? (
                    <div className="col-span-2 card p-8 text-center text-forensic-400 text-xs font-mono">
                      No resolved Person clusters found. Click &quot;Run Deep Correlation&quot; to cluster identities.
                    </div>
                  ) : (
                    filteredPersons.map((p) => (
                      <div
                        key={p.person_id}
                        className="card bg-forensic-900/60 border-forensic-800 p-4 hover:border-accent-cyan/40 transition-colors space-y-3"
                      >
                        <div className="flex items-center justify-between border-b border-forensic-800/80 pb-2.5">
                          <div className="flex items-center gap-2">
                            <div className="w-8 h-8 rounded-lg bg-accent-cyan/20 border border-accent-cyan/40 flex items-center justify-center text-accent-cyan font-bold font-mono text-xs">
                              {p.label ? p.label[0].toUpperCase() : 'P'}
                            </div>
                            <div>
                              <div className="text-xs font-bold font-mono text-forensic-100 flex items-center gap-2">
                                {p.label}
                                {p.is_ambiguous && (
                                  <span className="badge badge-amber text-[10px]">Ambiguous</span>
                                )}
                              </div>
                              <div className="text-[10px] font-mono text-forensic-500">{p.person_id}</div>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            <span className="badge badge-cyan text-[10px] font-mono">
                              {Math.round(p.confidence_score * 100)}% Confidence
                            </span>
                            <button
                              onClick={() => setSelectedInspectorItem(p)}
                              className="btn-secondary text-[11px] font-mono py-1 px-2 flex items-center gap-1"
                              title="Drill-down to evidence"
                            >
                              <Eye className="w-3 h-3" />
                              Inspect
                            </button>
                          </div>
                        </div>

                        {/* Accounts Grid */}
                        <div className="space-y-1.5">
                          <div className="text-[11px] font-mono text-forensic-400">Corroborated Accounts:</div>
                          <div className="flex flex-wrap gap-2">
                            {p.resolved_accounts && p.resolved_accounts.map((acc, idx) => (
                              <div
                                key={idx}
                                className={`px-2.5 py-1 rounded-md text-[11px] font-mono flex items-center gap-1.5 border ${
                                  acc.platform === 'whatsapp'
                                    ? 'bg-accent-emerald/10 border-accent-emerald/30 text-accent-emerald'
                                    : 'bg-accent-blue/10 border-accent-blue/30 text-accent-blue'
                                }`}
                              >
                                <span className="w-1.5 h-1.5 rounded-full bg-current" />
                                <span className="font-semibold capitalize">{acc.platform}:</span>
                                <span>{acc.display_name || acc.account_id}</span>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Phone & Handles */}
                        <div className="flex flex-wrap gap-3 text-xs font-mono pt-1">
                          {p.phone_numbers && p.phone_numbers.length > 0 && (
                            <div className="flex items-center gap-1 text-accent-cyan">
                              <Phone className="w-3 h-3" />
                              <span>{p.phone_numbers.join(', ')}</span>
                            </div>
                          )}
                          {p.handles && p.handles.length > 0 && (
                            <div className="flex items-center gap-1 text-accent-blue">
                              <Hash className="w-3 h-3" />
                              <span>{p.handles.join(', ')}</span>
                            </div>
                          )}
                        </div>

                        {/* Limitations Pill */}
                        {p.limitations && p.limitations.length > 0 && (
                          <div className="text-[10px] text-forensic-400 bg-forensic-950 p-2 rounded border border-forensic-800/60 font-mono">
                            <span className="text-amber-400 font-semibold">Limitations: </span>
                            {p.limitations.join(' ')}
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* TAB 2: PLATFORM HANDOVERS */}
            {activeTab === 'handovers' && (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-forensic-900/60 border border-forensic-800 flex items-center justify-between">
                  <div className="text-xs font-mono text-forensic-300">
                    <span className="font-bold text-amber-400">Platform Handover Detector: </span>
                    Identifies communication sequences shifting between platforms within temporal proximity ({configParams.handover_threshold_seconds}s) with transition language.
                  </div>
                  <span className="badge badge-amber text-[10px] font-mono">
                    {filteredHandovers.length} Candidates
                  </span>
                </div>

                {filteredHandovers.length === 0 ? (
                  <div className="card p-8 text-center text-forensic-400 text-xs font-mono">
                    No platform handover sequences detected for current threshold ({configParams.handover_threshold_seconds}s).
                  </div>
                ) : (
                  <div className="space-y-3">
                    {filteredHandovers.map((h, idx) => (
                      <div
                        key={idx}
                        className="card bg-forensic-900/60 border-forensic-800 p-4 hover:border-amber-500/40 transition-colors space-y-3"
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-forensic-800 pb-2">
                          <div className="flex items-center gap-2">
                            <span className="badge badge-amber text-[10px] font-mono">
                              {h.classification || 'PLATFORM_HANDOVER_CANDIDATE'}
                            </span>
                            <span className="text-xs font-mono text-forensic-400">
                              ⚡ Delta: <strong className="text-amber-300">{h.time_delta_seconds}s</strong> (≤ {h.threshold_seconds}s)
                            </span>
                          </div>
                          <span className="text-[11px] font-mono text-forensic-400">
                            Confidence: {Math.round(h.confidence_score * 100)}%
                          </span>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {/* From Platform */}
                          <div className="p-3 bg-forensic-950 rounded-lg border border-forensic-800 space-y-1">
                            <div className="flex items-center justify-between text-[11px] font-mono text-forensic-400">
                              <span className="capitalize font-semibold text-accent-emerald">{h.from_platform}</span>
                              <span>{formatDate(h.from_timestamp)}</span>
                            </div>
                            <div className="text-xs text-forensic-200 font-sans p-2 rounded bg-forensic-900/60 border border-forensic-800/80">
                              {h.from_body || '[Attachment]'}
                            </div>
                            <div className="text-[10px] font-mono text-forensic-500">From: {h.from_sender}</div>
                          </div>

                          {/* To Platform */}
                          <div className="p-3 bg-forensic-950 rounded-lg border border-forensic-800 space-y-1">
                            <div className="flex items-center justify-between text-[11px] font-mono text-forensic-400">
                              <span className="capitalize font-semibold text-accent-blue">{h.to_platform}</span>
                              <span>{formatDate(h.to_timestamp)}</span>
                            </div>
                            <div className="text-xs text-forensic-200 font-sans p-2 rounded bg-forensic-900/60 border border-forensic-800/80">
                              {h.to_body || '[Attachment]'}
                            </div>
                            <div className="text-[10px] font-mono text-forensic-500">To: {h.to_sender}</div>
                          </div>
                        </div>

                        {h.transition_keywords && h.transition_keywords.length > 0 && (
                          <div className="flex items-center gap-2 text-xs font-mono">
                            <span className="text-forensic-400 text-[11px]">Matched Transition Phrases:</span>
                            {h.transition_keywords.map((kw, kidx) => (
                              <span key={kidx} className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20 text-[10px]">
                                &ldquo;{kw}&rdquo;
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: PERCEPTUAL MEDIA MATCHES */}
            {activeTab === 'media' && (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-forensic-900/60 border border-forensic-800 flex items-center justify-between">
                  <div className="text-xs font-mono text-forensic-300">
                    <span className="font-bold text-indigo-400">Perceptual Media Correlator: </span>
                    Matches visually equivalent, resized, or re-compressed exhibits using dHash and 2D-DCT pHash (Threshold ≤ {configParams.media_hamming_distance} bits).
                  </div>
                  <span className="badge badge-indigo text-[10px] font-mono">
                    {mediaMatches.length} Links
                  </span>
                </div>

                {mediaMatches.length === 0 ? (
                  <div className="card p-8 text-center text-forensic-400 text-xs font-mono">
                    No perceptual media hash matches detected within Hamming distance threshold ({configParams.media_hamming_distance}).
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {mediaMatches.map((m, idx) => (
                      <div
                        key={idx}
                        className="card bg-forensic-900/60 border-forensic-800 p-4 space-y-3 hover:border-indigo-500/40 transition-colors"
                      >
                        <div className="flex items-center justify-between border-b border-forensic-800 pb-2">
                          <span className="badge badge-indigo text-[10px] font-mono">
                            Bitwise Hamming Distance: {m.min_distance} (≤ {m.threshold})
                          </span>
                          <span className="text-xs font-mono text-accent-cyan">
                            {Math.round(m.confidence_score * 100)}% Similarity
                          </span>
                        </div>

                        <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                          <div className="p-2.5 bg-forensic-950 rounded-lg border border-forensic-800 space-y-1">
                            <div className="font-bold text-forensic-100 truncate">{m.source_filename}</div>
                            <div className="text-[10px] text-forensic-400 truncate">SHA: {m.source_sha256}</div>
                            <div className="text-[10px] text-indigo-300 truncate">pHash: {m.source_phash}</div>
                            <div className="text-[10px] text-indigo-300 truncate">dHash: {m.source_dhash}</div>
                          </div>

                          <div className="p-2.5 bg-forensic-950 rounded-lg border border-forensic-800 space-y-1">
                            <div className="font-bold text-forensic-100 truncate">{m.target_filename}</div>
                            <div className="text-[10px] text-forensic-400 truncate">SHA: {m.target_sha256}</div>
                            <div className="text-[10px] text-indigo-300 truncate">pHash: {m.target_phash}</div>
                            <div className="text-[10px] text-indigo-300 truncate">dHash: {m.target_dhash}</div>
                          </div>
                        </div>

                        <div className="text-[10px] font-mono text-forensic-500">
                          {m.limitations && m.limitations.join(' ')}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* TAB 4: SHARED ARTIFACT STITCHING */}
            {activeTab === 'artifacts' && (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3 bg-forensic-900/60 p-3 rounded-xl border border-forensic-800">
                  <div className="flex items-center gap-2 text-xs font-mono">
                    <span className="text-forensic-400">Filter Category:</span>
                    {['ALL', 'CRYPTO', 'BANKING', 'LOGISTICS', 'CODEWORD'].map((cat) => (
                      <button
                        key={cat}
                        onClick={() => setArtifactFilter(cat)}
                        className={`px-2.5 py-1 rounded-md transition-colors ${
                          artifactFilter === cat
                            ? 'bg-accent-emerald/20 text-accent-emerald font-semibold border border-accent-emerald/40'
                            : 'text-forensic-400 hover:text-forensic-200'
                        }`}
                      >
                        {cat}
                      </button>
                    ))}
                  </div>
                  <span className="badge badge-emerald text-[10px] font-mono">
                    {filteredArtifacts.length} Artifacts Discovered
                  </span>
                </div>

                {filteredArtifacts.length === 0 ? (
                  <div className="card p-8 text-center text-forensic-400 text-xs font-mono">
                    No matching deterministic artifacts found for current category.
                  </div>
                ) : (
                  <div className="card border-forensic-800 p-0 overflow-hidden">
                    <div className="overflow-x-auto">
                      <table className="table-forensic text-xs">
                        <thead>
                          <tr>
                            <th>Type</th>
                            <th>Extracted Value</th>
                            <th>Checksum / Validation</th>
                            <th>Context Snippet</th>
                            <th>Platform & Evidence</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredArtifacts.map((art) => (
                            <tr key={art.artifact_id} className="hover:bg-forensic-900/40">
                              <td className="py-2.5 px-4 font-mono font-bold text-accent-cyan">
                                {art.artifact_type}
                              </td>
                              <td className="py-2.5 px-4 font-mono text-forensic-100">
                                <span className="bg-forensic-950 px-2 py-0.5 rounded border border-forensic-800">
                                  {art.value}
                                </span>
                              </td>
                              <td className="py-2.5 px-4">
                                <span
                                  className={`badge text-[10px] font-mono ${
                                    art.is_validated ? 'badge-emerald' : 'badge-amber'
                                  }`}
                                >
                                  {art.validation_status}
                                </span>
                              </td>
                              <td className="py-2.5 px-4 text-forensic-300 font-sans max-w-xs truncate">
                                &ldquo;{art.context_snippet}&rdquo;
                              </td>
                              <td className="py-2.5 px-4 font-mono text-forensic-400 capitalize">
                                {art.source_platform}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* TAB 5: SPATIOTEMPORAL RENDEZVOUS */}
            {activeTab === 'rendezvous' && (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-forensic-900/60 border border-forensic-800 flex items-center justify-between">
                  <div className="text-xs font-mono text-forensic-300">
                    <span className="font-bold text-rose-400">Spatiotemporal Rendezvous Detector: </span>
                    Analyzes EXIF GPS coordinates and live location messages for co-presence opportunities (Distance ≤ {configParams.rendezvous_distance_meters}m, Time ≤ {configParams.rendezvous_time_seconds}s).
                  </div>
                  <span className="badge badge-rose text-[10px] font-mono">
                    {rendezvous.length} Events
                  </span>
                </div>

                {rendezvous.length === 0 ? (
                  <div className="card p-8 text-center text-forensic-400 text-xs font-mono">
                    No rendezvous co-presence events meeting distance (≤ {configParams.rendezvous_distance_meters}m) and time (≤ {configParams.rendezvous_time_seconds}s) criteria.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {rendezvous.map((r, idx) => (
                      <div
                        key={idx}
                        className="card bg-forensic-900/60 border-forensic-800 p-4 space-y-3 hover:border-rose-500/40 transition-colors"
                      >
                        <div className="flex items-center justify-between border-b border-forensic-800 pb-2">
                          <span className="badge badge-rose text-[10px] font-mono">
                            Distance: {r.distance_meters}m (≤ {r.distance_threshold_meters}m)
                          </span>
                          <span className="text-xs font-mono text-amber-300">
                            Time Delta: {r.time_delta_seconds}s
                          </span>
                        </div>

                        <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                          <div className="p-2.5 bg-forensic-950 rounded border border-forensic-800 space-y-1">
                            <div className="text-accent-cyan font-bold capitalize">
                              {r.observation_a.platform} Location
                            </div>
                            <div className="text-[10px] text-forensic-300">
                              Lat: {r.observation_a.latitude}, Lon: {r.observation_a.longitude}
                            </div>
                            <div className="text-[10px] text-forensic-500">
                              Time: {formatDate(r.observation_a.timestamp)}
                            </div>
                          </div>

                          <div className="p-2.5 bg-forensic-950 rounded border border-forensic-800 space-y-1">
                            <div className="text-accent-blue font-bold capitalize">
                              {r.observation_b.platform} Location
                            </div>
                            <div className="text-[10px] text-forensic-300">
                              Lat: {r.observation_b.latitude}, Lon: {r.observation_b.longitude}
                            </div>
                            <div className="text-[10px] text-forensic-500">
                              Time: {formatDate(r.observation_b.timestamp)}
                            </div>
                          </div>
                        </div>

                        <div className="text-[10px] font-mono text-forensic-400 bg-forensic-950 p-2 rounded">
                          {r.limitations && r.limitations.join(' ')}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* TAB 6: TIME-WINDOW MESSAGE MATRIX */}
            {activeTab === 'matrix' && (
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
                    Showing {matrix.length} Correlated Pairs
                  </span>
                </div>

                {matrix.length === 0 ? (
                  <div className="p-8 text-center text-forensic-400 text-xs font-mono">
                    No cross-app message exchanges detected within {windowSeconds}s. Try adjusting the window threshold.
                  </div>
                ) : (
                  <div className="p-4 space-y-4 bg-forensic-950">
                    {matrix.map((item) => (
                      <div
                        key={item.id}
                        className="card bg-forensic-900/40 border-forensic-800 p-4 hover:border-accent-cyan/40 transition-colors"
                      >
                        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">
                          {/* WhatsApp Left */}
                          <div className="flex-1 bg-forensic-950 p-3.5 rounded-lg border border-accent-emerald/30">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-accent-emerald/15 text-accent-emerald font-semibold">
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
                              {item.wa_body || <span className="italic text-forensic-500">[Media attachment]</span>}
                            </div>
                          </div>

                          {/* Delta Badge */}
                          <div className="flex flex-col items-center justify-center px-2">
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

                          {/* Telegram Right */}
                          <div className="flex-1 bg-forensic-950 p-3.5 rounded-lg border border-accent-blue/30">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-accent-blue/15 text-accent-blue font-semibold">
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
                              {item.tg_body || <span className="italic text-forensic-500">[Media attachment]</span>}
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

        {/* Evidence Drill-Down Drawer / Inspector */}
        {selectedInspectorItem && (
          <div className="fixed inset-y-0 right-0 w-full sm:w-[480px] bg-forensic-950 border-l border-forensic-800 p-6 z-50 shadow-2xl overflow-y-auto space-y-6">
            <div className="flex items-center justify-between border-b border-forensic-800 pb-3">
              <div className="flex items-center gap-2 text-forensic-100 font-mono font-bold text-sm">
                <ShieldCheck className="w-4 h-4 text-accent-cyan" />
                Evidence Provenance Inspector
              </div>
              <button
                onClick={() => setSelectedInspectorItem(null)}
                className="text-forensic-400 hover:text-forensic-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4 text-xs font-mono">
              <div>
                <span className="text-forensic-500">Entity Cluster ID:</span>
                <div className="text-forensic-100 font-bold">{selectedInspectorItem.person_id}</div>
              </div>

              <div>
                <span className="text-forensic-500">Resolution Method:</span>
                <div className="text-accent-cyan font-semibold">{selectedInspectorItem.resolution_method}</div>
              </div>

              <div>
                <span className="text-forensic-500">Confidence Score:</span>
                <div className="text-forensic-100">
                  {Math.round((selectedInspectorItem.confidence_score || 1.0) * 100)}% (Mathematical Corroboration)
                </div>
              </div>

              <div>
                <span className="text-forensic-500">Corroborated Telecommunication Numbers:</span>
                <div className="space-y-1 mt-1">
                  {selectedInspectorItem.phone_numbers && selectedInspectorItem.phone_numbers.map((ph, i) => (
                    <div key={i} className="p-2 bg-forensic-900 rounded border border-forensic-800 text-forensic-200">
                      {ph}
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <span className="text-forensic-500">Source Evidence References:</span>
                <div className="space-y-1 mt-1">
                  {selectedInspectorItem.evidence_links && selectedInspectorItem.evidence_links.map((link, i) => (
                    <div key={i} className="p-2 bg-forensic-900 rounded border border-forensic-800 text-forensic-300">
                      Platform: <span className="capitalize text-forensic-100">{link.platform}</span> | Evidence Exhibit #{link.evidence_id} | ID: {link.identifier}
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <span className="text-forensic-500">Judicial Limitations & Constraints:</span>
                <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg text-forensic-200 space-y-1">
                  {selectedInspectorItem.limitations && selectedInspectorItem.limitations.length > 0 ? (
                    selectedInspectorItem.limitations.map((lim, i) => <div key={i}>• {lim}</div>)
                  ) : (
                    <div>• Exact cryptographic or E.164 telecom equivalence established.</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </CaseWorkspacePage>
  );
};

export default CorrelationPage;
