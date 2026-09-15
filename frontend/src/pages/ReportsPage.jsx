import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  FileText,
  BarChart3,
  Trash2,
  ClipboardList,
  Loader2,
  History,
  Download,
  Copy,
  Check,
  ShieldCheck,
  Sparkles,
  Scale,
  RefreshCw,
} from 'lucide-react';
import { caseService } from '../services/caseService';
import CaseWorkspacePage from './CaseWorkspacePage';
import { ReportPanel, ReportPdfPreview } from '../components/reports';
import { useReports, useReportSummaries } from '../hooks/useReports';
import { formatDistanceToNow } from 'date-fns';

const ReportsPage = () => {
  const { caseId } = useParams();
  const [caseData, setCaseData] = useState(null);
  const [loadingCase, setLoadingCase] = useState(true);
  const [showPreview, setShowPreview] = useState(true);
  const [copiedHash, setCopiedHash] = useState(null);

  // Form State shared between Panel and Live Preview
  const [formState, setFormState] = useState({
    reportType: 'full',
    options: {
      includeEvidence: true,
      includeCustodyLog: true,
      includeTimeline: true,
      includeDeleted: true,
      includeCorrelations: true,
    },
    leadAnalyst: 'Special Agent Examiner',
    agency: 'Digital Forensics & Cyber Division',
    caseNotes: '',
    swornDeclaration: true,
  });

  const {
    history,
    loadingHistory,
    loadHistory,
    reDownloadReport,
  } = useReports();

  const {
    evidenceSummary,
    timelineSummary,
    deletedSummary,
    loading: loadingSummaries,
    loadSummaries,
  } = useReportSummaries(caseId);

  useEffect(() => {
    const loadCase = async () => {
      try {
        setLoadingCase(true);
        const data = await caseService.getCase(caseId);
        setCaseData(data);
        if (data?.investigator) {
          setFormState((prev) => ({
            ...prev,
            leadAnalyst: data.investigator,
          }));
        }
      } catch (err) {
        console.error('Failed to load case:', err);
      } finally {
        setLoadingCase(false);
      }
    };

    if (caseId) {
      loadCase();
      loadSummaries();
      loadHistory(caseId);
    }
  }, [caseId, loadSummaries, loadHistory]);

  const handleCopyHash = (hash) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const handleReDownload = async (report) => {
    try {
      await reDownloadReport(caseId, report.report_id, report.filename);
    } catch (err) {
      alert('Failed to download report: ' + err.message);
    }
  };

  if (loadingCase) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center space-y-3">
          <Loader2 className="h-8 w-8 animate-spin text-accent-cyan mx-auto" />
          <span className="text-forensic-400 font-mono text-sm block">Loading Court Reporting Subsystem...</span>
        </div>
      </div>
    );
  }

  return (
    <CaseWorkspacePage>
      <div className="animate-in space-y-8">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-forensic-800">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-accent-cyan/10 border border-accent-cyan/20 flex items-center justify-center text-accent-cyan">
              <Scale className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-xl font-bold font-mono text-forensic-50 flex items-center gap-2">
                Court-Ready PDF Reports & Custody Tracker
              </h1>
              <p className="text-xs text-forensic-400">
                In-memory zero-workspace report compiler. Generates deterministic, ISO/IEC 27037 compliant court documentation.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <span className="text-xs font-mono px-3 py-1 rounded bg-forensic-900 border border-forensic-700 text-forensic-300 flex items-center gap-1.5">
            <History className="w-3.5 h-3.5 text-accent-cyan" />
            {history.length} Reports Tracked
          </span>
        </div>
      </div>

      {/* Main Two-Column Workstation Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Generator Configuration Panel (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          <ReportPanel
            caseId={caseId}
            caseData={caseData}
            showPreview={showPreview}
            setShowPreview={setShowPreview}
            formState={formState}
            setFormState={setFormState}
          />
        </div>

        {/* Right Column: Live Layout Preview or Summary Cards (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {showPreview ? (
            <ReportPdfPreview
              caseData={caseData}
              reportType={formState.reportType}
              options={formState.options}
              leadAnalyst={formState.leadAnalyst}
              agency={formState.agency}
              caseNotes={formState.caseNotes}
              swornDeclaration={formState.swornDeclaration}
              evidenceSummary={evidenceSummary}
              timelineSummary={timelineSummary}
              deletedSummary={deletedSummary}
            />
          ) : (
            /* Summary Cards when preview is collapsed */
            <div className="space-y-4">
              {/* Evidence Summary Card */}
              <div className="card">
                <div className="section-header mb-3">
                  <div className="section-icon text-accent-emerald">
                    <ClipboardList className="h-4 w-4" />
                  </div>
                  <h2 className="section-title text-sm">Evidence Manifest Scope</h2>
                </div>
                {loadingSummaries ? (
                  <div className="py-6 flex justify-center"><Loader2 className="h-5 w-5 animate-spin text-accent-cyan" /></div>
                ) : evidenceSummary ? (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="metric-card">
                      <p className="metric-value text-base">{evidenceSummary.total_evidence_files}</p>
                      <p className="metric-label text-[10px]">Containers</p>
                    </div>
                    <div className="metric-card">
                      <p className="metric-value text-base">{evidenceSummary.total_extracted_files}</p>
                      <p className="metric-label text-[10px]">Extracted Files</p>
                    </div>
                    <div className="metric-card">
                      <p className="metric-value text-base text-accent-violet">{evidenceSummary.media_summary?.total || 0}</p>
                      <p className="metric-label text-[10px]">Media Items</p>
                    </div>
                    <div className="metric-card">
                      <p className="metric-value text-base">{evidenceSummary.apps_found?.length || 0}</p>
                      <p className="metric-label text-[10px]">Apps Parsed</p>
                    </div>
                  </div>
                ) : null}
              </div>

              {/* Timeline Summary Card */}
              <div className="card">
                <div className="section-header mb-3">
                  <div className="section-icon text-accent-cyan">
                    <BarChart3 className="h-4 w-4" />
                  </div>
                  <h2 className="section-title text-sm">Timeline Reconstruction Scope</h2>
                </div>
                {timelineSummary ? (
                  <div className="flex items-center justify-between p-3 bg-forensic-800/40 rounded-lg border border-forensic-700/50">
                    <span className="text-xs text-forensic-300">Total Normalized Events</span>
                    <span className="font-mono text-lg font-bold text-accent-cyan">
                      {timelineSummary.total_events.toLocaleString()}
                    </span>
                  </div>
                ) : null}
              </div>

              {/* Deletions Summary Card */}
              <div className="card border-accent-rose/20">
                <div className="section-header mb-3">
                  <div className="section-icon text-accent-rose">
                    <Trash2 className="h-4 w-4" />
                  </div>
                  <h2 className="section-title text-sm">Anti-Forensic Deletion Anomalies</h2>
                </div>
                {deletedSummary ? (
                  <div className="flex items-center justify-between p-3 bg-accent-rose/10 rounded-lg border border-accent-rose/20">
                    <span className="text-xs text-forensic-300">Detected Gaps & Missing Messages</span>
                    <span className="font-mono text-lg font-bold text-accent-rose">
                      {deletedSummary.total_deletions}
                    </span>
                  </div>
                ) : null}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Bottom Section: In-App Report History Tracker Table */}
      <div className="card space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-forensic-800">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-accent-cyan" />
            <h2 className="text-sm font-semibold text-forensic-100 uppercase tracking-wide font-mono">
              In-App Report History Tracker (Database Manifest)
            </h2>
          </div>
          <button
            type="button"
            onClick={() => loadHistory(caseId)}
            className="text-xs font-mono text-forensic-400 hover:text-accent-cyan flex items-center gap-1 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingHistory ? 'animate-spin' : ''}`} />
            Refresh History
          </button>
        </div>

        {loadingHistory ? (
          <div className="py-8 text-center text-forensic-500 flex items-center justify-center gap-2 text-xs">
            <Loader2 className="w-4 h-4 animate-spin text-accent-cyan" />
            Loading report history records...
          </div>
        ) : history.length === 0 ? (
          <div className="py-12 text-center text-forensic-500 space-y-2">
            <FileText className="w-8 h-8 text-forensic-600 mx-auto opacity-50" />
            <p className="text-sm font-mono text-forensic-400">No court reports recorded for Case #{caseId} yet.</p>
            <p className="text-xs text-forensic-500">
              Configure parameters above and click "Generate & Stream Court PDF" to generate the first official court report.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-forensic-950 text-forensic-400 font-mono uppercase text-[11px] border-b border-forensic-800">
                <tr>
                  <th className="py-2.5 px-3">Report ID</th>
                  <th className="py-2.5 px-3">Type</th>
                  <th className="py-2.5 px-3">Lead Examiner & Agency</th>
                  <th className="py-2.5 px-3">Generated Date</th>
                  <th className="py-2.5 px-3">Pages / Size</th>
                  <th className="py-2.5 px-3">SHA-256 Verification Signature</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-forensic-800/60 font-sans">
                {history.map((rep) => {
                  const sizeFormatted = rep.size_bytes > 1024
                    ? `${(rep.size_bytes / 1024).toFixed(1)} KB`
                    : `${rep.size_bytes} B`;
                  const isCopied = copiedHash === rep.sha256;

                  return (
                    <tr key={rep.id || rep.report_id} className="hover:bg-forensic-800/30 transition-colors">
                      {/* Report ID */}
                      <td className="py-3 px-3 font-mono text-accent-cyan text-[11px]">
                        {rep.report_id ? rep.report_id.slice(0, 8) : '—'}...
                      </td>

                      {/* Type */}
                      <td className="py-3 px-3">
                        <span className="badge badge-gray text-[10px] uppercase font-mono">
                          {rep.report_type}
                        </span>
                      </td>

                      {/* Examiner & Agency */}
                      <td className="py-3 px-3">
                        <div className="font-medium text-forensic-200">{rep.lead_analyst || 'Examiner'}</div>
                        <div className="text-[10px] text-forensic-500">{rep.agency || 'Digital Forensics Unit'}</div>
                      </td>

                      {/* Date */}
                      <td className="py-3 px-3 font-mono text-forensic-400 text-[11px]">
                        {rep.generated_at ? (
                          <>
                            <div>{new Date(rep.generated_at).toISOString().replace('T', ' ').slice(0, 19)}</div>
                            <div className="text-[10px] text-forensic-600">
                              {formatDistanceToNow(new Date(rep.generated_at), { addSuffix: true })}
                            </div>
                          </>
                        ) : '—'}
                      </td>

                      {/* Pages & Size */}
                      <td className="py-3 px-3 font-mono text-forensic-300 text-[11px]">
                        {rep.total_pages} {rep.total_pages === 1 ? 'page' : 'pages'} ({sizeFormatted})
                      </td>

                      {/* SHA-256 Hash with click-to-copy */}
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-1.5">
                          <span
                            className="font-mono text-[10px] text-accent-cyan bg-accent-cyan/10 px-1.5 py-0.5 rounded border border-accent-cyan/20 truncate max-w-[140px]"
                            title={rep.sha256}
                          >
                            {rep.sha256 ? `${rep.sha256.slice(0, 12)}...${rep.sha256.slice(-6)}` : '—'}
                          </span>
                          <button
                            type="button"
                            onClick={() => handleCopyHash(rep.sha256)}
                            className="text-forensic-400 hover:text-forensic-100 p-1 rounded hover:bg-forensic-800 transition-colors"
                            title="Copy full SHA-256 hash"
                          >
                            {isCopied ? (
                              <Check className="w-3.5 h-3.5 text-accent-emerald" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      </td>

                      {/* Re-download Action */}
                      <td className="py-3 px-3 text-right">
                        <button
                          type="button"
                          onClick={() => handleReDownload(rep)}
                          className="btn-secondary py-1 px-2.5 text-xs inline-flex items-center gap-1.5"
                          title="Stream and re-download this report"
                        >
                          <Download className="w-3.5 h-3.5 text-accent-cyan" />
                          <span>Re-Download</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
    </CaseWorkspacePage>
  );
};

export default ReportsPage;
