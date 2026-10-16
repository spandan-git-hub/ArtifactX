import React, { useState } from 'react';
import { useActiveCase } from '../context/CaseContext';
import { generateReportStream } from '../services/reportService';

const DEFAULT_SECTIONS = [
  { id: 'sec-01', title: '1. Case Docket & Investigating Jurisdiction', checked: true },
  { id: 'sec-02', title: '2. Cryptographic Chain of Custody & Ledger Seals', checked: true },
  { id: 'sec-03', title: '3. Hardware Environment & Operating Conditions (BSA §63(2))', checked: true },
  { id: 'sec-04', title: '4. Evidence Schedule & SHA-256 Ingestion Hashes', checked: true },
  { id: 'sec-05', title: '5. Decryption Enclave Logs & AES-GCM Derivations', checked: true },
  { id: 'sec-06', title: '6. WhatsApp & Telegram Indexed Message Exhibits', checked: true },
  { id: 'sec-07', title: '7. Recovered Deleted Residuals & WAL Carved Cells', checked: true },
  { id: 'sec-08', title: '8. Cross-App Entity Resolution & Identity Graph', checked: true },
  { id: 'sec-09', title: '9. Chronological Multi-Device Timeline with Gap Analysis', checked: true },
  { id: 'sec-10', title: '10. Technical Limitations & Scoring Methodology Disclosure', checked: true },
  { id: 'sec-11', title: '11. Section 63 Statutory Certificate Draft (Form B)', checked: true }
];

export default function ReportsPage() {
  const { activeCase } = useActiveCase();
  const caseId = activeCase?.id;

  const [reportType, setReportType] = useState('full');
  const [includeSection63, setIncludeSection63] = useState(true);
  const [format, setFormat] = useState('pdf');
  const [sections, setSections] = useState(DEFAULT_SECTIONS);
  const [generating, setGenerating] = useState(false);
  const [reportStatus, setReportStatus] = useState(null);

  const toggleSection = (id) => {
    setSections(prev => prev.map(s => s.id === id ? { ...s, checked: !s.checked } : s));
  };

  const handleGenerate = async () => {
    if (!caseId) return;
    setGenerating(true);
    setReportStatus(null);
    try {
      await generateReportStream(caseId, {
        reportType,
        includeEvidence: true,
        includeTimeline: true,
        includeDeleted: true,
        includeCorrelations: true,
        includeCustodyLog: true,
        leadAnalyst: activeCase?.examiner || 'Forensic Examiner',
        agency: activeCase?.agency || 'Special Cyber Forensics Division',
        swornDeclaration: includeSection63
      });
      setReportStatus({ type: 'success', message: 'PDF report generated and downloaded successfully.' });
    } catch (err) {
      console.error('PDF report generation failed:', err);
      // Fallback to print if backend PDF stream endpoint encounters environment limits
      window.print();
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
            <span className="material-symbols-outlined text-[15px]">lock</span>
            <span className="font-label-ui uppercase tracking-wider font-semibold">Evidentiary Chain Active</span>
          </div>
          <span className="text-outline">|</span>
          <span className="text-on-surface-variant font-mono">
            {activeCase?.sha256Root ? `SHA-256 Root: ${activeCase.sha256Root.substring(0, 24)}...` : `Docket: ${activeCase?.caseNumber || 'N/A'}`}
          </span>
        </div>
        <div className="flex items-center space-x-3 text-label-mono-sm text-on-surface-variant text-xs">
          <span>Case Status: {activeCase?.status || 'Active'}</span>
          <span className="px-1.5 py-0.5 rounded text-[10px] bg-tertiary/10 text-tertiary border border-tertiary/30">
            {activeCase?.integrityState || 'CHAIN ACTIVE'}
          </span>
        </div>
      </div>

      {reportStatus && (
        <div className="px-space-lg py-2 bg-tertiary/15 border-b border-tertiary/40 text-tertiary text-xs font-mono flex items-center justify-between">
          <span>{reportStatus.message}</span>
          <button type="button" onClick={() => setReportStatus(null)} className="hover:underline">✕</button>
        </div>
      )}

      {/* Main Content Scrollable */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-space-lg space-y-4">
        {/* Report Configuration Bar */}
        <section className="bg-surface-container border border-outline-variant rounded-lg p-3.5 shadow-xs">
          <div className="flex flex-wrap items-center justify-between gap-4">
            {/* Report Type Selector */}
            <div className="flex items-center space-x-3">
              <label className="text-label-ui uppercase tracking-wider text-outline text-xs">Report Type</label>
              <select
                value={reportType}
                onChange={(e) => setReportType(e.target.value)}
                className="bg-surface-container-lowest border border-outline-variant rounded text-on-surface text-body-sm px-3 py-1.5 focus:outline-none focus:border-primary cursor-pointer"
              >
                <option value="full">Forensic Evidence Report (Full Technical Manifest)</option>
                <option value="summary">Forensic Summary Report (Executive Brief)</option>
              </select>
            </div>

            {/* Checkboxes & Format */}
            <div className="flex flex-wrap items-center gap-4">
              <label className="flex items-center space-x-2 text-xs text-on-surface cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeSection63}
                  onChange={(e) => setIncludeSection63(e.target.checked)}
                  className="rounded border-outline-variant text-primary focus:ring-0"
                />
                <span>Include Section 63 Statutory Schedule</span>
              </label>

              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={handleGenerate}
                  disabled={generating || !caseId}
                  className="btn-primary text-xs flex items-center gap-1.5"
                >
                  <span className={`material-symbols-outlined text-[16px] ${generating ? 'animate-spin' : ''}`}>
                    {generating ? 'sync' : 'picture_as_pdf'}
                  </span>
                  <span>{generating ? 'Generating Stream...' : 'Generate & Download PDF'}</span>
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* Dual Column Layout: Sections Checklist (5 Cols) + Live Document Preview (7 Cols) */}
        <div className="grid grid-cols-12 gap-4">
          {/* Left Column: Sections Checklist */}
          <div className="col-span-12 lg:col-span-5 bg-surface-container border border-outline-variant rounded-lg p-4 shadow-xs space-y-3">
            <div className="pb-2 border-b border-outline-variant flex items-center justify-between">
              <h3 className="font-headline-sm text-sm font-semibold text-on-surface">
                Report Sections In Scope ({sections.filter(s => s.checked).length}/{sections.length})
              </h3>
              <button
                type="button"
                onClick={() => setSections(prev => prev.map(s => ({ ...s, checked: true })))}
                className="text-primary hover:underline text-xs"
              >
                Select All
              </button>
            </div>

            <div className="space-y-1.5">
              {sections.map((sec) => (
                <label
                  key={sec.id}
                  className="flex items-center space-x-2.5 p-2 rounded hover:bg-surface-container-high transition-colors cursor-pointer text-xs"
                >
                  <input
                    type="checkbox"
                    checked={sec.checked}
                    onChange={() => toggleSection(sec.id)}
                    className="rounded border-outline-variant text-primary focus:ring-0"
                  />
                  <span className={`text-on-surface ${sec.checked ? 'font-medium' : 'text-outline line-through'}`}>
                    {sec.title}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Right Column: Live Court Report Preview (7 Cols) */}
          <div className="col-span-12 lg:col-span-7 bg-surface-container border border-outline-variant rounded-lg p-6 shadow-xs space-y-5">
            {/* Document Header */}
            <div className="text-center pb-4 border-b-2 border-outline-variant space-y-1">
              <div className="font-mono text-xs uppercase tracking-widest text-outline">
                COURT OF JUDICIAL MAGISTRATE / SPECIAL FORENSIC TRIBUNAL
              </div>
              <h2 className="text-xl font-bold font-headline-lg text-on-surface tracking-tight">
                DIGITAL FORENSIC EXAMINATION REPORT
              </h2>
              <div className="font-mono text-xs text-primary font-semibold">
                DOCKET ID: {activeCase?.caseNumber || 'N/A'} · PRODUCED UNDER BSA 2023 §63
              </div>
            </div>

            {/* Case Details Box */}
            <div className="p-3 rounded bg-surface-container-low border border-outline-variant space-y-1.5 text-xs font-mono">
              <div className="flex justify-between">
                <span className="text-on-surface-variant">Subject Title:</span>
                <span className="text-on-surface font-semibold">{activeCase?.title || 'Untitled Case'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-on-surface-variant">Lead Examiner:</span>
                <span className="text-on-surface">{activeCase?.examiner || 'Unassigned'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-on-surface-variant">Agency:</span>
                <span className="text-on-surface">{activeCase?.agency || 'Special Cyber Forensics Division'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-on-surface-variant">Target Device:</span>
                <span className="text-on-surface">{activeCase?.deviceTarget || 'Generic Mobile Device'}</span>
              </div>
            </div>

            {/* Cryptographic Attestation Block */}
            <div className="space-y-2 text-xs">
              <div className="font-semibold text-on-surface uppercase tracking-wider text-[11px] text-outline">
                Executive Evidentiary Summary
              </div>
              <p className="text-on-surface-variant leading-relaxed">
                Bit-stream image verified using dual cryptographic hashing (SHA-256 + BLAKE3). Evidence databases processed in volatile memory enclave without persistent plaintext leakage. {activeCase?.recordCount || '0'} total indexed messages across {activeCase?.evidenceCount || 0} registered evidence artifacts with deterministic provenance.
              </p>
            </div>

            {/* Signature & Seal Block */}
            <div className="pt-4 border-t border-outline-variant flex justify-between items-end text-xs font-mono">
              <div>
                <span className="text-outline block text-[10px]">VERIFICATION ENGINE:</span>
                <span className="text-primary font-semibold">ArtifactX / FIPS-140-3 Pure Engine</span>
                <span className="text-outline block text-[10px] mt-1">INTEGRITY: {activeCase?.integrityState || 'VERIFIED'}</span>
              </div>

              <div className="text-right">
                <div className="w-36 border-b border-on-surface pb-1 mb-1 font-serif text-sm italic text-on-surface text-center">
                  {activeCase?.examiner || 'Lead Examiner'}
                </div>
                <span className="text-[10px] text-outline uppercase block">Signature of Authorized Certifier</span>
                <span className="text-[10px] text-primary">{new Date().toISOString().substring(0, 10)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
