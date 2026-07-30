import { useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import {
  MessageSquare,
  Users,
  Image,
  Trash2,
  Layers,
  ArrowLeft,
  Search,
  Loader2,
  BarChart3,
  Activity,
  Clock,
  Hash,
  Zap,
  AlertCircle,
} from 'lucide-react';
import { useCaseOverview } from '../hooks/useDashboard';
import { StatsCard, AppStatsCard, RecentEvents, CorrelationSummary } from '../components/dashboard';

const DashboardPage = () => {
  const { caseId } = useParams();
  const { overview, loading, error, loadOverview } = useCaseOverview();

  useEffect(() => {
    if (caseId) {
      loadOverview(parseInt(caseId));
    }
  }, [caseId, loadOverview]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-accent-cyan mx-auto" />
          <span className="mt-3 text-forensic-400 block">Loading dashboard data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="alert alert-error max-w-2xl mx-auto">
          <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Failed to load dashboard</p>
            <p className="text-sm opacity-80">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!overview) {
    return (
      <div className="p-6 text-center">
        <div className="card max-w-md mx-auto py-12">
          <div className="w-16 h-16 rounded-2xl bg-forensic-800 flex items-center justify-center mx-auto mb-4">
            <BarChart3 className="h-8 w-8 text-forensic-500" />
          </div>
          <h3 className="text-lg font-semibold mb-2">No Dashboard Data</h3>
          <p className="text-sm text-forensic-500 mb-6">
            Upload evidence and run analysis to generate dashboard statistics.
          </p>
          <Link to={`/cases/${caseId}`} className="btn-secondary inline-flex items-center gap-2">
            <ArrowLeft className="h-4 w-4" />
            Back to Case
          </Link>
        </div>
      </div>
    );
  }

  const { stats, correlation_stats, timeline_stats, recent_events, apps } = overview;

  return (
    <div className="p-6 max-w-7xl mx-auto animate-in">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 text-sm text-forensic-500 mb-3">
          <Link to="/cases" className="hover:text-accent-cyan flex items-center gap-1 transition-colors">
            <ArrowLeft className="h-4 w-4" />
            Cases
          </Link>
          <span className="text-forensic-700">/</span>
          <span className="text-forensic-300">{overview.case_name}</span>
          <span className="text-forensic-700">/</span>
          <span className="text-accent-cyan">Dashboard</span>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-forensic-50 mb-1">
              {overview.case_name}
            </h1>
            <div className="flex items-center gap-3 flex-wrap">
              <span className={`badge ${
                overview.case_status === 'active' ? 'badge-emerald' :
                overview.case_status === 'archived' ? 'badge-amber' : 'badge-gray'
              }`}>
                {overview.case_status}
              </span>
              {overview.date_range_start && (
                <span className="text-sm text-forensic-500 flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" />
                  {formatDistanceToNow(new Date(overview.date_range_start), { addSuffix: true })} — {' '}
                  {formatDistanceToNow(new Date(overview.date_range_end), { addSuffix: true })}
                </span>
              )}
            </div>
          </div>

          <Link
            to={`/cases/${caseId}/search`}
            className="btn-primary flex items-center gap-2"
          >
            <Search className="h-4 w-4" />
            Search Evidence
          </Link>
        </div>
      </div>

      {/* Main Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8 stagger-children">
        <StatsCard
          title="Total Messages"
          value={stats.total_messages}
          icon={MessageSquare}
          color="cyan"
        />
        <StatsCard
          title="Total Contacts"
          value={stats.total_contacts}
          icon={Users}
          color="emerald"
        />
        <StatsCard
          title="Media Files"
          value={stats.total_media}
          icon={Image}
          color="violet"
        />
        <StatsCard
          title="Deletions Detected"
          value={stats.total_deleted}
          icon={Trash2}
          color="amber"
        />
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* App-specific Stats */}
        <div className="card">
          <div className="section-header">
            <div className="section-icon">
              <BarChart3 className="h-5 w-5" />
            </div>
            <h2 className="section-title">By Application</h2>
          </div>
          <div className="space-y-4">
            {apps?.includes('whatsapp') && stats?.whatsapp && (
              <AppStatsCard app="WhatsApp" stats={stats.whatsapp} icon="whatsapp" />
            )}
            {apps?.includes('telegram') && stats?.telegram && (
              <AppStatsCard app="Telegram" stats={stats.telegram} icon="telegram" />
            )}
            {(!apps?.includes('whatsapp') && !apps?.includes('telegram')) && (
              <div className="text-center py-8">
                <Layers className="h-12 w-12 text-forensic-600 mx-auto mb-3" />
                <p className="text-forensic-500">No app data available</p>
                <p className="text-sm text-forensic-600">Upload and analyze evidence to see statistics</p>
              </div>
            )}
          </div>
        </div>

        {/* Correlation & Recent Events */}
        <div className="space-y-6">
          <CorrelationSummary stats={correlation_stats} />

          <div className="card">
            <div className="section-header mb-4">
              <div className="section-icon">
                <Activity className="h-5 w-5" />
              </div>
              <h2 className="section-title">Recent Activity</h2>
            </div>
            <RecentEvents events={recent_events} />
          </div>
        </div>
      </div>

      {/* Timeline Stats */}
      {timeline_stats.total_events > 0 && (
        <div className="card mb-6">
          <div className="section-header mb-4">
            <div className="section-icon">
              <Clock className="h-5 w-5" />
            </div>
            <h2 className="section-title">Timeline Summary</h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="metric-card">
              <p className="metric-value">{timeline_stats.total_events.toLocaleString()}</p>
              <p className="metric-label">Total Events</p>
            </div>
            <div className="metric-card">
              <p className="metric-value text-accent-emerald">
                {timeline_stats.events_by_app?.whatsapp?.toLocaleString() ?? 0}
              </p>
              <p className="metric-label">WhatsApp Events</p>
            </div>
            <div className="metric-card">
              <p className="metric-value text-accent-blue">
                {timeline_stats.events_by_app?.telegram?.toLocaleString() ?? 0}
              </p>
              <p className="metric-label">Telegram Events</p>
            </div>
            <div className="metric-card">
              <p className="metric-value">{Object.keys(timeline_stats.events_by_type || {}).length}</p>
              <p className="metric-label">Event Types</p>
            </div>
          </div>
        </div>
      )}

      {/* Quick Links */}
      <div className="flex flex-wrap gap-3">
        <Link
          to={`/cases/${caseId}`}
          className="btn-secondary flex items-center gap-2"
        >
          <Activity className="h-4 w-4" />
          Full Timeline
        </Link>
        <Link
          to={`/cases/${caseId}`}
          className="btn-secondary flex items-center gap-2"
        >
          <Hash className="h-4 w-4" />
          Correlation Graph
        </Link>
        <Link
          to={`/cases/${caseId}`}
          className="btn-ghost flex items-center gap-2"
        >
          <Zap className="h-4 w-4" />
          Case Details
        </Link>
      </div>
    </div>
  );
};

export default DashboardPage;