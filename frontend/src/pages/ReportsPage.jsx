import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, FileText, BarChart3, Trash2, ClipboardList, Loader2 } from 'lucide-react';
import { caseService } from '../services/caseService';
import { ReportPanel } from '../components/reports';
import { useReportSummaries } from '../hooks/useReports';
import { formatDistanceToNow } from 'date-fns';

const ReportsPage = () => {
  const { caseId } = useParams();
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const { evidenceSummary, timelineSummary, deletedSummary, loading: loadingSummaries, loadSummaries } = useReportSummaries();

  useEffect(() => {
    const loadCase = async () => {
      try {
        setLoading(true);
        const data = await caseService.getCase(caseId);
        setCaseData(data);
      } catch (err) {
        console.error('Failed to load case:', err);
      } finally {
        setLoading(false);
      }
    };

    if (caseId) {
      loadCase();
      loadSummaries();
    }
  }, [caseId, loadSummaries]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-accent-cyan mx-auto" />
          <span className="mt-3 text-forensic-400 block">Loading case data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto animate-in">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 text-sm text-forensic-500 mb-3">
          <Link to="/cases" className="hover:text-accent-cyan flex items-center gap-1 transition-colors">
            <ArrowLeft className="h-4 w-4" />
            Cases
          </Link>
          <span className="text-forensic-700">/</span>
          <Link to={`/cases/${caseId}`} className="hover:text-accent-cyan transition-colors">
            {caseData?.name || 'Case'}
          </Link>
          <span className="text-forensic-700">/</span>
          <span className="text-accent-cyan">Reports</span>
        </div>
        <h1 className="text-2xl font-bold text-forensic-50 mb-1">Forensic Reports</h1>
        <p className="text-forensic-500">Generate PDF reports for: <span className="text-forensic-300">{caseData?.name}</span></p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Report Generation Panel */}
        <div className="lg:col-span-1">
          <div className="card">
            <div className="section-header mb-4">
              <div className="section-icon">
                <FileText className="h-5 w-5" />
              </div>
              <h2 className="section-title">Generate Report</h2>
            </div>
            <ReportPanel caseId={caseId} />
          </div>
        </div>

        {/* Summary Previews */}
        <div className="lg:col-span-2 space-y-6">
          {/* Evidence Summary */}
          <div className="card">
            <div className="section-header mb-4">
              <div className="section-icon text-accent-emerald">
                <ClipboardList className="h-5 w-5" />
              </div>
              <h2 className="section-title">Evidence Summary</h2>
            </div>
            {loadingSummaries ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-accent-cyan" />
              </div>
            ) : evidenceSummary ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="metric-card">
                  <p className="metric-value">{evidenceSummary.total_evidence_files}</p>
                  <p className="metric-label">Evidence Files</p>
                </div>
                <div className="metric-card">
                  <p className="metric-value">{evidenceSummary.total_extracted_files}</p>
                  <p className="metric-label">Extracted</p>
                </div>
                <div className="metric-card">
                  <p className="metric-value text-accent-violet">{evidenceSummary.media_summary?.total || 0}</p>
                  <p className="metric-label">Media Files</p>
                </div>
                <div className="metric-card">
                  <p className="metric-value">{evidenceSummary.apps_found?.length || 0}</p>
                  <p className="metric-label">Apps Found</p>
                </div>
              </div>
            ) : (
              <p className="text-center text-forensic-500 py-8">No evidence data available</p>
            )}
          </div>

          {/* Timeline Summary */}
          <div className="card">
            <div className="section-header mb-4">
              <div className="section-icon text-accent-cyan">
                <BarChart3 className="h-5 w-5" />
              </div>
              <h2 className="section-title">Timeline Summary</h2>
            </div>
            {loadingSummaries ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-accent-cyan" />
              </div>
            ) : timelineSummary ? (
              <div className="space-y-4">
                <div className="flex justify-between items-center p-4 bg-forensic-800/50 rounded-lg">
                  <span className="font-medium text-forensic-300">Total Events</span>
                  <span className="text-2xl font-bold text-accent-cyan font-mono">
                    {timelineSummary.total_events.toLocaleString()}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-forensic-800/30 rounded-lg text-center border border-forensic-700/50">
                    <p className="text-xl font-bold text-accent-emerald font-mono">
                      {timelineSummary.events_by_app?.whatsapp || 0}
                    </p>
                    <p className="text-xs text-forensic-500 mt-1">WhatsApp</p>
                  </div>
                  <div className="p-4 bg-forensic-800/30 rounded-lg text-center border border-forensic-700/50">
                    <p className="text-xl font-bold text-accent-blue font-mono">
                      {timelineSummary.events_by_app?.telegram || 0}
                    </p>
                    <p className="text-xs text-forensic-500 mt-1">Telegram</p>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-center text-forensic-500 py-8">No timeline data available</p>
            )}
          </div>

          {/* Deleted Messages Summary */}
          <div className="card border-accent-rose/20">
            <div className="section-header mb-4">
              <div className="section-icon text-accent-rose">
                <Trash2 className="h-5 w-5" />
              </div>
              <h2 className="section-title">Deleted Messages</h2>
            </div>
            {loadingSummaries ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-accent-cyan" />
              </div>
            ) : deletedSummary ? (
              <div className="space-y-4">
                <div className="flex justify-between items-center p-4 bg-accent-rose/10 rounded-lg border border-accent-rose/20">
                  <span className="font-medium text-forensic-300">Total Detections</span>
                  <span className="text-2xl font-bold text-accent-rose font-mono">
                    {deletedSummary.total_deletions}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div className="p-3 bg-accent-emerald/10 rounded-lg text-center border border-accent-emerald/20">
                    <p className="text-lg font-bold text-accent-emerald font-mono">
                      {deletedSummary.high_confidence_count || 0}
                    </p>
                    <p className="text-xs text-forensic-500 mt-0.5">High Conf.</p>
                  </div>
                  <div className="p-3 bg-accent-amber/10 rounded-lg text-center border border-accent-amber/20">
                    <p className="text-lg font-bold text-accent-amber font-mono">
                      {deletedSummary.medium_confidence_count || 0}
                    </p>
                    <p className="text-xs text-forensic-500 mt-0.5">Med Conf.</p>
                  </div>
                  <div className="p-3 bg-forensic-800/30 rounded-lg text-center border border-forensic-700/50">
                    <p className="text-lg font-bold text-forensic-400 font-mono">
                      {deletedSummary.low_confidence_count || 0}
                    </p>
                    <p className="text-xs text-forensic-500 mt-0.5">Low Conf.</p>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-center text-forensic-500 py-8">No deleted message data available</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportsPage;