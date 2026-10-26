import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import correlationService from '../services/correlationService';
import { formatContactLabel } from './TimelinePage';
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
  Sliders,
  X,
  ExternalLink,
  ChevronRight,
  Eye,
  Info,
  Link2,
  HelpCircle,
  ArrowLeftRight,
} from 'lucide-react';
import { format } from 'date-fns';

const TIME_WINDOWS = [
  { label: '1 Minute (60s)', value: 60 },
  { label: '3 Minutes (180s)', value: 180 },
  { label: '5 Minutes (300s)', value: 300 },
  { label: '15 Minutes (900s)', value: 900 },
  { label: '30 Minutes (1800s)', value: 1800 },
];

/**
 * Categorize confidence into intuitive, forensically sound certainty tiers.
 * Explains *why* the score was awarded rather than presenting arbitrary numbers.
 */
const getConfidenceTier = (score: number) => {
  const pct = Math.round((score || 0) * 100);
  if (pct >= 90) {
    return {
      pct,
      tierName: 'Deterministic Proof',
      tierLevel: 'Tier 1',
      badgeClass: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30',
      dotClass: 'bg-emerald-500',
      description: 'Direct cryptographic hash equality or verified telecom E.164 phone identity.',
    };
  }
  if (pct >= 75) {
    return {
      pct,
      tierName: 'Corroborated Evidence',
      tierLevel: 'Tier 2',
      badgeClass: 'bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 border-cyan-500/30',
      dotClass: 'bg-cyan-500',
      description: 'Multi-factor alignment (e.g. explicit handover phrase + prompt cross-app reply).',
    };
  }
  if (pct >= 60) {
    return {
      pct,
      tierName: 'Probable Sequence',
      tierLevel: 'Tier 3',
      badgeClass: 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30',
      dotClass: 'bg-amber-500',
      description: 'Close temporal proximity between active participants within conversation window.',
    };
  }
  return {
    pct,
    tierName: 'Contextual Proximity',
    tierLevel: 'Tier 4',
    badgeClass: 'bg-slate-500/10 text-slate-700 dark:text-slate-300 border-slate-500/30',
    dotClass: 'bg-slate-400',
    description: 'Chronological co-occurrence without corroborated participant linkage.',
  };
};

const CorrelationPage = () => {
  const { caseId } = useParams();

  const [loading, setLoading] = useState(true);
  const [correlateLoading, setCorrelateLoading] = useState(false);
  const [showConfigModal, setShowConfigModal] = useState(false);

  // Core Data States
  const [edges, setEdges] = useState<any[]>([]);
  const [entities, setEntities] = useState<any[]>([]);
  const [matrix, setMatrix] = useState<any[]>([]);
  const [persons, setPersons] = useState<any[]>([]);
  const [handovers, setHandovers] = useState<any[]>([]);
  const [mediaMatches, setMediaMatches] = useState<any[]>([]);
  const [artifacts, setArtifacts] = useState<any[]>([]);
  const [rendezvous, setRendezvous] = useState<any[]>([]);
  const [graphData, setGraphData] = useState<any>({ nodes: [], edges: [], metadata: {} });

  // Status & Counts
  const [evidenceCount, setEvidenceCount] = useState(0);
  const [hasWa, setHasWa] = useState(false);
  const [hasTg, setHasTg] = useState(false);

  // Filters & Active Tab
  const [windowSeconds, setWindowSeconds] = useState(300);
  const [searchTerm, setSearchTerm] = useState('');
  const [artifactFilter, setArtifactFilter] = useState('ALL');
  const [tierFilter, setTierFilter] = useState('ALL');
  const [activeTab, setActiveTab] = useState<'entities' | 'handovers' | 'media' | 'artifacts' | 'rendezvous' | 'matrix'>('handovers');

  // Selected Item for Drill-Down Inspector
  const [selectedInspectorItem, setSelectedInspectorItem] = useState<any>(null);

  // Configuration Parameters
  const [configParams, setConfigParams] = useState({
    handover_threshold_seconds: 180,
    media_hamming_distance: 4,
    rendezvous_distance_meters: 250.0,
    rendezvous_time_seconds: 1800,
    custom_keywords_input: 'secret, cash, transfer, drop, package',
  });

  const [statusNotification, setStatusNotification] = useState<{ type: string; message: string } | null>(null);

  // Load all correlation data
  const loadCorrelationData = useCallback(async () => {
    if (!caseId) return;
    try {
      setLoading(true);
      const results = await Promise.allSettled([
        correlationService.getCorrelationEdges(caseId),
        correlationService.getEntityResolutions(caseId),
        correlationService.getMessageMatrix(caseId, windowSeconds),
        correlationService.getCorrelationStatus(caseId),
        correlationService.getResolvedPersons(caseId),
        correlationService.getPlatformHandovers(caseId),
        correlationService.getMediaCorrelations(caseId),
        correlationService.getSharedArtifacts(caseId),
        correlationService.getRendezvousEvents(caseId),
        correlationService.getCorrelationGraph(caseId),
      ]);

      const val = (idx: number, fallback: any) =>
        results[idx].status === 'fulfilled' ? ((results[idx] as PromiseFulfilledResult<any>).value || fallback) : fallback;

      const edgesData = val(0, []);
      const entitiesData = val(1, []);
      const matrixData = val(2, []);
      const statusData = val(3, {});
      const personsData = val(4, []);
      const handoversData = val(5, []);
      const mediaData = val(6, []);
      const artifactsData = val(7, []);
      const rendezvousData = val(8, []);
      const graphRes = val(9, { nodes: [], edges: [], metadata: {} });

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
      setStatusNotification({
        type: 'error',
        message: 'Correlation data could not be loaded. Please click "Run Deep Correlation" to process cross-platform evidence.',
      });
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
        message: `R4 Deep Correlation completed successfully! Linked ${res.persons_count || 0} Persons, ${res.handovers_count || 0} Platform Handovers, ${res.media_matches_count || 0} Media Links, ${res.artifacts_count || 0} Deterministic Artifacts, and ${res.rendezvous_count || 0} Rendezvous Events.`,
      });
      setShowConfigModal(false);
      setTimeout(() => setStatusNotification(null), 8000);
    } catch (err: any) {
      console.error('Failed to run deep correlation:', err);
      setStatusNotification({
        type: 'error',
        message: err.response?.data?.detail || err.message || 'Failed to run Deep Correlation Engine.',
      });
      setTimeout(() => setStatusNotification(null), 8000);
    } finally {
      setCorrelateLoading(false);
    }
  };

  const formatDate = (ts: any) => {
    if (!ts) return 'Recorded in exhibit';
    try {
      const date = typeof ts === 'number' && ts < 10000000000 ? new Date(ts * 1000) : new Date(ts);
      return format(date, 'MMM d, yyyy HH:mm:ss') + ' UTC';
    } catch (e) {
      return String(ts);
    }
  };

  // Filtered Persons & Entities
  const filteredPersons = useMemo(() => {
    return persons.filter((p) => {
      const term = searchTerm.toLowerCase();
      const matchesSearch =
        (p.label && p.label.toLowerCase().includes(term)) ||
        (p.phone_numbers && p.phone_numbers.some((ph: string) => ph.toLowerCase().includes(term))) ||
        (p.handles && p.handles.some((h: string) => h.toLowerCase().includes(term))) ||
        (p.aliases && p.aliases.some((a: string) => a.toLowerCase().includes(term)));

      if (!matchesSearch) return false;
      if (tierFilter !== 'ALL') {
        const tier = getConfidenceTier(p.confidence_score || 0.95);
        if (tier.tierLevel !== tierFilter) return false;
      }
      return true;
    });
  }, [persons, searchTerm, tierFilter]);

  const ambiguousEdges = useMemo(() => {
    return edges.filter((e) => (e.metadata || {}).is_ambiguous);
  }, [edges]);

  // Filtered Handovers
  const filteredHandovers = useMemo(() => {
    return handovers.filter((h) => {
      const term = searchTerm.toLowerCase();
      const matchesSearch =
        (h.from_body && h.from_body.toLowerCase().includes(term)) ||
        (h.to_body && h.to_body.toLowerCase().includes(term)) ||
        (h.transition_keywords && h.transition_keywords.some((k: string) => k.toLowerCase().includes(term))) ||
        (h.from_sender && h.from_sender.toLowerCase().includes(term)) ||
        (h.to_sender && h.to_sender.toLowerCase().includes(term)) ||
        (h.rationale && h.rationale.toLowerCase().includes(term));

      if (!matchesSearch) return false;
      if (tierFilter !== 'ALL') {
        const tier = getConfidenceTier(h.confidence_score || 0.65);
        if (tier.tierLevel !== tierFilter) return false;
      }
      return true;
    });
  }, [handovers, searchTerm, tierFilter]);

  // Filtered Artifacts
  const filteredArtifacts = useMemo(() => {
    return artifacts.filter((a) => {
      const term = searchTerm.toLowerCase();
      const matchesCategory = artifactFilter === 'ALL' || a.artifact_category === artifactFilter;
      const matchesTerm =
        (a.value && a.value.toLowerCase().includes(term)) ||
        (a.artifact_type && a.artifact_type.toLowerCase().includes(term)) ||
        (a.context_snippet && a.context_snippet.toLowerCase().includes(term));
      return matchesCategory && matchesTerm;
    });
  }, [artifacts, searchTerm, artifactFilter]);

  return (
    <div className="flex-1 flex flex-col h-full bg-background text-on-surface overflow-y-auto custom-scrollbar p-6">
      <div className="space-y-6 max-w-7xl mx-auto w-full">
        {/* Status Notification Toast */}
        {statusNotification && (
          <div
            className={`p-4 rounded-xl border flex items-center justify-between text-xs font-mono animate-in ${
              statusNotification.type === 'success'
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300'
                : 'bg-red-500/10 border-red-500/30 text-red-700 dark:text-red-300'
            }`}
          >
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{statusNotification.message}</span>
            </div>
            <button onClick={() => setStatusNotification(null)} className="hover:opacity-80 ml-4 font-bold">
              ✕
            </button>
          </div>
        )}

        {/* Top Header Section */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-surface border border-outline-variant p-5 rounded-2xl shadow-sm">
          <div>
            <div className="flex items-center gap-2.5 mb-1">
              <GitFork className="w-5 h-5 text-primary" />
              <h1 className="text-xl font-bold font-mono text-on-surface">
                Cross-Platform Correlation &amp; Entity Stitching
              </h1>
              <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-primary/10 text-primary border border-primary/20">
                Judicial Proof Standards
              </span>
            </div>
            <p className="text-xs text-on-surface-variant font-sans">
              Deterministic linking of identities, platform handovers, visual media equivalence, shared crypto/codeword artifacts, and rendezvous co-presence.
            </p>
          </div>

          <div className="flex items-center gap-2.5 shrink-0">
            <button
              onClick={() => setShowConfigModal(true)}
              className="btn-secondary inline-flex items-center gap-2 text-xs font-mono py-2 px-3 h-9"
              title="Configure temporal windows, Hamming distances, and keywords"
            >
              <Sliders className="w-3.5 h-3.5 text-on-surface-variant" />
              Tune Parameters
            </button>

            <button
              onClick={handleRunDeepCorrelation}
              disabled={correlateLoading}
              className="btn-primary inline-flex items-center gap-2 text-xs font-mono py-2 px-4 h-9 whitespace-nowrap"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${correlateLoading ? 'animate-spin' : ''}`} />
              {correlateLoading ? 'Correlating Case...' : 'Run Deep Correlation'}
            </button>
          </div>
        </div>

        {/* Configuration Modal */}
        {showConfigModal && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-surface border border-outline-variant rounded-2xl p-6 max-w-lg w-full space-y-4 shadow-2xl">
              <div className="flex items-center justify-between border-b border-outline-variant pb-3">
                <div className="flex items-center gap-2 text-on-surface font-mono font-bold text-sm">
                  <Sliders className="w-4 h-4 text-primary" />
                  R4 Correlation Parameters
                </div>
                <button
                  onClick={() => setShowConfigModal(false)}
                  className="text-on-surface-variant hover:text-on-surface p-1 rounded-lg"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="space-y-3.5 text-xs font-mono text-on-surface">
                <div>
                  <label className="block mb-1 font-semibold text-on-surface">
                    Platform Handover Max Window (Seconds)
                  </label>
                  <input
                    type="number"
                    value={configParams.handover_threshold_seconds}
                    onChange={(e) =>
                      setConfigParams({ ...configParams, handover_threshold_seconds: Number(e.target.value) })
                    }
                    className="w-full bg-surface-container border border-outline-variant rounded-lg p-2.5 text-on-surface focus:border-primary focus:outline-none"
                  />
                  <span className="text-[10px] text-on-surface-variant mt-0.5 block">
                    Max interval between cross-app messages to qualify as candidate handover (Default: 180s).
                  </span>
                </div>

                <div>
                  <label className="block mb-1 font-semibold text-on-surface">
                    Perceptual Media Hamming Distance Threshold
                  </label>
                  <input
                    type="number"
                    value={configParams.media_hamming_distance}
                    onChange={(e) =>
                      setConfigParams({ ...configParams, media_hamming_distance: Number(e.target.value) })
                    }
                    className="w-full bg-surface-container border border-outline-variant rounded-lg p-2.5 text-on-surface focus:border-primary focus:outline-none"
                  />
                  <span className="text-[10px] text-on-surface-variant mt-0.5 block">
                    Max bit difference for visual similarity via dHash/pHash (0 = identical, 1–4 = recompressed).
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block mb-1 font-semibold text-on-surface">Rendezvous Distance (m)</label>
                    <input
                      type="number"
                      value={configParams.rendezvous_distance_meters}
                      onChange={(e) =>
                        setConfigParams({ ...configParams, rendezvous_distance_meters: Number(e.target.value) })
                      }
                      className="w-full bg-surface-container border border-outline-variant rounded-lg p-2.5 text-on-surface focus:border-primary focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block mb-1 font-semibold text-on-surface">Rendezvous Window (s)</label>
                    <input
                      type="number"
                      value={configParams.rendezvous_time_seconds}
                      onChange={(e) =>
                        setConfigParams({ ...configParams, rendezvous_time_seconds: Number(e.target.value) })
                      }
                      className="w-full bg-surface-container border border-outline-variant rounded-lg p-2.5 text-on-surface focus:border-primary focus:outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="block mb-1 font-semibold text-on-surface">Codewords / Watchwords (Comma Separated)</label>
                  <input
                    type="text"
                    value={configParams.custom_keywords_input}
                    onChange={(e) =>
                      setConfigParams({ ...configParams, custom_keywords_input: e.target.value })
                    }
                    placeholder="e.g. secret, cash, drop, package"
                    className="w-full bg-surface-container border border-outline-variant rounded-lg p-2.5 text-on-surface focus:border-primary focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2.5 pt-3 border-t border-outline-variant">
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
                  Save &amp; Run Analysis
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Metrics Summary Overview Tiles */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {[
            { id: 'handovers', label: 'Platform Handovers', count: handovers.length, sub: 'App Shifts', icon: Zap, color: 'text-amber-500' },
            { id: 'entities', label: 'Person Clusters', count: persons.length, sub: 'Resolved Identities', icon: Users, color: 'text-primary' },
            { id: 'media', label: 'Perceptual Media', count: mediaMatches.length, sub: 'Image Matches', icon: FileImage, color: 'text-indigo-500' },
            { id: 'artifacts', label: 'Shared Artifacts', count: artifacts.length, sub: 'Crypto & Codewords', icon: Coins, color: 'text-emerald-500' },
            { id: 'rendezvous', label: 'Rendezvous', count: rendezvous.length, sub: 'GPS Co-Presence', icon: MapPin, color: 'text-rose-500' },
            { id: 'matrix', label: 'Message Matrix', count: matrix.length, sub: 'Cross-App Exchanges', icon: MessageSquare, color: 'text-cyan-500' },
          ].map((tile) => {
            const Icon = tile.icon;
            const isActive = activeTab === tile.id;
            return (
              <div
                key={tile.id}
                onClick={() => setActiveTab(tile.id as any)}
                className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                  isActive
                    ? 'bg-surface border-primary ring-2 ring-primary/30 shadow-sm'
                    : 'bg-surface-container border-outline-variant hover:border-primary/50'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[11px] font-mono font-medium text-on-surface-variant truncate">
                    {tile.label}
                  </span>
                  <Icon className={`w-4 h-4 ${tile.color} shrink-0`} />
                </div>
                <div className="text-2xl font-bold font-mono text-on-surface">{tile.count}</div>
                <div className="text-[10px] text-on-surface-variant font-mono truncate">{tile.sub}</div>
              </div>
            );
          })}
        </div>

        {/* Filter & Sub-Nav Bar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-surface border border-outline-variant p-2 rounded-xl">
          <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
            {[
              { id: 'handovers', label: `Handovers (${handovers.length})`, icon: Zap },
              { id: 'entities', label: `Persons (${persons.length})`, icon: Users },
              { id: 'media', label: `Media Links (${mediaMatches.length})`, icon: FileImage },
              { id: 'artifacts', label: `Artifacts (${artifacts.length})`, icon: Coins },
              { id: 'rendezvous', label: `Rendezvous (${rendezvous.length})`, icon: MapPin },
              { id: 'matrix', label: `Matrix (${matrix.length})`, icon: MessageSquare },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all flex items-center gap-1.5 whitespace-nowrap ${
                    isActive
                      ? 'bg-primary text-on-primary shadow-sm'
                      : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {tab.label}
                </button>
              );
            })}
          </div>

          <div className="flex items-center gap-2">
            <select
              value={tierFilter}
              onChange={(e) => setTierFilter(e.target.value)}
              className="bg-surface-container border border-outline-variant text-on-surface text-xs rounded-lg px-2.5 py-1.5 font-mono focus:border-primary focus:outline-none"
            >
              <option value="ALL">All Certainty Tiers</option>
              <option value="Tier 1">Tier 1: Deterministic (≥90%)</option>
              <option value="Tier 2">Tier 2: Corroborated (75-89%)</option>
              <option value="Tier 3">Tier 3: Probable (60-74%)</option>
              <option value="Tier 4">Tier 4: Proximity (&lt;60%)</option>
            </select>

            <div className="relative w-full sm:w-56">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" />
              <input
                type="text"
                placeholder="Search findings..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="bg-surface-container border border-outline-variant text-on-surface pl-8 pr-3 py-1.5 text-xs w-full font-mono rounded-lg focus:border-primary focus:outline-none placeholder:text-on-surface-variant/50"
              />
            </div>
          </div>
        </div>

        {/* Loading State */}
        {loading ? (
          <div className="card p-12 flex flex-col items-center justify-center text-center border-outline-variant bg-surface">
            <RefreshCw className="w-8 h-8 animate-spin text-primary mb-3" />
            <p className="text-sm font-mono text-on-surface">Evaluating multi-entity forensic correlations...</p>
            <p className="text-xs text-on-surface-variant font-mono mt-1">Cross-referencing timeline events, SHA-256 hashes, and message payloads.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* TAB 1: PLATFORM HANDOVERS (Most intuitive cross-app transitions) */}
            {activeTab === 'handovers' && (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-surface border border-outline-variant flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-sm">
                  <div className="text-xs font-mono text-on-surface">
                    <span className="font-bold text-primary">Cross-Platform Handover Detection: </span>
                    Identifies communication sequences shifting between WhatsApp and Telegram within temporal threshold ({configParams.handover_threshold_seconds}s).
                  </div>
                  <span className="px-2.5 py-1 rounded text-[11px] font-mono font-medium bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/30 whitespace-nowrap">
                    {filteredHandovers.length} Candidates
                  </span>
                </div>

                {filteredHandovers.length === 0 ? (
                  <div className="card p-10 text-center text-on-surface-variant text-xs font-mono bg-surface border-outline-variant">
                    No cross-platform handover sequences detected for current threshold ({configParams.handover_threshold_seconds}s). Click &quot;Run Deep Correlation&quot; to re-evaluate with current parameters.
                  </div>
                ) : (
                  <div className="space-y-4">
                    {filteredHandovers.map((h, idx) => {
                      const tier = getConfidenceTier(h.confidence_score);
                      const hasKeywords = h.transition_keywords && h.transition_keywords.length > 0;
                      return (
                        <div
                          key={idx}
                          className="bg-surface border border-outline-variant rounded-xl p-5 shadow-sm hover:border-primary/50 transition-all space-y-3.5"
                        >
                          {/* Card Header: Correlation Type & Certainty Tier */}
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-outline-variant/60 pb-3">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-primary/10 text-primary border border-primary/20">
                                {hasKeywords ? 'EXPLICIT HANDOVER SEQUENCE' : 'CROSS-APP CONTINUITY CANDIDATE'}
                              </span>
                              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${tier.badgeClass}`}>
                                {tier.tierLevel}: {tier.tierName} ({tier.pct}%)
                              </span>
                              <span className="text-xs font-mono text-on-surface-variant flex items-center gap-1">
                                <Clock className="w-3.5 h-3.5 text-amber-500" />
                                Sequence Interval: <strong className="text-on-surface">{h.time_delta_seconds}s</strong> (≤ {h.threshold_seconds}s limit)
                              </span>
                            </div>

                            <button
                              onClick={() => setSelectedInspectorItem(h)}
                              className="btn-secondary text-[11px] font-mono py-1 px-2.5 h-7 flex items-center gap-1 self-start sm:self-auto"
                              title="Inspect full forensic provenance"
                            >
                              <Eye className="w-3 h-3" />
                              Inspect Provenance
                            </button>
                          </div>

                          {/* Forensic Rationale Banner: Explains WHY this correlation was established */}
                          <div className="p-2.5 rounded-lg bg-surface-container border border-outline-variant/60 flex items-start gap-2.5 text-xs font-mono text-on-surface">
                            <Info className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                            <div>
                              <span className="font-semibold text-primary">Forensic Link Rationale: </span>
                              {h.rationale || (
                                hasKeywords
                                  ? `Explicit transition phrase ('${h.transition_keywords[0]}') in WhatsApp followed by Telegram activity within ${h.time_delta_seconds}s.`
                                  : `Conversation sequence shifted from ${h.from_platform} to ${h.to_platform} within ${h.time_delta_seconds} seconds between active case participants.`
                              )}
                            </div>
                          </div>

                          {/* Side-by-Side Visual Bridge: From Platform -> To Platform */}
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* Origin Message (Left) */}
                            <div className="p-3.5 bg-surface-container-low rounded-xl border border-outline-variant/60 space-y-2">
                              <div className="flex items-center justify-between text-xs font-mono">
                                <span className="font-bold text-emerald-600 dark:text-emerald-400 capitalize flex items-center gap-1.5">
                                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                                  Origin: {h.from_platform}
                                </span>
                                <span className="text-[11px] text-on-surface-variant">{formatDate(h.from_timestamp)}</span>
                              </div>
                              <div className="text-[11px] font-mono text-on-surface-variant">
                                Sender / Key: <span className="text-on-surface font-semibold">{formatContactLabel(h.from_sender)}</span>
                              </div>
                              <div className="text-xs text-on-surface font-sans p-2.5 rounded-lg bg-surface border border-outline-variant/80">
                                {h.from_body ? (
                                  <span>&ldquo;{h.from_body}&rdquo;</span>
                                ) : (
                                  <span className="italic text-on-surface-variant font-mono text-[11px]">[Attached exhibit media / message payload]</span>
                                )}
                              </div>
                            </div>

                            {/* Destination Message (Right) */}
                            <div className="p-3.5 bg-surface-container-low rounded-xl border border-outline-variant/60 space-y-2">
                              <div className="flex items-center justify-between text-xs font-mono">
                                <span className="font-bold text-blue-600 dark:text-blue-400 capitalize flex items-center gap-1.5">
                                  <span className="w-2 h-2 rounded-full bg-blue-500" />
                                  Destination: {h.to_platform}
                                </span>
                                <span className="text-[11px] text-on-surface-variant">{formatDate(h.to_timestamp)}</span>
                              </div>
                              <div className="text-[11px] font-mono text-on-surface-variant">
                                Recipient / User: <span className="text-on-surface font-semibold">{formatContactLabel(h.to_sender)}</span>
                              </div>
                              <div className="text-xs text-on-surface font-sans p-2.5 rounded-lg bg-surface border border-outline-variant/80">
                                {h.to_body ? (
                                  <span>&ldquo;{h.to_body}&rdquo;</span>
                                ) : (
                                  <span className="italic text-on-surface-variant font-mono text-[11px]">[Attached exhibit media / message payload]</span>
                                )}
                              </div>
                            </div>
                          </div>

                          {/* Transition Keywords & Limitations Pill */}
                          <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono pt-1">
                            {hasKeywords ? (
                              <div className="flex items-center gap-1.5">
                                <span className="text-on-surface-variant text-[11px]">Matched Transition Phrases:</span>
                                {h.transition_keywords.map((kw: string, kidx: number) => (
                                  <span key={kidx} className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/20 text-[10px] font-semibold">
                                    &ldquo;{kw}&rdquo;
                                  </span>
                                ))}
                              </div>
                            ) : (
                              <div className="text-[11px] text-on-surface-variant">
                                Direct sequence co-occurrence (verified within {configParams.handover_threshold_seconds}s limit).
                              </div>
                            )}

                            {h.limitations && h.limitations.length > 0 && (
                              <span className="text-[10px] text-on-surface-variant bg-surface-container px-2 py-0.5 rounded border border-outline-variant/60">
                                ⚖️ {h.limitations[0]}
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: IDENTITY RESOLUTION & PERSON CLUSTERS */}
            {activeTab === 'entities' && (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-surface border border-outline-variant flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-sm">
                  <div className="text-xs font-mono text-on-surface">
                    <span className="font-bold text-primary">Multi-Modal Identity Resolution: </span>
                    Clusters cross-platform accounts into unified Person entities strictly using verified E.164 phone numbers and verified cryptographic keys (display names alone are rejected to prevent decoy spoofing).
                  </div>
                  <span className="px-2.5 py-1 rounded text-[11px] font-mono font-medium bg-primary/10 text-primary border border-primary/20 whitespace-nowrap">
                    {filteredPersons.length} Resolved Clusters
                  </span>
                </div>

                {ambiguousEdges.length > 0 && (
                  <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                    <div className="text-xs font-mono text-on-surface">
                      <span className="font-bold text-amber-700 dark:text-amber-300">Forensic Admissibility Rule: </span>
                      {ambiguousEdges.length} ambiguous name candidate(s) detected. Identities are NEVER clustered solely on display name similarity without E.164 phone or cryptographic corroboration.
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {filteredPersons.length === 0 ? (
                    <div className="col-span-2 card p-10 text-center text-on-surface-variant text-xs font-mono bg-surface border-outline-variant">
                      No resolved Person clusters found. Click &quot;Run Deep Correlation&quot; to cluster cross-app identities from phone numbers and handles.
                    </div>
                  ) : (
                    filteredPersons.map((p) => {
                      const tier = getConfidenceTier(p.confidence_score || 0.95);
                      return (
                        <div
                          key={p.person_id}
                          className="bg-surface border border-outline-variant rounded-xl p-4 shadow-sm hover:border-primary/50 transition-all space-y-3"
                        >
                          <div className="flex items-center justify-between border-b border-outline-variant/60 pb-2.5">
                            <div className="flex items-center gap-2.5">
                              <div className="w-9 h-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary font-bold font-mono text-sm">
                                {p.label ? p.label[0].toUpperCase() : 'P'}
                              </div>
                              <div>
                                <div className="text-xs font-bold font-mono text-on-surface flex items-center gap-2">
                                  {p.label || 'Identified Person'}
                                  {p.is_ambiguous && (
                                    <span className="px-1.5 py-0.5 rounded text-[10px] bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/30 font-mono">
                                      Ambiguous
                                    </span>
                                  )}
                                </div>
                                <div className="text-[10px] font-mono text-on-surface-variant">{p.person_id}</div>
                              </div>
                            </div>

                            <div className="flex items-center gap-2">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${tier.badgeClass}`}>
                                {tier.tierLevel}: {tier.pct}% Match
                              </span>
                              <button
                                onClick={() => setSelectedInspectorItem(p)}
                                className="btn-secondary text-[11px] font-mono py-1 px-2 flex items-center gap-1 h-7"
                                title="Inspect evidence links"
                              >
                                <Eye className="w-3 h-3" />
                                Inspect
                              </button>
                            </div>
                          </div>

                          {/* Forensic Link Rationale Banner */}
                          <div className="p-2.5 rounded-lg bg-surface-container border border-outline-variant/60 flex items-start gap-2.5 text-xs font-mono text-on-surface">
                            <Info className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                            <div>
                              <span className="font-semibold text-primary">Forensic Link Rationale: </span>
                              {p.resolution_method || (
                                p.phone_numbers && p.phone_numbers.length > 0
                                  ? `Unified WhatsApp and Telegram profiles via identical verified E.164 phone registration (${p.phone_numbers.join(', ')}).`
                                  : 'Unified multi-platform identity via corroborated account handles and cryptographic keys.'
                              )}
                            </div>
                          </div>

                          {/* Corroborated Accounts */}
                          <div className="space-y-1.5">
                            <div className="text-[11px] font-mono text-on-surface-variant font-medium">Corroborated Accounts:</div>
                            <div className="flex flex-wrap gap-2">
                              {p.resolved_accounts && p.resolved_accounts.map((acc: any, idx: number) => (
                                <div
                                  key={idx}
                                  className={`px-2.5 py-1 rounded-md text-[11px] font-mono flex items-center gap-1.5 border ${
                                    acc.platform === 'whatsapp'
                                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300'
                                      : 'bg-blue-500/10 border-blue-500/30 text-blue-700 dark:text-blue-300'
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
                              <div className="flex items-center gap-1 text-primary">
                                <Phone className="w-3 h-3" />
                                <span>{p.phone_numbers.join(', ')}</span>
                              </div>
                            )}
                            {p.handles && p.handles.length > 0 && (
                              <div className="flex items-center gap-1 text-blue-600 dark:text-blue-400">
                                <Hash className="w-3 h-3" />
                                <span>{p.handles.join(', ')}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            )}

            {/* TAB 3: PERCEPTUAL MEDIA MATCHES */}
            {activeTab === 'media' && (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-surface border border-outline-variant flex items-center justify-between shadow-sm">
                  <div className="text-xs font-mono text-on-surface">
                    <span className="font-bold text-indigo-600 dark:text-indigo-400">Perceptual Media Correlator: </span>
                    Matches visually equivalent, resized, or re-compressed exhibits using dHash and 2D-DCT pHash (Threshold ≤ {configParams.media_hamming_distance} bits).
                  </div>
                  <span className="px-2.5 py-1 rounded text-[11px] font-mono font-medium bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-500/30">
                    {mediaMatches.length} Links
                  </span>
                </div>

                {mediaMatches.length === 0 ? (
                  <div className="card p-10 text-center text-on-surface-variant text-xs font-mono bg-surface border-outline-variant">
                    No perceptual media hash matches detected within Hamming distance threshold ({configParams.media_hamming_distance}).
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {mediaMatches.map((m, idx) => (
                      <div
                        key={idx}
                        className="bg-surface border border-outline-variant rounded-xl p-4 space-y-3 shadow-sm hover:border-indigo-500/50 transition-all"
                      >
                        <div className="flex items-center justify-between border-b border-outline-variant/60 pb-2">
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-500/30">
                            Hamming Distance: {m.min_distance} (≤ {m.threshold})
                          </span>
                          <span className="text-xs font-mono font-semibold text-primary">
                            {Math.round(m.confidence_score * 100)}% Similarity
                          </span>
                        </div>

                        <div className="text-[11px] font-mono p-2 rounded bg-surface-container text-on-surface">
                          <strong>Visual Match Basis: </strong>
                          {m.min_distance === 0
                            ? 'Exact visual equivalence established (Hamming distance 0). Image transmitted across exhibits with identical perceptual vectors.'
                            : `Perceptual hash collision within ${m.min_distance} bit tolerance, indicating re-compression or resolution scaling.`}
                        </div>

                        <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                          <div className="p-3 bg-surface-container-low rounded-lg border border-outline-variant/60 space-y-1">
                            <div className="font-bold text-on-surface truncate">{m.source_filename}</div>
                            <div className="text-[10px] text-on-surface-variant truncate">SHA: {m.source_sha256}</div>
                            <div className="text-[10px] text-indigo-600 dark:text-indigo-400 truncate">pHash: {m.source_phash}</div>
                            <div className="text-[10px] text-indigo-600 dark:text-indigo-400 truncate">dHash: {m.source_dhash}</div>
                          </div>

                          <div className="p-3 bg-surface-container-low rounded-lg border border-outline-variant/60 space-y-1">
                            <div className="font-bold text-on-surface truncate">{m.target_filename}</div>
                            <div className="text-[10px] text-on-surface-variant truncate">SHA: {m.target_sha256}</div>
                            <div className="text-[10px] text-indigo-600 dark:text-indigo-400 truncate">pHash: {m.target_phash}</div>
                            <div className="text-[10px] text-indigo-600 dark:text-indigo-400 truncate">dHash: {m.target_dhash}</div>
                          </div>
                        </div>

                        {m.limitations && (
                          <div className="text-[10px] font-mono text-on-surface-variant">
                            {m.limitations.join(' ')}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* TAB 4: SHARED ARTIFACT STITCHING */}
            {activeTab === 'artifacts' && (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-surface border border-outline-variant flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-sm">
                  <div className="text-xs font-mono text-on-surface">
                    <span className="font-bold text-emerald-600 dark:text-emerald-400">Deterministic Artifact Stitcher: </span>
                    Correlates independent exhibits through exact checksum-validated tokens, including Bech32 Bitcoin wallets, EIP-55 Ethereum addresses, IBAN/SWIFT banking codes, and case codewords.
                  </div>
                  <span className="px-2.5 py-1 rounded text-[11px] font-mono font-medium bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30 whitespace-nowrap">
                    {filteredArtifacts.length} Discovered Artifacts
                  </span>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 bg-surface p-4 rounded-xl border border-outline-variant shadow-sm">
                  <div className="flex items-center gap-2 text-xs font-mono">
                    <span className="text-on-surface-variant font-semibold">Filter Category:</span>
                    {['ALL', 'CRYPTO', 'BANKING', 'LOGISTICS', 'CODEWORD'].map((cat) => (
                      <button
                        key={cat}
                        onClick={() => setArtifactFilter(cat)}
                        className={`px-2.5 py-1 rounded-md text-xs font-mono transition-colors ${
                          artifactFilter === cat
                            ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 font-semibold border border-emerald-500/30'
                            : 'text-on-surface-variant hover:text-on-surface'
                        }`}
                      >
                        {cat}
                      </button>
                    ))}
                  </div>
                  <span className="px-2.5 py-1 rounded text-[11px] font-mono font-medium bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30">
                    Category: {artifactFilter} ({filteredArtifacts.length})
                  </span>
                </div>

                {filteredArtifacts.length === 0 ? (
                  <div className="card p-10 text-center text-on-surface-variant text-xs font-mono bg-surface border-outline-variant">
                    No matching deterministic artifacts found for current category.
                  </div>
                ) : (
                  <div className="bg-surface border border-outline-variant rounded-xl overflow-hidden shadow-sm">
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="border-b border-outline-variant bg-surface-container font-mono text-on-surface-variant">
                            <th className="py-3 px-4 font-semibold">Type</th>
                            <th className="py-3 px-4 font-semibold">Extracted Value</th>
                            <th className="py-3 px-4 font-semibold">Checksum / Validation</th>
                            <th className="py-3 px-4 font-semibold">Forensic Corroboration</th>
                            <th className="py-3 px-4 font-semibold">Context Snippet</th>
                            <th className="py-3 px-4 font-semibold">Platform &amp; Exhibit</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-outline-variant/60">
                          {filteredArtifacts.map((art) => (
                            <tr key={art.artifact_id} className="hover:bg-surface-container transition-colors">
                              <td className="py-3 px-4 font-mono font-bold text-primary">
                                {art.artifact_type}
                              </td>
                              <td className="py-3 px-4 font-mono text-on-surface">
                                <span className="bg-surface-container px-2 py-1 rounded border border-outline-variant/80 font-bold">
                                  {art.value}
                                </span>
                              </td>
                              <td className="py-3 px-4">
                                <span
                                  className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${
                                    art.is_validated
                                      ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30'
                                      : 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30'
                                  }`}
                                >
                                  {art.validation_status}
                                </span>
                              </td>
                              <td className="py-3 px-4 font-mono text-[11px] text-on-surface">
                                <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-semibold">
                                  <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                                  <span>Deterministic {art.artifact_type}</span>
                                </div>
                                <div className="text-[10px] text-on-surface-variant mt-0.5">
                                  Cross-referenced in {art.source_platform}
                                </div>
                              </td>
                              <td className="py-3 px-4 text-on-surface font-sans max-w-xs truncate">
                                &ldquo;{art.context_snippet}&rdquo;
                              </td>
                              <td className="py-3 px-4 font-mono text-on-surface-variant capitalize">
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
                <div className="p-4 rounded-xl bg-surface border border-outline-variant flex items-center justify-between shadow-sm">
                  <div className="text-xs font-mono text-on-surface">
                    <span className="font-bold text-rose-600 dark:text-rose-400">Spatiotemporal Rendezvous Detector: </span>
                    Analyzes EXIF GPS coordinates and live location messages for co-presence opportunities (Distance ≤ {configParams.rendezvous_distance_meters}m, Time ≤ {configParams.rendezvous_time_seconds}s).
                  </div>
                  <span className="px-2.5 py-1 rounded text-[11px] font-mono font-medium bg-rose-500/10 text-rose-700 dark:text-rose-300 border border-rose-500/30">
                    {rendezvous.length} Events
                  </span>
                </div>

                {rendezvous.length === 0 ? (
                  <div className="card p-10 text-center text-on-surface-variant text-xs font-mono bg-surface border-outline-variant">
                    No rendezvous co-presence events meeting distance (≤ {configParams.rendezvous_distance_meters}m) and time (≤ {configParams.rendezvous_time_seconds}s) criteria.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {rendezvous.map((r, idx) => (
                      <div
                        key={idx}
                        className="bg-surface border border-outline-variant rounded-xl p-4 space-y-3 shadow-sm hover:border-rose-500/50 transition-all"
                      >
                        <div className="flex items-center justify-between border-b border-outline-variant/60 pb-2">
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-rose-500/10 text-rose-700 dark:text-rose-300 border border-rose-500/30">
                            Distance: {r.distance_meters}m (≤ {r.distance_threshold_meters}m)
                          </span>
                          <span className="text-xs font-mono font-semibold text-amber-600 dark:text-amber-400">
                            Time Delta: {r.time_delta_seconds}s
                          </span>
                        </div>

                        <div className="text-[11px] font-mono p-2 rounded bg-surface-container text-on-surface">
                          <strong>Co-Presence Hypothesis: </strong>
                          Devices recorded coordinates colocated within {r.distance_meters} meters during a {Math.round(r.time_delta_seconds / 60)} minute window.
                        </div>

                        <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                          <div className="p-3 bg-surface-container-low rounded-lg border border-outline-variant/60 space-y-1">
                            <div className="text-primary font-bold capitalize">
                              {r.observation_a.platform} Location
                            </div>
                            <div className="text-[10px] text-on-surface">
                              Lat: {r.observation_a.latitude}, Lon: {r.observation_a.longitude}
                            </div>
                            <div className="text-[10px] text-on-surface-variant">
                              Time: {formatDate(r.observation_a.timestamp)}
                            </div>
                          </div>

                          <div className="p-3 bg-surface-container-low rounded-lg border border-outline-variant/60 space-y-1">
                            <div className="text-blue-600 dark:text-blue-400 font-bold capitalize">
                              {r.observation_b.platform} Location
                            </div>
                            <div className="text-[10px] text-on-surface">
                              Lat: {r.observation_b.latitude}, Lon: {r.observation_b.longitude}
                            </div>
                            <div className="text-[10px] text-on-surface-variant">
                              Time: {formatDate(r.observation_b.timestamp)}
                            </div>
                          </div>
                        </div>

                        {r.limitations && (
                          <div className="text-[10px] font-mono text-on-surface-variant">
                            {r.limitations.join(' ')}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* TAB 6: TIME-WINDOW MESSAGE MATRIX */}
            {activeTab === 'matrix' && (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-surface border border-outline-variant flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-sm">
                  <div className="text-xs font-mono text-on-surface">
                    <span className="font-bold text-cyan-600 dark:text-cyan-400">Cross-App Message Exchange Matrix: </span>
                    Correlates concurrent messaging streams between distinct platforms within an analyst-defined temporal window (≤ {windowSeconds}s) to trace coordinated multi-party operations.
                  </div>
                  <span className="px-2.5 py-1 rounded text-[11px] font-mono font-medium bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 border border-cyan-500/20 whitespace-nowrap">
                    {matrix.length} Correlated Pairs
                  </span>
                </div>

                <div className="bg-surface border border-outline-variant rounded-xl overflow-hidden shadow-sm">
                  <div className="p-4 bg-surface-container border-b border-outline-variant flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <MessageSquare className="w-4 h-4 text-cyan-500" />
                      <h3 className="text-sm font-bold font-mono text-on-surface">
                        Cross-App Message Sequences
                      </h3>
                      <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-cyan-500/10 text-cyan-600 dark:text-cyan-300 border border-cyan-500/20">
                        Window: ≤ {windowSeconds}s
                      </span>
                    </div>
                    <span className="text-xs text-on-surface-variant font-mono">
                      Showing {matrix.length} Correlated Pairs
                    </span>
                  </div>

                  {matrix.length === 0 ? (
                    <div className="p-10 text-center text-on-surface-variant text-xs font-mono">
                      No cross-app message exchanges detected within {windowSeconds}s. Try adjusting the window threshold in parameters.
                    </div>
                  ) : (
                    <div className="p-4 space-y-3.5 bg-background">
                      {matrix.map((item) => (
                        <div
                          key={item.id}
                          className="bg-surface border border-outline-variant rounded-xl p-4 hover:border-cyan-500/50 transition-all shadow-sm space-y-3"
                        >
                          {/* Forensic Exchange Basis Banner */}
                          <div className="p-2.5 rounded-lg bg-surface-container border border-outline-variant/60 flex items-start gap-2.5 text-xs font-mono text-on-surface">
                            <Info className="w-4 h-4 text-cyan-500 shrink-0 mt-0.5" />
                            <div>
                              <span className="font-semibold text-cyan-600 dark:text-cyan-400">Forensic Exchange Basis: </span>
                              Cross-app message exchange within {item.time_delta_seconds}s temporal window ({item.same_entity_pair ? 'Sent by the same resolved Person identity across applications' : 'Active sequence co-occurrence between case participants'}).
                            </div>
                          </div>

                          <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">
                            {/* WhatsApp Left */}
                            <div className="flex-1 bg-surface-container-low p-3.5 rounded-xl border border-emerald-500/30">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 font-semibold">
                                WhatsApp
                              </span>
                              <span className="text-[11px] font-mono text-on-surface-variant">
                                {formatDate(item.wa_timestamp)}
                              </span>
                            </div>
                            <div className="text-xs font-mono text-on-surface-variant mb-1.5">
                              From: <span className="text-on-surface font-semibold">{formatContactLabel(item.wa_sender_jid)}</span>
                            </div>
                            <div className="text-xs text-on-surface bg-surface p-2.5 rounded-lg border border-outline-variant/60 font-sans">
                              {item.wa_body || <span className="italic text-on-surface-variant">[Media attachment / binary payload]</span>}
                            </div>
                          </div>

                          {/* Delta Badge */}
                          <div className="flex flex-col items-center justify-center px-2 shrink-0">
                            <div className="flex items-center gap-1 text-xs font-mono text-amber-600 dark:text-amber-400 bg-amber-500/10 px-3 py-1 rounded-full border border-amber-500/20 whitespace-nowrap mb-1">
                              <Zap className="w-3.5 h-3.5" />
                              ⚡ {item.time_delta_seconds}s Delta
                            </div>
                            {item.same_entity_pair && (
                              <span className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400 flex items-center gap-1 font-semibold">
                                <CheckCircle2 className="w-3 h-3" />
                                Same Identity
                              </span>
                            )}
                            <span className="text-[10px] font-mono text-on-surface-variant">
                              {Math.round((item.confidence_score || 0.8) * 100)}% Certainty
                            </span>
                          </div>

                          {/* Telegram Right */}
                          <div className="flex-1 bg-surface-container-low p-3.5 rounded-xl border border-blue-500/30">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-blue-500/15 text-blue-700 dark:text-blue-300 font-semibold">
                                Telegram
                              </span>
                              <span className="text-[11px] font-mono text-on-surface-variant">
                                {formatDate(item.tg_timestamp)}
                              </span>
                            </div>
                            <div className="text-xs font-mono text-on-surface-variant mb-1.5">
                              From: <span className="text-on-surface font-semibold">{formatContactLabel(item.tg_sender_id)}</span>
                            </div>
                            <div className="text-xs text-on-surface bg-surface p-2.5 rounded-lg border border-outline-variant/60 font-sans">
                              {item.tg_body || <span className="italic text-on-surface-variant">[Media attachment / binary payload]</span>}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Evidence Drill-Down Drawer / Inspector */}
        {selectedInspectorItem && (
          <div className="fixed inset-y-0 right-0 w-full sm:w-[480px] bg-surface border-l border-outline-variant p-6 z-50 shadow-2xl overflow-y-auto space-y-6">
            <div className="flex items-center justify-between border-b border-outline-variant pb-3">
              <div className="flex items-center gap-2 text-on-surface font-mono font-bold text-sm">
                <ShieldCheck className="w-4 h-4 text-primary" />
                Evidence Provenance Inspector
              </div>
              <button
                onClick={() => setSelectedInspectorItem(null)}
                className="text-on-surface-variant hover:text-on-surface p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4 text-xs font-mono text-on-surface">
              <div>
                <span className="text-on-surface-variant font-medium">Correlation Record ID:</span>
                <div className="text-on-surface font-bold text-sm">{selectedInspectorItem.handover_id || selectedInspectorItem.person_id || 'ID_LINK'}</div>
              </div>

              <div>
                <span className="text-on-surface-variant font-medium">Link Classification:</span>
                <div className="text-primary font-semibold">{selectedInspectorItem.classification || selectedInspectorItem.resolution_method || 'PLATFORM_HANDOVER_CANDIDATE'}</div>
              </div>

              <div>
                <span className="text-on-surface-variant font-medium">Mathematical Certainty Score:</span>
                <div className="text-on-surface font-bold">
                  {Math.round((selectedInspectorItem.confidence_score || 1.0) * 100)}% ({getConfidenceTier(selectedInspectorItem.confidence_score || 0.8).tierName})
                </div>
                <p className="text-[11px] text-on-surface-variant font-sans mt-0.5">
                  {getConfidenceTier(selectedInspectorItem.confidence_score || 0.8).description}
                </p>
              </div>

              {selectedInspectorItem.rationale && (
                <div>
                  <span className="text-on-surface-variant font-medium">Forensic Basis:</span>
                  <div className="p-3 bg-surface-container rounded-lg border border-outline-variant text-on-surface font-sans text-xs">
                    {selectedInspectorItem.rationale}
                  </div>
                </div>
              )}

              {selectedInspectorItem.phone_numbers && (
                <div>
                  <span className="text-on-surface-variant font-medium">Corroborated Telecommunication Numbers:</span>
                  <div className="space-y-1 mt-1">
                    {selectedInspectorItem.phone_numbers.map((ph: string, i: number) => (
                      <div key={i} className="p-2 bg-surface-container rounded border border-outline-variant text-on-surface font-bold">
                        {ph}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <span className="text-on-surface-variant font-medium">Judicial Limitations &amp; Neutral Disclaimers:</span>
                <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg text-on-surface space-y-1 mt-1">
                  {selectedInspectorItem.limitations && selectedInspectorItem.limitations.length > 0 ? (
                    selectedInspectorItem.limitations.map((lim: string, i: number) => <div key={i}>• {lim}</div>)
                  ) : (
                    <div>• Verified through mathematical or cryptographic corroboration standards.</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CorrelationPage;
