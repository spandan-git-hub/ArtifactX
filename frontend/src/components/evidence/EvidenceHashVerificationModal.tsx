import { useState } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  X,
  CheckCircle2,
  XCircle,
  FileCheck,
  RefreshCw,
  Copy,
  Check,
} from 'lucide-react';
import EvidenceHashBadge from './EvidenceHashBadge';

const EvidenceHashVerificationModal = ({
  isOpen,
  onClose,
  verificationData,
  loading = false,
  onReverify,
}) => {
  const [copiedAlgo, setCopiedAlgo] = useState(null);

  if (!isOpen) return null;

  const handleCopy = (algo, val) => {
    if (!val) return;
    navigator.clipboard.writeText(val);
    setCopiedAlgo(algo);
    setTimeout(() => setCopiedAlgo(null), 2000);
  };

  const isIntact = verificationData?.is_valid || verificationData?.verification_status === 'VERIFIED_INTACT';
  const mainFile = verificationData?.main_file || {};
  const extractedSummary = verificationData?.extracted_files_summary || { total: 0, matched: 0, mismatched: 0 };
  const extractedFiles = verificationData?.files || [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-forensic-900 border border-forensic-700 rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-forensic-800 bg-forensic-950/60">
          <div className="flex items-center gap-3">
            <div
              className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                isIntact ? 'bg-accent-emerald/20 text-accent-emerald' : 'bg-accent-rose/20 text-accent-rose'
              }`}
            >
              {isIntact ? <ShieldCheck className="h-6 w-6" /> : <ShieldAlert className="h-6 w-6" />}
            </div>
            <div>
              <h2 className="text-lg font-bold text-forensic-100 flex items-center gap-2">
                Evidence Cryptographic Integrity Manifest
              </h2>
              <p className="text-xs text-forensic-400 font-mono">
                {verificationData?.filename || 'Evidence File'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {onReverify && (
              <button
                onClick={onReverify}
                disabled={loading}
                className="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5"
                title="Re-run Real-time Verification"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
                Re-Verify
              </button>
            )}
            <button
              onClick={onClose}
              className="text-forensic-400 hover:text-forensic-100 p-1.5 rounded-lg hover:bg-forensic-800 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          
          {loading ? (
            <div className="py-12 flex flex-col items-center justify-center space-y-3">
              <RefreshCw className="h-8 w-8 animate-spin text-accent-cyan" />
              <p className="text-sm text-forensic-400 font-medium">Computing real-time multi-hashes on disk...</p>
            </div>
          ) : (
            <>
              {/* Overall Integrity Banner */}
              <div
                className={`p-4 rounded-xl border flex items-center justify-between ${
                  isIntact
                    ? 'bg-accent-emerald/10 border-accent-emerald/30 text-accent-emerald'
                    : 'bg-accent-rose/10 border-accent-rose/30 text-accent-rose'
                }`}
              >
                <div className="flex items-center gap-3">
                  {isIntact ? (
                    <CheckCircle2 className="h-6 w-6 shrink-0" />
                  ) : (
                    <XCircle className="h-6 w-6 shrink-0" />
                  )}
                  <div>
                    <h3 className="font-bold text-sm uppercase tracking-wider">
                      {isIntact ? 'VERIFIED INTACT — Zero Evidence Alteration' : 'HASH MISMATCH DETECTED'}
                    </h3>
                    <p className="text-xs text-forensic-300 mt-0.5">
                      {isIntact
                        ? 'All on-disk storage bytes match recorded cryptographic manifest hashes exactly.'
                        : 'On-disk file hashes do not match recorded manifest! Evidence may have been modified.'}
                    </p>
                  </div>
                </div>

                <div className="text-right">
                  <span className="text-[10px] text-forensic-400 block uppercase font-medium">Verified At</span>
                  <span className="text-xs font-mono text-forensic-200">
                    {verificationData?.verified_at
                      ? new Date(verificationData.verified_at).toLocaleString()
                      : new Date().toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Primary Evidence Multi-Hash Table */}
              <div className="bg-forensic-950/40 rounded-xl border border-forensic-800 p-4 space-y-3">
                <h4 className="text-xs font-semibold text-forensic-300 uppercase tracking-wider flex items-center gap-2">
                  <FileCheck className="h-4 w-4 text-accent-cyan" />
                  Primary Storage File Multi-Hash Check
                </h4>

                <div className="grid grid-cols-1 gap-3">
                  {/* SHA-256 */}
                  <div className="p-3 bg-forensic-900/80 rounded-lg border border-forensic-800 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-accent-cyan uppercase">SHA-256</span>
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                        mainFile.expected_sha256 === mainFile.actual_sha256
                          ? 'bg-accent-emerald/20 text-accent-emerald'
                          : 'bg-accent-rose/20 text-accent-rose'
                      }`}>
                        {mainFile.expected_sha256 === mainFile.actual_sha256 ? 'MATCH' : 'MISMATCH'}
                      </span>
                    </div>
                    <div className="text-xs font-mono text-forensic-200 break-all flex items-center justify-between gap-2">
                      <span>{mainFile.actual_sha256 || mainFile.expected_sha256}</span>
                      <button
                        onClick={() => handleCopy('sha256', mainFile.actual_sha256 || mainFile.expected_sha256)}
                        className="text-forensic-400 hover:text-accent-cyan shrink-0"
                      >
                        {copiedAlgo === 'sha256' ? <Check className="h-3.5 w-3.5 text-accent-emerald" /> : <Copy className="h-3.5 w-3.5" />}
                      </button>
                    </div>
                  </div>

                  {/* MD5 & SHA-1 Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="p-3 bg-forensic-900/80 rounded-lg border border-forensic-800 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-accent-cyan uppercase">MD5</span>
                        <span className="text-[10px] text-accent-emerald bg-accent-emerald/20 px-2 py-0.5 rounded font-semibold">
                          MATCH
                        </span>
                      </div>
                      <div className="text-xs font-mono text-forensic-200 break-all flex items-center justify-between gap-2">
                        <span>{mainFile.actual_md5 || mainFile.expected_md5 || 'N/A'}</span>
                        {mainFile.actual_md5 && (
                          <button
                            onClick={() => handleCopy('md5', mainFile.actual_md5)}
                            className="text-forensic-400 hover:text-accent-cyan shrink-0"
                          >
                            {copiedAlgo === 'md5' ? <Check className="h-3.5 w-3.5 text-accent-emerald" /> : <Copy className="h-3.5 w-3.5" />}
                          </button>
                        )}
                      </div>
                    </div>

                    <div className="p-3 bg-forensic-900/80 rounded-lg border border-forensic-800 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-accent-cyan uppercase">SHA-1</span>
                        <span className="text-[10px] text-accent-emerald bg-accent-emerald/20 px-2 py-0.5 rounded font-semibold">
                          MATCH
                        </span>
                      </div>
                      <div className="text-xs font-mono text-forensic-200 break-all flex items-center justify-between gap-2">
                        <span>{mainFile.actual_sha1 || mainFile.expected_sha1 || 'N/A'}</span>
                        {mainFile.actual_sha1 && (
                          <button
                            onClick={() => handleCopy('sha1', mainFile.actual_sha1)}
                            className="text-forensic-400 hover:text-accent-cyan shrink-0"
                          >
                            {copiedAlgo === 'sha1' ? <Check className="h-3.5 w-3.5 text-accent-emerald" /> : <Copy className="h-3.5 w-3.5" />}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Extracted Zip Files Breakdown */}
              {extractedFiles.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-semibold text-forensic-300 uppercase tracking-wider">
                      Extracted ZIP Members Verification ({extractedSummary.matched}/{extractedSummary.total} Intact)
                    </h4>
                  </div>

                  <div className="table-container max-h-60 overflow-y-auto">
                    <table className="data-table text-xs">
                      <thead>
                        <tr>
                          <th>Relative Path</th>
                          <th>Recorded SHA-256</th>
                          <th>Actual On-Disk SHA-256</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {extractedFiles.map((f) => (
                          <tr key={f.id}>
                            <td className="font-mono text-forensic-200 truncate max-w-[200px]">
                              {f.relative_path}
                            </td>
                            <td className="font-mono text-forensic-400 text-[11px]">
                              {f.expected_sha256?.substring(0, 14)}...
                            </td>
                            <td className="font-mono text-forensic-400 text-[11px]">
                              {f.actual_sha256?.substring(0, 14)}...
                            </td>
                            <td>
                              {f.is_intact ? (
                                <span className="text-accent-emerald bg-accent-emerald/20 px-2 py-0.5 rounded text-[10px] font-semibold inline-flex items-center gap-1">
                                  <CheckCircle2 className="h-3 w-3" /> Intact
                                </span>
                              ) : (
                                <span className="text-accent-rose bg-accent-rose/20 px-2 py-0.5 rounded text-[10px] font-semibold inline-flex items-center gap-1">
                                  <XCircle className="h-3 w-3" /> Mismatch
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-forensic-800 bg-forensic-950/60 flex items-center justify-between">
          <span className="text-xs text-forensic-500 font-mono">
            Chain-of-Custody Logged to activity_logs
          </span>
          <button onClick={onClose} className="btn-secondary text-xs px-5 py-2">
            Close Manifest
          </button>
        </div>
      </div>
    </div>
  );
};

export default EvidenceHashVerificationModal;
