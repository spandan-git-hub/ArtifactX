import React from 'react';
import { Shield, FileCheck, CheckCircle2, AlertTriangle, Scale, Lock } from 'lucide-react';

const ReportPdfPreview = ({
  caseData,
  reportType,
  options,
  leadAnalyst,
  agency,
  caseNotes,
  swornDeclaration,
  evidenceSummary,
  timelineSummary,
  deletedSummary,
}) => {
  const currentDate = new Date().toISOString().slice(0, 10);

  return (
    <div className="bg-forensic-900 border border-forensic-700 rounded-xl overflow-hidden shadow-2xl flex flex-col">
      {/* Top Preview Bar */}
      <div className="bg-forensic-950 px-4 py-3 border-b border-forensic-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded-full bg-accent-rose/80" />
          <div className="h-3 w-3 rounded-full bg-accent-amber/80" />
          <div className="h-3 w-3 rounded-full bg-accent-emerald/80" />
          <span className="text-xs font-mono text-forensic-400 ml-2">Live Court PDF Layout Preview</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono text-accent-cyan bg-accent-cyan/10 px-2 py-0.5 rounded border border-accent-cyan/20">
            ISO/IEC 27037 Compliant
          </span>
          <span className="text-[11px] font-mono text-accent-rose bg-accent-rose/10 px-2 py-0.5 rounded border border-accent-rose/20 flex items-center gap-1">
            <Lock className="w-3 h-3" />
            AI Content Excluded
          </span>
        </div>
      </div>

      {/* Simulated Document Body (Letter Aspect Ratio / White Paper Feel with Forensic Styling) */}
      <div className="p-6 overflow-y-auto max-h-[640px] space-y-6 text-forensic-200 font-sans">
        {/* Document Header Banner */}
        <div className="text-center pb-4 border-b-2 border-forensic-700 space-y-1">
          <div className="inline-flex items-center gap-2 text-accent-rose text-xs font-mono font-bold tracking-widest uppercase">
            <Shield className="w-3.5 h-3.5" />
            Law Enforcement & Judicial Evidence Document // Restricted
          </div>
          <h1 className="text-xl font-bold font-mono text-forensic-50 tracking-tight">
            DIGITAL EVIDENCE EXAMINATION REPORT
          </h1>
          <p className="text-xs text-accent-cyan font-mono tracking-wider uppercase">
            Official Forensic Artifact Extraction & Reconstruction Manifest
          </p>
        </div>

        {/* Case & Examiner Metadata Box */}
        <div className="bg-forensic-950/70 border border-forensic-800 rounded-lg p-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
          <div>
            <span className="text-forensic-500 block uppercase text-[10px] font-mono">Case Identifier</span>
            <span className="font-semibold text-forensic-100 font-mono">
              #{caseData?.id || '—'} {caseData?.name || 'Evidence Case'}
            </span>
          </div>
          <div>
            <span className="text-forensic-500 block uppercase text-[10px] font-mono">Lead Examiner</span>
            <span className="font-semibold text-forensic-100">{leadAnalyst || 'Forensic Examiner'}</span>
          </div>
          <div>
            <span className="text-forensic-500 block uppercase text-[10px] font-mono">Agency / Department</span>
            <span className="font-semibold text-forensic-100">{agency || 'Digital Forensics Unit'}</span>
          </div>
          <div>
            <span className="text-forensic-500 block uppercase text-[10px] font-mono">Report Classification</span>
            <span className="font-semibold text-accent-emerald font-mono uppercase">{reportType} Examination</span>
          </div>
        </div>

        {/* Legal Admissibility Alert Callout */}
        <div className="bg-blue-950/20 border border-blue-800/40 rounded-lg p-3 text-xs flex items-start gap-2.5">
          <Scale className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
          <div className="text-blue-200/90 leading-relaxed text-[11px]">
            <b>Judicial Admissibility Guarantee:</b> This court document compiles bit-level hashes, chronological timeline
            reconstructions, and unallocated sequence gap anomalies. In accordance with evidentiary standards,
            all subjective AI copilot analyses and conversational sentiment scores are strictly excluded.
          </div>
        </div>

        {/* Section Checklist & Content Previews */}
        <div className="space-y-3">
          <h3 className="text-xs font-mono font-bold uppercase text-forensic-400 tracking-wider">
            Included Document Sections ({reportType.toUpperCase()})
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
            {/* Section 1 */}
            <div className={`p-2.5 rounded-lg border flex items-center justify-between ${
              options.includeEvidence ? 'bg-forensic-800/60 border-forensic-700 text-forensic-200' : 'bg-forensic-950/30 border-forensic-800/50 text-forensic-600 line-through'
            }`}>
              <div className="flex items-center gap-2">
                <FileCheck className="w-4 h-4 text-accent-cyan shrink-0" />
                <span>1. Evidence Manifest & SHA-256 Hashes</span>
              </div>
              <span className="font-mono text-[10px] text-forensic-400">
                {evidenceSummary ? `${evidenceSummary.total_extracted_files} files` : 'Active'}
              </span>
            </div>

            {/* Section 2 */}
            <div className={`p-2.5 rounded-lg border flex items-center justify-between ${
              options.includeCustodyLog ? 'bg-forensic-800/60 border-forensic-700 text-forensic-200' : 'bg-forensic-950/30 border-forensic-800/50 text-forensic-600 line-through'
            }`}>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-accent-emerald shrink-0" />
                <span>2. Chain of Custody & Audit Trail</span>
              </div>
              <span className="font-mono text-[10px] text-forensic-400">ISO/IEC 27037</span>
            </div>

            {/* Section 3 */}
            <div className="p-2.5 rounded-lg border bg-forensic-800/60 border-forensic-700 text-forensic-200 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-accent-violet shrink-0" />
                <span>3. Communications & Media Breakdown</span>
              </div>
              <span className="font-mono text-[10px] text-forensic-400">WhatsApp & Telegram</span>
            </div>

            {/* Section 4 */}
            <div className={`p-2.5 rounded-lg border flex items-center justify-between ${
              options.includeTimeline ? 'bg-forensic-800/60 border-forensic-700 text-forensic-200' : 'bg-forensic-950/30 border-forensic-800/50 text-forensic-600 line-through'
            }`}>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-accent-cyan shrink-0" />
                <span>4. Reconstructed Chronological Timeline</span>
              </div>
              <span className="font-mono text-[10px] text-forensic-400">
                {timelineSummary ? `${timelineSummary.total_events} events` : 'Active'}
              </span>
            </div>

            {/* Section 5 */}
            <div className={`p-2.5 rounded-lg border flex items-center justify-between ${
              options.includeDeleted ? 'bg-forensic-800/60 border-accent-rose/30 text-forensic-200' : 'bg-forensic-950/30 border-forensic-800/50 text-forensic-600 line-through'
            }`}>
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-accent-rose shrink-0" />
                <span>5. Anti-Forensics & Deletion Anomalies</span>
              </div>
              <span className="font-mono text-[10px] text-accent-rose">
                {deletedSummary ? `${deletedSummary.total_deletions} gaps` : 'Active'}
              </span>
            </div>

            {/* Section 6 */}
            <div className={`p-2.5 rounded-lg border flex items-center justify-between ${
              options.includeCorrelations ? 'bg-forensic-800/60 border-forensic-700 text-forensic-200' : 'bg-forensic-950/30 border-forensic-800/50 text-forensic-600 line-through'
            }`}>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-accent-cyan shrink-0" />
                <span>6. Cross-Platform Correlated Entities</span>
              </div>
              <span className="font-mono text-[10px] text-forensic-400">Entity Links</span>
            </div>
          </div>
        </div>

        {/* Analyst Remarks Preview */}
        {caseNotes && (
          <div className="bg-forensic-950/50 border border-forensic-800 rounded-lg p-3 text-xs">
            <span className="text-forensic-400 font-mono uppercase text-[10px] block mb-1">
              Examiner Remarks & Notes
            </span>
            <p className="text-forensic-300 italic">{caseNotes}</p>
          </div>
        )}

        {/* Sworn Attestation Block Preview */}
        <div className="border border-forensic-700 bg-forensic-950/80 rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold uppercase text-accent-emerald flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5" />
              Sworn Forensic Attestation & Sign-off
            </span>
            <span className="text-[10px] font-mono text-forensic-500">Date: {currentDate}</span>
          </div>

          <p className="text-[11px] text-forensic-300 leading-relaxed">
            "I, <b>{leadAnalyst || 'Forensic Examiner'}</b>, representing <b>{agency || 'Digital Forensics Unit'}</b>,
            solemnly attest under penalty of perjury that the digital forensic findings compiled herein were
            extracted from original seized evidence without alteration, maintaining complete cryptographic chain of custody."
          </p>

          <div className="pt-3 border-t border-forensic-800 flex items-center justify-between text-xs font-mono">
            <div>
              <div className="h-0.5 w-48 bg-forensic-600 mb-1" />
              <span className="text-forensic-400 block text-[10px]">{leadAnalyst || 'Forensic Examiner'} (Signature)</span>
            </div>
            <div className="text-right">
              <span className="text-accent-cyan text-[10px] font-mono">[ SEAL: ARTIFACTX FORENSIC ENGINE ]</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportPdfPreview;
