import React, { useState } from 'react';
import { useActiveCase } from '../context/CaseContext';

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

  const [reportType, setReportType] = useState('full');
  const [includeSection63, setIncludeSection63] = useState(true);
  const [format, setFormat] = useState('pdf');
  const [sections, setSections] = useState(DEFAULT_SECTIONS);
  const [generating, setGenerating] = useState(false);

  const toggleSection = (id) => {
    setSections(prev => prev.map(s => s.id === id ? { ...s, checked: !s.checked } : s));
  };

  const handleGenerate = () => {
    setGenerating(true);
    setTimeout(() => {
      setGenerating(false);
      window.print();
    }, 600);
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
          <span className="text-on-surface-variant font-mono">SHA-256 Root: 9f83a8b41bc8e9102cba3ef8109d...e54a</span>
        </div>
        <div className="flex items-center space-x-3 text-label-mono-sm text-on-surface-variant text-xs">
          <span>Source: msgstore.decrypted.db</span>
          <span className="px-1.5 py-0.5 rounded text-[10px] bg-tertiary/10 text-tertiary border border-tertiary/30">
            TAMPER SEAL VALID
          </span>
        </div>
      </div>

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

            {/* Toggle Switch for Section 63 Appendix */}
            <label className="flex items-center space-x-2.5 px-3 py-1 bg-surface-container-lowest border border-outline-variant rounded cursor-pointer">
              <input
                type="checkbox"
                checked={includeSection63}
                onChange={(e) => setIncludeSection63(e.target.checked)}
                className="rounded border-outline-variant text-primary focus:ring-0 cursor-pointer"
              />
              <span className="text-body-sm text-on-surface text-xs">
                Include Section 63 appendix <span className="text-outline font-mono">(draft for review)</span>
              </span>
            </label>

            {/* Format Selector + Primary Action Button */}
            <div className="flex items-center space-x-3">
              <div className="flex bg-surface-container-lowest border border-outline-variant rounded p-0.5 text-xs">
                <button
                  type="button"
                  onClick={() => setFormat('pdf')}
                  className={`px-3 py-1 rounded font-semibold transition-colors ${
                    format === 'pdf' ? 'bg-primary text-on-primary shadow-xs' : 'text-on-surface-variant hover:text-on-surface'
                  }`}
                >
                  PDF
                </button>
                <button
                  type="button"
                  onClick={() => setFormat('json')}
                  className={`px-3 py-1 rounded font-semibold transition-colors ${
                    format === 'json' ? 'bg-primary text-on-primary shadow-xs' : 'text-on-surface-variant hover:text-on-surface'
                  }`}
                >
                  JSON Manifest
                </button>
              </div>

              <button
                type="button"
                onClick={handleGenerate}
                disabled={generating}
                className="btn-primary"
              >
                <span className="material-symbols-outlined text-[16px]">
                  {generating ? 'sync' : 'article'}
                </span>
                <span>{generating ? 'Compiling Report...' : 'Generate Report'}</span>
              </button>
            </div>
          </div>
        </section>

        {/* Two-Column Workspace */}
        <div className="grid grid-cols-12 gap-4 items-start">
          {/* Left Column: Manifest Composition (5 Cols) */}
          <div className="col-span-12 lg:col-span-5 bg-surface-container border border-outline-variant rounded-lg p-4 flex flex-col space-y-3 shadow-xs">
            <div className="flex items-center justify-between pb-2 border-b border-outline-variant">
              <div>
                <h2 className="text-headline-sm font-headline-sm text-on-surface font-semibold flex items-center space-x-2">
                  <span className="material-symbols-outlined text-primary">checklist</span>
                  <span>Manifest Composition</span>
                </h2>
                <p className="text-body-sm text-on-surface-variant mt-0.5 text-xs">
                  {sections.filter(s => s.checked).length} of {sections.length} sections selected
                </p>
              </div>

              <div className="flex space-x-1 font-mono text-[10px]">
                <button
                  type="button"
                  onClick={() => setSections(sections.map(s => ({ ...s, checked: true })))}
                  className="px-2 py-0.5 bg-surface-container-low border border-outline-variant text-on-surface-variant hover:text-on-surface rounded"
                >
                  Select All
                </button>
                <button
                  type="button"
                  onClick={() => setSections(sections.map(s => ({ ...s, checked: false })))}
                  className="px-2 py-0.5 bg-surface-container-low border border-outline-variant text-on-surface-variant hover:text-on-surface rounded"
                >
                  Clear
                </button>
              </div>
            </div>

            <div className="space-y-1.5 max-h-[520px] overflow-y-auto custom-scrollbar pr-1">
              {sections.map((s) => (
                <label
                  key={s.id}
                  className={`flex items-center justify-between p-2 rounded border cursor-pointer transition-colors text-xs ${
                    s.checked ? 'bg-surface-container-low border-primary/40 text-on-surface' : 'bg-surface-container-lowest border-outline-variant text-outline'
                  }`}
                >
                  <span className="truncate pr-2">{s.title}</span>
                  <input
                    type="checkbox"
                    checked={s.checked}
                    onChange={() => toggleSection(s.id)}
                    className="rounded border-outline-variant text-primary focus:ring-0"
                  />
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
                DOCKET ID: {activeCase?.caseNumber} · PRODUCED UNDER BSA 2023 §63
              </div>
            </div>

            {/* Case Details Box */}
            <div className="p-3 rounded bg-surface-container-low border border-outline-variant space-y-1.5 text-xs font-mono">
              <div className="flex justify-between">
                <span className="text-on-surface-variant">Subject Title:</span>
                <span className="text-on-surface font-semibold">{activeCase?.title}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-on-surface-variant">Lead Examiner:</span>
                <span className="text-on-surface">{activeCase?.examiner}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-on-surface-variant">Agency:</span>
                <span className="text-on-surface">{activeCase?.agency}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-on-surface-variant">Target Device:</span>
                <span className="text-on-surface">{activeCase?.deviceTarget}</span>
              </div>
            </div>

            {/* Cryptographic Attestation Block */}
            <div className="space-y-2 text-xs">
              <div className="font-semibold text-on-surface uppercase tracking-wider text-[11px] text-outline">
                Executive Evidentiary Summary
              </div>
              <p className="text-on-surface-variant leading-relaxed">
                Bit-stream image verified using dual cryptographic hashing (SHA-256 + BLAKE3). WhatsApp msgstore.db.crypt15 and Telegram cache4.db successfully decrypted in volatile RAM enclave without persistent plaintext leakage. 12,842 total messages, 218 carved residuals, and 7 cross-platform identity linkages established with deterministic provenance.
              </p>
            </div>

            {/* Signature & Seal Block */}
            <div className="pt-4 border-t border-outline-variant flex justify-between items-end text-xs font-mono">
              <div>
                <span className="text-outline block text-[10px]">VERIFICATION ENGINE:</span>
                <span className="text-primary font-semibold">ArtifactX v4.12.0 / FIPS-140-3</span>
                <span className="text-outline block text-[10px] mt-1">LEDGER COMMIT: Block #40921-X9</span>
              </div>

              <div className="text-right">
                <div className="w-36 border-b border-on-surface pb-1 mb-1 font-serif text-sm italic text-on-surface text-center">
                  A. Verma
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
