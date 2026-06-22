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
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-3 text-gray-600">Loading dashboard...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      </div>
    );
  }

  if (!overview) {
    return (
      <div className="p-6 text-center">
        <p className="text-gray-500">No dashboard data available.</p>
      </div>
    );
  }

  const { stats, correlation_stats, timeline_stats, recent_events, apps } = overview;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
          <Link to="/cases" className="hover:text-blue-600 flex items-center gap-1">
            <ArrowLeft className="h-4 w-4" />
            Cases
          </Link>
          <span>/</span>
          <span>{overview.case_name}</span>
          <span>/</span>
          <span>Dashboard</span>
        </div>
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold">{overview.case_name}</h1>
            <p className="text-gray-600">
              Status: <span className="capitalize">{overview.case_status}</span>
            </p>
          </div>
          <Link
            to={`/cases/${caseId}/search`}
            className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 flex items-center gap-2"
          >
            <Search className="h-4 w-4" />
            Search
          </Link>
        </div>

        {overview.date_range_start && (
          <p className="text-sm text-gray-500 mt-2">
            Data range: {formatDistanceToNow(new Date(overview.date_range_start), { addSuffix: true })} to{' '}
            {formatDistanceToNow(new Date(overview.date_range_end), { addSuffix: true })}
          </p>
        )}
      </div>

      {/* Main Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatsCard
          title="Total Messages"
          value={stats.total_messages}
          icon={MessageSquare}
          color="blue"
        />
        <StatsCard
          title="Total Contacts"
          value={stats.total_contacts}
          icon={Users}
          color="green"
        />
        <StatsCard
          title="Total Media"
          value={stats.total_media}
          icon={Image}
          color="purple"
        />
        <StatsCard
          title="Deleted Messages"
          value={stats.total_deleted}
          icon={Trash2}
          color="orange"
        />
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* App-specific Stats */}
        <div>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            By Application
          </h2>
          <div className="space-y-4">
            {apps.includes('whatsapp') && stats.whatsapp && (
              <AppStatsCard app="WhatsApp" stats={stats.whatsapp} />
            )}
            {apps.includes('telegram') && stats.telegram && (
              <AppStatsCard app="Telegram" stats={stats.telegram} />
            )}
            {(!apps.includes('whatsapp') && !apps.includes('telegram')) && (
              <p className="text-gray-500 text-center py-8">No app data available.</p>
            )}
          </div>
        </div>

        {/* Correlation & Recent Events */}
        <div className="space-y-6">
          <CorrelationSummary stats={correlation_stats} />

          <div>
            <h2 className="text-lg font-semibold mb-4">Recent Activity</h2>
            <RecentEvents events={recent_events} />
          </div>
        </div>
      </div>

      {/* Timeline Stats */}
      {timeline_stats.total_events > 0 && (
        <div className="mt-6 border rounded-lg p-4">
          <h2 className="text-lg font-semibold mb-4">Timeline Summary</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold">{timeline_stats.total_events.toLocaleString()}</p>
              <p className="text-sm text-gray-500">Total Events</p>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold">
                {timeline_stats.events_by_app?.whatsapp?.toLocaleString() ?? 0}
              </p>
              <p className="text-sm text-gray-500">WhatsApp Events</p>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold">
                {timeline_stats.events_by_app?.telegram?.toLocaleString() ?? 0}
              </p>
              <p className="text-sm text-gray-500">Telegram Events</p>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold">
                {Object.keys(timeline_stats.events_by_type || {}).length}
              </p>
              <p className="text-sm text-gray-500">Event Types</p>
            </div>
          </div>
        </div>
      )}

      {/* Quick Links */}
      <div className="mt-6 flex flex-wrap gap-3">
        <Link
          to={`/cases/${caseId}?tab=timeline`}
          className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
        >
          View Full Timeline
        </Link>
        <Link
          to={`/cases/${caseId}?tab=correlation`}
          className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
        >
          View Correlation Graph
        </Link>
        <Link
          to={`/cases/${caseId}`}
          className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
        >
          Case Details
        </Link>
      </div>
    </div>
  );
};

export default DashboardPage;