import React, { useState } from 'react';
import { useActiveCase } from '../context/CaseContext';

export default function Section63Page() {
  const { activeCase } = useActiveCase();

  const [certifier, setCertifier] = useState({
    name: 'Abhishek Verma',
    designation: 'Senior Forensic Analyst & Cryptographic Certifier',
    agency: 'Special Cyber Forensics Division, Directorate of Enforcement',
    station: 'New Delhi Forensic Enclave WS-04',
    certificateRef: 'BSA-2023-SEC63-ARX-2026-014',
    date: new Date().toISOString().substring(0, 10),
    attested: true
  });

  const [artifacts] = useState([
    {
      item: '01',
      name: 'msgstore.db.crypt15',
      size: '182.4 MiB',
      algo: 'SHA-256',
      hash: '8a72cf19d45e08b1a32f91bc740192e8fa312904bc78e120aa45192803bba221',
      role: 'Primary Evidence DB (WhatsApp)',
      verifiedUtc: '2026-03-30 08:35:12',
      status: 'Match'
    },
    {
      item: '02',
      name: 'wa_unencrypted_dump.crypt15',
      size: '41.2 MiB',
      algo: 'SHA-256',
      hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      role: 'Plain SQLite Dump',
      verifiedUtc: '2026-03-30 08:35:14',
      status: 'Match'
    },
    {
      item: '03',
      name: 'cache4.db',
      size: '48.2 MiB',
      algo: 'SHA-256',
      hash: '01f5e88d11ac293847291048b291048572910485729104857291048572910485',
      role: 'Primary Evidence DB (Telegram)',
      verifiedUtc: '2026-03-30 08:35:19',
      status: 'Match'
    },
    {
      item: '04',
      name: 'cache4.db-wal',
      size: '12.8 MiB',
      algo: 'SHA-256',
      hash: '4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c',
      role: 'WAL Residual Journal',
      verifiedUtc: '2026-03-30 08:35:21',
      status: 'Match'
    }
  ]);

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden">
      {/* 1. Amber Warning Banner at Top (Strict Stitch Requirement) */}
      <section className="bg-amber-950/30 border-b border-amber-600/40 px-space-lg py-2.5 flex items-start gap-3 shrink-0">
        <span className="material-symbols-outlined text-amber-400 text-lg shrink-0 mt-0.5">warning</span>
        <div className="flex flex-col">
          <p className="text-body-sm font-body-sm text-amber-200">
            <span className="font-semibold uppercase tracking-wider text-amber-400">
              ⚠ DRAFT FOR EXPERT REVIEW — not a certificate.
            </span>{' '}
            This tool prepares technical schedules for verification and signature by an authorized certifier under Section 63 of the Bharatiya Sakshya Adhiniyam, 2023. Do not submit unexamined output to court.
          </p>
          <div className="flex flex-wrap items-center gap-4 mt-1 text-label-mono-sm font-label-mono-sm text-amber-400 text-xs">
            <span>Statutory Reference: BSA 2023 s. 63(4)</span>
            <span>•</span>
            <span>Master Case Hash: <code className="text-on-surface bg-surface-container-lowest px-1 py-0.2 rounded font-mono">8f7e2a9b...7c41d0ea</code></span>
          </div>
        </div>
      </section>

      {/* Main Scrollable Canvas */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-space-lg space-y-5">
        {/* Section 1: Cryptographic Hash Report (Schedule of Artifacts) */}
        <div className="bg-surface-container border border-outline-variant rounded-lg overflow-hidden shadow-xs">
          <div className="flex flex-wrap items-center justify-between p-3 border-b border-outline-variant bg-surface-container-low gap-3">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-base">fingerprint</span>
              <h2 className="text-headline-sm font-headline-sm font-semibold text-on-surface">
                Cryptographic Hash Report (Schedule of Artifacts)
              </h2>
              <span className="text-label-mono-sm text-outline bg-surface-container-lowest border border-outline-variant px-2 py-0.5 rounded text-xs">
                {artifacts.length} Items Identified
              </span>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-label-mono-sm text-xs text-on-surface-variant font-mono">Algorithm: SHA-256 (Statutory Primary)</span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-body-sm font-body-sm">
              <thead>
                <tr className="bg-surface-container-lowest/80 border-b border-outline-variant h-8 text-label-ui font-label-ui text-on-surface-variant uppercase tracking-wider text-[11px]">
                  <th className="py-2.5 px-3 w-12 text-center">Item</th>
                  <th className="py-2.5 px-3">Filename / Container</th>
                  <th className="py-2.5 px-3 w-24">Size</th>
                  <th className="py-2.5 px-3 w-28">Algorithm</th>
                  <th className="py-2.5 px-3 font-mono">Cryptographic Hash Digest</th>
                  <th className="py-2.5 px-3">Evidentiary Role</th>
                  <th className="py-2.5 px-3 text-right">Integrity Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/60 text-xs">
                {artifacts.map((a) => (
                  <tr key={a.item} className="hover:bg-surface-container-high/40 transition-colors">
                    <td className="py-2.5 px-3 text-center font-mono text-outline">{a.item}</td>
                    <td className="py-2.5 px-3 font-medium text-on-surface">
                      <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-sm text-primary">database</span>
                        <span>{a.name}</span>
                      </div>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-on-surface-variant">{a.size}</td>
                    <td className="py-2.5 px-3 font-mono text-primary font-semibold">{a.algo}</td>
                    <td className="py-2.5 px-3">
                      <code className="text-on-surface bg-surface-container-lowest px-2 py-0.5 rounded border border-outline-variant font-mono text-[11px] block truncate max-w-md">
                        {a.hash}
                      </code>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="text-[11px] font-mono text-primary bg-primary/10 px-1.5 py-0.5 rounded border border-primary/20">
                        {a.role}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <span className="inline-flex items-center gap-1 text-[11px] font-label-ui text-tertiary bg-tertiary/10 border border-tertiary/30 px-2 py-0.5 rounded-full">
                        <span className="w-1.5 h-1.5 rounded-full bg-tertiary" />
                        Match
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Section 2: Operating Conditions & System Environment */}
        <div className="bg-surface-container border border-outline-variant rounded-lg p-space-lg space-y-3 shadow-xs">
          <div className="flex items-center justify-between pb-2 border-b border-outline-variant">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-[18px]">terminal</span>
              <h2 className="text-headline-sm font-headline-sm font-semibold text-on-surface">
                Workstation System Environment &amp; Operating Conditions
              </h2>
            </div>
            <span className="text-[11px] font-mono text-outline">BSA 2023 §63(2) Technical Schedule</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            <div className="p-3 rounded bg-surface-container-low border border-outline-variant space-y-1">
              <span className="text-on-surface-variant block font-medium">Workstation Unit:</span>
              <span className="font-mono text-on-surface font-semibold text-sm">F-AIRGAP-09 (Forensic Workstation)</span>
              <span className="text-[10px] text-tertiary block">Hardware Enclave Isolation Verified</span>
            </div>

            <div className="p-3 rounded bg-surface-container-low border border-outline-variant space-y-1">
              <span className="text-on-surface-variant block font-medium">Extraction Software Build:</span>
              <span className="font-mono text-on-surface font-semibold text-sm">ArtifactX DFIR Suite v4.12.0</span>
              <span className="text-[10px] text-outline block">Reproducible Build Signature Ed25519</span>
            </div>

            <div className="p-3 rounded bg-surface-container-low border border-outline-variant space-y-1">
              <span className="text-on-surface-variant block font-medium">Kernel &amp; Cryptographic Library:</span>
              <span className="font-mono text-on-surface font-semibold text-sm">Linux 6.8 / OpenSSL 3.0.13 FIPS</span>
              <span className="text-[10px] text-primary block">Deterministic Stage Transformation</span>
            </div>
          </div>
        </div>

        {/* Section 3: Statutory Declaration Form (Draft Section 63(4) Part B) */}
        <div className="bg-surface-container border border-outline-variant rounded-lg p-space-lg space-y-4 shadow-xs">
          <div className="flex items-center justify-between pb-2 border-b border-outline-variant">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-[18px]">history_edu</span>
              <h2 className="text-headline-sm font-headline-sm font-semibold text-on-surface">
                Statutory Declaration Form (Draft Section 63(4) Part B)
              </h2>
            </div>
            <span className="text-[11px] font-mono text-primary font-semibold">{certifier.certificateRef}</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="space-y-1">
              <label className="text-label-ui uppercase tracking-wider text-on-surface-variant block">
                Authorized Certifier Name
              </label>
              <input
                type="text"
                value={certifier.name}
                onChange={(e) => setCertifier({ ...certifier, name: e.target.value })}
                className="w-full bg-surface-container-lowest border border-outline-variant rounded p-2 text-on-surface text-sm focus:outline-none focus:border-primary"
              />
            </div>

            <div className="space-y-1">
              <label className="text-label-ui uppercase tracking-wider text-on-surface-variant block">
                Designation / Rank / Station
              </label>
              <input
                type="text"
                value={certifier.designation}
                onChange={(e) => setCertifier({ ...certifier, designation: e.target.value })}
                className="w-full bg-surface-container-lowest border border-outline-variant rounded p-2 text-on-surface text-sm focus:outline-none focus:border-primary"
              />
            </div>
          </div>

          <div className="p-3 rounded bg-surface-container-low border border-outline-variant space-y-2">
            <label className="flex items-start gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={certifier.attested}
                onChange={(e) => setCertifier({ ...certifier, attested: e.target.checked })}
                className="mt-0.5 rounded border-outline-variant text-primary focus:ring-0 cursor-pointer"
              />
              <p className="text-body-sm text-on-surface leading-relaxed text-xs">
                I hereby declare that the electronic records detailed in the schedules above were produced by the computer during the period over which the computer was used regularly to store or process information, and that throughout the material part of the said period, the computer was operating properly and the integrity of the data was maintained without alteration.
              </p>
            </label>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <span className="text-xs text-outline font-mono">Date of Statutory Attestation: {certifier.date}</span>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => window.print()}
                className="btn-secondary text-xs"
              >
                <span className="material-symbols-outlined text-sm">print</span>
                <span>Print Section 63 Schedule</span>
              </button>
              <button
                type="button"
                onClick={() => alert('Exporting signed draft PDF...')}
                className="btn-primary text-xs"
              >
                <span className="material-symbols-outlined text-sm">file_download</span>
                <span>Export Official Certificate Draft</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
