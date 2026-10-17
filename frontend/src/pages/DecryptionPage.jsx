import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useActiveCase } from '../context/CaseContext';
import { decryptionService } from '../services/decryptionService';
import { Link } from 'react-router-dom';

export default function DecryptionPage() {
  const { activeCase } = useActiveCase();
  const caseId = activeCase?.id;

  const [inventory, setInventory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [feedback, setFeedback] = useState(null);

  // Form states per encrypted file: { [fileId]: string }
  const [keyInputs, setKeyInputs] = useState({});
  const [keyFileIds, setKeyFileIds] = useState({});
  const [keySources, setKeySources] = useState({});
  const [decryptingId, setDecryptingId] = useState(null);

  // Modal states
  const [selectedEncryptedFile, setSelectedEncryptedFile] = useState(null);
  const [inspectModalFile, setInspectModalFile] = useState(null);

  // Filter & Search states for directly usable files
  const [usableCategory, setUsableCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedHash, setCopiedHash] = useState(null);

  const loadInventory = useCallback(async (isSilent = false) => {
    if (!caseId) {
      setInventory(null);
      setLoading(false);
      return;
    }
    if (!isSilent) setLoading(true);
    else setRefreshing(true);

    try {
      const data = await decryptionService.getInventory(caseId);
      setInventory(data);

      // Pre-fill default autofill candidate keys if not already manually typed
      if (data?.encrypted_files) {
        setKeyInputs(prev => {
          const next = { ...prev };
          const nextFileIds = { ...keyFileIds };
          const nextSources = { ...keySources };

          data.encrypted_files.forEach(ef => {
            if (ef.autofill_key && !next[ef.id]) {
              next[ef.id] = ef.autofill_key.autofill_value;
              nextFileIds[ef.id] = ef.autofill_key.key_file_id;
              nextSources[ef.id] = 'autofill';
            }
          });
          setKeyFileIds(nextFileIds);
          setKeySources(nextSources);
          return next;
        });

        // Also update selectedEncryptedFile if modal is open
        setSelectedEncryptedFile(prev => {
          if (!prev) return null;
          return data.encrypted_files.find(f => f.id === prev.id) || prev;
        });
      }
    } catch (err) {
      console.error('Error loading decryption inventory:', err);
      setFeedback({
        type: 'error',
        message: err.response?.data?.detail || err.message || 'Failed to load case file inventory.'
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [caseId]);

  useEffect(() => {
    loadInventory();
  }, [loadInventory]);

  const handleCopyHash = (hash) => {
    if (!hash) return;
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2500);
  };

  const handleAutofillKey = (file, candidateKey) => {
    if (!candidateKey) return;
    setKeyInputs(prev => ({ ...prev, [file.id]: candidateKey.autofill_value }));
    setKeyFileIds(prev => ({ ...prev, [file.id]: candidateKey.key_file_id }));
    setKeySources(prev => ({ ...prev, [file.id]: 'autofill' }));
    setFeedback({
      type: 'info',
      message: `Autofilled candidate key "${candidateKey.filename}" (${candidateKey.key_type}) for ${file.filename}.`
    });
  };

  const handleAutofillAll = () => {
    if (!inventory?.encrypted_files) return;
    let count = 0;
    const nextInputs = { ...keyInputs };
    const nextFileIds = { ...keyFileIds };
    const nextSources = { ...keySources };

    inventory.encrypted_files.forEach(ef => {
      if (ef.autofill_key) {
        nextInputs[ef.id] = ef.autofill_key.autofill_value;
        nextFileIds[ef.id] = ef.autofill_key.key_file_id;
        nextSources[ef.id] = 'autofill';
        count++;
      }
    });

    setKeyInputs(nextInputs);
    setKeyFileIds(nextFileIds);
    setKeySources(nextSources);
    setFeedback({
      type: 'success',
      message: `Autofilled matching evidence keys for ${count} encrypted file(s).`
    });
  };

  const handlePasteKey = async (fileId) => {
    try {
      const text = await navigator.clipboard.readText();
      if (text && text.trim()) {
        const clean = text.trim();
        setKeyInputs(prev => ({ ...prev, [fileId]: clean }));
        setKeySources(prev => ({ ...prev, [fileId]: 'manual' }));
        setFeedback({
          type: 'info',
          message: 'Pasted key material from clipboard.'
        });
      }
    } catch {
      // Fallback if clipboard permission denied
    }
  };

  const handleExecuteDecryption = async (file) => {
    const keyVal = keyInputs[file.id];
    const keyFId = keyFileIds[file.id];

    if (!keyVal && !keyFId) {
      setFeedback({
        type: 'error',
        message: `Please enter a manual key or select an autofill key for ${file.filename}.`
      });
      return;
    }

    setDecryptingId(file.id);
    setFeedback(null);

    try {
      const payload = {
        evidence_id: file.evidence_id,
        candidate_file_id: file.file_id,
        key_data: keyVal || undefined,
        key_file_id: keyFId || undefined,
        format_override: file.detected_format || undefined
      };

      const res = await decryptionService.executeDecryption(caseId, payload);

      setFeedback({
        type: 'success',
        message: `Successfully decrypted "${file.filename}"! Derived exhibit #${res.derived_artifact_id || ''} staged into memory and database records indexed.`
      });

      // Reload inventory silently to update directly usable section
      await loadInventory(true);
    } catch (err) {
      console.error('Decryption execution error:', err);
      setFeedback({
        type: 'error',
        message: err.response?.data?.detail || err.message || `Failed to decrypt ${file.filename}.`
      });
    } finally {
      setDecryptingId(null);
    }
  };

  // Filter directly usable files
  const filteredUsableFiles = useMemo(() => {
    if (!inventory?.directly_usable_files) return [];
    return inventory.directly_usable_files.filter(item => {
      // Category filter
      if (usableCategory === 'database' && item.category !== 'database') return false;
      if (usableCategory === 'derived' && !item.is_derived) return false;
      if (usableCategory === 'media' && item.category !== 'media') return false;
      if (usableCategory === 'config' && item.category !== 'config') return false;
      if (usableCategory === 'key' && item.category !== 'key') return false;
      if (usableCategory === 'document' && item.category !== 'document') return false;
      if (usableCategory === 'other' && (['database', 'media', 'config', 'key', 'document'].includes(item.category) || item.is_derived)) return false;

      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesName = item.filename.toLowerCase().includes(q);
        const matchesPath = item.relative_path.toLowerCase().includes(q);
        const matchesContainer = item.source_container.toLowerCase().includes(q);
        const matchesHash = item.sha256?.toLowerCase().includes(q);
        if (!matchesName && !matchesPath && !matchesContainer && !matchesHash) return false;
      }
      return true;
    });
  }, [inventory, usableCategory, searchQuery]);

  const stats = inventory?.stats || {
    total_identified_files: 0,
    encrypted_count: 0,
    directly_usable_count: 0,
    discovered_keys_count: 0,
    decrypted_count: 0
  };

  const getCategoryIcon = (category, isDerived) => {
    if (isDerived) return 'lock_open';
    switch (category) {
      case 'database': return 'database';
      case 'media': return 'image';
      case 'config': return 'settings_suggest';
      case 'key': return 'vpn_key';
      case 'document': return 'description';
      default: return 'draft';
    }
  };

  const formatBytes = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 h-full w-full bg-background overflow-y-auto custom-scrollbar p-4 md:p-6 space-y-6 pb-32">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-outline-variant shrink-0">
        <div>
          <div className="flex items-center space-x-3 mb-1">
            <h1 className="text-headline-lg font-headline-lg font-bold text-on-surface">
              Cryptographic Subsystem &amp; Decryption
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-label-mono-sm bg-primary/10 text-primary border border-primary/30 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
              HARDWARE ENCLAVE ACTIVE
            </span>
          </div>
          <p className="text-body-sm text-on-surface-variant">
            Forensic file identification across uploaded exhibits: resolve encrypted containers and inspect directly accessible artifacts for case{' '}
            <span className="font-semibold text-on-surface">{activeCase?.caseNumber || 'N/A'}</span>.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={() => loadInventory(false)}
            disabled={loading || refreshing}
            className="btn-secondary text-xs flex items-center gap-1.5"
            title="Reload evidence inventory"
          >
            <span className={`material-symbols-outlined text-sm ${refreshing ? 'animate-spin' : ''}`}>
              refresh
            </span>
            <span>{refreshing ? 'Refreshing...' : 'Refresh Inventory'}</span>
          </button>
        </div>
      </div>

      {/* KPI Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 shrink-0">
        <div className="p-3.5 bg-surface-container border border-outline-variant rounded-lg">
          <div className="text-[11px] uppercase tracking-wider text-on-surface-variant font-medium">Total Identified</div>
          <div className="text-2xl font-bold font-mono text-on-surface mt-1">{stats.total_identified_files}</div>
          <div className="text-[11px] text-outline mt-0.5">Across evidence exhibits</div>
        </div>

        <div className="p-3.5 bg-surface-container border border-amber-500/30 rounded-lg">
          <div className="text-[11px] uppercase tracking-wider text-amber-400 font-medium flex items-center gap-1">
            <span className="material-symbols-outlined text-xs">lock</span>
            <span>Encrypted Files</span>
          </div>
          <div className="text-2xl font-bold font-mono text-amber-300 mt-1">{stats.encrypted_count}</div>
          <div className="text-[11px] text-on-surface-variant mt-0.5">Awaiting key or pipeline</div>
        </div>

        <div className="p-3.5 bg-surface-container border border-tertiary/30 rounded-lg">
          <div className="text-[11px] uppercase tracking-wider text-tertiary font-medium flex items-center gap-1">
            <span className="material-symbols-outlined text-xs">lock_open</span>
            <span>Directly Usable</span>
          </div>
          <div className="text-2xl font-bold font-mono text-tertiary mt-1">{stats.directly_usable_count}</div>
          <div className="text-[11px] text-on-surface-variant mt-0.5">Plaintext &amp; derived files</div>
        </div>

        <div className="p-3.5 bg-surface-container border border-primary/30 rounded-lg">
          <div className="text-[11px] uppercase tracking-wider text-primary font-medium flex items-center gap-1">
            <span className="material-symbols-outlined text-xs">vpn_key</span>
            <span>Discovered Keys</span>
          </div>
          <div className="text-2xl font-bold font-mono text-primary mt-1">{stats.discovered_keys_count}</div>
          <div className="text-[11px] text-on-surface-variant mt-0.5">Detected in exhibits</div>
        </div>

        <div className="p-3.5 bg-surface-container border border-outline-variant rounded-lg">
          <div className="text-[11px] uppercase tracking-wider text-on-surface-variant font-medium">Decrypted Derived</div>
          <div className="text-2xl font-bold font-mono text-on-surface mt-1">{stats.decrypted_count}</div>
          <div className="text-[11px] text-outline mt-0.5">PostgreSQL BYTEA staged</div>
        </div>
      </div>

      {/* Feedback Banner */}
      {feedback && (
        <div className={`p-3.5 rounded-lg text-xs font-mono flex items-center justify-between border shrink-0 ${
          feedback.type === 'error'
            ? 'bg-error/15 border-error/40 text-error'
            : feedback.type === 'info'
              ? 'bg-primary/15 border-primary/40 text-primary'
              : 'bg-tertiary/15 border-tertiary/40 text-tertiary'
        }`}>
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-base">
              {feedback.type === 'error' ? 'error' : feedback.type === 'info' ? 'info' : 'check_circle'}
            </span>
            <span>{feedback.message}</span>
          </div>
          <button
            type="button"
            onClick={() => setFeedback(null)}
            className="text-on-surface-variant hover:text-on-surface"
          >
            ✕
          </button>
        </div>
      )}

      {/* SECTION 0: DISCOVERED KEYS BANNER (If available in evidence) */}
      {inventory?.discovered_keys && inventory.discovered_keys.length > 0 && (
        <div className="p-4 bg-primary/5 border border-primary/20 rounded-lg space-y-3 shrink-0">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-xl">vpn_key</span>
              <div>
                <h3 className="font-semibold text-sm text-on-surface">
                  Candidate Keys Detected in Evidence Files ({inventory.discovered_keys.length})
                </h3>
                <p className="text-xs text-on-surface-variant">
                  ArtifactX automatically parsed potential decryption key materials discovered directly in uploaded exhibits.
                </p>
              </div>
            </div>

            {stats.encrypted_count > 0 && (
              <button
                type="button"
                onClick={handleAutofillAll}
                className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5 self-start sm:self-auto border-primary/30 text-primary hover:bg-primary/10"
              >
                <span className="material-symbols-outlined text-sm">auto_fix_high</span>
                <span>Autofill All Matching Keys</span>
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5 pt-1">
            {inventory.discovered_keys.map((dk) => (
              <div
                key={dk.key_file_id}
                className="p-3 bg-surface-container border border-outline-variant rounded-md flex flex-col justify-between text-xs space-y-2"
              >
                <div className="flex items-center justify-between gap-1">
                  <span className="font-semibold text-on-surface font-mono truncate">{dk.filename}</span>
                  <span className="px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 text-[10px] font-mono">
                    {dk.key_type}
                  </span>
                </div>
                <div className="text-[11px] text-outline truncate" title={dk.relative_path}>
                  From: {dk.source_container}
                </div>
                <div className="flex items-center justify-between gap-2 pt-1 border-t border-outline-variant/60 font-mono text-[10px]">
                  <span className="text-on-surface-variant truncate">
                    Hex: {dk.preview_hex.substring(0, 18)}...
                  </span>
                  <button
                    type="button"
                    onClick={() => handleCopyHash(dk.autofill_value)}
                    className="text-primary hover:underline flex items-center gap-0.5 shrink-0"
                    title="Copy full key hex"
                  >
                    <span className="material-symbols-outlined text-xs">
                      {copiedHash === dk.autofill_value ? 'done' : 'content_copy'}
                    </span>
                    <span>{copiedHash === dk.autofill_value ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SECTION 1: ENCRYPTED FILES (Requiring Decryption) */}
      <div className="bg-surface-container border border-amber-500/30 rounded-lg overflow-hidden shadow-xs shrink-0">
        <div className="p-4 border-b border-outline-variant bg-surface-container-high/30 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center space-x-2.5">
            <span className="p-1.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center justify-center">
              <span className="material-symbols-outlined text-lg">lock</span>
            </span>
            <div>
              <h2 className="font-headline-sm text-on-surface font-bold text-base flex items-center gap-2">
                <span>Encrypted Files</span>
                <span className="px-2 py-0.2 rounded-full text-xs font-mono bg-amber-500/15 text-amber-300 border border-amber-500/30">
                  {inventory?.encrypted_files?.length || 0}
                </span>
              </h2>
              <p className="text-xs text-on-surface-variant">
                Files identified with encryption headers. Use an autofilled key found in evidence or enter a manual key to execute in-memory decryption.
              </p>
            </div>
          </div>
        </div>

        {loading && (
          <div className="p-12 text-center text-on-surface-variant">
            <span className="material-symbols-outlined text-3xl animate-spin text-primary mb-2">sync</span>
            <p className="font-medium text-sm">Inspecting cryptographic containers &amp; candidate keys...</p>
          </div>
        )}

        {!loading && (!inventory?.encrypted_files || inventory.encrypted_files.length === 0) && (
          <div className="p-8 text-center text-on-surface-variant">
            <span className="material-symbols-outlined text-3xl text-outline mb-1">lock_open</span>
            <p className="font-semibold text-on-surface text-sm">No Encrypted Files Found</p>
            <p className="text-xs text-outline mt-0.5">All identified files in this case are directly usable in plaintext.</p>
          </div>
        )}

        {!loading && inventory?.encrypted_files && inventory.encrypted_files.length > 0 && (
          <div className="divide-y divide-outline-variant">
            {inventory.encrypted_files.map((file) => {
              const currentInput = keyInputs[file.id] || '';
              const isDecrypting = decryptingId === file.id;
              const isDecrypted = file.status === 'DECRYPTED';

              return (
                <div
                  key={file.id}
                  className={`p-4 md:p-5 transition-colors space-y-4 ${
                    isDecrypted ? 'bg-tertiary/5' : 'hover:bg-surface-container-high/30'
                  }`}
                >
                  {/* File Metadata Bar */}
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-sm text-on-surface font-mono">{file.filename}</span>
                        <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-amber-500/10 text-amber-300 border border-amber-500/20">
                          {file.format_name}
                        </span>
                        {isDecrypted && (
                          <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-tertiary/10 text-tertiary border border-tertiary/30 flex items-center gap-1">
                            <span className="material-symbols-outlined text-xs">check_circle</span>
                            <span>Decrypted (Derived Exhibit Staged)</span>
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-on-surface-variant flex flex-wrap items-center gap-x-3 gap-y-1 font-mono">
                        <span>Path: {file.relative_path}</span>
                        <span>•</span>
                        <span>Container: {file.source_container}</span>
                        <span>•</span>
                        <span>Size: {formatBytes(file.size_bytes)}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        type="button"
                        onClick={() => handleCopyHash(file.sha256)}
                        className="px-2.5 py-1.5 rounded bg-surface-container-lowest border border-outline-variant text-[11px] font-mono text-on-surface-variant hover:text-on-surface flex items-center gap-1"
                        title="Copy SHA-256 Digest"
                      >
                        <span className="material-symbols-outlined text-xs">
                          {copiedHash === file.sha256 ? 'done' : 'fingerprint'}
                        </span>
                        <span>{file.sha256 ? `${file.sha256.substring(0, 12)}...` : 'No hash'}</span>
                      </button>

                      {/* Modal Open Button */}
                      <button
                        type="button"
                        onClick={() => setSelectedEncryptedFile(file)}
                        className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1 border-primary/30 text-primary hover:bg-primary/10"
                        title="Open spacious decryption modal"
                      >
                        <span className="material-symbols-outlined text-sm">open_in_full</span>
                        <span>Configure Key &amp; Decrypt</span>
                      </button>
                    </div>
                  </div>

                  {/* Inline Key Configuration Bar (Spacious & Responsive) */}
                  <div className="pt-3 border-t border-outline-variant/60 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
                    <div className="flex-1 space-y-2">
                      {/* Autofill option chip */}
                      {file.autofill_key && (
                        <div className="flex flex-wrap items-center gap-2 text-xs">
                          <span className="text-on-surface-variant font-medium">Discovered Key Available:</span>
                          <button
                            type="button"
                            onClick={() => handleAutofillKey(file, file.autofill_key)}
                            className="px-2.5 py-1 rounded bg-primary/15 text-primary border border-primary/30 hover:bg-primary/25 font-mono text-[11px] flex items-center gap-1.5 transition-all"
                            title="Click to autofill this key material"
                          >
                            <span className="material-symbols-outlined text-xs">auto_fix_high</span>
                            <span>Autofill {file.autofill_key.filename} ({file.autofill_key.key_type})</span>
                          </button>
                          {keySources[file.id] === 'autofill' && (
                            <span className="text-[11px] text-tertiary flex items-center gap-1 font-mono">
                              <span className="material-symbols-outlined text-xs">verified</span>
                              Key Autofilled
                            </span>
                          )}
                        </div>
                      )}

                      {/* Input controls */}
                      <div className="flex items-center gap-2 max-w-3xl">
                        <div className="relative flex-1">
                          <input
                            type="text"
                            placeholder="Enter 64-char hex key (AES-256), base64 keyfile, or click autofill..."
                            value={currentInput}
                            onChange={(e) => {
                              const val = e.target.value;
                              setKeyInputs(prev => ({ ...prev, [file.id]: val }));
                              setKeySources(prev => ({ ...prev, [file.id]: 'manual' }));
                            }}
                            className="w-full bg-surface-container-lowest border border-outline-variant rounded px-3 py-2 text-xs font-mono text-on-surface placeholder:text-outline focus:outline-none focus:border-primary"
                          />
                          {currentInput && (
                            <button
                              type="button"
                              onClick={() => {
                                setKeyInputs(prev => ({ ...prev, [file.id]: '' }));
                                setKeyFileIds(prev => ({ ...prev, [file.id]: null }));
                                setKeySources(prev => ({ ...prev, [file.id]: null }));
                              }}
                              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-outline hover:text-on-surface text-xs"
                              title="Clear key"
                            >
                              ✕
                            </button>
                          )}
                        </div>
                        <button
                          type="button"
                          onClick={() => handlePasteKey(file.id)}
                          className="px-2.5 py-2 rounded bg-surface-container border border-outline-variant hover:bg-surface-container-highest text-on-surface-variant hover:text-on-surface text-xs font-mono shrink-0 flex items-center gap-1"
                          title="Paste from clipboard"
                        >
                          <span className="material-symbols-outlined text-sm">content_paste</span>
                          <span>Paste</span>
                        </button>
                      </div>
                    </div>

                    {/* Inline Decrypt Button */}
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        type="button"
                        onClick={() => handleExecuteDecryption(file)}
                        disabled={isDecrypting || !currentInput}
                        className={`btn-primary text-xs px-4 py-2 flex items-center gap-1.5 ${
                          isDecrypted ? 'bg-tertiary text-on-tertiary hover:bg-tertiary/90' : ''
                        }`}
                      >
                        <span className={`material-symbols-outlined text-sm ${isDecrypting ? 'animate-spin' : ''}`}>
                          {isDecrypting ? 'sync' : isDecrypted ? 'refresh' : 'lock_open'}
                        </span>
                        <span>
                          {isDecrypting
                            ? 'Decrypting...'
                            : isDecrypted
                              ? 'Re-Decrypt File'
                              : 'Decrypt File'}
                        </span>
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* SECTION 2: DIRECTLY USABLE FILES */}
      <div className="bg-surface-container border border-outline-variant rounded-lg overflow-hidden shadow-xs shrink-0">
        {/* Usable Section Header */}
        <div className="p-4 border-b border-outline-variant bg-surface-container-high/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-2.5">
            <span className="p-1.5 rounded bg-tertiary/10 text-tertiary border border-tertiary/20 flex items-center justify-center">
              <span className="material-symbols-outlined text-lg">folder_open</span>
            </span>
            <div>
              <h2 className="font-headline-sm text-on-surface font-bold text-base flex items-center gap-2">
                <span>Directly Usable &amp; Decrypted Files</span>
                <span className="px-2 py-0.2 rounded-full text-xs font-mono bg-tertiary/15 text-tertiary border border-tertiary/30">
                  {inventory?.directly_usable_files?.length || 0}
                </span>
              </h2>
              <p className="text-xs text-on-surface-variant">
                Plaintext SQLite databases, derived exhibits, media assets, XML configurations, and logs available without decryption.
              </p>
            </div>
          </div>

          {/* Search Box */}
          <div className="relative w-full sm:w-72">
            <span className="material-symbols-outlined absolute left-2.5 top-1/2 -translate-y-1/2 text-outline text-sm">
              search
            </span>
            <input
              type="text"
              placeholder="Search filename or path..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-surface-container-lowest border border-outline-variant rounded pl-8 pr-3 py-1.5 text-xs text-on-surface placeholder:text-outline focus:outline-none focus:border-primary"
            />
          </div>
        </div>

        {/* Filter Category Chips */}
        <div className="p-3 border-b border-outline-variant/60 bg-surface-container-lowest/50 flex flex-wrap items-center gap-1.5 text-xs">
          <span className="text-outline text-[11px] uppercase tracking-wider mr-1">Filter:</span>

          <button
            type="button"
            onClick={() => setUsableCategory('all')}
            className={`px-2.5 py-1 rounded-md transition-colors ${
              usableCategory === 'all'
                ? 'bg-primary text-on-primary font-semibold'
                : 'bg-surface-container text-on-surface-variant hover:text-on-surface'
            }`}
          >
            All Files ({inventory?.directly_usable_files?.length || 0})
          </button>

          <button
            type="button"
            onClick={() => setUsableCategory('database')}
            className={`px-2.5 py-1 rounded-md transition-colors flex items-center gap-1 ${
              usableCategory === 'database'
                ? 'bg-primary text-on-primary font-semibold'
                : 'bg-surface-container text-on-surface-variant hover:text-on-surface'
            }`}
          >
            <span className="material-symbols-outlined text-xs">database</span>
            <span>Databases</span>
          </button>

          <button
            type="button"
            onClick={() => setUsableCategory('derived')}
            className={`px-2.5 py-1 rounded-md transition-colors flex items-center gap-1 ${
              usableCategory === 'derived'
                ? 'bg-primary text-on-primary font-semibold'
                : 'bg-surface-container text-on-surface-variant hover:text-on-surface'
            }`}
          >
            <span className="material-symbols-outlined text-xs">lock_open</span>
            <span>Decrypted Exhibits ({inventory?.directly_usable_files?.filter(f => f.is_derived).length || 0})</span>
          </button>

          <button
            type="button"
            onClick={() => setUsableCategory('media')}
            className={`px-2.5 py-1 rounded-md transition-colors flex items-center gap-1 ${
              usableCategory === 'media'
                ? 'bg-primary text-on-primary font-semibold'
                : 'bg-surface-container text-on-surface-variant hover:text-on-surface'
            }`}
          >
            <span className="material-symbols-outlined text-xs">image</span>
            <span>Media</span>
          </button>

          <button
            type="button"
            onClick={() => setUsableCategory('config')}
            className={`px-2.5 py-1 rounded-md transition-colors flex items-center gap-1 ${
              usableCategory === 'config'
                ? 'bg-primary text-on-primary font-semibold'
                : 'bg-surface-container text-on-surface-variant hover:text-on-surface'
            }`}
          >
            <span className="material-symbols-outlined text-xs">settings_suggest</span>
            <span>Configs &amp; Logs</span>
          </button>

          <button
            type="button"
            onClick={() => setUsableCategory('key')}
            className={`px-2.5 py-1 rounded-md transition-colors flex items-center gap-1 ${
              usableCategory === 'key'
                ? 'bg-primary text-on-primary font-semibold'
                : 'bg-surface-container text-on-surface-variant hover:text-on-surface'
            }`}
          >
            <span className="material-symbols-outlined text-xs">vpn_key</span>
            <span>Keys</span>
          </button>
        </div>

        {/* Usable Files Table */}
        <div className="overflow-x-auto custom-scrollbar">
          <table className="w-full text-left border-collapse text-body-sm">
            <thead className="bg-surface-container-high border-b border-outline-variant">
              <tr className="h-8 text-label-ui uppercase tracking-wider text-[11px] text-on-surface-variant">
                <th className="py-2.5 px-3">File / Artifact</th>
                <th className="py-2.5 px-3">Category</th>
                <th className="py-2.5 px-3">Origin / Container</th>
                <th className="py-2.5 px-3">Size &amp; Tables</th>
                <th className="py-2.5 px-3">SHA-256 Digest</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/60 font-mono text-xs">
              {loading && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-on-surface-variant">
                    <span className="material-symbols-outlined text-2xl animate-spin text-primary mb-1">sync</span>
                    <p>Loading files inventory...</p>
                  </td>
                </tr>
              )}

              {!loading && filteredUsableFiles.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-10 text-center text-on-surface-variant">
                    <span className="material-symbols-outlined text-3xl text-outline mb-1">find_in_page</span>
                    <p className="font-semibold text-on-surface text-sm">No Files Match Your Filter</p>
                    <p className="text-xs text-outline mt-0.5">Try clearing the search query or selecting a different category.</p>
                  </td>
                </tr>
              )}

              {!loading && filteredUsableFiles.map((item) => (
                <tr key={item.id} className="hover:bg-surface-container-high/40 transition-colors">
                  {/* File Name & Path */}
                  <td className="py-3 px-3 max-w-sm">
                    <div className="flex items-center space-x-2.5">
                      <span className={`material-symbols-outlined text-lg ${
                        item.is_derived ? 'text-tertiary' : 'text-primary'
                      }`}>
                        {getCategoryIcon(item.category, item.is_derived)}
                      </span>
                      <div className="truncate">
                        <div className="font-semibold text-on-surface font-sans text-xs truncate" title={item.filename}>
                          {item.filename}
                        </div>
                        <div className="text-[10px] text-outline font-mono truncate" title={item.relative_path}>
                          {item.relative_path}
                        </div>
                      </div>
                    </div>
                  </td>

                  {/* Category */}
                  <td className="py-3 px-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                      item.is_derived
                        ? 'bg-tertiary/15 text-tertiary border border-tertiary/30'
                        : item.category === 'database'
                          ? 'bg-primary/10 text-primary border border-primary/20'
                          : item.category === 'media'
                            ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                            : item.category === 'key'
                              ? 'bg-amber-500/10 text-amber-300 border border-amber-500/20'
                              : 'bg-surface-container-highest text-on-surface-variant'
                    }`}>
                      {item.is_derived ? 'Decrypted DB' : item.category}
                    </span>
                  </td>

                  {/* Origin */}
                  <td className="py-3 px-3 text-on-surface-variant text-[11px] truncate max-w-[200px]" title={item.source_container}>
                    {item.source_container}
                  </td>

                  {/* Size & Tables */}
                  <td className="py-3 px-3">
                    <div className="text-on-surface text-xs font-mono">{formatBytes(item.size_bytes)}</div>
                    {item.table_count ? (
                      <div className="text-[10px] text-tertiary font-mono flex items-center gap-1">
                        <span>{item.table_count} tables</span>
                      </div>
                    ) : (
                      <div className="text-[10px] text-outline">Plaintext file</div>
                    )}
                  </td>

                  {/* SHA-256 */}
                  <td className="py-3 px-3">
                    <button
                      type="button"
                      onClick={() => handleCopyHash(item.sha256)}
                      className="px-2 py-1 rounded bg-surface-container-lowest border border-outline-variant text-[10px] text-on-surface-variant hover:text-on-surface flex items-center gap-1"
                      title="Click to copy full SHA-256"
                    >
                      <span className="material-symbols-outlined text-xs">
                        {copiedHash === item.sha256 ? 'done' : 'content_copy'}
                      </span>
                      <span>{item.sha256 ? `${item.sha256.substring(0, 10)}...` : 'N/A'}</span>
                    </button>
                  </td>

                  {/* Action */}
                  <td className="py-3 px-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => setInspectModalFile(item)}
                        className="px-2.5 py-1.5 rounded bg-surface-container border border-outline-variant hover:bg-surface-container-highest text-[11px] font-sans text-on-surface flex items-center gap-1"
                        title="Inspect file details"
                      >
                        <span className="material-symbols-outlined text-xs">info</span>
                        <span>Details</span>
                      </button>

                      {item.category === 'database' && (
                        <Link
                          to={`/cases/${caseId}/messages`}
                          className="px-2.5 py-1.5 rounded bg-primary/10 border border-primary/30 text-primary hover:bg-primary/20 text-[11px] font-sans font-medium flex items-center gap-1"
                          title="Open database records"
                        >
                          <span className="material-symbols-outlined text-xs">open_in_new</span>
                          <span>Parse</span>
                        </Link>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ================= SPACIOUS, UNSQUEEZED ENCRYPTED FILE DECRYPTION MODAL ================= */}
      {selectedEncryptedFile && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in">
          <div className="bg-surface-container border border-outline-variant rounded-xl max-w-3xl lg:max-w-4xl w-full p-6 space-y-6 shadow-2xl max-h-[90vh] overflow-y-auto custom-scrollbar">
            {/* Modal Header */}
            <div className="flex items-start justify-between pb-4 border-b border-outline-variant">
              <div className="flex items-center gap-3">
                <span className="p-2.5 rounded-lg bg-amber-500/15 text-amber-400 border border-amber-500/30 flex items-center justify-center">
                  <span className="material-symbols-outlined text-2xl">lock</span>
                </span>
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-headline-sm font-headline-sm font-bold text-on-surface font-mono">
                      {selectedEncryptedFile.filename}
                    </h2>
                    <span className="px-2.5 py-0.5 rounded text-xs font-mono bg-amber-500/10 text-amber-300 border border-amber-500/30">
                      {selectedEncryptedFile.format_name}
                    </span>
                    {selectedEncryptedFile.status === 'DECRYPTED' && (
                      <span className="px-2 py-0.5 rounded text-xs font-semibold bg-tertiary/15 text-tertiary border border-tertiary/30 flex items-center gap-1">
                        <span className="material-symbols-outlined text-xs">check_circle</span>
                        <span>Decrypted</span>
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-on-surface-variant mt-0.5">
                    Hardware-isolated in-memory cryptographic decryption with zero disk writes (master.md R4, R5).
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={() => setSelectedEncryptedFile(null)}
                className="p-1.5 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors"
                title="Close modal"
              >
                <span className="material-symbols-outlined text-lg">close</span>
              </button>
            </div>

            {/* Container & Hash Information Card */}
            <div className="p-4 bg-surface-container-lowest border border-outline-variant rounded-lg space-y-3">
              <div className="text-label-ui uppercase tracking-wider text-on-surface-variant font-semibold text-[11px]">
                Target Container Forensic Parameters
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 text-xs font-mono">
                <div className="p-2 rounded bg-surface-container/60 border border-outline-variant/60">
                  <div className="text-[10px] text-outline uppercase">Relative Path</div>
                  <div className="font-semibold text-on-surface break-all mt-0.5" title={selectedEncryptedFile.relative_path}>
                    {selectedEncryptedFile.relative_path}
                  </div>
                </div>

                <div className="p-2 rounded bg-surface-container/60 border border-outline-variant/60">
                  <div className="text-[10px] text-outline uppercase">Origin Container</div>
                  <div className="font-semibold text-on-surface truncate mt-0.5" title={selectedEncryptedFile.source_container}>
                    {selectedEncryptedFile.source_container}
                  </div>
                </div>

                <div className="p-2 rounded bg-surface-container/60 border border-outline-variant/60">
                  <div className="text-[10px] text-outline uppercase">File Size</div>
                  <div className="font-semibold text-on-surface mt-0.5">
                    {formatBytes(selectedEncryptedFile.size_bytes)} ({selectedEncryptedFile.size_bytes} B)
                  </div>
                </div>

                <div className="p-2 rounded bg-surface-container/60 border border-outline-variant/60">
                  <div className="text-[10px] text-outline uppercase">Decryption Cipher</div>
                  <div className="font-semibold text-amber-300 mt-0.5">
                    {selectedEncryptedFile.detected_format.toUpperCase()}
                  </div>
                </div>
              </div>

              {/* SHA-256 Digest */}
              <div className="p-2.5 rounded bg-surface-container/60 border border-outline-variant/60 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs font-mono">
                <div className="truncate">
                  <span className="text-[10px] text-outline uppercase block">SHA-256 Cryptographic Digest:</span>
                  <span className="text-on-surface break-all">{selectedEncryptedFile.sha256}</span>
                </div>
                <button
                  type="button"
                  onClick={() => handleCopyHash(selectedEncryptedFile.sha256)}
                  className="btn-secondary text-[11px] px-2.5 py-1 shrink-0 self-start sm:self-auto flex items-center gap-1"
                >
                  <span className="material-symbols-outlined text-xs">
                    {copiedHash === selectedEncryptedFile.sha256 ? 'done' : 'content_copy'}
                  </span>
                  <span>{copiedHash === selectedEncryptedFile.sha256 ? 'Copied' : 'Copy Hash'}</span>
                </button>
              </div>
            </div>

            {/* Candidate Keys Found in Evidence (Option A) */}
            {selectedEncryptedFile.candidate_keys && selectedEncryptedFile.candidate_keys.length > 0 && (
              <div className="p-4 bg-primary/5 border border-primary/25 rounded-lg space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-primary text-base">vpn_key</span>
                    <span className="text-label-ui uppercase tracking-wider text-primary font-semibold text-xs">
                      Option A: Candidate Keys Discovered in Evidence ({selectedEncryptedFile.candidate_keys.length})
                    </span>
                  </div>
                  <span className="text-[11px] text-on-surface-variant font-mono">Automatic evidence linkage</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {selectedEncryptedFile.candidate_keys.map((ck) => {
                    const isSelected = keyInputs[selectedEncryptedFile.id] === ck.autofill_value;

                    return (
                      <div
                        key={ck.key_file_id}
                        className={`p-3.5 rounded-lg border transition-all text-xs space-y-2 ${
                          isSelected
                            ? 'bg-primary/15 border-primary shadow-xs'
                            : 'bg-surface-container border-outline-variant hover:border-primary/50'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-semibold text-on-surface font-mono truncate">{ck.filename}</span>
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-primary/20 text-primary border border-primary/30">
                            {ck.key_type}
                          </span>
                        </div>

                        <div className="text-[11px] text-outline font-mono truncate" title={ck.relative_path}>
                          Path: {ck.relative_path} ({ck.size_bytes} bytes)
                        </div>

                        <div className="pt-1.5 border-t border-outline-variant/60 flex items-center justify-between gap-2 font-mono text-[10px]">
                          <span className="text-on-surface-variant truncate">
                            Preview: {ck.preview_hex.substring(0, 16)}...
                          </span>

                          <button
                            type="button"
                            onClick={() => handleAutofillKey(selectedEncryptedFile, ck)}
                            className={`px-3 py-1 rounded text-xs font-sans font-medium flex items-center gap-1 transition-colors ${
                              isSelected
                                ? 'bg-primary text-on-primary font-semibold'
                                : 'btn-secondary text-primary border-primary/30 hover:bg-primary/10'
                            }`}
                          >
                            <span className="material-symbols-outlined text-xs">
                              {isSelected ? 'check' : 'auto_fix_high'}
                            </span>
                            <span>{isSelected ? 'Autofilled' : 'Autofill This Key'}</span>
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Manual Key Entry Section (Option B) */}
            <div className="p-4 bg-surface-container-lowest border border-outline-variant rounded-lg space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-on-surface-variant text-base">edit_note</span>
                  <span className="text-label-ui uppercase tracking-wider text-on-surface font-semibold text-xs">
                    Option B: Manual Cryptographic Key Input
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handlePasteKey(selectedEncryptedFile.id)}
                    className="btn-secondary text-xs px-2.5 py-1 flex items-center gap-1 font-mono"
                    title="Paste from clipboard"
                  >
                    <span className="material-symbols-outlined text-xs">content_paste</span>
                    <span>Paste</span>
                  </button>
                  {keyInputs[selectedEncryptedFile.id] && (
                    <button
                      type="button"
                      onClick={() => {
                        setKeyInputs(prev => ({ ...prev, [selectedEncryptedFile.id]: '' }));
                        setKeyFileIds(prev => ({ ...prev, [selectedEncryptedFile.id]: null }));
                        setKeySources(prev => ({ ...prev, [selectedEncryptedFile.id]: null }));
                      }}
                      className="text-xs text-outline hover:text-on-surface px-1.5 py-1"
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>

              <div className="space-y-1.5">
                <textarea
                  rows={3}
                  placeholder="Enter 64-character hexadecimal key (AES-256), Base64-encoded keyfile, or raw secret..."
                  value={keyInputs[selectedEncryptedFile.id] || ''}
                  onChange={(e) => {
                    const val = e.target.value;
                    setKeyInputs(prev => ({ ...prev, [selectedEncryptedFile.id]: val }));
                    setKeySources(prev => ({ ...prev, [selectedEncryptedFile.id]: 'manual' }));
                  }}
                  className="w-full bg-surface-container border border-outline-variant rounded-lg p-3 text-xs font-mono text-on-surface placeholder:text-outline focus:outline-none focus:border-primary resize-y"
                />

                <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-outline font-mono">
                  <span>Supported formats: 64-Hex Root Key | Java-Serialized 59-byte Base64 | 158-byte Crypt14</span>
                  {keySources[selectedEncryptedFile.id] && (
                    <span className="text-tertiary font-semibold">
                      Source: {keySources[selectedEncryptedFile.id] === 'autofill' ? 'Autofilled from Evidence' : 'Manual Entry'}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Modal Actions Footer */}
            <div className="pt-4 border-t border-outline-variant flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="text-xs text-on-surface-variant font-mono">
                Enclave status: <span className="text-tertiary font-semibold">READY</span> · FIPS-140-3 Mode
              </div>

              <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
                <button
                  type="button"
                  onClick={() => setSelectedEncryptedFile(null)}
                  className="btn-secondary text-xs px-4 py-2"
                >
                  Cancel
                </button>

                <button
                  type="button"
                  onClick={async () => {
                    await handleExecuteDecryption(selectedEncryptedFile);
                  }}
                  disabled={decryptingId === selectedEncryptedFile.id || !keyInputs[selectedEncryptedFile.id]}
                  className="btn-primary text-xs px-6 py-2 flex items-center gap-2"
                >
                  <span className={`material-symbols-outlined text-sm ${decryptingId === selectedEncryptedFile.id ? 'animate-spin' : ''}`}>
                    {decryptingId === selectedEncryptedFile.id ? 'sync' : 'lock_open'}
                  </span>
                  <span>
                    {decryptingId === selectedEncryptedFile.id
                      ? 'Executing In-Memory Decryption...'
                      : selectedEncryptedFile.status === 'DECRYPTED'
                        ? 'Re-Execute Decryption'
                        : 'Decrypt File Now'}
                  </span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ================= SPACIOUS FILE DETAILS INSPECT MODAL ================= */}
      {inspectModalFile && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in">
          <div className="bg-surface-container border border-outline-variant rounded-xl max-w-3xl w-full p-6 space-y-5 shadow-2xl max-h-[85vh] overflow-y-auto custom-scrollbar">
            <div className="flex items-center justify-between pb-3 border-b border-outline-variant">
              <div className="flex items-center gap-2.5">
                <span className="p-2 rounded bg-surface-container-high text-primary flex items-center justify-center">
                  <span className="material-symbols-outlined text-xl">
                    {getCategoryIcon(inspectModalFile.category, inspectModalFile.is_derived)}
                  </span>
                </span>
                <div>
                  <h3 className="font-semibold text-base text-on-surface truncate">
                    {inspectModalFile.filename}
                  </h3>
                  <span className="text-[11px] text-on-surface-variant font-mono">
                    {inspectModalFile.is_derived ? 'Decrypted Derived Exhibit' : 'Plaintext Evidence Member'}
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setInspectModalFile(null)}
                className="p-1.5 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors"
              >
                <span className="material-symbols-outlined text-lg">close</span>
              </button>
            </div>

            <div className="space-y-4 text-xs font-mono">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-3.5 bg-surface-container-lowest rounded-lg border border-outline-variant">
                <div>
                  <span className="text-[10px] text-outline uppercase block">Forensic Status:</span>
                  <span className="font-semibold text-tertiary text-xs">{inspectModalFile.status}</span>
                </div>

                <div>
                  <span className="text-[10px] text-outline uppercase block">Origin Container:</span>
                  <span className="text-on-surface text-xs truncate block">{inspectModalFile.source_container}</span>
                </div>

                <div className="md:col-span-2">
                  <span className="text-[10px] text-outline uppercase block">Relative Archive Path:</span>
                  <span className="break-all text-on-surface text-xs">{inspectModalFile.relative_path}</span>
                </div>

                <div>
                  <span className="text-[10px] text-outline uppercase block">Size:</span>
                  <span className="text-on-surface text-xs">{formatBytes(inspectModalFile.size_bytes)} ({inspectModalFile.size_bytes} bytes)</span>
                </div>

                <div>
                  <span className="text-[10px] text-outline uppercase block">MIME Type:</span>
                  <span className="text-on-surface text-xs">{inspectModalFile.mime_type || 'application/octet-stream'}</span>
                </div>

                <div className="md:col-span-2">
                  <span className="text-[10px] text-outline uppercase block">SHA-256 Digest:</span>
                  <span className="break-all text-on-surface text-xs">{inspectModalFile.sha256}</span>
                </div>
              </div>

              {/* Tables Preview for SQLite Databases */}
              {inspectModalFile.tables && inspectModalFile.tables.length > 0 && (
                <div className="space-y-2 pt-1">
                  <div className="font-sans font-semibold text-on-surface text-xs flex items-center justify-between">
                    <span>Identified SQLite Database Tables ({inspectModalFile.table_count || inspectModalFile.tables.length})</span>
                    <span className="text-[11px] text-tertiary font-mono">Zero-disk in-memory verification</span>
                  </div>
                  <div className="flex flex-wrap gap-2 p-3 bg-surface-container-lowest rounded-lg border border-outline-variant max-h-48 overflow-y-auto custom-scrollbar">
                    {inspectModalFile.tables.map((t) => (
                      <span key={t} className="px-2.5 py-1 rounded bg-surface-container-high text-on-surface border border-outline-variant text-xs">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-outline-variant flex items-center justify-between">
              {inspectModalFile.category === 'database' ? (
                <Link
                  to={`/cases/${caseId}/messages`}
                  className="btn-primary text-xs px-4 py-1.5 flex items-center gap-1.5"
                >
                  <span className="material-symbols-outlined text-sm">open_in_new</span>
                  <span>Open Database Records</span>
                </Link>
              ) : <div />}

              <button
                type="button"
                onClick={() => setInspectModalFile(null)}
                className="btn-secondary text-xs px-4 py-1.5"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
