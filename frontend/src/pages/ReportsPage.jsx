import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, FileText, BarChart3 } from 'lucide-react';
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
    return <div className="p-6">Loading case...</div>;
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
          <Link to="/cases" className="hover:text-blue-600 flex items-center gap-1">
            <ArrowLeft className="h-4 w-4" />
            Cases
          </Link>
          <span>/</span>
          <Link to={`/cases/${caseId}`} className="hover:text-blue-600">
            {caseData?.name || 'Case'}
          </Link>
          <span>/</span>
          <span>Reports</span>
        </div>
        <h1 className="text-2xl font-bold">Forensic Reports</h1>
        <p className="text-gray-600">Generate PDF reports for case: {caseData?.name}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Report Generation Panel */}
        <div className="lg:col-span-1">
          <ReportPanel caseId={caseId} />
        </div>

        {/* Summary Previews */}
        <div className="lg:col-span-2 space-y-6">
          {/* Evidence Summary */}
          <div className="bg-white p-4 rounded-lg shadow">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <FileText className="h-5 w-5 text-blue-600" />
              Evidence Summary
            </h3>
            {loadingSummaries ? (
              <p className="text-gray-500">Loading...</p>
            ) : evidenceSummary ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-3 bg-gray-50 rounded-lg">
                  <p className="text-2xl font-bold">{evidenceSummary.total_evidence_files}</p>
                  <p className="text-xs text-gray-500">Evidence Files</p>
                </div>
                <div className="text-center p-3 bg-gray-50 rounded-lg">
                  <p className="text-2xl font-bold">{evidenceSummary.total_extracted_files}</p>
                  <p className="text-xs text-gray-500">Extracted Files</p>
                </div>
                <div className="text-center p-3 bg-gray-50 rounded-lg">
                  <p className="text-2xl font-bold">{evidenceSummary.media_summary?.total || 0}</p>
                  <p className="text-xs text-gray-500">Media Files</p>
                </div>
                <div className="text-center p-3 bg-gray-50 rounded-lg">
                  <p className="text-2xl font-bold">{evidenceSummary.apps_found?.length || 0}</p>
                  <p className="text-xs text-gray-500">Apps Found</p>
                </div>
              </div>
            ) : (
              <p className="text-gray-500">No evidence data</p>
            )}
          </div>

          {/* Timeline Summary */}
          <div className="bg-white p-4 rounded-lg shadow">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-green-600" />
              Timeline Summary
            </h3>
            {loadingSummaries ? (
              <p className="text-gray-500">Loading...</p>
            ) : timelineSummary ? (
              <div className="space-y-2">
                <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                  <span className="font-medium">Total Events</span>
                  <span className="text-xl font-bold">{timelineSummary.total_events}</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="p-2 bg-blue-50 rounded text-center">
                    <p className="font-semibold">{timelineSummary.events_by_app?.whatsapp || 0}</p>
                    <p className="text-xs text-gray-500">WhatsApp</p>
                  </div>
                  <div className="p-2 bg-blue-50 rounded text-center">
                    <p className="font-semibold">{timelineSummary.events_by_app?.telegram || 0}</p>
                    <p className="text-xs text-gray-500">Telegram</p>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-gray-500">No timeline data</p>
            )}
          </div>

          {/* Deleted Messages Summary */}
          <div className="bg-white p-4 rounded-lg shadow">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <span className="text-red-600">⚠</span>
              Deleted Messages
            </h3>
            {loadingSummaries ? (
              <p className="text-gray-500">Loading...</p>
            ) : deletedSummary ? (
              <div className="space-y-2">
                <div className="flex justify-between items-center p-3 bg-red-50 rounded-lg">
                  <span className="font-medium">Total Detections</span>
                  <span className="text-xl font-bold text-red-600">{deletedSummary.total_deletions}</span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center text-sm">
                  <div className="p-2 bg-green-50 rounded">
                    <p className="font-semibold text-green-600">{deletedSummary.high_confidence_count || 0}</p>
                    <p className="text-xs text-gray-500">High Conf.</p>
                  </div>
                  <div className="p-2 bg-yellow-50 rounded">
                    <p className="font-semibold text-yellow-600">{deletedSummary.medium_confidence_count || 0}</p>
                    <p className="text-xs text-gray-500">Med Conf.</p>
                  </div>
                  <div className="p-2 bg-gray-50 rounded">
                    <p className="font-semibold text-gray-600">{deletedSummary.low_confidence_count || 0}</p>
                    <p className="text-xs text-gray-500">Low Conf.</p>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-gray-500">No deleted message data</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportsPage;