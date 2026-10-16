import React, { useState } from 'react';
import { useActiveCase } from '../context/CaseContext';

export default function DecryptionPage() {
  const { activeCase } = useActiveCase();

  const [keys, setKeys] = useState([
    {
      id: 'k-01',
      reference: 'KREF-WA-2026-01',
      target: 'msgstore.db.crypt15',
      algo: 'AES-256-GCM / crypt15',
      fingerprint: '0x98A1...E41F (64-hex AES-256 deriv)',
      status: 'Decrypted',
      outputDb: 'msgstore.decrypted.db',
      outputSize: '180.2 MiB',
      recordsFound: '12,842 rows',
      enclaveBound: true
    },
    {
      id: 'k-02',
      reference: 'KREF-TG-SYSTEM-2025-04',
      target: 'cache4.db (Telegram)',
      algo: 'Local Telegram KEK / SQLCipher',
      fingerprint: '0x44B2...A901 (Enclave Deriv)',
      status: 'Decrypted',
      outputDb: 'cache4.decrypted.db',
      outputSize: '48.1 MiB',
      recordsFound: '7,893 rows',
      enclaveBound: true
    },
    {
      id: 'k-03',
      reference: 'KREF-RAW-HEX-MANUAL',
      target: 'wa_backup_legacy.crypt14',
      algo: 'AES-256-CTR / crypt14',
      fingerprint: 'Awaiting Key Input',
      status: 'Pending Key',
      outputDb: 'None staged',
      outputSize: '0 B',
      recordsFound: '0 rows',
      enclaveBound: false
    }
  ]);

  const [hexKeyInput, setHexKeyInput] = useState('');
  const [injectModalOpen, setInjectModalOpen] = useState(false);
  const [executing, setExecuting] = useState(false);

  const handleInjectKey = (e) => {
    e.preventDefault();
    if (!hexKeyInput) return;
    setKeys(prev => prev.map(k => {
      if (k.id === 'k-03') {
        return {
          ...k,
          fingerprint: `0x${hexKeyInput.substring(0, 4)}...${hexKeyInput.substring(hexKeyInput.length - 4)}`,
          status: 'Key Loaded (Ready)'
        };
      }
      return k;
    }));
    setHexKeyInput('');
    setInjectModalOpen(false);
  };

  const handleExecuteDecryption = () => {
    setExecuting(true);
    setTimeout(() => {
      setExecuting(false);
      setKeys(prev => prev.map(k => ({
        ...k,
        status: 'Decrypted'
      })));
    }, 800);
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-y-auto custom-scrollbar p-space-lg space-y-4">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-outline-variant">
        <div>
          <div className="flex items-center space-x-2.5 mb-1">
            <h1 className="text-headline-lg font-headline-lg font-semibold text-on-surface">
              Cryptographic Subsystem &amp; Decryption
            </h1>
            <span className="px-2 py-0.5 rounded text-[11px] font-label-mono-sm bg-primary/10 text-primary border border-primary/30">
              HARDWARE ENCLAVE ISOLATED
            </span>
          </div>
          <p className="text-body-sm font-body-sm text-on-surface-variant">
            Hardware-isolated key derivation and AES-256 database decryption pipeline for case {activeCase?.caseNumber}.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={() => setInjectModalOpen(true)}
            className="btn-secondary"
          >
            <span className="material-symbols-outlined text-[16px]">vpn_key</span>
            <span>Inject Key Token</span>
          </button>
          <button
            type="button"
            onClick={handleExecuteDecryption}
            disabled={executing}
            className="btn-primary"
          >
            <span className="material-symbols-outlined text-[16px]">
              {executing ? 'sync' : 'play_arrow'}
            </span>
            <span>{executing ? 'Decrypting Enclave...' : 'Execute Decryption'}</span>
          </button>
        </div>
      </div>

      {/* Amber Security Banner */}
      <div className="flex items-center space-x-2.5 px-3.5 py-2.5 rounded-lg border border-amber-600/40 bg-amber-950/20 text-amber-200 text-body-sm">
        <span className="material-symbols-outlined text-amber-400 text-lg shrink-0">security</span>
        <div className="text-[12px] leading-relaxed">
          <strong className="text-amber-300">Volatile RAM Security Protocol:</strong> Decryption keys are held in volatile enclave memory and wiped immediately upon process termination. Keys are never serialized to disk or exported into court schedules.
        </div>
      </div>

      {/* Decryption Targets Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {keys.map((k) => (
          <div
            key={k.id}
            className="bg-surface-container border border-outline-variant rounded-lg p-4 flex flex-col justify-between shadow-xs space-y-3"
          >
            <div>
              <div className="flex items-center justify-between pb-2 border-b border-outline-variant">
                <span className="font-label-mono-sm text-label-mono-sm text-primary font-semibold">
                  {k.reference}
                </span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-label-mono-sm font-medium ${
                    k.status === 'Decrypted'
                      ? 'bg-tertiary/10 text-tertiary border border-tertiary/30'
                      : k.status.includes('Ready')
                      ? 'bg-primary/10 text-primary border border-primary/30'
                      : 'bg-amber-500/10 text-amber-500 border border-amber-500/30'
                  }`}
                >
                  {k.status}
                </span>
              </div>

              <div className="mt-3 space-y-2 text-xs">
                <div>
                  <span className="text-on-surface-variant text-[11px] block">Target Artifact:</span>
                  <span className="font-mono text-on-surface font-semibold text-sm">{k.target}</span>
                </div>

                <div className="p-2 rounded bg-surface-container-low border border-outline-variant space-y-1 font-label-mono-sm text-[11px]">
                  <div className="flex justify-between">
                    <span className="text-on-surface-variant">Algorithm:</span>
                    <span className="text-on-surface">{k.algo}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-on-surface-variant">Key Ref:</span>
                    <span className="text-primary truncate max-w-[130px]">{k.fingerprint}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-on-surface-variant">Output SQLite:</span>
                    <span className="text-on-surface">{k.outputDb}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-on-surface-variant">Yield:</span>
                    <span className="text-tertiary font-semibold">{k.recordsFound}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-outline-variant flex items-center justify-between text-[11px] text-on-surface-variant">
              <span>{k.enclaveBound ? 'Enclave Hardware Bound' : 'Manual Hex Injection'}</span>
              <button
                type="button"
                onClick={() => setInjectModalOpen(true)}
                className="text-primary hover:underline font-medium"
              >
                Inspect
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Technical Key Derivation Ledger */}
      <div className="bg-surface-container border border-outline-variant rounded-lg p-space-lg space-y-3 shadow-xs">
        <div className="flex items-center justify-between pb-2 border-b border-outline-variant">
          <div className="flex items-center space-x-2">
            <span className="material-symbols-outlined text-primary text-[18px]">key</span>
            <h2 className="text-headline-sm font-headline-sm text-on-surface">
              Enclave Key Derivation Ledger
            </h2>
          </div>
          <span className="text-[11px] font-label-mono-sm text-outline">FIPS 140-3 Mode Active</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-body-sm font-body-sm">
            <thead>
              <tr className="bg-surface-container-lowest/80 border-b border-outline-variant h-8 text-label-ui font-label-ui text-on-surface-variant uppercase tracking-wider text-[11px]">
                <th className="py-2 px-3">Binding Reference</th>
                <th className="py-2 px-3">Target Container</th>
                <th className="py-2 px-3">Key Derivative Method</th>
                <th className="py-2 px-3 font-mono">IV / Salt Digest</th>
                <th className="py-2 px-3 text-right">Decryption State</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/60 font-label-mono-sm text-xs">
              <tr>
                <td className="py-2 px-3 font-medium text-primary">KREF-WA-2026-01</td>
                <td className="py-2 px-3 text-on-surface">msgstore.db.crypt15</td>
                <td className="py-2 px-3 text-on-surface-variant">HKDF-SHA256 (WhatsApp v15 Spec)</td>
                <td className="py-2 px-3 text-on-surface">1e4a0912f8a4...091b</td>
                <td className="py-2 px-3 text-right text-tertiary">Verified Match (0 Errors)</td>
              </tr>
              <tr>
                <td className="py-2 px-3 font-medium text-primary">KREF-TG-SYSTEM-2025-04</td>
                <td className="py-2 px-3 text-on-surface">cache4.db</td>
                <td className="py-2 px-3 text-on-surface-variant">PBKDF2-HMAC-SHA1 (4000 iters)</td>
                <td className="py-2 px-3 text-on-surface">8c912049ba01...219f</td>
                <td className="py-2 px-3 text-right text-tertiary">Verified Match (0 Errors)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Key Injection Modal */}
      {injectModalOpen && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-surface-container border border-outline-variant rounded-xl max-w-lg w-full p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-outline-variant">
              <div className="flex items-center space-x-2">
                <span className="material-symbols-outlined text-primary text-[20px]">vpn_key</span>
                <h3 className="text-headline-sm font-headline-sm text-on-surface">Inject Ephemeral Decryption Key</h3>
              </div>
              <button
                type="button"
                onClick={() => setInjectModalOpen(false)}
                className="text-on-surface-variant hover:text-on-surface p-1 rounded"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </div>

            <form onSubmit={handleInjectKey} className="space-y-4 text-body-sm">
              <div className="space-y-1">
                <label className="text-label-ui uppercase tracking-wider text-on-surface-variant block text-xs">
                  Target Keystore Slot
                </label>
                <select className="w-full bg-surface-container-low border border-outline-variant rounded p-2 text-on-surface text-body-sm focus:outline-none focus:border-primary">
                  <option>KREF-RAW-HEX-MANUAL (wa_backup_legacy.crypt14)</option>
                  <option>KREF-WA-2026-01 (Override Slot)</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-label-ui uppercase tracking-wider text-on-surface-variant block text-xs">
                  Raw 64-Hex AES Key or Base64 Token
                </label>
                <input
                  type="text"
                  placeholder="e.g. 7f8a2c1b9d0e44f8ca56449102c019dbebf883651139eef7b5a8e032148b8df2"
                  value={hexKeyInput}
                  onChange={(e) => setHexKeyInput(e.target.value)}
                  required
                  className="w-full bg-surface-container-lowest border border-outline-variant rounded p-2 font-mono text-xs text-on-surface focus:outline-none focus:border-primary"
                />
              </div>

              <div className="p-3 rounded bg-surface-container-low border border-outline-variant text-xs text-on-surface-variant">
                Keys loaded via this form exist exclusively in ephemeral RAM for the duration of the current analysis thread.
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setInjectModalOpen(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                >
                  Stage Key in Enclave
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
