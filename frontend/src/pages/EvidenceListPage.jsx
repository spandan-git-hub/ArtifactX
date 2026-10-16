import React, { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useActiveCase } from '../context/CaseContext';

const DEFAULT_ARTIFACTS = [
  {
    id: 'art-01',
    name: 'msgstore.db.crypt15',
    role: 'Primary Encrypted DB',
    app: 'WhatsApp',
    size: '182.4 MiB',
    sha256: '8a72cf19d45e08b1a32f91bc740192e8fa312904bc78e120aa45192803bba221',
    blake3: 'b149f80214a9c801eef234091a84210e',
    md5: '7fa0218b9412e84c9012a8120b33411a',
    status: 'Verified',
    verifiedUtc: '2026-03-30 08:35:12',
    path: '/data/data/com.whatsapp/databases/msgstore.db.crypt15',
    volume: 'Target_01.raw (ext4)',
    sectorOffset: '0x0041F800',
    readOnly: true,
  },
  {
    id: 'art-02',
    name: 'wa_unencrypted_dump.crypt15',
    role: 'Plain SQLite Dump',
    app: 'WhatsApp',
    size: '41.2 MiB',
    sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    blake3: '8c912049ba012e84219fb941208a0021',
    md5: '410b29c0192a84ef9012e84c9012aa01',
    status: 'Verified',
    verifiedUtc: '2026-03-30 08:35:14',
    path: '/mnt/forensic_stage/dumps/wa_unencrypted_dump.crypt15',
    volume: 'Target_01.raw (ext4)',
    sectorOffset: '0x0098A200',
    readOnly: true,
  },
  {
    id: 'art-03',
    name: 'cache4.db',
    role: 'Telegram Primary DB',
    app: 'Telegram',
    size: '48.2 MiB',
    sha256: '01f5e88d11ac293847291048b291048572910485729104857291048572910485',
    blake3: '4481092e01a8b94210ec94120b334112',
    md5: '98412e84c9012a8120b33411a7fa0218',
    status: 'Verified',
    verifiedUtc: '2026-03-30 08:35:19',
    path: '/data/data/org.telegram.messenger/files/cache4.db',
    volume: 'Target_01.raw (ext4)',
    sectorOffset: '0x011A4000',
    readOnly: true,
  },
  {
    id: 'art-04',
    name: 'cache4.db-wal',
    role: 'WAL Journal Frame',
    app: 'Telegram',
    size: '12.8 MiB',
    sha256: '4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c',
    blake3: '9a012e84219fb941208a00218c912049',
    md5: 'a8120b33411a7fa0218b9412e84c9012',
    status: 'Verified',
    verifiedUtc: '2026-03-30 08:35:21',
    path: '/data/data/org.telegram.messenger/files/cache4.db-wal',
    volume: 'Target_01.raw (ext4)',
    sectorOffset: '0x01402800',
    readOnly: true,
  },
  {
    id: 'art-05',
    name: 'cache4.db-shm',
    role: 'Shared Memory Map',
    app: 'Telegram',
    size: '32 KiB',
    sha256: '9b4a11f082e4c9012a8120b33411a7fa0218b9412e84c9012a8120b33411a7fa',
    blake3: '10ec94120b3341124481092e01a8b942',
    md5: '84c9012a8120b33411a7fa0218b9412e',
    status: 'Verified',
    verifiedUtc: '2026-03-30 08:35:22',
    path: '/data/data/org.telegram.messenger/files/cache4.db-shm',
    volume: 'Target_01.raw (ext4)',
    sectorOffset: '0x01580000',
    readOnly: true,
  },
  {
    id: 'art-06',
    name: 'media_attachments.zip',
    role: 'Media Archive Package',
    app: 'Cross-App',
    size: '94.6 MiB',
    sha256: '7fa0218b9412e84c9012a8120b33411ae3b0c44298fc1c149afbf4c8996fb924',
    blake3: '208a00218c9120499a012e84219fb941',
    md5: '012a8120b33411a7fa0218b9412e84c9',
    status: 'Verified',
    verifiedUtc: '2026-03-30 08:35:28',
    path: '/sdcard/Android/media/com.whatsapp/WhatsApp/Media',
    volume: 'Target_01.raw (ext4)',
    sectorOffset: '0x028B1000',
    readOnly: true,
  },
  {
    id: 'art-07',
    name: 'encrypted_backup.key',
    role: 'AES Key Reference',
    app: 'WhatsApp',
    size: '128 B',
    sha256: '01f5e88d11ac293847291048b291048572910485729104857291048572910485',
    blake3: 'ff00921a84210eb149f80214a9c801ee',
    md5: '120b33411a7fa0218b9412e84c9012a8',
    status: 'Checksum Mismatch',
    verifiedUtc: '2026-03-30 08:35:30',
    path: '/data/data/com.whatsapp/files/key',
    volume: 'Target_01.raw (ext4)',
    sectorOffset: '0x00100400',
    readOnly: true,
  }
];

export default function EvidenceListPage() {
  const { caseId } = useParams();
  const { activeCase } = useActiveCase();

  const [artifacts, setArtifacts] = useState(DEFAULT_ARTIFACTS);
  const [selectedArtifact, setSelectedArtifact] = useState(DEFAULT_ARTIFACTS[0]);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  const [verifyAlertVisible, setVerifyAlertVisible] = useState(true);

  const filtered = artifacts.filter(item => {
    const matchesSearch = item.name.toLowerCase().includes(search.toLowerCase()) ||
                          item.sha256.toLowerCase().includes(search.toLowerCase()) ||
                          item.app.toLowerCase().includes(search.toLowerCase());
    const matchesRole = roleFilter === 'All' || item.role.includes(roleFilter);
    const matchesStatus = statusFilter === 'All' || item.status === statusFilter;
    return matchesSearch && matchesRole && matchesStatus;
  });

  const handleVerifyNow = (artId) => {
    setArtifacts(prev => prev.map(a => {
      if (a.id === artId) {
        return {
          ...a,
          status: 'Verified',
          verifiedUtc: new Date().toISOString().replace('T', ' ').substring(0, 19)
        };
      }
      return a;
    }));
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden">
      {/* Top Summary / Integrity Alert Banner */}
      {verifyAlertVisible && (
        <div className="bg-error/15 border-b border-error/40 px-4 py-2.5 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-3">
            <span className="material-symbols-outlined text-error text-[18px] shrink-0">warning</span>
            <div className="text-body-sm font-body-sm text-on-surface">
              <span className="font-semibold text-error">Integrity alert:</span> File{' '}
              <code className="font-label-mono-sm text-error bg-surface-container-lowest px-1.5 py-0.5 rounded border border-error/30">
                encrypted_backup.key
              </code>{' '}
              failed cryptographic verification against claimed acquisition hash. Tampering or transport corruption flagged in audit log.
            </div>
          </div>
          <div className="flex items-center space-x-2 shrink-0 ml-4">
            <button
              type="button"
              onClick={() => {
                const item = artifacts.find(a => a.name === 'encrypted_backup.key');
                if (item) setSelectedArtifact(item);
              }}
              className="px-2.5 py-1 rounded bg-error/20 hover:bg-error/30 text-error border border-error/50 text-label-ui font-label-ui font-medium flex items-center gap-1 transition-colors"
            >
              <span>Inspect Exception</span>
              <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
            </button>
            <button
              type="button"
              onClick={() => setVerifyAlertVisible(false)}
              className="p-1 text-on-surface-variant hover:text-on-surface rounded"
            >
              <span className="material-symbols-outlined text-[14px]">close</span>
            </button>
          </div>
        </div>
      )}

      {/* Audit Chain Status Ribbon */}
      <div className="bg-surface-container-high/40 border-b border-outline-variant px-4 py-1.5 flex items-center justify-between text-label-mono-sm font-label-mono-sm shrink-0">
        <div className="flex items-center space-x-2 text-on-surface-variant">
          <span className="material-symbols-outlined text-tertiary text-[14px]">check_circle</span>
          <span className="text-on-surface">Evidence Store: {artifacts.length} artifacts mounted</span>
          <span className="text-outline">|</span>
          <span>Root Merkle: <span className="text-primary font-medium">9a4f..88c1</span></span>
          <span className="text-outline">|</span>
          <span>Chain verification: ACTIVE (UTC {new Date().toISOString().substring(0, 10)})</span>
        </div>
        <div className="flex items-center space-x-3 text-on-surface-variant">
          <span>Volume: Target_01.raw</span>
          <span className="px-1.5 py-0.2 rounded bg-surface-container border border-outline-variant text-on-surface font-label-ui text-[10px]">
            READ-ONLY
          </span>
        </div>
      </div>

      {/* Controls & Filter Bar */}
      <div className="p-3 bg-surface-container/60 border-b border-outline-variant flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-2 flex-1 max-w-xl">
          <div className="relative flex-1">
            <span className="material-symbols-outlined absolute left-2.5 top-2 text-on-surface-variant text-[16px]">
              search
            </span>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter evidence by name, hash, role..."
              className="w-full bg-surface-container-lowest border border-outline-variant rounded h-8 pl-8 pr-3 text-body-sm font-body-sm text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:border-primary"
            />
          </div>

          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="h-8 px-2.5 bg-surface-container-lowest border border-outline-variant rounded text-label-ui text-on-surface focus:outline-none focus:border-primary cursor-pointer"
          >
            <option value="All">Role: All Roles</option>
            <option value="Encrypted DB">Encrypted DB</option>
            <option value="SQLite">SQLite Dump</option>
            <option value="WAL">WAL Journal</option>
            <option value="Archive">Media Archive</option>
            <option value="Key">Key Reference</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-8 px-2.5 bg-surface-container-lowest border border-outline-variant rounded text-label-ui text-on-surface focus:outline-none focus:border-primary cursor-pointer"
          >
            <option value="All">Integrity: All ({artifacts.length})</option>
            <option value="Verified">Verified</option>
            <option value="Checksum Mismatch">Checksum Mismatch</option>
          </select>
        </div>

        <Link
          to={`/cases/${caseId || activeCase?.id}/upload`}
          className="btn-primary"
        >
          <span className="material-symbols-outlined text-[16px]">upload_file</span>
          <span>Upload Evidence</span>
        </Link>
      </div>

      {/* Split Canvas: Main Table (Left) + Detail Inspector (Right) */}
      <div className="flex-1 flex overflow-hidden">
        {/* Main Table Area */}
        <div className="flex-1 overflow-y-auto custom-scrollbar border-r border-outline-variant">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-lowest/80 border-b border-outline-variant h-8 text-label-ui font-label-ui text-on-surface-variant uppercase tracking-wider text-[11px] sticky top-0 z-10">
                <th className="py-2 px-3 w-10 text-center">#</th>
                <th className="py-2 px-3">Filename / Container</th>
                <th className="py-2 px-3 w-28">App / Source</th>
                <th className="py-2 px-3 w-24 text-right">Size</th>
                <th className="py-2 px-3 font-mono text-[11px]">SHA-256 Digest</th>
                <th className="py-2 px-3 w-36">Integrity Status</th>
                <th className="py-2 px-3 w-20 text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/60 text-body-sm font-body-sm">
              {filtered.map((item, idx) => {
                const isSelected = selectedArtifact?.id === item.id;
                return (
                  <tr
                    key={item.id}
                    onClick={() => setSelectedArtifact(item)}
                    className={`hover:bg-surface-container-high/60 transition-colors cursor-pointer ${
                      isSelected ? 'bg-primary/10 border-l-2 border-primary' : ''
                    } ${item.status === 'Checksum Mismatch' ? 'bg-error/5' : ''}`}
                  >
                    <td className="py-2.5 px-3 text-center text-label-mono-sm text-outline">
                      {String(idx + 1).padStart(2, '0')}
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="flex items-center space-x-2">
                        <span className={`material-symbols-outlined text-[16px] ${
                          item.status === 'Checksum Mismatch' ? 'text-error' : 'text-primary'
                        }`}>
                          {item.name.endsWith('.key') ? 'key' : item.name.endsWith('.zip') ? 'folder_zip' : 'database'}
                        </span>
                        <div>
                          <div className="font-medium text-on-surface">{item.name}</div>
                          <span className="text-[10px] text-outline font-mono">{item.role}</span>
                        </div>
                      </div>
                    </td>
                    <td className="py-2.5 px-3 text-on-surface-variant text-xs">
                      {item.app}
                    </td>
                    <td className="py-2.5 px-3 text-right font-label-mono-sm text-on-surface">
                      {item.size}
                    </td>
                    <td className="py-2.5 px-3">
                      <code className="text-label-mono-sm font-mono text-[11px] text-on-surface bg-surface-container-lowest px-1.5 py-0.5 rounded border border-outline-variant block max-w-xs truncate">
                        {item.sha256}
                      </code>
                    </td>
                    <td className="py-2.5 px-3">
                      {item.status === 'Verified' ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-label-ui text-tertiary bg-tertiary/10 border border-tertiary/30 px-2 py-0.5 rounded-full">
                          <span className="w-1.5 h-1.5 rounded-full bg-tertiary" />
                          Verified
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-label-ui text-error bg-error/10 border border-error/30 px-2 py-0.5 rounded-full">
                          <span className="w-1.5 h-1.5 rounded-full bg-error" />
                          Checksum Mismatch
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleVerifyNow(item.id);
                        }}
                        className="p-1 text-on-surface-variant hover:text-primary rounded transition-colors"
                        title="Re-verify SHA-256"
                      >
                        <span className="material-symbols-outlined text-[16px]">refresh</span>
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Right Detail Inspector Drawer */}
        {selectedArtifact && (
          <aside className="w-[360px] bg-surface-container border-l border-outline-variant flex flex-col justify-between overflow-y-auto custom-scrollbar p-4 space-y-4 shrink-0">
            <div className="space-y-4">
              {/* Drawer Header */}
              <div className="flex items-start justify-between pb-3 border-b border-outline-variant">
                <div className="space-y-1">
                  <div className="flex items-center space-x-1.5">
                    <span className="material-symbols-outlined text-primary text-[18px]">info</span>
                    <span className="font-label-ui uppercase tracking-wider text-outline text-[11px]">Artifact Inspector</span>
                  </div>
                  <h3 className="font-headline-sm font-headline-sm text-on-surface truncate max-w-[280px]">
                    {selectedArtifact.name}
                  </h3>
                </div>
                <span className={`px-2 py-0.5 rounded text-[10px] font-label-mono-sm font-semibold uppercase ${
                  selectedArtifact.status === 'Verified' ? 'bg-tertiary/10 text-tertiary border border-tertiary/30' : 'bg-error/10 text-error border border-error/30'
                }`}>
                  {selectedArtifact.status}
                </span>
              </div>

              {/* Physical Storage Details */}
              <div className="space-y-2 text-xs">
                <div className="text-label-ui uppercase tracking-wider text-outline font-semibold">
                  Physical Storage Parameters
                </div>
                <div className="p-2.5 rounded bg-surface-container-low border border-outline-variant space-y-1.5 font-label-mono-sm text-[11px]">
                  <div className="flex justify-between">
                    <span className="text-on-surface-variant">Container Path:</span>
                    <span className="text-on-surface truncate max-w-[170px]" title={selectedArtifact.path}>
                      {selectedArtifact.path}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-on-surface-variant">Mounted Volume:</span>
                    <span className="text-on-surface">{selectedArtifact.volume}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-on-surface-variant">Sector Offset:</span>
                    <span className="text-primary">{selectedArtifact.sectorOffset}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-on-surface-variant">Bytes Size:</span>
                    <span className="text-on-surface">{selectedArtifact.size}</span>
                  </div>
                </div>
              </div>

              {/* Cryptographic Digests */}
              <div className="space-y-2 text-xs">
                <div className="text-label-ui uppercase tracking-wider text-outline font-semibold">
                  Cryptographic Verification Digests
                </div>

                <div className="space-y-2">
                  <div className="p-2 rounded bg-surface-container-low border border-outline-variant space-y-1">
                    <div className="flex justify-between items-center text-[11px] text-on-surface-variant">
                      <span className="font-semibold text-primary">SHA-256 (Statutory Primary)</span>
                      <button
                        type="button"
                        onClick={() => navigator.clipboard?.writeText(selectedArtifact.sha256)}
                        className="text-outline hover:text-primary"
                        title="Copy"
                      >
                        <span className="material-symbols-outlined text-[13px]">content_copy</span>
                      </button>
                    </div>
                    <code className="text-[11px] font-mono text-on-surface block break-all bg-surface-container-lowest p-1.5 rounded border border-outline-variant">
                      {selectedArtifact.sha256}
                    </code>
                  </div>

                  <div className="p-2 rounded bg-surface-container-low border border-outline-variant space-y-1">
                    <div className="flex justify-between items-center text-[11px] text-on-surface-variant">
                      <span>BLAKE3-256 (High-Speed Enclave)</span>
                      <button
                        type="button"
                        onClick={() => navigator.clipboard?.writeText(selectedArtifact.blake3)}
                        className="text-outline hover:text-primary"
                        title="Copy"
                      >
                        <span className="material-symbols-outlined text-[13px]">content_copy</span>
                      </button>
                    </div>
                    <code className="text-[11px] font-mono text-on-surface block break-all bg-surface-container-lowest p-1.5 rounded border border-outline-variant">
                      {selectedArtifact.blake3}
                    </code>
                  </div>
                </div>
              </div>

              {/* Last Checked */}
              <div className="p-2.5 rounded bg-surface-container-low border border-outline-variant text-label-mono-sm text-[11px] text-on-surface-variant flex items-center justify-between">
                <span>Last Verified (UTC):</span>
                <span className="text-on-surface font-semibold">{selectedArtifact.verifiedUtc}</span>
              </div>
            </div>

            {/* Actions */}
            <div className="pt-3 border-t border-outline-variant space-y-2">
              <button
                type="button"
                onClick={() => handleVerifyNow(selectedArtifact.id)}
                className="btn-primary w-full"
              >
                <span className="material-symbols-outlined text-[15px]">verified</span>
                <span>Recalculate SHA-256 Digest</span>
              </button>

              <Link
                to={`/cases/${caseId || activeCase?.id}/pipeline`}
                className="btn-secondary w-full"
              >
                <span className="material-symbols-outlined text-[15px]">alt_route</span>
                <span>Stage in Forensic Pipeline</span>
              </Link>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
