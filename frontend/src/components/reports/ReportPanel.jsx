import { useState } from 'react';
import {
  FileText,
  Loader2,
  CheckCircle,
  AlertCircle,
  Download,
  ShieldCheck,
  Eye,
  EyeOff,
  UserCheck,
  Building,
  FileSignature,
} from 'lucide-react';
import { useReports } from '../../hooks/useReports';

const ReportPanel = ({
  caseId,
  caseData,
  showPreview,
  setShowPreview,
  formState,
  setFormState,
}) => {
  const {
    reportType,
    options,
    leadAnalyst,
    agency,
    caseNotes,
    swornDeclaration,
  } = formState;

  const { loading, error, lastReport, generateReport } = useReports();

  const handleGenerate = async () => {
    try {
      await generateReport(caseId, {
        reportType,
        ...options,
        leadAnalyst,
        agency,
        caseNotes,
        swornDeclaration,
      });
    } catch (err) {
      // Handled in hook
    }
  };

  const toggleOption = (key) => {
    setFormState((prev) => ({
      ...prev,
      options: { ...prev.options, [key]: !prev.options[key] },
    }));
  };

  return (
    <div className="card space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-forensic-800">
        <h2 className="text-base font-semibold text-forensic-100 flex items-center gap-2">
          <FileText className="h-5 w-5 text-accent-cyan" />
          Court Report Configuration
        </h2>
        <button
          type="button"
          onClick={() => setShowPreview(!showPreview)}
          className="text-xs font-mono text-forensic-400 hover:text-accent-cyan flex items-center gap-1.5 transition-colors"
        >
          {showPreview ? (
            <>
              <EyeOff className="w-3.5 h-3.5" /> Hide Preview
            </>
          ) : (
            <>
              <Eye className="w-3.5 h-3.5" /> Show Live Preview
            </>
          )}
        </button>
      </div>

      {/* Report Type Selector */}
      <div>
        <label className="block text-xs font-medium text-forensic-400 mb-1.5 uppercase font-mono">
          Report Category
        </label>
        <select
          value={reportType}
          onChange={(e) => setFormState((prev) => ({ ...prev, reportType: e.target.value }))}
          className="w-full px-3 py-2 rounded-lg bg-forensic-800 border border-forensic-700
                     text-forensic-100 text-sm focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan"
        >
          <option value="full">Full Forensic Examination (Complete Case Report)</option>
          <option value="evidence">Evidence Manifest & Hash Verification Only</option>
          <option value="timeline">Reconstructed Chronological Timeline Only</option>
          <option value="deleted">Anti-Forensics & Deletion Anomaly Report</option>
          <option value="summary">Executive Summary & Entity Correlations</option>
        </select>
      </div>

      {/* Lead Analyst & Agency Inputs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-forensic-400 mb-1.5 flex items-center gap-1">
            <UserCheck className="w-3.5 h-3.5 text-accent-cyan" />
            Lead Forensic Examiner
          </label>
          <input
            type="text"
            value={leadAnalyst}
            onChange={(e) => setFormState((prev) => ({ ...prev, leadAnalyst: e.target.value }))}
            placeholder="e.g. Special Agent J. Miller"
            className="w-full px-3 py-2 rounded-lg bg-forensic-800 border border-forensic-700
                       text-forensic-100 text-sm focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-forensic-400 mb-1.5 flex items-center gap-1">
            <Building className="w-3.5 h-3.5 text-accent-cyan" />
            Law Enforcement Agency / Unit
          </label>
          <input
            type="text"
            value={agency}
            onChange={(e) => setFormState((prev) => ({ ...prev, agency: e.target.value }))}
            placeholder="e.g. State Digital Forensics Lab"
            className="w-full px-3 py-2 rounded-lg bg-forensic-800 border border-forensic-700
                       text-forensic-100 text-sm focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan"
          />
        </div>
      </div>

      {/* Section Toggles */}
      <div className="space-y-2">
        <label className="block text-xs font-medium text-forensic-400 mb-1 font-mono uppercase">
          Evidence Modules to Include
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {[
            { key: 'includeEvidence', label: '1. Evidence Hashes (SHA-256)' },
            { key: 'includeCustodyLog', label: '2. Chain of Custody Audit Log' },
            { key: 'includeTimeline', label: '3. Reconstructed Timeline' },
            { key: 'includeDeleted', label: '4. Anti-Forensic Deletion Gaps' },
            { key: 'includeCorrelations', label: '5. Cross-Platform Correlations' },
          ].map(({ key, label }) => (
            <label
              key={key}
              className="flex items-center gap-2.5 p-2 rounded-lg bg-forensic-800/40 border border-forensic-700/60 cursor-pointer hover:bg-forensic-800 transition-colors"
            >
              <input
                type="checkbox"
                checked={options[key]}
                onChange={() => toggleOption(key)}
                className="w-4 h-4 rounded border-forensic-600 bg-forensic-800 text-accent-cyan
                           focus:ring-accent-cyan focus:ring-offset-0"
              />
              <span className="text-xs text-forensic-200">{label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Case Notes / Remarks */}
      <div>
        <label className="block text-xs font-medium text-forensic-400 mb-1.5 flex items-center gap-1">
          <FileSignature className="w-3.5 h-3.5 text-accent-cyan" />
          Examiner Remarks / Case Notes
        </label>
        <textarea
          rows={2}
          value={caseNotes}
          onChange={(e) => setFormState((prev) => ({ ...prev, caseNotes: e.target.value }))}
          placeholder="Enter formal forensic observations, search warrant references, or scope limitations..."
          className="w-full px-3 py-2 rounded-lg bg-forensic-800 border border-forensic-700
                     text-forensic-100 text-sm focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan resize-none"
        />
      </div>

      {/* Sworn Integrity Declaration Checkbox */}
      <div className="p-3 rounded-lg bg-accent-cyan/5 border border-accent-cyan/20">
        <label className="flex items-start gap-2.5 cursor-pointer">
          <input
            type="checkbox"
            checked={swornDeclaration}
            onChange={(e) => setFormState((prev) => ({ ...prev, swornDeclaration: e.target.checked }))}
            className="w-4 h-4 mt-0.5 rounded border-forensic-600 bg-forensic-800 text-accent-cyan focus:ring-accent-cyan"
          />
          <span className="text-xs text-forensic-300 leading-relaxed">
            <b>Sworn Forensic Declaration:</b> I solemnly attest under penalty of perjury that this report
            compiles deterministic evidence extracted without alteration in accordance with ISO/IEC 27037 standards.
          </span>
        </label>
      </div>

      {/* Primary Generation Action */}
      <button
        onClick={handleGenerate}
        disabled={loading || !swornDeclaration}
        className="btn-primary w-full py-2.5 flex items-center justify-center gap-2 text-sm font-semibold tracking-wide disabled:opacity-50"
      >
        {loading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin text-forensic-950" />
            <span>Compiling In-Memory Court PDF...</span>
          </>
        ) : (
          <>
            <ShieldCheck className="h-4 w-4" />
            <span>Generate & Stream Court PDF</span>
          </>
        )}
      </button>

      {/* Success Notification */}
      {lastReport && lastReport.status === 'completed' && (
        <div className="p-3 bg-accent-emerald/10 border border-accent-emerald/30 rounded-lg space-y-1.5 animate-in">
          <div className="flex items-center gap-2 text-accent-emerald font-semibold text-xs">
            <CheckCircle className="h-4 w-4" />
            <span>Court Report Generated & Streamed!</span>
          </div>
          <p className="text-[11px] text-forensic-300 font-mono break-all">
            SHA-256: <span className="text-accent-cyan">{lastReport.sha256}</span>
          </p>
          <p className="text-[11px] text-forensic-400">
            Downloaded: <span className="text-forensic-200">{lastReport.filename}</span> ({lastReport.totalPages} pages)
          </p>
        </div>
      )}

      {/* Error Notification */}
      {error && (
        <div className="p-3 bg-accent-rose/10 border border-accent-rose/30 rounded-lg flex items-start gap-2">
          <AlertCircle className="h-4 w-4 text-accent-rose shrink-0 mt-0.5" />
          <p className="text-xs text-accent-rose">{error}</p>
        </div>
      )}
    </div>
  );
};

export default ReportPanel;