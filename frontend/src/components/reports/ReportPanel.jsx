import { useState } from 'react';
import { FileText, Loader2, CheckCircle, AlertCircle, Download } from 'lucide-react';
import { useReports, useReportSummaries } from '../hooks/useReports';

const ReportPanel = ({ caseId }) => {
  const [reportType, setReportType] = useState('full');
  const [options, setOptions] = useState({
    includeEvidence: true,
    includeTimeline: true,
    includeDeleted: true,
    includeCorrelations: true,
  });

  const { loading, error, lastReport, generateReport, downloadReport } = useReports();
  const { evidenceSummary, timelineSummary, deletedSummary, loading: loadingSummaries, error: summaryError } = useReportSummaries();

  const handleGenerate = async () => {
    try {
      await generateReport(caseId, { reportType, ...options });
    } catch (err) {
      // Error handled by hook
    }
  };

  const toggleOption = (key) => {
    setOptions(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
        <FileText className="h-5 w-5" />
        Generate Report
      </h2>

      {/* Report Type Selection */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Report Type
        </label>
        <select
          value={reportType}
          onChange={(e) => setReportType(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="full">Full Report</option>
          <option value="evidence">Evidence Summary</option>
          <option value="timeline">Timeline Analysis</option>
          <option value="deleted">Deleted Messages</option>
          <option value="summary">Executive Summary</option>
        </select>
      </div>

      {/* Options (for full report) */}
      {reportType === 'full' && (
        <div className="mb-4 space-y-2">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Include Sections
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={options.includeEvidence}
              onChange={() => toggleOption('includeEvidence')}
              className="rounded text-blue-600"
            />
            <span className="text-sm">Evidence Analysis</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={options.includeTimeline}
              onChange={() => toggleOption('includeTimeline')}
              className="rounded text-blue-600"
            />
            <span className="text-sm">Timeline Analysis</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={options.includeDeleted}
              onChange={() => toggleOption('includeDeleted')}
              className="rounded text-blue-600"
            />
            <span className="text-sm">Deleted Message Analysis</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={options.includeCorrelations}
              onChange={() => toggleOption('includeCorrelations')}
              className="rounded text-blue-600"
            />
            <span className="text-sm">Evidence Correlations</span>
          </label>
        </div>
      )}

      {/* Generate Button */}
      <button
        onClick={handleGenerate}
        disabled={loading}
        className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:bg-gray-300 flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <Loader2 className="h-5 w-5 animate-spin" />
            Generating...
          </>
        ) : (
          <>
            <FileText className="h-5 w-5" />
            Generate {reportType === 'full' ? 'Full Report' : reportType.charAt(0).toUpperCase() + reportType.slice(1) + ' Report'}
          </>
        )}
      </button>

      {/* Success Message */}
      {lastReport && lastReport.status === 'completed' && (
        <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-center gap-2 text-green-700">
            <CheckCircle className="h-5 w-5" />
            <span className="font-medium">Report Generated!</span>
          </div>
          <p className="text-sm text-green-600 mt-1">{lastReport.message}</p>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center gap-2 text-red-700">
            <AlertCircle className="h-5 w-5" />
            <span className="font-medium">Error</span>
          </div>
          <p className="text-sm text-red-600 mt-1">{error}</p>
        </div>
      )}
    </div>
  );
};

export default ReportPanel;