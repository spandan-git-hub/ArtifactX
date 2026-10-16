import React, { useState, useEffect, useCallback } from 'react';
import { useActiveCase } from '../context/CaseContext';
import { decryptionService } from '../services/decryptionService';
import { evidenceService } from '../services/evidenceService';

export default function DecryptionPage() {
  const { activeCase } = useActiveCase();
  const caseId = activeCase?.id;

  const [artifacts, setArtifacts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hexKeyInput, setHexKeyInput] = useState('');
  const [selectedEvidenceId, setSelectedEvidenceId] = useState('');
  const [injectModalOpen, setInjectModalOpen] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const loadData = useCallback(async () => {
    if (!caseId) {
      setArtifacts([]);
      return;
    }
    setLoading(true);
    try {
      // Fetch both case derived artifacts and evidence files
      const [derived, evidences] = await Promise.all([
        decryptionService.getCaseDerivedArtifacts(caseId).catch(() => []),
        evidenceService.getEvidences(caseId).catch(() => [])
      ]);

      const evList = Array.isArray(evidences) ? evidences : (evidences?.evidences || []);
      const derList = Array.isArray(derived) ? derived : (derived?.derived_artifacts || []);

      // Build unified list of decryptable/derived items
      const items = evList.map(ev => {
        const matchingDer = derList.find(d => d.evidence_id === ev.id);
        const fname = ev.original_filename || ev.name || `evidence_${ev.id}`;
        const isEncrypted = fname.includes('.crypt') || fname.includes('cache4') || ev.evidence_type?.includes('Encrypted');
        return {
          id: ev.id,
          reference: `KREF-EV-${ev.id}`,
          target: fname,
          algo: fname.includes('crypt15') ? 'AES-256-GCM / crypt15' : (fname.includes('crypt14') ? 'AES-256-CTR / crypt14' : 'SQLCipher / AES-256-CBC'),
          fingerprint: ev.sha256 ? `${ev.sha256.substring(0, 10)}...${ev.sha256.substring(ev.sha256.length - 8)}` : 'Awaiting Digest',
          status: matchingDer ? 'Decrypted' : (isEncrypted ? 'Pending Key / Pipeline' : 'Plaintext Staged'),
          outputDb: matchingDer ? (matchingDer.artifact_name || 'decrypted.db') : (isEncrypted ? 'None staged' : fname),
          outputSize: matchingDer ? `${(matchingDer.file_size_bytes / (1024 * 1024)).toFixed(1)} MiB` : '0 B',
          recordsFound: matchingDer?.record_count ? `${matchingDer.record_count} rows` : (matchingDer ? 'Extracted' : '0 rows'),
          enclaveBound: true
        };
      });

      setArtifacts(items);
      if (items.length > 0 && !selectedEvidenceId) {
        setSelectedEvidenceId(String(items[0].id));
      }
    } catch (err) {
      console.warn('Error loading decryption operations:', err);
      setArtifacts([]);
    } finally {
      setLoading(false);
    }
  }, [caseId, selectedEvidenceId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleInjectKey = async (e) => {
    e.preventDefault();
    if (!hexKeyInput || !selectedEvidenceId) return;
    setExecuting(true);
    setFeedback(null);
    try {
      await decryptionService.runDecryption(selectedEvidenceId, {
        key_hex: hexKeyInput,
        format: 'auto'
      });
      setFeedback({ type: 'success', message: `Key successfully loaded into hardware enclave for evidence #${selectedEvidenceId}.` });
      setHexKeyInput('');
      setInjectModalOpen(false);
      await loadData();
    } catch (err) {
      console.error('Decryption execution error:', err);
      setFeedback({ type: 'error', message: err.response?.data?.detail || err.message || 'Key injection failed.' });
    } finally {
      setExecuting(false);
    }
  };

  const handleExecuteDecryption = async () => {
    if (!selectedEvidenceId) return;
    setExecuting(true);
    setFeedback(null);
    try {
      await decryptionService.runDecryption(selectedEvidenceId, { format: 'auto' });
      setFeedback({ type: 'success', message: 'Decryption pipeline executed successfully.' });
      await loadData();
    } catch (err) {
      console.error('Decryption run error:', err);
      setFeedback({ type: 'error', message: err.response?.data?.detail || err.message || 'Decryption execution failed.' });
    } finally {
      setExecuting(false);
    }
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
            Hardware-isolated key derivation and AES-256 database decryption pipeline for case {activeCase?.caseNumber || 'docket'}.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={() => setInjectModalOpen(true)}
            disabled={artifacts.length === 0}
            className="btn-secondary"
          >
            <span className="material-symbols-outlined text-sm">vpn_key</span>
            <span>Inject Manual Hex Key</span>
          </button>

          <button
            type="button"
            onClick={handleExecuteDecryption}
            disabled={executing || artifacts.length === 0}
            className="btn-primary"
          >
            <span className={`material-symbols-outlined text-sm ${executing ? 'animate-spin' : ''}`}>
              {executing ? 'sync' : 'lock_open'}
            </span>
            <span>{executing ? 'Decrypting...' : 'Execute Decryption Run'}</span>
          </button>
        </div>
      </div>

      {feedback && (
        <div className={`p-3 rounded-lg text-xs font-mono flex items-center justify-between ${
          feedback.type === 'error' ? 'bg-error/15 border border-error/40 text-error' : 'bg-tertiary/15 border border-tertiary/40 text-tertiary'
        }`}>
          <span>{feedback.message}</span>
          <span className="material-symbols-outlined text-sm">
            {feedback.type === 'error' ? 'error' : 'check_circle'}
          </span>
        </div>
      )}

      {/* Enclave Status Bar */}
      <div className="p-3 bg-surface-container border border-outline-variant rounded-lg flex flex-wrap items-center justify-between gap-3 text-label-mono-sm text-xs">
        <div className="flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-primary" />
          <span className="text-on-surface font-semibold">ENCLAVE STATUS: READY</span>
          <span className="text-outline">|</span>
          <span className="text-on-surface-variant">Zero-Disk Plaintext Buffer Enforced (R4)</span>
        </div>
        <div className="flex items-center space-x-3 text-outline">
          <span>Active Case ID: {caseId || 'N/A'}</span>
          <span>•</span>
          <span>FIPS 140-3 Mode: Compliant</span>
        </div>
      </div>

      {/* Decryption Targets Table */}
      <div className="bg-surface-container border border-outline-variant rounded-lg overflow-hidden shadow-xs">
        <div className="p-3 border-b border-outline-variant flex items-center justify-between">
          <h3 className="font-headline-sm text-on-surface font-semibold text-sm">
            Key Material &amp; Target Databases ({artifacts.length})
          </h3>
          <span className="text-[11px] font-mono text-outline">Deterministic HKDF &amp; AES-GCM Ingestion</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-body-sm">
            <thead>
              <tr className="bg-surface-container-lowest/80 border-b border-outline-variant h-8 text-label-ui uppercase tracking-wider text-[11px] text-on-surface-variant">
                <th className="py-2.5 px-3">Target Container</th>
                <th className="py-2.5 px-3">Cryptographic Cipher</th>
                <th className="py-2.5 px-3">Digest / Fingerprint</th>
                <th className="py-2.5 px-3">Decrypted Output</th>
                <th className="py-2.5 px-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/60 font-mono text-xs">
              {loading && (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-on-surface-variant">
                    <span className="material-symbols-outlined text-2xl animate-spin text-primary mb-1">sync</span>
                    <p>Inspecting cryptographic containers...</p>
                  </td>
                </tr>
              )}

              {!loading && artifacts.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-on-surface-variant">
                    <span className="material-symbols-outlined text-3xl text-outline mb-1">key_off</span>
                    <p className="font-semibold text-on-surface text-sm">No Encrypted Evidence Containers</p>
                    <p className="text-xs text-outline mt-0.5">Upload .crypt14/.crypt15 or SQLCipher evidence to stage decryption.</p>
                  </td>
                </tr>
              )}

              {!loading && artifacts.map((item) => (
                <tr key={item.id} className="hover:bg-surface-container-high/40 transition-colors">
                  <td className="py-3 px-3">
                    <div className="font-semibold text-on-surface font-sans text-sm">{item.target}</div>
                    <div className="text-[10px] text-outline font-mono">{item.reference}</div>
                  </td>
                  <td className="py-3 px-3 text-on-surface-variant">{item.algo}</td>
                  <td className="py-3 px-3">
                    <code className="text-on-surface bg-surface-container-lowest px-1.5 py-0.5 rounded border border-outline-variant text-[10px]">
                      {item.fingerprint}
                    </code>
                  </td>
                  <td className="py-3 px-3">
                    <div className="text-on-surface font-sans text-xs">{item.outputDb}</div>
                    <div className="text-[10px] text-outline">{item.recordsFound} · {item.outputSize}</div>
                  </td>
                  <td className="py-3 px-3 text-right">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                      item.status === 'Decrypted'
                        ? 'bg-tertiary/10 text-tertiary border border-tertiary/30'
                        : item.status === 'Plaintext Staged'
                          ? 'bg-primary/10 text-primary border border-primary/30'
                          : 'bg-amber-500/10 text-amber-300 border border-amber-500/30'
                    }`}>
                      {item.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Inject Key Modal */}
      {injectModalOpen && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-surface-container border border-outline-variant rounded-lg max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-2 border-b border-outline-variant">
              <h3 className="font-headline-sm font-semibold text-on-surface">Inject Manual Hex Key</h3>
              <button
                type="button"
                onClick={() => setInjectModalOpen(false)}
                className="text-on-surface-variant hover:text-on-surface"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleInjectKey} className="space-y-4">
              <div className="space-y-1">
                <label className="text-label-ui uppercase tracking-wider text-on-surface-variant block text-xs">
                  Target Evidence Container
                </label>
                <select
                  value={selectedEvidenceId}
                  onChange={(e) => setSelectedEvidenceId(e.target.value)}
                  className="w-full bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1.5 text-body-sm text-on-surface focus:outline-none focus:border-primary"
                >
                  {artifacts.map(a => (
                    <option key={a.id} value={a.id}>{a.target} (#{a.id})</option>
                  ))}
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-label-ui uppercase tracking-wider text-on-surface-variant block text-xs">
                  64-Character Hexadecimal Key String (AES-256)
                </label>
                <input
                  type="text"
                  placeholder="e.g. 8a72cf19d45e08b1a32f91bc740192e8fa312904bc78e120aa45192803bba221"
                  value={hexKeyInput}
                  onChange={(e) => setHexKeyInput(e.target.value)}
                  className="w-full bg-surface-container-lowest border border-outline-variant rounded px-2.5 py-1.5 font-mono text-body-sm text-on-surface focus:outline-none focus:border-primary"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setInjectModalOpen(false)}
                  className="btn-secondary text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={executing || !hexKeyInput}
                  className="btn-primary text-xs"
                >
                  {executing ? 'Injecting...' : 'Load into Enclave'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
