import { useState, useEffect } from 'react';
import {
  AlertTriangle,
  Activity,
  Info,
  ChevronDown,
  ChevronRight,
  Filter,
  RefreshCw,
  Loader2,
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
  { id: 'activity', label: 'Activity', icon: Activity, color: 'cyan' },
  { id: 'analysis', label: 'Analysis', icon: Info, color: 'emerald' },
  { id: 'errors', label: 'Errors', icon: AlertTriangle, color: 'rose' },
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
  const config = LOG_TABS.find((t) => t.id === logType) || LOG_TABS[0];

  const borderColors = {
    cyan: 'border-l-accent-cyan',
    emerald: 'border-l-accent-emerald',
    rose: 'border-l-accent-rose',
  };
  const textColors = {
    cyan: 'text-accent-cyan',
    emerald: 'text-accent-emerald',
    rose: 'text-accent-rose',
  };

  return (
    <div
      className={`border-l-4 ${borderColors[config.color] || 'border-l-forensic-600'}
                  bg-forensic-900/50 p-3 mb-2 rounded-r
                  hover:bg-forensic-800/50 transition-colors`}
    >
      <div
        className="flex items-start justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start gap-3">
          <config.icon
            className={`h-5 w-5 ${textColors[config.color] || 'text-forensic-500'} mt-0.5 flex-shrink-0`}
          />
          <div>
            <p className="font-medium text-forensic-100">{log.message}</p>
            <p className="text-sm text-forensic-500 mt-1">
              {formatTimestamp(log.timestamp)}
              {log.case_id && ` • Case #${log.case_id}`}
              {log.evidence_id && ` • Evidence #${log.evidence_id}`}
            </p>
            <div className="flex flex-wrap gap-2 mt-2">
              {log.action && (
                <span className="badge badge-gray">{log.action}</span>
              )}
              {log.log_type && (
                <span className="badge badge-cyan">{log.log_type}</span>
              )}
              {log.error_type && (
                <span className="badge badge-rose">{log.error_type}</span>
              )}
              {log.stack_trace && (
                <span className="badge badge-amber">Has stack trace</span>
              )}
            </div>
          </div>
        </div>
        {expanded ? (
          <ChevronDown className="h-5 w-5 text-forensic-500" />
        ) : (
          <ChevronRight className="h-5 w-5 text-forensic-500" />
        )}
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="mt-3 pt-3 border-t border-forensic-700 text-sm space-y-2">
          {(log.details || log.metadata_) && (
            <div>
              <span className="text-forensic-500">Details: </span>
              <pre className="data-block mt-1">
                {JSON.stringify(log.details || log.metadata_ || {}, null, 2)}
              </pre>
            </div>
          )}
          {log.stack_trace && (
            <div>
              <span className="text-forensic-500">Stack Trace: </span>
              <pre className="data-block mt-1 text-accent-rose border border-accent-rose/30">
                {log.stack_trace}
              </pre>
            </div>
          )}
          {log.endpoint && (
            <p className="text-forensic-400">
              <span className="text-forensic-500">Endpoint: </span>
              <span className="font-mono">{log.method} {log.endpoint}</span>
              {log.client_ip && ` ({log.client_ip})`}
            </p>
          )}
          {log.description && (
            <p className="text-forensic-400">
              <span className="text-forensic-500">Description: </span>
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
    <div className="card mb-4">
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-forensic-500" />
          <span className="text-sm font-medium text-forensic-300">Filters</span>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm text-forensic-500">Case ID:</label>
          <input
            type="number"
            value={filters.case_id || ''}
            onChange={(e) =>
              onChange({ ...filters, case_id: e.target.value || undefined })
            }
            className="w-24 rounded px-2 py-1.5 text-sm border bg-forensic-800 border-forensic-700 text-forensic-100"
            placeholder="ID"
          />
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm text-forensic-500">Evidence ID:</label>
          <input
            type="number"
            value={filters.evidence_id || ''}
            onChange={(e) =>
              onChange({ ...filters, evidence_id: e.target.value || undefined })
            }
            className="w-24 rounded px-2 py-1.5 text-sm border bg-forensic-800 border-forensic-700 text-forensic-100"
            placeholder="ID"
          />
        </div>

        {logType === 'analysis' && (
          <div className="flex items-center gap-2">
            <label className="text-sm text-forensic-500">Log Type:</label>
            <input
              type="text"
              value={filters.log_type || ''}
              onChange={(e) =>
                onChange({ ...filters, log_type: e.target.value || undefined })
              }
              className="w-32 rounded px-2 py-1.5 text-sm border bg-forensic-800 border-forensic-700 text-forensic-100"
              placeholder="e.g., info, warning"
            />
          </div>
        )}

        {logType === 'errors' && (
          <div className="flex items-center gap-2">
            <label className="text-sm text-forensic-500">Error Type:</label>
            <input
              type="text"
              value={filters.error_type || ''}
              onChange={(e) =>
                onChange({ ...filters, error_type: e.target.value || undefined })
              }
              className="w-32 rounded px-2 py-1.5 text-sm border bg-forensic-800 border-forensic-700 text-forensic-100"
              placeholder="e.g., ValidationError"
            />
          </div>
        )}

        <div className="flex items-center gap-2">
          <label className="text-sm text-forensic-500">Limit:</label>
          <select
            value={filters.limit || 100}
            onChange={(e) =>
              onChange({ ...filters, limit: parseInt(e.target.value) })
            }
            className="rounded px-2 py-1.5 text-sm border bg-forensic-800 border-forensic-700 text-forensic-100"
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

  const loadingMap = { activity: loadingActivity, analysis: loadingAnalysis, errors: loadingError };
  const errorMap = { activity: errorActivity, analysis: errorAnalysis, errors: errorError };
  const logsMap = { activity: activityLogs, analysis: analysisLogs, errors: errorLogs };

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-forensic-100">System Logs</h2>
        <button
          onClick={handleRefresh}
          disabled={loadingMap[activeTab]}
          className="btn-ghost flex items-center gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${loadingMap[activeTab] ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 bg-forensic-800/50 p-1 rounded-lg">
        {LOG_TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`tab-button flex items-center gap-2 ${activeTab === tab.id ? 'tab-button-active' : ''}`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Filters */}
      <FilterBar filters={filters} onChange={setFilters} logType={activeTab} />

      {/* Log List */}
      <div className="mt-4">
        {loadingMap[activeTab] && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-accent-cyan" />
            <span className="ml-2 text-forensic-400">Loading logs...</span>
          </div>
        )}

        {errorMap[activeTab] && (
          <div className="alert alert-error">
            <AlertTriangle className="h-5 w-5" />
            <div>
              <p className="font-semibold">Error loading logs</p>
              <p className="text-sm opacity-80">{errorMap[activeTab]}</p>
            </div>
          </div>
        )}

        {!loadingMap[activeTab] && !errorMap[activeTab] && (
          <>
            {logsMap[activeTab].length === 0 ? (
              <div className="text-center py-8 card">
                <p className="text-forensic-500">No {activeTab} logs found</p>
              </div>
            ) : (
              <div className="max-h-[400px] overflow-y-auto">
                {logsMap[activeTab].map((log, index) => (
                  <LogEntry key={log.id || index} log={log} logType={activeTab} />
                ))}
              </div>
            )}
            <p className="text-sm text-forensic-500 mt-2 text-center">
              Showing {logsMap[activeTab].length} logs
            </p>
          </>
        )}
      </div>
    </div>
  );
};

export default LogsViewer;