import { useState } from 'react';
import { FileText, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { useReports } from '../../hooks/useReports';

const ReportPanel = ({ caseId }) => {
  const [reportType, setReportType] = useState('full');
  const [options, setOptions] = useState({
    includeEvidence: true,
    includeTimeline: true,
    includeDeleted: true,
    includeCorrelations: true,
  });

  const { loading, error, lastReport, generateReport } = useReports();

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
    <div className="card">
      <h2 className="text-lg font-semibold text-forensic-100 mb-4 flex items-center gap-2">
        <FileText className="h-5 w-5 text-accent-cyan" />
        Generate Report
      </h2>

      {/* Report Type Selection */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-forensic-400 mb-2">
          Report Type
        </label>
        <select
          value={reportType}
          onChange={(e) => setReportType(e.target.value)}
          className="w-full px-4 py-2.5 rounded-lg bg-forensic-800 border border-forensic-700
                     text-forensic-100 focus:border-accent-cyan focus:ring-2 focus:ring-accent-cyan/20"
        >
          <option value="full">Full Report — Complete forensic analysis</option>
          <option value="evidence">Evidence Summary — File inventory and analysis</option>
          <option value="timeline">Timeline Analysis — Event timeline and patterns</option>
          <option value="deleted">Deleted Messages — Deletion detection report</option>
          <option value="summary">Executive Summary — High-level overview</option>
        </select>
      </div>

      {/* Options (for full report) */}
      {reportType === 'full' && (
        <div className="mb-4 space-y-2">
          <label className="block text-sm font-medium text-forensic-400 mb-2">
            Include Sections
          </label>
          {[
            { key: 'includeEvidence', label: 'Evidence Analysis' },
            { key: 'includeTimeline', label: 'Timeline Analysis' },
            { key: 'includeDeleted', label: 'Deleted Message Detection' },
            { key: 'includeCorrelations', label: 'Evidence Correlations' },
          ].map(({ key, label }) => (
            <label key={key} className="flex items-center gap-3 cursor-pointer group">
              <input
                type="checkbox"
                checked={options[key]}
                onChange={() => toggleOption(key)}
                className="w-4 h-4 rounded border-forensic-600 bg-forensic-800 text-accent-cyan
                           focus:ring-accent-cyan focus:ring-offset-0"
              />
              <span className="text-sm text-forensic-300 group-hover:text-forensic-100 transition-colors">
                {label}
              </span>
            </label>
          ))}
        </div>
      )}

      {/* Generate Button */}
      <button
        onClick={handleGenerate}
        disabled={loading}
        className="btn-primary w-full"
      >
        {loading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Generating PDF...
          </>
        ) : (
          <>
            <FileText className="h-4 w-4" />
            {reportType === 'full'
              ? 'Generate Full Report'
              : `Generate ${reportType.charAt(0).toUpperCase() + reportType.slice(1)} Report`}
          </>
        )}
      </button>

      {/* Success Message */}
      {lastReport && lastReport.status === 'completed' && (
        <div className="mt-4 p-3 bg-accent-emerald/10 border border-accent-emerald/30 rounded-lg">
          <div className="flex items-center gap-2 text-accent-emerald">
            <CheckCircle className="h-5 w-5" />
            <span className="font-medium">Report Generated!</span>
          </div>
          <p className="text-sm text-accent-emerald/80 mt-1">
            {lastReport.message || 'PDF report is ready for download.'}
          </p>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="mt-4 p-3 bg-accent-rose/10 border border-accent-rose/30 rounded-lg">
          <div className="flex items-center gap-2 text-accent-rose">
            <AlertCircle className="h-5 w-5" />
            <span className="font-medium">Error</span>
          </div>
          <p className="text-sm text-accent-rose/80 mt-1">{error}</p>
        </div>
      )}
    </div>
  );
};

export default ReportPanel;