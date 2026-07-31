import { useState, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import CaseWorkspacePage from './CaseWorkspacePage';
import useTimeline from '../hooks/useTimeline';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { format, parseISO, isValid, subDays, subHours } from 'date-fns';
import {
  Clock,
  Search,
  Filter,
  RefreshCw,
  Copy,
  Check,
  Calendar,
  MessageSquare,
  AlertTriangle,
  FileSpreadsheet,
  FileText,
  ChevronLeft,
  ChevronRight,
  Info,
  Hash,
  Database,
  User,
  SlidersHorizontal,
  X,
} from 'lucide-react';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

const TimelinePage = () => {
  const { caseId } = useParams();
  const {
    events,
    histogram,
    loading,
    histogramLoading,
    rebuilding,
    error,
    filters,
    updateFilters,
    resetFilters,
    rebuildTimeline,
  } = useTimeline(caseId);

  const [copiedHash, setCopiedHash] = useState(null);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [page, setPage] = useState(1);
  const pageSize = 25;

  const handleCopyHash = (hash, e) => {
    e.stopPropagation();
    if (!hash) return;
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const [activePreset, setActivePreset] = useState('all');

  // Preset Date Handlers
  const handlePresetDate = (preset) => {
    setActivePreset(preset);
    setPage(1);
    const now = new Date();
    if (preset === '24h') {
      updateFilters({ startDate: subHours(now, 24).toISOString(), endDate: '' });
    } else if (preset === '7d') {
      updateFilters({ startDate: subDays(now, 7).toISOString(), endDate: '' });
    } else if (preset === '30d') {
      updateFilters({ startDate: subDays(now, 30).toISOString(), endDate: '' });
    } else if (preset === 'all') {
      updateFilters({ startDate: '', endDate: '' });
    }
  };


  // Compute effective histogram bins from backend response or client-side fallback from events
  const effectiveBins = useMemo(() => {
    if (histogram && histogram.bins && histogram.bins.length > 0) {
      return histogram.bins;
    }
    if (!events || events.length === 0) return [];

    const binsMap = {};
    events.forEach((evt) => {
      let dateKey = 'Today';
      if (evt.normalized_timestamp) {
        try {
          const d = parseISO(evt.normalized_timestamp);
          if (isValid(d)) dateKey = format(d, 'yyyy-MM-dd');
        } catch {}
      } else if (evt.timestamp) {
        try {
          const ts = evt.timestamp > 1e11 ? evt.timestamp : evt.timestamp * 1000;
          const d = new Date(ts);
          if (isValid(d)) dateKey = format(d, 'yyyy-MM-dd');
        } catch {}
      }

      if (!binsMap[dateKey]) {
        binsMap[dateKey] = {
          date: dateKey,
          total: 0,
          whatsapp: 0,
          telegram: 0,
          deleted_gap: 0,
          evidence_ingest: 0,
          other: 0,
        };
      }

      binsMap[dateKey].total += 1;
      const isWa = evt.source_app === 'whatsapp';
      const isTg = evt.source_app === 'telegram';
      const isGap = evt.event_type === 'deleted_gap';
      const isIngest = evt.event_type === 'evidence_ingest';

      if (isGap) binsMap[dateKey].deleted_gap += 1;
      else if (isIngest) binsMap[dateKey].evidence_ingest += 1;
      else if (isWa) binsMap[dateKey].whatsapp += 1;
      else if (isTg) binsMap[dateKey].telegram += 1;
      else binsMap[dateKey].other += 1;
    });

    return Object.keys(binsMap).sort().map((k) => binsMap[k]);
  }, [histogram, events]);

  // Histogram Chart Data Preparation for Chart.js
  const chartData = useMemo(() => {
    if (!effectiveBins || effectiveBins.length === 0) {
      return { labels: [], datasets: [] };
    }

    const labels = effectiveBins.map((bin) => {
      try {
        const d = parseISO(bin.date);
        return isValid(d) ? format(d, 'MMM d') : bin.date;
      } catch {
        return bin.date;
      }
    });

    return {
      labels,
      datasets: [
        {
          label: 'WhatsApp Messages',
          data: effectiveBins.map((b) => b.whatsapp || 0),
          backgroundColor: '#10b981', // emerald
          borderRadius: 4,
        },
        {
          label: 'Telegram Messages',
          data: effectiveBins.map((b) => b.telegram || 0),
          backgroundColor: '#3b82f6', // sky blue
          borderRadius: 4,
        },
        {
          label: 'Deleted Gaps',
          data: effectiveBins.map((b) => b.deleted_gap || 0),
          backgroundColor: '#f43f5e', // rose
          borderRadius: 4,
        },
        {
          label: 'Evidence Ingest',
          data: effectiveBins.map((b) => b.evidence_ingest || 0),
          backgroundColor: '#a855f7', // purple
          borderRadius: 4,
        },
      ],
    };
  }, [effectiveBins]);


  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        align: 'end',
        labels: {
          color: '#94a3b8',
          boxWidth: 10,
          boxHeight: 10,
          padding: 12,
          font: { family: 'Inter, sans-serif', size: 11 },
        },
      },
      tooltip: {
        backgroundColor: '#0f172a',
        borderColor: '#334155',
        borderWidth: 1,
        titleColor: '#f8fafc',
        bodyColor: '#cbd5e1',
        padding: 10,
      },
    },
    scales: {
      x: {
        stacked: true,
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: { color: '#64748b', font: { size: 11 } },
      },
      y: {
        stacked: true,
        beginAtZero: true,
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: { color: '#64748b', precision: 0, font: { size: 11 } },
      },
    },
  };

  // Pagination calculation
  const totalPages = Math.ceil(events.length / pageSize) || 1;
  const paginatedEvents = useMemo(() => {
    const start = (page - 1) * pageSize;
    return events.slice(start, start + pageSize);
  }, [events, page, pageSize]);

  return (
    <CaseWorkspacePage activeTab="timeline">
      <div className="space-y-6 animate-in">
        {/* Top Header & Rebuild Control */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-forensic-900 border border-forensic-800 p-4 rounded-xl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-accent-cyan/10 border border-accent-cyan/20 flex items-center justify-center">
              <Clock className="w-5 h-5 text-accent-cyan" />
            </div>
            <div>
              <h1 className="text-lg font-bold font-mono text-forensic-100 flex items-center gap-2">
                Reconstructed Forensic Timeline
              </h1>
              <p className="text-xs text-forensic-400">
                Unified cross-platform event stream & time-density histogram visualization
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={rebuildTimeline}
              disabled={rebuilding}
              className="btn-secondary text-xs flex items-center gap-2"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${rebuilding ? 'animate-spin text-accent-cyan' : ''}`} />
              {rebuilding ? 'Rebuilding Index...' : 'Rebuild Timeline'}
            </button>
          </div>
        </div>

        {/* Filter Toolbar */}
        <div className="card space-y-4">
          <div className="flex items-center justify-between border-b border-forensic-800 pb-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-forensic-200">
              <SlidersHorizontal className="w-4 h-4 text-accent-cyan" />
              <span>Timeline Filters</span>
            </div>
            {(filters.search || filters.sourceApp !== 'all' || filters.eventType !== 'all' || filters.startDate || filters.endDate) && (
              <button
                onClick={resetFilters}
                className="text-xs text-accent-cyan hover:underline flex items-center gap-1"
              >
                <X className="w-3 h-3" /> Clear Filters
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Search Query */}
            <div>
              <label className="text-xs font-medium text-forensic-400 mb-1 flex items-center gap-1.5">
                <Search className="w-3.5 h-3.5 text-accent-cyan" /> Search Keyword
              </label>
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search description, JID, text..."
                  value={filters.search}
                  onChange={(e) => {
                    updateFilters({ search: e.target.value });
                    setPage(1);
                  }}
                  className="input-field text-xs pl-8"
                />
                <Search className="w-3.5 h-3.5 text-forensic-500 absolute left-2.5 top-2.5" />
              </div>
            </div>

            {/* Source App Filter */}
            <div>
              <label className="text-xs font-medium text-forensic-400 mb-1 flex items-center gap-1.5">
                <Filter className="w-3.5 h-3.5 text-accent-cyan" /> Source Application
              </label>
              <select
                value={filters.sourceApp}
                onChange={(e) => {
                  updateFilters({ sourceApp: e.target.value });
                  setPage(1);
                }}
                className="input-field text-xs bg-forensic-900"
              >
                <option value="all">All Applications</option>
                <option value="whatsapp">WhatsApp</option>
                <option value="telegram">Telegram</option>
              </select>
            </div>

            {/* Event Type Filter */}
            <div>
              <label className="text-xs font-medium text-forensic-400 mb-1 flex items-center gap-1.5">
                <MessageSquare className="w-3.5 h-3.5 text-accent-cyan" /> Event Type
              </label>
              <select
                value={filters.eventType}
                onChange={(e) => {
                  updateFilters({ eventType: e.target.value });
                  setPage(1);
                }}
                className="input-field text-xs bg-forensic-900"
              >
                <option value="all">All Event Types</option>
                <option value="message">Messages</option>
                <option value="deleted_gap">Deleted Message Gaps</option>
                <option value="evidence_ingest">Evidence Ingest</option>
              </select>
            </div>

            {/* Date Quick Presets */}
            <div>
              <label className="text-xs font-medium text-forensic-400 mb-1 flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-accent-cyan" /> Quick Time Window
              </label>
              <div className="grid grid-cols-4 gap-1">
                <button
                  type="button"
                  onClick={() => handlePresetDate('all')}
                  className={`px-2 py-1.5 text-xs rounded border transition-all cursor-pointer ${
                    activePreset === 'all'
                      ? 'bg-accent-cyan/20 border-accent-cyan text-accent-cyan font-semibold'
                      : 'border-forensic-700 bg-forensic-900 text-forensic-300 hover:border-forensic-600'
                  }`}
                >
                  All
                </button>
                <button
                  type="button"
                  onClick={() => handlePresetDate('24h')}
                  className={`px-2 py-1.5 text-xs rounded border transition-all cursor-pointer ${
                    activePreset === '24h'
                      ? 'bg-accent-cyan/20 border-accent-cyan text-accent-cyan font-semibold'
                      : 'border-forensic-700 bg-forensic-900 text-forensic-300 hover:border-forensic-600'
                  }`}
                >
                  24h
                </button>
                <button
                  type="button"
                  onClick={() => handlePresetDate('7d')}
                  className={`px-2 py-1.5 text-xs rounded border transition-all cursor-pointer ${
                    activePreset === '7d'
                      ? 'bg-accent-cyan/20 border-accent-cyan text-accent-cyan font-semibold'
                      : 'border-forensic-700 bg-forensic-900 text-forensic-300 hover:border-forensic-600'
                  }`}
                >
                  7d
                </button>
                <button
                  type="button"
                  onClick={() => handlePresetDate('30d')}
                  className={`px-2 py-1.5 text-xs rounded border transition-all cursor-pointer ${
                    activePreset === '30d'
                      ? 'bg-accent-cyan/20 border-accent-cyan text-accent-cyan font-semibold'
                      : 'border-forensic-700 bg-forensic-900 text-forensic-300 hover:border-forensic-600'
                  }`}
                >
                  30d
                </button>
              </div>
            </div>

          </div>
        </div>

        {/* Time Density Histogram Card */}
        <div className="card space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-accent-cyan" />
              <h2 className="text-sm font-semibold text-forensic-100 font-mono">
                Time-Density Histogram
              </h2>
            </div>
            {histogram && (
              <div className="flex items-center gap-3 text-xs font-mono">
                <span className="text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                  WA: {histogram.apps_breakdown?.whatsapp || 0}
                </span>
                <span className="text-sky-400 bg-sky-500/10 px-2 py-0.5 rounded border border-sky-500/20">
                  TG: {histogram.apps_breakdown?.telegram || 0}
                </span>
                <span className="text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
                  Gaps: {histogram.types_breakdown?.deleted_gap || 0}
                </span>
                <span className="text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">
                  Ingest: {histogram.types_breakdown?.evidence_ingest || 0}
                </span>
              </div>
            )}
          </div>

          <div className="min-h-[220px] h-60 relative w-full">
            {histogramLoading && !effectiveBins.length ? (
              <div className="absolute inset-0 flex items-center justify-center bg-forensic-900/50 backdrop-blur-xs rounded border border-forensic-800">
                <div className="text-xs text-forensic-400 flex items-center gap-2 font-mono">
                  <RefreshCw className="w-4 h-4 animate-spin text-accent-cyan" />
                  Calculating time density buckets...
                </div>
              </div>
            ) : effectiveBins.length > 0 ? (
              <div className="h-full relative w-full">
                <Bar data={chartData} options={chartOptions} />
              </div>
            ) : (
              <div className="absolute inset-0 flex items-center justify-center text-xs text-forensic-500 font-mono border border-dashed border-forensic-800 rounded">
                No event density data matching current filter scope
              </div>
            )}
          </div>



        </div>

        {/* Chronological Event Stream */}
        <div className="card space-y-4">
          <div className="flex items-center justify-between border-b border-forensic-800 pb-3">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-accent-cyan" />
              <h2 className="text-sm font-semibold text-forensic-100 font-mono">
                Event Stream ({events.length} Total Events)
              </h2>
            </div>
            {/* Pagination Info */}
            <div className="flex items-center gap-2 text-xs font-mono text-forensic-400">
              <span>
                Page {page} of {totalPages}
              </span>
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(p - 1, 1))}
                className="p-1 rounded bg-forensic-800 hover:bg-forensic-700 disabled:opacity-30 disabled:hover:bg-forensic-800 text-forensic-200"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
                className="p-1 rounded bg-forensic-800 hover:bg-forensic-700 disabled:opacity-30 disabled:hover:bg-forensic-800 text-forensic-200"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {loading ? (
            <div className="py-12 text-center text-xs text-forensic-400 font-mono flex items-center justify-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-accent-cyan" /> Loading event stream...
            </div>
          ) : events.length === 0 ? (
            <div className="py-12 text-center text-xs text-forensic-500 font-mono border border-dashed border-forensic-800 rounded">
              No timeline events found for this case or current filter settings.
            </div>
          ) : (
            <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-forensic-800">
              {paginatedEvents.map((evt) => {
                const isWa = evt.source_app === 'whatsapp';
                const isTg = evt.source_app === 'telegram';
                const isGap = evt.event_type === 'deleted_gap';
                const isIngest = evt.event_type === 'evidence_ingest';

                const dateObj = evt.normalized_timestamp
                  ? parseISO(evt.normalized_timestamp)
                  : new Date(evt.timestamp > 1e11 ? evt.timestamp : evt.timestamp * 1000);
                const formattedDate = isValid(dateObj) ? format(dateObj, 'yyyy-MM-dd HH:mm:ss') : 'Unknown Date';

                const metadata = evt.metadata || {};
                const hashFp = metadata.hash_fingerprint || '';
                const entityJid = metadata.entity_jid || evt.entity_id || 'System';

                return (
                  <div
                    key={evt.id}
                    onClick={() => setSelectedEvent(evt)}
                    className="relative bg-forensic-900 border border-forensic-800 hover:border-forensic-700 p-3.5 rounded-lg transition-all cursor-pointer group"
                  >
                    {/* Timeline Node Dot */}
                    <div
                      className={`absolute -left-[27px] top-4 w-3 h-3 rounded-full border-2 bg-forensic-950 ${
                        isWa
                          ? 'border-emerald-500'
                          : isTg
                          ? 'border-sky-500'
                          : isGap
                          ? 'border-rose-500 animate-pulse'
                          : 'border-purple-500'
                      }`}
                    />

                    {/* Top Row: Timestamp & App Badge */}
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2 font-mono text-xs text-forensic-400">
                        <Calendar className="w-3.5 h-3.5 text-forensic-500" />
                        <span className="text-forensic-200">{formattedDate}</span>
                      </div>

                      <div className="flex items-center gap-2">
                        {/* App Badge */}
                        <span
                          className={`badge text-[10px] font-mono uppercase tracking-wider ${
                            isWa
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                              : isTg
                              ? 'bg-sky-500/10 text-sky-400 border-sky-500/20'
                              : isGap
                              ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                              : 'bg-purple-500/10 text-purple-400 border-purple-500/20'
                          }`}
                        >
                          {evt.source_app}
                        </span>

                        {/* Event Type Badge */}
                        <span className="badge badge-gray text-[10px] font-mono">
                          {evt.event_type}
                        </span>
                      </div>
                    </div>

                    {/* Entity JID / Handle */}
                    <div className="mb-2 flex items-center gap-2">
                      <User className="w-3.5 h-3.5 text-accent-cyan" />
                      <span className="font-mono text-xs text-accent-cyan bg-accent-cyan/10 px-2 py-0.5 rounded border border-accent-cyan/20 truncate max-w-md">
                        {entityJid}
                      </span>
                    </div>

                    {/* Event Description */}
                    <p className={`text-xs leading-relaxed mb-3 ${isGap ? 'text-rose-400 font-semibold font-mono' : 'text-forensic-200'}`}>
                      {evt.description || '<No Content>'}
                    </p>

                    {/* Cryptographic Hash Fingerprint Badge */}
                    {hashFp && (
                      <div className="flex items-center justify-between pt-2 border-t border-forensic-850">
                        <div className="flex items-center gap-2 text-xs font-mono text-forensic-500">
                          <Hash className="w-3.5 h-3.5 text-accent-cyan" />
                          <span className="text-[11px] text-forensic-400">Fingerprint SHA-256:</span>
                          <span className="text-accent-cyan text-[11px] bg-forensic-950 px-2 py-0.5 rounded border border-forensic-800 truncate max-w-[280px]">
                            {hashFp}
                          </span>
                        </div>

                        <button
                          onClick={(e) => handleCopyHash(hashFp, e)}
                          className="btn-secondary text-[10px] px-2 py-0.5 flex items-center gap-1 text-forensic-300 hover:text-accent-cyan"
                        >
                          {copiedHash === hashFp ? (
                            <>
                              <Check className="w-3 h-3 text-accent-emerald" /> Copied
                            </>
                          ) : (
                            <>
                              <Copy className="w-3 h-3" /> Copy Hash
                            </>
                          )}
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Event Details Inspection Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4">
          <div className="card max-w-2xl w-full max-h-[85vh] overflow-y-auto space-y-4 border-forensic-700 animate-in">
            <div className="flex items-center justify-between pb-3 border-b border-forensic-800">
              <div className="flex items-center gap-2">
                <Info className="w-5 h-5 text-accent-cyan" />
                <h3 className="text-base font-bold font-mono text-forensic-100">
                  Timeline Event Metadata Inspector
                </h3>
              </div>
              <button
                onClick={() => setSelectedEvent(null)}
                className="p-1 rounded text-forensic-400 hover:text-forensic-100 hover:bg-forensic-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs font-mono">
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-forensic-900 p-2.5 rounded border border-forensic-800">
                  <span className="text-forensic-500 block mb-1">Event ID</span>
                  <span className="text-forensic-200">{selectedEvent.id}</span>
                </div>
                <div className="bg-forensic-900 p-2.5 rounded border border-forensic-800">
                  <span className="text-forensic-500 block mb-1">Source App</span>
                  <span className="text-accent-cyan uppercase">{selectedEvent.source_app}</span>
                </div>
                <div className="bg-forensic-900 p-2.5 rounded border border-forensic-800">
                  <span className="text-forensic-500 block mb-1">Event Type</span>
                  <span className="text-forensic-200">{selectedEvent.event_type}</span>
                </div>
                <div className="bg-forensic-900 p-2.5 rounded border border-forensic-800">
                  <span className="text-forensic-500 block mb-1">Timestamp</span>
                  <span className="text-forensic-200">{selectedEvent.normalized_timestamp}</span>
                </div>
              </div>

              <div className="bg-forensic-900 p-3 rounded border border-forensic-800 space-y-1">
                <span className="text-forensic-500 block">Description</span>
                <p className="text-forensic-100 font-sans text-sm">{selectedEvent.description || 'N/A'}</p>
              </div>

              {selectedEvent.metadata && (
                <div className="bg-forensic-900 p-3 rounded border border-forensic-800 space-y-2">
                  <span className="text-forensic-500 block">Raw Event Metadata JSON</span>
                  <pre className="text-[11px] text-accent-cyan bg-forensic-950 p-2.5 rounded border border-forensic-850 overflow-x-auto">
                    {JSON.stringify(selectedEvent.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="pt-2 flex justify-end">
              <button onClick={() => setSelectedEvent(null)} className="btn-secondary text-xs">
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </CaseWorkspacePage>
  );
};

export default TimelinePage;
