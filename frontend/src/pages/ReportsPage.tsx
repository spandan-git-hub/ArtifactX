import React, { useState, useEffect, useCallback } from 'react';
import { useActiveCase } from '../context/CaseContext';
import {
  generateReportStream,
  getReportHistory,
  downloadHistoricalReport,
} from '../services/reportService';

const REPORT_SECTIONS = [
  { id: 'sec-01', title: '1. Official Case Details & Ingestion Manifest', desc: 'Case docket, jurisdiction, scope, target device, root SHA-256 hash, and high-level metrics', checked: true },
  { id: 'sec-02', title: '2. Forensic Analysis Methodology & Proper Process Followed', desc: 'Methods used (Bitstream hashing, In-memory decryption, AST SQLite parsing, Carving) and ISO/IEC 27037 5-stage SOP', checked: true },
  { id: 'sec-03', title: '3. Evidence Schedule & Hash Integrity Verification (with Metrics)', desc: 'Intake SHA-256 vs re-computed SHA-256 comparison table, match status, and 100% preservation verification metrics', checked: true },
  { id: 'sec-04', title: '4. Deleted Data Recovery Findings by Strength (with Metrics)', desc: '4-Tier classification breakdown (Tier 1 Explicit, Tier 2 WAL, Tier 3 Freelist/Slack, Tier 4 Gap indicators) with metrics', checked: true },
  { id: 'sec-05', title: '5. Cross-Platform Evidence Correlations Performed (with Metrics)', desc: 'Resolved person identities, platform handovers, perceptual media hashes, and shared deterministic artifacts', checked: true },
  { id: 'sec-06', title: '6. Reconstructed Chronological Conversation Timeline', desc: 'Natural chronological sequence of conversation dialogue and evidentiary events normalized to UTC', checked: true },
  { id: 'sec-07', title: '7. Technical Limitations of Application & Architectural Set Rules', desc: 'Mandatory rules (R3 Integrity, R4 Zero-Disk, R8 Dual-Score, R10 Idempotency, R12 AI Exclusion) and heuristic caveats', checked: true },
  { id: 'sec-08', title: '8. Examiner Sworn Declaration & Statutory Certification', desc: 'Formal certifier statement, BSA 2023 §63 Form B compliance schedule, and cryptographic verification seal', checked: true },
];

export default function ReportsPage() {
  const { activeCase } = useActiveCase();
  const caseId = activeCase?.id;

  const [reportType, setReportType] = useState('full');
  const [leadAnalyst, setLeadAnalyst] = useState(activeCase?.examiner || 'Forensic Examiner');
  const [agency, setAgency] = useState(activeCase?.agency || 'Digital Forensics Unit');
  const [caseNotes, setCaseNotes] = useState('');
  const [sections, setSections] = useState(REPORT_SECTIONS);
  const [generating, setGenerating] = useState(false);
  const [reportStatus, setReportStatus] = useState(null);
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Sync analyst defaults when activeCase updates
  useEffect(() => {
    if (activeCase?.examiner) setLeadAnalyst(activeCase.examiner);
    if (activeCase?.agency) setAgency(activeCase.agency);
  }, [activeCase]);

  const loadHistory = useCallback(async () => {
    if (!caseId) return;
    setLoadingHistory(true);
    try {
      const data = await getReportHistory(caseId);
      setHistory(data?.reports || []);
    } catch {
      setHistory([]);
    } finally {
      setLoadingHistory(false);
    }
  }, [caseId]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const toggleSection = (id) => {
    setSections(prev => prev.map(s => s.id === id ? { ...s, checked: !s.checked } : s));
  };

  const handleGenerate = async () => {
    if (!caseId) return;
    setGenerating(true);
    setReportStatus(null);
    try {
      const result = await generateReportStream(caseId, {
        reportType,
        includeEvidence: sections.find(s => s.id === 'sec-03')?.checked !== false,
        includeTimeline: sections.find(s => s.id === 'sec-06')?.checked !== false,
        includeDeleted: sections.find(s => s.id === 'sec-04')?.checked !== false,
        includeCorrelations: sections.find(s => s.id === 'sec-05')?.checked !== false,
        includeCustodyLog: true,
        leadAnalyst: leadAnalyst.trim() || 'Forensic Examiner',
        agency: agency.trim() || 'Digital Forensics Unit',
        caseNotes: caseNotes.trim(),
        swornDeclaration: sections.find(s => s.id === 'sec-08')?.checked !== false,
      });

      setReportStatus({
        type: 'success',
        message: `PDF report successfully generated & downloaded (${result.totalPages} pages, SHA-256: ${result.sha256?.substring(0, 16)}...).`,
      });
      await loadHistory();
    } catch (err) {
      console.error('PDF report generation failed:', err);
      setReportStatus({
        type: 'error',
        message: err.response?.data?.detail || err.message || 'Failed to stream forensic PDF report.',
      });
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden">
      {/* Top Banner */}
      <div className="bg-surface-container-low border-b border-outline-variant px-space-lg py-1.5 flex flex-wrap items-center justify-between text-body-sm shrink-0 gap-2">
        <div className="flex items-center space-x-3 text-xs">
          <div className="flex items-center space-x-1.5 text-primary">
            <span className="material-symbols-outlined text-[15px]">verified</span>
            <span className="font-label-ui uppercase tracking-wider font-semibold">Evidentiary Chain Active</span>
          </div>
          <span className="text-outline">|</span>
          <span className="text-on-surface-variant font-mono">
            {activeCase?.sha256Root ? `Root Hash: ${activeCase.sha256Root.substring(0, 20)}...` : `Docket: ${activeCase?.caseNumber || 'N/A'}`}
          </span>
        </div>
        <div className="flex items-center space-x-3 text-label-mono-sm text-on-surface-variant text-xs">
          <span>Case: {activeCase?.caseNumber || activeCase?.name || 'Active'}</span>
          {activeCase?.integrityState && (
            <span className="px-1.5 py-0.5 rounded text-[10px] bg-tertiary/10 text-tertiary border border-tertiary/30">
              {activeCase.integrityState}
            </span>
          )}
        </div>
      </div>

      {reportStatus && (
        <div className={`px-space-lg py-2 border-b text-xs font-mono flex items-center justify-between ${
          reportStatus.type === 'success'
            ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300'
            : 'bg-error/15 border-error/40 text-error'
        }`}>
          <span>{reportStatus.message}</span>
          <button type="button" onClick={() => setReportStatus(null)} className="hover:underline ml-2">✕</button>
        </div>
      )}

      {/* Main Content Scrollable */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-space-lg space-y-4">
        {/* Report Configuration Bar */}
        <section className="bg-surface-container border border-outline-variant rounded-lg p-3.5 shadow-xs">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center space-x-3">
              <label className="text-label-ui uppercase tracking-wider text-outline text-xs">Report Type</label>
              <select
                value={reportType}
                onChange={(e) => setReportType(e.target.value)}
                className="bg-surface-container-lowest border border-outline-variant rounded text-on-surface text-body-sm px-3 py-1.5 focus:outline-none focus:border-primary cursor-pointer"
              >
                <option value="full">Forensic Evidence Report (Complete Technical Manifest — Draft for Expert Review)</option>
                <option value="summary">Forensic Summary Report (Executive Brief with Hash Metrics)</option>
              </select>
            </div>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={handleGenerate}
                disabled={generating || !caseId}
                className="btn-primary text-xs flex items-center gap-1.5 h-8 px-3"
              >
                <span className={`material-symbols-outlined text-[16px] ${generating ? 'animate-spin' : ''}`}>
                  {generating ? 'sync' : 'picture_as_pdf'}
                </span>
                <span>{generating ? 'Compiling In-Memory PDF...' : 'Download PDF Report'}</span>
              </button>
            </div>
          </div>

          {/* Examiner Metadata Inputs */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-3 mt-3 border-t border-outline-variant/60 text-xs font-mono">
            <div>
              <label className="block text-outline uppercase text-[10px] mb-1">Lead Examiner</label>
              <input
                type="text"
                value={leadAnalyst}
                onChange={(e) => setLeadAnalyst(e.target.value)}
                placeholder="Examiner Name"
                className="w-full bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1 text-on-surface focus:outline-none focus:border-primary"
              />
            </div>
            <div>
              <label className="block text-outline uppercase text-[10px] mb-1">Agency / Department</label>
              <input
                type="text"
                value={agency}
                onChange={(e) => setAgency(e.target.value)}
                placeholder="Agency Name"
                className="w-full bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1 text-on-surface focus:outline-none focus:border-primary"
              />
            </div>
            <div>
              <label className="block text-outline uppercase text-[10px] mb-1">Case Notes / Remarks</label>
              <input
                type="text"
                value={caseNotes}
                onChange={(e) => setCaseNotes(e.target.value)}
                placeholder="Optional examiner remarks"
                className="w-full bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1 text-on-surface focus:outline-none focus:border-primary"
              />
            </div>
          </div>
        </section>

        {/* Dual Column Layout: Sections Checklist (5 Cols) + Historical Reports (7 Cols) */}
        <div className="grid grid-cols-12 gap-4 items-start">
          {/* Left Column: Sections Checklist */}
          <div className="col-span-12 lg:col-span-5 bg-surface-container border border-outline-variant rounded-lg p-4 shadow-xs space-y-3">
            <div className="pb-2 border-b border-outline-variant flex items-center justify-between">
              <div>
                <h3 className="font-headline-sm text-sm font-semibold text-on-surface">
                  Report Sections Included ({sections.filter(s => s.checked).length}/{sections.length})
                </h3>
                <span className="text-[11px] text-on-surface-variant">
                  Select sections to include in the generated PDF draft
                </span>
              </div>
              <button
                type="button"
                onClick={() => setSections(prev => prev.map(s => ({ ...s, checked: true })))}
                className="text-primary hover:underline text-xs"
              >
                Select All
              </button>
            </div>

            <div className="space-y-2">
              {sections.map((sec) => (
                <label
                  key={sec.id}
                  className="flex items-start space-x-2.5 p-2 rounded hover:bg-surface-container-high transition-colors cursor-pointer text-xs"
                >
                  <input
                    type="checkbox"
                    checked={sec.checked}
                    onChange={() => toggleSection(sec.id)}
                    className="rounded border-outline-variant text-primary focus:ring-0 mt-0.5"
                  />
                  <div className="flex-1">
                    <div className={`text-on-surface ${sec.checked ? 'font-semibold' : 'text-outline line-through'}`}>
                      {sec.title}
                    </div>
                    <p className="text-[11px] text-on-surface-variant mt-0.5 leading-snug">
                      {sec.desc}
                    </p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Right Column: Historical Generated Reports Table (7 Cols) */}
          <section className="col-span-12 lg:col-span-7 bg-surface-container border border-outline-variant rounded-lg p-4 shadow-xs space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-outline-variant">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-base">history</span>
                <h3 className="font-headline-sm text-sm font-semibold text-on-surface">
                  Generated Report History ({history.length})
                </h3>
              </div>
              <button
                type="button"
                onClick={loadHistory}
                className="text-xs text-primary hover:underline flex items-center gap-1"
              >
                <span className="material-symbols-outlined text-[13px]">refresh</span>
                Refresh History
              </button>
            </div>

            {loadingHistory && (
              <div className="py-4 text-center text-xs font-mono text-outline">Loading report history...</div>
            )}

            {!loadingHistory && history.length === 0 && (
              <div className="py-6 text-center text-xs font-mono text-outline">
                No reports have been generated yet for this case. Click "Download PDF Report" above to generate a draft forensic report.
              </div>
            )}

            {!loadingHistory && history.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="border-b border-outline-variant text-outline uppercase text-[10px]">
                      <th className="pb-2">Generated Timestamp</th>
                      <th className="pb-2">Report Filename</th>
                      <th className="pb-2">Examiner</th>
                      <th className="pb-2">Pages</th>
                      <th className="pb-2">SHA-256 Digest</th>
                      <th className="pb-2 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant/40">
                    {history.map((rep) => (
                      <tr key={rep.report_id} className="hover:bg-surface-container-high transition-colors">
                        <td className="py-2 text-on-surface">
                          {rep.created_at ? rep.created_at.replace('T', ' ').substring(0, 19) : '—'}
                        </td>
                        <td className="py-2 text-on-surface font-semibold max-w-[200px] truncate" title={rep.filename}>
                          {rep.filename}
                        </td>
                        <td className="py-2 text-on-surface-variant">{rep.lead_analyst || 'Examiner'}</td>
                        <td className="py-2 text-on-surface">{rep.total_pages || 1}</td>
                        <td className="py-2 text-primary font-mono text-[11px]" title={rep.sha256}>
                          {rep.sha256 ? `${rep.sha256.substring(0, 16)}...` : '—'}
                        </td>
                        <td className="py-2 text-right">
                          <button
                            type="button"
                            onClick={() => downloadHistoricalReport(caseId, rep.report_id, rep.filename)}
                            className="px-2 py-1 rounded bg-primary/10 hover:bg-primary/20 text-primary border border-primary/30 text-[11px] font-semibold cursor-pointer"
                          >
                            Re-Download
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
