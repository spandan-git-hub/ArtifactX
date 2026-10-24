import { useState } from 'react';
import { Copy, Check, ShieldCheck, ShieldAlert } from 'lucide-react';

const EvidenceHashBadge = ({
  hash,
  algorithm = 'SHA-256',
  status = null, // 'VERIFIED_INTACT' | 'HASH_MISMATCH' | null
  shorten = true,
  showLabel = false,
  className = '',
}) => {
  const [copied, setCopied] = useState(false);

  if (!hash) {
    return <span className="text-forensic-500 text-xs italic">No Hash</span>;
  }

  const displayHash = shorten && hash.length > 16 ? `${hash.substring(0, 16)}...` : hash;

  const handleCopy = (e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(hash);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`inline-flex items-center gap-2 ${className}`}>
      {showLabel && (
        <span className="text-xs text-forensic-400 font-medium uppercase tracking-wider">
          {algorithm}:
        </span>
      )}

      <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded border border-accent-cyan/30 bg-accent-cyan/10 font-mono text-xs text-accent-cyan transition-colors hover:border-accent-cyan/60">
        <span title={hash}>{displayHash}</span>
        <button
          onClick={handleCopy}
          className="text-accent-cyan/70 hover:text-accent-cyan p-0.5 transition-colors"
          title="Copy Hash"
        >
          {copied ? (
            <Check className="h-3 w-3 text-accent-emerald" />
          ) : (
            <Copy className="h-3 w-3" />
          )}
        </button>
      </div>

      {status === 'VERIFIED_INTACT' && (
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold tracking-wide uppercase bg-accent-emerald/20 text-accent-emerald border border-accent-emerald/40">
          <ShieldCheck className="h-3 w-3" />
          Intact
        </span>
      )}

      {status === 'HASH_MISMATCH' && (
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold tracking-wide uppercase bg-accent-rose/20 text-accent-rose border border-accent-rose/40">
          <ShieldAlert className="h-3 w-3" />
          Mismatch
        </span>
      )}
    </div>
  );
};

export default EvidenceHashBadge;
