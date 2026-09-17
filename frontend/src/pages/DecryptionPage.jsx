import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { decryptionService } from '../services/decryptionService';
import { getEvidences } from '../services/evidenceService';
import {
  KeyRound,
  ShieldCheck,
  Lock,
  Unlock,
  Sparkles,
  FileCode,
  Search,
  Filter,
  RefreshCw,
  Hash,
  Clock,
  Layers,
  FileText,
  Copy,
  Check,
  Database,
  Info,
  AlertCircle,
  Eye,
  Download,
  Terminal,
} from 'lucide-react';

export default function DecryptionPage() {
  const { caseId } = useParams();

  const [evidenceList, setEvidenceList] = useState([]);
  const [derivedArtifacts, setDerivedArtifacts] = useState([]);
  const [operations, setOperations] = useState([]);
  const [selectedEvidence, setSelectedEvidence] = useState(null);
  const [detectionResults, setDetectionResults] = useState({});
  const [activeTab, setActiveTab] = useState('inventory'); // 'inventory', 'workbench', 'ledger', 'derived'

  // Workbench Form State
  const [selectedFormat, setSelectedFormat] = useState('auto_detect');
  const [keyInput, setKeyInput] = useState('');
  const [passcodeInput, setPasscodeInput] = useState('');
  const [mediaType, setMediaType] = useState('image');
  const [sqlcipherProfile, setSqlcipherProfile] = useState('v4');

  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [copiedHash, setCopiedHash] = useState(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [evData, artData] = await Promise.all([
        getEvidences(caseId),
        decryptionService.getCaseDerivedArtifacts(caseId).catch(() => []),
      ]);
      setEvidenceList(evData || []);
      setDerivedArtifacts(artData || []);
      if (evData && evData.length > 0 && !selectedEvidence) {
        setSelectedEvidence(evData[0]);
      }
    } catch (err) {
      console.error('Failed to load decryption data:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load case evidence');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (caseId) {
      loadData();
    }
  }, [caseId]);

  const handleDetect = async (ev) => {
    try {
      setActionLoading(true);
      setError(null);
      const res = await decryptionService.detectFormat(ev.id);
      setDetectionResults((prev) => ({ ...prev, [ev.id]: res }));
      setSelectedEvidence(ev);
    } catch (err) {
      setError(err.response?.data?.detail || 'Format detection failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRunDecryption = async () => {
    if (!selectedEvidence) {
      setError('Please select an evidence container first.');
      return;
    }

    try {
      setActionLoading(true);
      setError(null);
      setSuccessMsg(null);

      const payload = {
        key_material: keyInput.trim() || null,
        passcode: passcodeInput.trim() || null,
        format_override: selectedFormat !== 'auto_detect' ? selectedFormat : null,
        parameters: {
          media_type: mediaType,
          profile: sqlcipherProfile,
        },
      };

      const res = await decryptionService.runDecryption(selectedEvidence.id, payload);
      setSuccessMsg(`Decryption SUCCEEDED! Derived exhibit SHA-256: ${res.output_sha256}`);
      setKeyInput('');
      setPasscodeInput('');
      await loadData();
      setActiveTab('derived');
    } catch (err) {
      console.error('Decryption execution failed:', err);
      setError(err.response?.data?.detail || err.message || 'Decryption failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const copyToClipboard = (text, key) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(key);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  return (
    <div className="min-h-screen bg-forensic-950 text-forensic-100 p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-forensic-800 pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-forensic-500 mb-1">
            <Link to="/cases" className="hover:text-accent-cyan">Cases</Link>
            <span>/</span>
            <Link to={`/cases/${caseId}`} className="hover:text-accent-cyan">Case #{caseId}</Link>
            <span>/</span>
            <span className="text-accent-cyan">Decryption Subsystem</span>
          </div>
          <h1 className="text-2xl font-bold flex items-center gap-3">
            <KeyRound className="h-7 w-7 text-accent-cyan" />
            <span>Cryptographic Decryption Subsystem</span>
          </h1>
          <p className="text-sm text-forensic-400 mt-1">
            Auditable in-memory decryption for WhatsApp Crypt12/14/15, .enc Media, and Telegram SQLCipher & MTProto
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-forensic-900 border border-forensic-700 text-xs font-mono">
            <div className="status-dot status-dot-active" />
            <span>Zero-Disk Protected (PostgreSQL BYTEA)</span>
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="btn-secondary text-xs inline-flex items-center gap-2"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Error & Success Banners */}
      {error && (
        <div className="p-4 rounded-lg bg-red-950/40 border border-red-800/60 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-red-200">
            <span className="font-semibold">Decryption Warning: </span>
            {error}
          </div>
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-lg bg-accent-emerald/10 border border-accent-emerald/40 flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 text-accent-emerald flex-shrink-0 mt-0.5" />
          <div className="text-sm text-accent-emerald font-mono">
            {successMsg}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-forensic-800 space-x-6 text-sm font-mono">
        <button
          onClick={() => setActiveTab('inventory')}
          className={`pb-3 border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'inventory'
              ? 'border-accent-cyan text-accent-cyan font-bold'
              : 'border-transparent text-forensic-400 hover:text-forensic-200'
          }`}
        >
          <Database className="w-4 h-4" />
          <span>Encrypted Evidence Inventory ({evidenceList.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('workbench')}
          className={`pb-3 border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'workbench'
              ? 'border-accent-cyan text-accent-cyan font-bold'
              : 'border-transparent text-forensic-400 hover:text-forensic-200'
          }`}
        >
          <Lock className="w-4 h-4" />
          <span>Decryption Workbench</span>
        </button>

        <button
          onClick={() => setActiveTab('derived')}
          className={`pb-3 border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'derived'
              ? 'border-accent-cyan text-accent-cyan font-bold'
              : 'border-transparent text-forensic-400 hover:text-forensic-200'
          }`}
        >
          <Unlock className="w-4 h-4" />
          <span>Derived Forensic Exhibits ({derivedArtifacts.length})</span>
        </button>
      </div>

      {/* Tab 1: Evidence Inventory & Format Detection */}
      {activeTab === 'inventory' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {evidenceList.map((ev) => {
              const det = detectionResults[ev.id];
              const isSelected = selectedEvidence?.id === ev.id;
              return (
                <div
                  key={ev.id}
                  className={`p-4 rounded-lg border transition-all ${
                    isSelected
                      ? 'bg-forensic-900 border-accent-cyan shadow-lg shadow-accent-cyan/10'
                      : 'bg-forensic-900/60 border-forensic-800 hover:border-forensic-700'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div className="truncate">
                      <div className="font-mono text-sm font-semibold truncate text-forensic-100" title={ev.original_filename}>
                        {ev.original_filename}
                      </div>
                      <div className="text-xs text-forensic-500 font-mono mt-0.5">
                        Evidence #{ev.id} • {ev.content_type || 'binary'}
                      </div>
                    </div>
                    {det && det.is_encrypted ? (
                      <span className="badge border border-amber-500/40 bg-amber-500/10 text-amber-400 text-xs px-2 py-0.5 rounded font-mono">
                        {det.format?.toUpperCase()}
                      </span>
                    ) : (
                      <span className="badge border border-forensic-700 bg-forensic-800 text-forensic-400 text-xs px-2 py-0.5 rounded font-mono">
                        {ev.evidence_type || 'CONTAINER'}
                      </span>
                    )}
                  </div>

                  <div className="text-xs font-mono text-forensic-400 space-y-1 mb-4">
                    <div className="flex items-center justify-between">
                      <span className="text-forensic-600">SHA-256:</span>
                      <span className="truncate max-w-[180px]" title={ev.sha256}>
                        {ev.sha256.substring(0, 16)}...
                      </span>
                    </div>
                    {det && (
                      <div className="flex items-center justify-between">
                        <span className="text-forensic-600">Entropy:</span>
                        <span className="text-accent-cyan font-bold">{det.entropy} / 8.0 bits</span>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2 pt-2 border-t border-forensic-800">
                    <button
                      onClick={() => handleDetect(ev)}
                      disabled={actionLoading}
                      className="btn-secondary text-xs flex-1 inline-flex items-center justify-center gap-1.5 py-1.5"
                    >
                      <Terminal className="w-3.5 h-3.5 text-accent-cyan" />
                      Detect Format
                    </button>
                    <button
                      onClick={() => {
                        setSelectedEvidence(ev);
                        if (det?.format) setSelectedFormat(det.format);
                        setActiveTab('workbench');
                      }}
                      className="btn-primary text-xs flex-1 inline-flex items-center justify-center gap-1.5 py-1.5"
                    >
                      <KeyRound className="w-3.5 h-3.5" />
                      Workbench
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {evidenceList.length === 0 && !loading && (
            <div className="text-center py-12 border border-dashed border-forensic-800 rounded-xl">
              <Database className="w-12 h-12 text-forensic-700 mx-auto mb-3" />
              <div className="text-forensic-400 font-mono text-sm">No evidence files found in this case.</div>
              <Link to={`/cases/${caseId}/evidence`} className="btn-secondary text-xs mt-4 inline-flex items-center gap-2">
                Upload Seized Evidence
              </Link>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Decryption Workbench */}
      {activeTab === 'workbench' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Controls Form */}
          <div className="lg:col-span-2 space-y-6 bg-forensic-900/60 border border-forensic-800 rounded-xl p-6">
            <div>
              <h2 className="text-lg font-bold text-forensic-100 flex items-center gap-2">
                <Lock className="w-5 h-5 text-accent-cyan" />
                Decryption Execution Workbench
              </h2>
              <p className="text-xs text-forensic-400 mt-1">
                Configure key material and format profiles. Secrets are held in ephemeral memory and never persisted.
              </p>
            </div>

            {/* Target Exhibit Banner */}
            <div className="p-3.5 rounded-lg bg-forensic-950 border border-forensic-700 flex items-center justify-between">
              <div>
                <span className="text-xs text-forensic-500 font-mono">TARGET EVIDENCE EXHIBIT:</span>
                <div className="font-mono text-sm font-semibold text-accent-cyan">
                  {selectedEvidence ? selectedEvidence.original_filename : 'No evidence selected'}
                </div>
              </div>
              {selectedEvidence && (
                <span className="text-xs font-mono text-forensic-400">
                  ID #{selectedEvidence.id} • SHA-256: {selectedEvidence.sha256.substring(0, 12)}...
                </span>
              )}
            </div>

            {/* Format Selection */}
            <div>
              <label className="block text-xs font-mono text-forensic-300 mb-2 uppercase">
                Encryption Format / Engine
              </label>
              <select
                value={selectedFormat}
                onChange={(e) => setSelectedFormat(e.target.value)}
                className="w-full bg-forensic-950 border border-forensic-700 rounded-lg p-2.5 text-sm font-mono text-forensic-100 focus:border-accent-cyan outline-none"
              >
                <option value="auto_detect">Automatic Detection (Entropy & Header Inspection)</option>
                <option value="crypt12">WhatsApp Crypt12 (AES-256-GCM)</option>
                <option value="crypt14">WhatsApp Crypt14 (PBKDF2-HMAC-SHA256 + AES-GCM)</option>
                <option value="crypt15">WhatsApp Crypt15 (64-Hex Passkey + SHA512 PBKDF2)</option>
                <option value="whatsapp_enc">WhatsApp Media .enc (HKDF RFC 5869 + AES-CBC)</option>
                <option value="sqlcipher">Telegram SQLCipher (cache4.db)</option>
                <option value="mtproto">Telegram MTProto Secret Chat (enc_chats IGE)</option>
              </select>
            </div>

            {/* Key / Passcode Inputs based on format */}
            {selectedFormat !== 'sqlcipher' && selectedFormat !== 'mtproto' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-mono text-forensic-300 mb-2 uppercase">
                    WhatsApp Key Material / 64-Hex Passkey
                  </label>
                  <textarea
                    rows={3}
                    value={keyInput}
                    onChange={(e) => setKeyInput(e.target.value)}
                    placeholder="Paste raw 32-byte key hex, base64 key file contents, or 64-char Crypt15 passkey..."
                    className="w-full bg-forensic-950 border border-forensic-700 rounded-lg p-3 text-xs font-mono text-forensic-100 focus:border-accent-cyan outline-none"
                  />
                  <span className="text-[11px] text-forensic-500 font-mono mt-1 block">
                    Supports 158-byte /data/data/com.whatsapp/files/key or 64-character hexadecimal passkeys.
                  </span>
                </div>

                {selectedFormat === 'whatsapp_enc' && (
                  <div>
                    <label className="block text-xs font-mono text-forensic-300 mb-2 uppercase">
                      Media Attachment Type
                    </label>
                    <div className="grid grid-cols-4 gap-3">
                      {['image', 'audio', 'video', 'document'].map((m) => (
                        <button
                          key={m}
                          type="button"
                          onClick={() => setMediaType(m)}
                          className={`p-2 rounded text-xs font-mono uppercase border transition-all ${
                            mediaType === m
                              ? 'border-accent-cyan bg-accent-cyan/20 text-accent-cyan font-bold'
                              : 'border-forensic-800 bg-forensic-950 text-forensic-400 hover:border-forensic-700'
                          }`}
                        >
                          {m}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {selectedFormat === 'sqlcipher' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-mono text-forensic-300 mb-2 uppercase">
                    Telegram App Passcode / PIN
                  </label>
                  <input
                    type="password"
                    value={passcodeInput}
                    onChange={(e) => setPasscodeInput(e.target.value)}
                    placeholder="Enter known Telegram PIN or passcode..."
                    className="w-full bg-forensic-950 border border-forensic-700 rounded-lg p-2.5 text-sm font-mono text-forensic-100 focus:border-accent-cyan outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono text-forensic-300 mb-2 uppercase">
                    SQLCipher Parameter Profile
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      { id: 'v4', label: 'SQLCipher v4 (Default)', desc: '4096B page, PBKDF2-SHA512 (256,000 iter)' },
                      { id: 'v3', label: 'SQLCipher v3 (Legacy)', desc: '1024B page, PBKDF2-SHA1 (64,000 iter)' },
                    ].map((prof) => (
                      <button
                        key={prof.id}
                        type="button"
                        onClick={() => setSqlcipherProfile(prof.id)}
                        className={`p-3 rounded-lg text-left border transition-all ${
                          sqlcipherProfile === prof.id
                            ? 'border-accent-cyan bg-accent-cyan/10 text-forensic-100'
                            : 'border-forensic-800 bg-forensic-950 text-forensic-400'
                        }`}
                      >
                        <div className="text-xs font-bold font-mono">{prof.label}</div>
                        <div className="text-[11px] text-forensic-500 mt-1">{prof.desc}</div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Execute Button */}
            <div className="pt-4 border-t border-forensic-800 flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs text-forensic-500 font-mono">
                <ShieldCheck className="w-4 h-4 text-accent-emerald" />
                <span>Zero Secret Leakage Guarantee</span>
              </div>
              <button
                onClick={handleRunDecryption}
                disabled={actionLoading || !selectedEvidence}
                className="btn-primary inline-flex items-center gap-2 px-6 py-2.5 text-sm font-semibold"
              >
                {actionLoading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Executing Decryption...</span>
                  </>
                ) : (
                  <>
                    <Unlock className="w-4 h-4" />
                    <span>Run Decryption Engine</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Side Info & Specifications */}
          <div className="space-y-4">
            <div className="p-5 bg-forensic-900/60 border border-forensic-800 rounded-xl space-y-3">
              <h3 className="text-xs font-mono font-bold text-forensic-300 uppercase flex items-center gap-2">
                <Info className="w-4 h-4 text-accent-cyan" />
                Chain-of-Custody Invariants
              </h3>
              <ul className="text-xs text-forensic-400 space-y-2 list-disc list-inside">
                <li>Original evidence is never modified or overwritten.</li>
                <li>Plaintext databases are persisted directly to PostgreSQL BYTEA.</li>
                <li>Parent file SHA-256 and output SHA-256 are cryptographically verified.</li>
                <li>Local folders (<code>uploads/</code>, <code>reports/</code>) remain strictly empty.</li>
              </ul>
            </div>

            <div className="p-5 bg-forensic-900/60 border border-forensic-800 rounded-xl space-y-3">
              <h3 className="text-xs font-mono font-bold text-forensic-300 uppercase flex items-center gap-2">
                <Terminal className="w-4 h-4 text-accent-cyan" />
                Forensic Key Formats
              </h3>
              <div className="text-xs text-forensic-400 space-y-2 font-mono">
                <div>
                  <span className="text-accent-cyan">WhatsApp Key:</span> 158-byte binary file located at <code>/data/data/com.whatsapp/files/key</code>
                </div>
                <div>
                  <span className="text-accent-cyan">Crypt15 Passkey:</span> 64 hexadecimal characters configured during backup creation.
                </div>
                <div>
                  <span className="text-accent-cyan">SQLCipher:</span> 4-to-6 digit device passcode or alphanumeric app lock password.
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Derived Forensic Exhibits */}
      {activeTab === 'derived' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {derivedArtifacts.map((art) => (
              <div
                key={art.id}
                className="p-5 bg-forensic-900/60 border border-forensic-800 rounded-xl hover:border-forensic-700 transition-all space-y-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="truncate">
                    <div className="font-mono text-sm font-bold text-accent-cyan truncate">
                      {art.original_filename}
                    </div>
                    <div className="text-xs text-forensic-500 font-mono mt-0.5">
                      Exhibit #{art.id} • Parent Evidence #{art.parent_evidence_id}
                    </div>
                  </div>
                  <span className="badge border border-accent-emerald/40 bg-accent-emerald/10 text-accent-emerald text-xs px-2.5 py-0.5 rounded font-mono">
                    {art.artifact_type.toUpperCase()}
                  </span>
                </div>

                <div className="text-xs font-mono text-forensic-400 space-y-1.5 bg-forensic-950 p-3 rounded-lg border border-forensic-800/80">
                  <div className="flex items-center justify-between">
                    <span className="text-forensic-600">Output SHA-256:</span>
                    <div className="flex items-center gap-1.5">
                      <span className="text-forensic-200">{art.sha256.substring(0, 20)}...</span>
                      <button
                        onClick={() => copyToClipboard(art.sha256, `art-${art.id}`)}
                        className="text-forensic-500 hover:text-accent-cyan"
                      >
                        {copiedHash === `art-${art.id}` ? <Check className="w-3.5 h-3.5 text-accent-emerald" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-forensic-600">Size:</span>
                    <span>{(art.size_bytes / 1024).toFixed(1)} KB</span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-forensic-600">MIME Type:</span>
                    <span>{art.mime_type || 'application/octet-stream'}</span>
                  </div>

                  {art.provenance?.validation?.table_count !== undefined && (
                    <div className="flex items-center justify-between">
                      <span className="text-forensic-600">SQLite Tables:</span>
                      <span className="text-accent-emerald font-bold">
                        {art.provenance.validation.table_count} tables (Integrity: {art.provenance.validation.integrity_check})
                      </span>
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <a
                    href={decryptionService.getStreamUrl(caseId, art.id)}
                    target="_blank"
                    rel="noreferrer"
                    className="btn-secondary text-xs inline-flex items-center gap-1.5 py-1.5 px-3"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download Plaintext Stream
                  </a>
                </div>
              </div>
            ))}
          </div>

          {derivedArtifacts.length === 0 && !loading && (
            <div className="text-center py-12 border border-dashed border-forensic-800 rounded-xl">
              <Unlock className="w-12 h-12 text-forensic-700 mx-auto mb-3" />
              <div className="text-forensic-400 font-mono text-sm">No decrypted exhibits generated yet.</div>
              <button
                onClick={() => setActiveTab('workbench')}
                className="btn-primary text-xs mt-4 inline-flex items-center gap-2"
              >
                <Lock className="w-3.5 h-3.5" />
                Open Decryption Workbench
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
