import React, { useState } from 'react';
import { useActiveCase } from '../context/CaseContext';

const TIMELINE_EVENTS = [
  {
    id: 'tl-01',
    app: 'WhatsApp',
    type: 'Incoming Message',
    timestamp: '2026-03-30 10:14:01.092 UTC',
    actor: '+91 98765 43210 (K. Patel)',
    content: 'Target coordinates confirmed: 28.6139° N, 77.2090° E. Deploying field unit now.',
    strength: 'Deterministic',
    strengthScore: 0.98,
    hash: '8a72cf19d45e08b1a32f91bc740192e8fa312904bc78e120aa45192803bba221',
    rowid: 84922
  },
  {
    id: 'tl-02',
    app: 'WhatsApp',
    type: 'Outgoing Message',
    timestamp: '2026-03-30 10:12:45.412 UTC',
    actor: 'Target Subject (+91 98111 22334)',
    content: 'Decrypt token accepted. Do not commit logs until Section 63 schedule drafted.',
    strength: 'Deterministic',
    strengthScore: 0.96,
    hash: '9b4a11f082e4c9012a8120b33411a7fa0218b9412e84c9012a8120b33411a7fa',
    rowid: 84921
  },
  {
    id: 'tl-03',
    app: 'Telegram',
    type: 'Channel Broadcast',
    timestamp: '2026-03-30 09:42:15.118 UTC',
    actor: '@falcon_lead (Commander)',
    content: 'File crypt15 staged on node 04 for batch recovery.',
    strength: 'Strong',
    strengthScore: 0.88,
    hash: '4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c',
    rowid: 4121
  },
  {
    id: 'tl-04',
    app: 'WhatsApp',
    type: 'Remote Revocation (Deleted)',
    timestamp: '2026-03-30 07:55:10.004 UTC',
    actor: 'Target Subject',
    content: '[CARVED WAL FRAME #189]: Transfer completed to wallet 0x71C...49b2. Wipe all cache.',
    strength: 'Strong',
    strengthScore: 0.94,
    hash: '01f5e88d11ac293847291048b291048572910485729104857291048572910485',
    rowid: 84900,
    isCarved: true
  },
  {
    id: 'tl-gap-01',
    isGap: true,
    duration: '4 hours 15 minutes',
    range: '2026-03-30 03:40:00 — 2026-03-30 07:55:00 UTC',
    note: 'Inactivity interval flagged across all messaging databases. Device potentially in flight or RF-shielded bag.'
  },
  {
    id: 'tl-05',
    app: 'Telegram',
    type: 'Media Attachment',
    timestamp: '2026-03-30 03:39:48.891 UTC',
    actor: '@falcon_lead',
    content: 'Image transmission: key_derivation_chart.png (SHA-256: 7fa0218b...33411a)',
    strength: 'Deterministic',
    strengthScore: 0.95,
    hash: '7fa0218b9412e84c9012a8120b33411ae3b0c44298fc1c149afbf4c8996fb924',
    rowid: 4110
  }
];

export default function TimelinePage() {
  const { activeCase } = useActiveCase();

  const [appFilter, setAppFilter] = useState('All');
  const [strengthFilter, setStrengthFilter] = useState('All');
  const [search, setSearch] = useState('');

  const filteredEvents = TIMELINE_EVENTS.filter((e) => {
    if (e.isGap) return true;
    if (appFilter !== 'All' && e.app !== appFilter) return false;
    if (strengthFilter !== 'All' && e.strength !== strengthFilter) return false;
    if (search && !e.content.toLowerCase().includes(search.toLowerCase()) && !e.actor.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden">
      {/* Top Action Bar */}
      <section className="border-b border-outline-variant bg-surface-container px-space-lg py-2.5 space-y-2.5 shrink-0">
        <div className="flex flex-wrap justify-between items-center gap-3">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-headline-md font-headline-md text-on-surface font-semibold">
                Forensic Chronological Timeline
              </h1>
              <span className="px-2 py-0.5 text-label-ui rounded bg-tertiary/10 border border-tertiary/30 text-tertiary flex items-center gap-1 text-xs">
                <span className="material-symbols-outlined text-[13px]">check_circle</span>
                Rebuilt — identical
              </span>
            </div>
            <p className="text-body-sm text-on-surface-variant mt-0.5">
              Multi-source reconstructed timeline across WhatsApp and Telegram evidentiary databases for case {activeCase?.caseNumber}.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center h-8 px-2 rounded bg-surface-container-lowest border border-outline-variant font-mono text-xs text-on-surface-variant">
              <span className="text-outline mr-1">SHA-256:</span>
              <span className="text-on-surface mr-1.5 font-medium">9b4a11f082e4...</span>
              <button
                type="button"
                onClick={() => navigator.clipboard?.writeText('9b4a11f082e4c9012a8120b33411a7fa0218b9412e84c9012a8120b33411a7fa')}
                className="hover:text-primary transition-colors cursor-pointer"
                title="Copy Hash"
              >
                <span className="material-symbols-outlined text-[13px]">content_copy</span>
              </button>
            </div>

            <button
              type="button"
              onClick={() => alert('Exporting Timeline CSV...')}
              className="btn-secondary text-xs h-8"
            >
              <span className="material-symbols-outlined text-[14px]">file_download</span>
              <span>Export Timeline CSV</span>
            </button>

            <button
              type="button"
              onClick={() => alert('Opening Section 63 Chronology Slip...')}
              className="btn-primary text-xs h-8"
            >
              <span className="material-symbols-outlined text-[14px]">gavel</span>
              <span>Section 63 Chronology Slip</span>
            </button>
          </div>
        </div>

        {/* Filter Controls Row */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-outline-variant/60">
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={appFilter}
              onChange={(e) => setAppFilter(e.target.value)}
              className="h-7 px-2.5 rounded bg-surface-container-lowest border border-outline-variant text-[11px] text-on-surface focus:outline-none focus:border-primary cursor-pointer"
            >
              <option value="All">App: All (WhatsApp, Telegram)</option>
              <option value="WhatsApp">WhatsApp Only</option>
              <option value="Telegram">Telegram Only</option>
            </select>

            <select
              value={strengthFilter}
              onChange={(e) => setStrengthFilter(e.target.value)}
              className="h-7 px-2.5 rounded bg-surface-container-lowest border border-outline-variant text-[11px] text-on-surface focus:outline-none focus:border-primary cursor-pointer"
            >
              <option value="All">Strength: All Heuristics</option>
              <option value="Deterministic">Deterministic (&gt;= 0.95)</option>
              <option value="Strong">Strong (&gt;= 0.80)</option>
            </select>

            <div className="relative flex items-center">
              <span className="material-symbols-outlined absolute left-2 text-[14px] text-outline">search</span>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search timeline text, participant..."
                className="h-7 pl-7 pr-3 rounded bg-surface-container-lowest border border-outline-variant text-on-surface placeholder:text-outline text-[11px] focus:outline-none focus:border-primary w-64"
              />
            </div>
          </div>

          <div className="flex items-center gap-1.5 text-label-ui text-outline text-xs">
            <span>Indexed Chrono Events:</span>
            <span className="text-primary font-mono font-semibold">12,842</span>
          </div>
        </div>
      </section>

      {/* Visual Chronological Timeline Feed */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
        <div className="max-w-4xl mx-auto space-y-4">
          {filteredEvents.map((item) => {
            if (item.isGap) {
              return (
                <div
                  key={item.id}
                  className="p-3 rounded-lg border border-dashed border-amber-600/50 bg-amber-950/15 flex items-center gap-3 text-amber-200 text-xs my-3"
                >
                  <span className="material-symbols-outlined text-amber-400 text-lg">timelapse</span>
                  <div className="flex-1">
                    <div className="font-semibold text-amber-300">
                      Forensic Inactivity Gap Detected: {item.duration}
                    </div>
                    <p className="text-on-surface-variant text-[11px] mt-0.5">{item.note}</p>
                  </div>
                  <span className="font-mono text-[10px] text-amber-400/80">{item.range}</span>
                </div>
              );
            }

            return (
              <div
                key={item.id}
                className={`p-4 rounded-lg border bg-surface-container transition-all hover:border-primary/50 space-y-2 ${
                  item.isCarved ? 'border-amber-600/40 bg-amber-950/10' : 'border-outline-variant'
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-outline-variant/60 pb-2">
                  <div className="flex items-center gap-2">
                    <span className={`material-symbols-outlined text-sm ${
                      item.app === 'WhatsApp' ? 'text-emerald-400' : 'text-blue-400'
                    }`}>
                      {item.app === 'WhatsApp' ? 'chat' : 'send'}
                    </span>
                    <span className="font-semibold text-on-surface text-sm">{item.actor}</span>
                    <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-surface-container-high border border-outline-variant text-on-surface-variant">
                      {item.type}
                    </span>
                    {item.isCarved && (
                      <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-amber-500/20 text-amber-400 border border-amber-500/40 font-semibold">
                        CARVED RESIDUAL
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-3 font-mono text-xs text-on-surface-variant">
                    <span className="text-on-surface">{item.timestamp}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                      item.strength === 'Deterministic'
                        ? 'bg-tertiary/10 text-tertiary border border-tertiary/30'
                        : 'bg-primary/10 text-primary border border-primary/30'
                    }`}>
                      {item.strength} ({(item.strengthScore * 100).toFixed(0)}%)
                    </span>
                  </div>
                </div>

                <p className="text-body-md text-on-surface leading-relaxed text-sm select-text">
                  {item.content}
                </p>

                <div className="pt-1 flex items-center justify-between font-mono text-[10px] text-outline">
                  <span>RowID: {item.rowid}</span>
                  <div className="flex items-center gap-1">
                    <span>SHA-256:</span>
                    <span className="text-on-surface-variant">{item.hash.substring(0, 24)}...</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
