import React, { useState } from 'react';
import { useActiveCase } from '../context/CaseContext';

const CORRELATIONS = [
  {
    id: 'cor-01',
    type: 'Phone',
    icon: 'phone',
    identifier: '+91 98765 43210',
    waEntity: '919876543210@s.whatsapp.net (K. Patel)',
    tgEntity: 'Telegram User ID #481920 (@k_patel_ops)',
    heuristicScore: 0.98,
    rating: 'Deterministic (Primary Fact)',
    rule: 'Exact E.164 MSISDN String Match & Profile Card Sync',
    citations: 'WhatsApp rowid 84920 ↔ Telegram cache4.db rowid 4120'
  },
  {
    id: 'cor-02',
    type: 'Wallet',
    icon: 'account_balance_wallet',
    identifier: '0x71C2a849b2910485729104857291048572910485',
    waEntity: 'Mentioned in Chat: Nexus Core Operational (Row 84900)',
    tgEntity: 'Staged in Falcon Channel Broadcast (Row 4121)',
    heuristicScore: 0.96,
    rating: 'Deterministic (Primary Fact)',
    rule: 'EIP-55 Validated Ethereum Hex Address Match',
    citations: 'WAL Carved Frame #189 ↔ Telegram Cache Frame #410'
  },
  {
    id: 'cor-03',
    type: 'IBAN',
    icon: 'credit_card',
    identifier: 'IN49HDFC00018920194821',
    waEntity: 'Beneficiary wire details text payload (Row 83100)',
    tgEntity: 'Exported transaction statement PDF exhibit (Row 3890)',
    heuristicScore: 0.94,
    rating: 'Deterministic',
    rule: 'MOD-97 Validated Bank Account String Identity',
    citations: 'WhatsApp rowid 83100 ↔ Telegram doc_hash_8921'
  },
  {
    id: 'cor-04',
    type: 'URL',
    icon: 'link',
    identifier: 'https://nexus-vault-alpha.io/auth/enclave',
    waEntity: 'Shared in Direct Message (Target Subject)',
    tgEntity: 'Pinned channel announcement URL link',
    heuristicScore: 0.88,
    rating: 'Strong',
    rule: 'Canonical FQDN & Subdirectory Token Match',
    citations: 'WhatsApp rowid 84102 ↔ Telegram rowid 4099'
  },
  {
    id: 'cor-05',
    type: 'Media similarity',
    icon: 'image_search',
    identifier: 'img_exfil_vault_floorplan.jpg',
    waEntity: 'WhatsApp Media ZIP / IMG-20260330-WA0012.jpg',
    tgEntity: 'Telegram Cache / photo_481029102.jpg',
    heuristicScore: 0.99,
    rating: 'Deterministic',
    rule: 'dHash <= 1 (Perceptual & SHA-256 Byte Match)',
    citations: 'SHA-256: 7fa0218b9412e84c9012a8120b33411ae3b0c442...'
  },
  {
    id: 'cor-06',
    type: 'Handover',
    icon: 'swap_horiz',
    identifier: 'Session Handoff: "Switching to Telegram @falcon"',
    waEntity: 'Last message in WhatsApp thread (10:14:01 UTC)',
    tgEntity: 'First message in Telegram channel (10:14:45 UTC)',
    heuristicScore: 0.82,
    rating: 'Strong',
    rule: 'Temporal Delta <= 45s with Direct Platform Keyword Reference',
    citations: 'Time delta: 44 seconds between separate app transports'
  },
  {
    id: 'cor-07',
    type: 'Rendezvous',
    icon: 'pin_drop',
    identifier: 'GPS Pin: 28.6139° N, 77.2090° E (New Delhi)',
    waEntity: 'WhatsApp Live Location payload row 84922',
    tgEntity: 'Telegram Venue coordinates row 4132',
    heuristicScore: 0.95,
    rating: 'Deterministic',
    rule: 'WGS84 Coordinate Identity (Within 5m radius)',
    citations: 'WhatsApp rowid 84922 ↔ Telegram venue ID #941'
  }
];

export default function CorrelationsPage() {
  const { activeCase } = useActiveCase();

  const [selectedType, setSelectedType] = useState('All');
  const [selectedItem, setSelectedItem] = useState(CORRELATIONS[0]);

  const filtered = CORRELATIONS.filter(c => {
    if (selectedType === 'All') return true;
    return c.type.toLowerCase().includes(selectedType.toLowerCase());
  });

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden">
      {/* Header Section */}
      <div className="p-space-lg bg-surface-container border-b border-outline-variant shrink-0 space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <h1 className="text-headline-md font-headline-md font-semibold text-on-surface tracking-tight">
              Cross-Source Correlations &amp; Entity Resolution
            </h1>
            <p className="text-body-sm font-body-sm text-on-surface-variant mt-0.5">
              Automated heuristic linkage across WhatsApp and Telegram evidentiary databases for case {activeCase?.caseNumber}.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-label-mono-sm font-label-mono-sm text-on-surface-variant text-xs">Database Pairs:</span>
            <span className="px-2.5 py-1 rounded bg-surface-container-high border border-outline-variant text-label-mono-sm font-label-mono-sm text-on-surface text-xs font-semibold">
              msgstore.db ↔ cache4.db
            </span>
          </div>
        </div>

        {/* 7 Filter Metric Cards from Stitch Design */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-space-xs pt-1">
          <div
            onClick={() => setSelectedType(selectedType === 'Phone' ? 'All' : 'Phone')}
            className={`flex flex-col p-2 rounded border transition-all cursor-pointer ${
              selectedType === 'Phone' ? 'border-primary bg-primary/10' : 'bg-surface-container-low border-outline-variant hover:border-outline'
            }`}
          >
            <div className="flex items-center justify-between text-on-surface-variant text-xs">
              <span className="font-label-ui">Phone</span>
              <span className="material-symbols-outlined text-[14px]">phone</span>
            </div>
            <div className="text-headline-sm font-semibold text-on-surface mt-1">28</div>
            <span className="text-[10px] font-mono text-outline">33.3% share</span>
          </div>

          <div
            onClick={() => setSelectedType(selectedType === 'Wallet' ? 'All' : 'Wallet')}
            className={`flex flex-col p-2 rounded border transition-all cursor-pointer ${
              selectedType === 'Wallet' ? 'border-primary bg-primary/10' : 'bg-surface-container-low border-outline-variant hover:border-outline'
            }`}
          >
            <div className="flex items-center justify-between text-primary text-xs">
              <span className="font-label-ui font-semibold">Wallet</span>
              <span className="material-symbols-outlined text-[14px] text-primary">account_balance_wallet</span>
            </div>
            <div className="text-headline-sm font-semibold text-primary mt-1">14</div>
            <span className="text-[10px] font-mono text-primary/80">EIP-55 valid</span>
          </div>

          <div
            onClick={() => setSelectedType(selectedType === 'IBAN' ? 'All' : 'IBAN')}
            className={`flex flex-col p-2 rounded border transition-all cursor-pointer ${
              selectedType === 'IBAN' ? 'border-primary bg-primary/10' : 'bg-surface-container-low border-outline-variant hover:border-outline'
            }`}
          >
            <div className="flex items-center justify-between text-on-surface-variant text-xs">
              <span className="font-label-ui">IBAN</span>
              <span className="material-symbols-outlined text-[14px]">credit_card</span>
            </div>
            <div className="text-headline-sm font-semibold text-on-surface mt-1">6</div>
            <span className="text-[10px] font-mono text-outline">MOD-97 chk</span>
          </div>

          <div
            onClick={() => setSelectedType(selectedType === 'URL' ? 'All' : 'URL')}
            className={`flex flex-col p-2 rounded border transition-all cursor-pointer ${
              selectedType === 'URL' ? 'border-primary bg-primary/10' : 'bg-surface-container-low border-outline-variant hover:border-outline'
            }`}
          >
            <div className="flex items-center justify-between text-on-surface-variant text-xs">
              <span className="font-label-ui">URL</span>
              <span className="material-symbols-outlined text-[14px]">link</span>
            </div>
            <div className="text-headline-sm font-semibold text-on-surface mt-1">19</div>
            <span className="text-[10px] font-mono text-outline">FQDN match</span>
          </div>

          <div
            onClick={() => setSelectedType(selectedType === 'Media' ? 'All' : 'Media')}
            className={`flex flex-col p-2 rounded border transition-all cursor-pointer ${
              selectedType === 'Media' ? 'border-primary bg-primary/10' : 'bg-surface-container-low border-outline-variant hover:border-outline'
            }`}
          >
            <div className="flex items-center justify-between text-on-surface-variant text-xs">
              <span className="font-label-ui">Media</span>
              <span className="material-symbols-outlined text-[14px]">image_search</span>
            </div>
            <div className="text-headline-sm font-semibold text-on-surface mt-1">8</div>
            <span className="text-[10px] font-mono text-outline">dHash &lt;= 1</span>
          </div>

          <div
            onClick={() => setSelectedType(selectedType === 'Handover' ? 'All' : 'Handover')}
            className={`flex flex-col p-2 rounded border transition-all cursor-pointer ${
              selectedType === 'Handover' ? 'border-primary bg-primary/10' : 'bg-surface-container-low border-outline-variant hover:border-outline'
            }`}
          >
            <div className="flex items-center justify-between text-on-surface-variant text-xs">
              <span className="font-label-ui">Handover</span>
              <span className="material-symbols-outlined text-[14px]">swap_horiz</span>
            </div>
            <div className="text-headline-sm font-semibold text-on-surface mt-1">5</div>
            <span className="text-[10px] font-mono text-outline">Session hints</span>
          </div>

          <div
            onClick={() => setSelectedType(selectedType === 'Rendezvous' ? 'All' : 'Rendezvous')}
            className={`flex flex-col p-2 rounded border transition-all cursor-pointer ${
              selectedType === 'Rendezvous' ? 'border-primary bg-primary/10' : 'bg-surface-container-low border-outline-variant hover:border-outline'
            }`}
          >
            <div className="flex items-center justify-between text-on-surface-variant text-xs">
              <span className="font-label-ui">Rendezvous</span>
              <span className="material-symbols-outlined text-[14px]">pin_drop</span>
            </div>
            <div className="text-headline-sm font-semibold text-on-surface mt-1">4</div>
            <span className="text-[10px] font-mono text-outline">GPS proximity</span>
          </div>
        </div>
      </div>

      {/* Split Table & Inspector Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Table Area */}
        <div className="flex-1 overflow-y-auto custom-scrollbar border-r border-outline-variant">
          <table className="w-full text-left border-collapse text-body-sm font-body-sm">
            <thead>
              <tr className="bg-surface-container-lowest/80 border-b border-outline-variant h-8 text-label-ui font-label-ui text-on-surface-variant uppercase tracking-wider text-[11px] sticky top-0 z-10">
                <th className="py-2.5 px-3 w-10 text-center">#</th>
                <th className="py-2.5 px-3">Resolved Identifier</th>
                <th className="py-2.5 px-3 w-28">Entity Type</th>
                <th className="py-2.5 px-3">Cross-Platform Linked Endpoints</th>
                <th className="py-2.5 px-3 w-28 text-center">Heuristic Score</th>
                <th className="py-2.5 px-3 w-40">Admissibility Rating</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/60 text-xs">
              {filtered.map((item, idx) => {
                const isSelected = selectedItem?.id === item.id;
                return (
                  <tr
                    key={item.id}
                    onClick={() => setSelectedItem(item)}
                    className={`hover:bg-surface-container-high/60 transition-colors cursor-pointer ${
                      isSelected ? 'bg-primary/10 border-l-2 border-primary' : ''
                    }`}
                  >
                    <td className="py-3 px-3 text-center font-mono text-outline">
                      {String(idx + 1).padStart(2, '0')}
                    </td>
                    <td className="py-3 px-3">
                      <div className="flex items-center space-x-2">
                        <span className="material-symbols-outlined text-primary text-[16px]">{item.icon}</span>
                        <span className="font-mono font-medium text-on-surface text-sm">{item.identifier}</span>
                      </div>
                    </td>
                    <td className="py-3 px-3">
                      <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-surface-container-high border border-outline-variant text-on-surface">
                        {item.type}
                      </span>
                    </td>
                    <td className="py-3 px-3 space-y-0.5">
                      <div className="flex items-center space-x-1.5 text-on-surface truncate">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                        <span className="truncate">{item.waEntity}</span>
                      </div>
                      <div className="flex items-center space-x-1.5 text-on-surface-variant truncate">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                        <span className="truncate">{item.tgEntity}</span>
                      </div>
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span className="px-2 py-0.5 rounded font-mono font-semibold text-tertiary bg-tertiary/10 border border-tertiary/30">
                        {(item.heuristicScore * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <span className="text-[11px] text-on-surface font-medium block">
                        {item.rating}
                      </span>
                      <span className="text-[10px] text-outline truncate block max-w-xs">{item.rule}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Right Detail Inspector Drawer */}
        {selectedItem && (
          <aside className="w-[360px] bg-surface-container border-l border-outline-variant flex flex-col justify-between overflow-y-auto custom-scrollbar p-4 space-y-4 shrink-0">
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-outline-variant">
                <span className="font-label-ui uppercase tracking-wider text-xs font-semibold text-outline">
                  Correlation Inspector
                </span>
                <span className="px-1.5 py-0.2 rounded bg-primary/20 text-primary text-[10px] font-mono">
                  {selectedItem.id}
                </span>
              </div>

              {/* Resolved Target */}
              <div className="p-3 rounded bg-surface-container-low border border-outline-variant space-y-1">
                <span className="text-on-surface-variant text-[11px] block">Resolved Common Identity</span>
                <div className="font-mono text-sm font-semibold text-primary break-all">
                  {selectedItem.identifier}
                </div>
              </div>

              {/* Cross-Platform Endpoints */}
              <div className="space-y-2 text-xs">
                <div className="text-label-ui uppercase tracking-wider text-outline font-semibold">
                  Evidence Endpoints
                </div>

                <div className="p-2.5 rounded bg-surface-container-low border border-outline-variant space-y-1">
                  <div className="flex items-center space-x-1 text-emerald-400 font-semibold text-[11px]">
                    <span className="material-symbols-outlined text-[14px]">chat</span>
                    <span>WhatsApp Evidentiary Endpoint</span>
                  </div>
                  <div className="text-on-surface font-mono text-[11px] break-all">
                    {selectedItem.waEntity}
                  </div>
                </div>

                <div className="p-2.5 rounded bg-surface-container-low border border-outline-variant space-y-1">
                  <div className="flex items-center space-x-1 text-blue-400 font-semibold text-[11px]">
                    <span className="material-symbols-outlined text-[14px]">send</span>
                    <span>Telegram Evidentiary Endpoint</span>
                  </div>
                  <div className="text-on-surface font-mono text-[11px] break-all">
                    {selectedItem.tgEntity}
                  </div>
                </div>
              </div>

              {/* Admissibility & Citations */}
              <div className="space-y-2 text-xs">
                <div className="text-label-ui uppercase tracking-wider text-outline font-semibold">
                  Forensic Rule &amp; Citations
                </div>
                <div className="p-2.5 rounded bg-surface-container-low border border-outline-variant space-y-1.5 font-label-mono-sm text-[11px]">
                  <div>
                    <span className="text-outline block">Heuristic Matching Rule:</span>
                    <span className="text-on-surface font-medium">{selectedItem.rule}</span>
                  </div>
                  <div>
                    <span className="text-outline block">Citation References:</span>
                    <span className="text-primary break-all">{selectedItem.citations}</span>
                  </div>
                  <div>
                    <span className="text-outline block">Evidentiary Weight:</span>
                    <span className="text-tertiary font-semibold">{selectedItem.rating}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-outline-variant">
              <button
                type="button"
                onClick={() => navigator.clipboard?.writeText(JSON.stringify(selectedItem, null, 2))}
                className="btn-secondary w-full text-xs"
              >
                <span className="material-symbols-outlined text-[15px]">content_copy</span>
                <span>Copy Correlation Manifest Record</span>
              </button>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
