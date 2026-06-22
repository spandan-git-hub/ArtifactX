import { useState, useEffect } from 'react';
import {
  AlertTriangle,
  Activity,
  Info,
  ChevronDown,
  ChevronRight,
  Filter,
  RefreshCw,
} from 'lucide-react';
import {
  useAnalysisLogs,
  useErrorLogs,
  useActivityLogs,
} from '../../hooks/useLogs';

/**
 * Tab configuration for log types
 */
const LOG_TABS = [
  { id: 'activity', label: 'Activity', icon: Activity, color: 'blue' },
  { id: 'analysis', label: 'Analysis', icon: Info, color: 'green' },
  { id: 'errors', label: 'Errors', icon: AlertTriangle, color: 'red' },
];

/**
 * Format timestamp to readable format
 */
const formatTimestamp = (timestamp) => {
  if (!timestamp) return 'N/A';
  const date = new Date(timestamp);
  return date.toLocaleString();
};

/**
 * Individual log entry component
 */
const LogEntry = ({ log, logType }) => {
  const [expanded, setExpanded] = useState(false);
  const Icon = LOG_TABS.find((t) => t.id === logType)?.icon || Info;
  const colorClass = LOG_TABS.find((t) => t.id === logType)?.color || 'gray';

  return (
    <div
      className={`border-l-4 border-${colorClass}-500 bg-white p-3 mb-2 rounded-r shadow-sm hover:shadow transition-shadow`}
    >
      <div
        className="flex items-start justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start gap-3">
          <Icon
            className={`h-5 w-5 text-${colorClass}-500 mt-0.5 flex-shrink-0`}
          />
          <div>
            <p className="font-medium text-gray-900">{log.message}</p>
            <p className="text-sm text-gray-500 mt-1">
              {formatTimestamp(log.timestamp)}
              {log.case_id && ` • Case #${log.case_id}`}
              {log.evidence_id && ` • Evidence #${log.evidence_id}`}
            </p>
            {log.action && (
              <span className="inline-block mt-1 px-2 py-0.5 bg-gray-100 text-gray-700 text-xs rounded">
                {log.action}
              </span>
            )}
            {log.error_type && (
              <span className="inline-block mt-1 mr-2 px-2 py-0.5 bg-red-100 text-red-700 text-xs rounded">
                {log.error_type}
              </span>
            )}
            {log.stack_trace && (
              <span className="inline-block mt-1 px-2 py-0.5 bg-orange-100 text-orange-700 text-xs rounded">
                Has stack trace
              </span>
            )}
          </div>
        </div>
        {expanded ? (
          <ChevronDown className="h-5 w-5 text-gray-400" />
        ) : (
          <ChevronRight className="h-5 w-5 text-gray-400" />
        )}
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="mt-3 pt-3 border-t border-gray-200 text-sm">
          {(log.details || log.metadata_) && (
            <div className="mb-2">
              <span className="text-gray-500">Details: </span>
              <pre className="bg-gray-50 p-2 rounded overflow-x-auto text-xs">
                {JSON.stringify(log.details || log.metadata_ || {}, null, 2)}
              </pre>
            </div>
          )}
          {log.stack_trace && (
            <div className="mb-2">
              <span className="text-gray-500">Stack Trace: </span>
              <pre className="bg-red-50 p-2 rounded overflow-x-auto text-xs text-red-700">
                {log.stack_trace}
              </pre>
            </div>
          )}
          {log.endpoint && (
            <p className="text-gray-600">
              <span className="text-gray-500">Endpoint: </span>
              {log.method} {log.endpoint}
              {log.client_ip && ` (${log.client_ip})`}
            </p>
          )}
          {log.description && (
            <p className="text-gray-600">
              <span className="text-gray-500">Description: </span>
              {log.description}
            </p>
          )}
        </div>
      )}
    </div>
  );
};

/**
 * Filter bar component
 */
const FilterBar = ({ filters, onChange, logType }) => {
  return (
    <div className="bg-white p-3 rounded-lg shadow-sm mb-4">
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-gray-400" />
          <span className="text-sm font-medium text-gray-700">Filters</span>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600">Case ID:</label>
          <input
            type="number"
            value={filters.case_id || ''}
            onChange={(e) =>
              onChange({ ...filters, case_id: e.target.value || undefined })
            }
            className="w-24 border border-gray-300 rounded px-2 py-1 text-sm"
            placeholder="ID"
          />
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600">Evidence ID:</label>
          <input
            type="number"
            value={filters.evidence_id || ''}
            onChange={(e) =>
              onChange({ ...filters, evidence_id: e.target.value || undefined })
            }
            className="w-24 border border-gray-300 rounded px-2 py-1 text-sm"
            placeholder="ID"
          />
        </div>

        {logType === 'analysis' && (
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">Log Type:</label>
            <input
              type="text"
              value={filters.log_type || ''}
              onChange={(e) =>
                onChange({ ...filters, log_type: e.target.value || undefined })
              }
              className="w-32 border border-gray-300 rounded px-2 py-1 text-sm"
              placeholder="e.g., info, warning"
            />
          </div>
        )}

        {logType === 'errors' && (
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">Error Type:</label>
            <input
              type="text"
              value={filters.error_type || ''}
              onChange={(e) =>
                onChange({ ...filters, error_type: e.target.value || undefined })
              }
              className="w-32 border border-gray-300 rounded px-2 py-1 text-sm"
              placeholder="e.g., ValidationError"
            />
          </div>
        )}

        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600">Limit:</label>
          <select
            value={filters.limit || 100}
            onChange={(e) =>
              onChange({ ...filters, limit: parseInt(e.target.value) })
            }
            className="border border-gray-300 rounded px-2 py-1 text-sm"
          >
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={250}>250</option>
            <option value={500}>500</option>
          </select>
        </div>
      </div>
    </div>
  );
};

/**
 * Main LogsViewer component
 */
const LogsViewer = ({ caseId }) => {
  const [activeTab, setActiveTab] = useState('activity');
  const [filters, setFilters] = useState({ case_id: caseId, limit: 100 });

  const {
    logs: activityLogs,
    loading: loadingActivity,
    error: errorActivity,
    fetchLogs: fetchActivity,
  } = useActivityLogs();

  const {
    logs: analysisLogs,
    loading: loadingAnalysis,
    error: errorAnalysis,
    fetchLogs: fetchAnalysis,
  } = useAnalysisLogs();

  const {
    logs: errorLogs,
    loading: loadingError,
    error: errorError,
    fetchLogs: fetchError,
  } = useErrorLogs();

  // Set case_id when caseId prop changes
  useEffect(() => {
    if (caseId) {
      setFilters((prev) => ({ ...prev, case_id: caseId }));
    }
  }, [caseId]);

  // Fetch logs when tab or filters change
  useEffect(() => {
    const fetchLogsMap = {
      activity: fetchActivity,
      analysis: fetchAnalysis,
      errors: fetchError,
    };

    const fetchFn = fetchLogsMap[activeTab];
    if (fetchFn) {
      fetchFn(filters);
    }
  }, [activeTab, filters, fetchActivity, fetchAnalysis, fetchError]);

  const handleRefresh = () => {
    const fetchLogsMap = {
      activity: fetchActivity,
      analysis: fetchAnalysis,
      errors: fetchError,
    };

    const fetchFn = fetchLogsMap[activeTab];
    if (fetchFn) {
      fetchFn(filters);
    }
  };

  const loadingMap = {
    activity: loadingActivity,
    analysis: loadingAnalysis,
    errors: loadingError,
  };

  const errorMap = {
    activity: errorActivity,
    analysis: errorAnalysis,
    errors: errorError,
  };

  const logsMap = {
    activity: activityLogs,
    analysis: analysisLogs,
    errors: errorLogs,
  };

  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-800">
          System Logs
        </h2>
        <button
          onClick={handleRefresh}
          disabled={loadingMap[activeTab]}
          className="flex items-center gap-2 px-3 py-1.5 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
        >
          <RefreshCw
            className={`h-4 w-4 ${loadingMap[activeTab] ? 'animate-spin' : ''}`}
          />
          <span className="text-sm">Refresh</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 bg-white p-1 rounded-lg">
        {LOG_TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? `bg-${tab.color}-100 text-${tab.color}-700`
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Filters */}
      <FilterBar
        filters={filters}
        onChange={setFilters}
        logType={activeTab}
      />

      {/* Log List */}
      <div className="mt-4">
        {loadingMap[activeTab] && (
          <div className="text-center py-8 text-gray-500">
            <div className="animate-pulse">Loading logs...</div>
          </div>
        )}

        {errorMap[activeTab] && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            <p className="font-medium">Error loading logs</p>
            <p className="text-sm mt-1">{errorMap[activeTab]}</p>
          </div>
        )}

        {!loadingMap[activeTab] && !errorMap[activeTab] && (
          <>
            {logsMap[activeTab].length === 0 ? (
              <div className="text-center py-8 text-gray-500 bg-white rounded-lg">
                <p>No {activeTab} logs found</p>
              </div>
            ) : (
              <div className="max-h-96 overflow-y-auto">
                {logsMap[activeTab].map((log, index) => (
                  <LogEntry key={log.id || index} log={log} logType={activeTab} />
                ))}
              </div>
            )}

            <p className="text-sm text-gray-500 mt-2 text-center">
              Showing {logsMap[activeTab].length} logs
            </p>
          </>
        )}
      </div>
    </div>
  );
};

export default LogsViewer;