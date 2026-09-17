import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { recoveryService } from '../services/recoveryService';
import { caseService } from '../services/caseService';
import CaseWorkspacePage from './CaseWorkspacePage';
import {
  Sparkles,
  ShieldCheck,
  AlertTriangle,
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
  ChevronRight,
  Database,
  Info,
  Terminal,
} from 'lucide-react';

export default function RecoveryPage() {
  const { caseId } = useParams();

  const [findings, setFindings] = useState([]);
  const [runs, setRuns] = useState([]);
  const [selectedFinding, setSelectedFinding] = useState(null);
  const [loading, setLoading] = useState(true);
  const [runningRecovery, setRunningRecovery] = useState(false);
  const [error, setError] = useState(null);
  const [copiedHash, setCopiedHash] = useState(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [methodFilter, setMethodFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const loadRecoveryData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [findingsData, runsData] = await Promise.all([
        recoveryService.getRecoveryFindings(caseId),
        recoveryService.getRecoveryRuns(caseId),
      ]);
      setFindings(findingsData || []);
      setRuns(runsData || []);
      if (findingsData && findingsData.length > 0 && !selectedFinding) {
        setSelectedFinding(findingsData[0]);
      }
    } catch (err) {
      console.error('Failed to load recovery data:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load recovery data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (caseId) {
      loadRecoveryData();
    }
  }, [caseId]);

  const handleRunRecovery = async () => {
    try {
      setRunningRecovery(true);
      setError(null);
      await recoveryService.runRecovery(caseId);
      await loadRecoveryData();
    } catch (err) {
      console.error('Physical recovery execution failed:', err);
      setError(err.response?.data?.detail || err.message || 'Physical recovery carving failed');
    } finally {
      setRunningRecovery(false);
    }
  };

  const copyToClipboard = (text, key) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(key);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'RECOVERED':
        return (
          <span className="badge border border-accent-emerald/40 bg-accent-emerald/10 text-accent-emerald font-mono font-bold text-xs px-2.5 py-0.5 rounded">
            RECOVERED
          </span>
        );
      case 'PARTIALLY_RECONSTRUCTED':
        return (
          <span className="badge border border-accent-cyan/40 bg-accent-cyan/10 text-accent-cyan font-mono text-xs px-2.5 py-0.5 rounded">
            PARTIAL
          </span>
        );
      case 'CANDIDATE':
        return (
          <span className="badge border border-accent-amber/40 bg-accent-amber/10 text-accent-amber font-mono text-xs px-2.5 py-0.5 rounded">
            CANDIDATE
          </span>
        );
      default:
        return (
          <span className="badge border border-forensic-700 bg-forensic-800 text-forensic-400 font-mono text-xs px-2.5 py-0.5 rounded">
            UNVALIDATED
          </span>
        );
    }
  };

  const getMethodBadge = (method) => {
    switch (method) {
      case 'wal':
        return (
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-purple-950/60 border border-purple-500/30 text-purple-300">
            WAL FRAME
          </span>
        );
      case 'freelist':
        return (
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-blue-950/60 border border-blue-500/30 text-blue-300">
            FREELIST
          </span>
        );
      case 'slack':
        return (
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-teal-950/60 border border-teal-500/30 text-teal-300">
            CELL SLACK
          </span>
        );
      default:
        return (
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-forensic-800 border border-forensic-700 text-forensic-400">
            {method.toUpperCase()}
          </span>
        );
    }
  };

  const filteredFindings = findings.filter((f) => {
    if (statusFilter !== 'ALL' && f.validation_status !== statusFilter) return false;
    if (methodFilter !== 'ALL' && f.method !== methodFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const bodyMatch = f.body && f.body.toLowerCase().includes(q);
      const chatMatch = f.chat_id && f.chat_id.toLowerCase().includes(q);
      const senderMatch = f.sender_id && f.sender_id.toLowerCase().includes(q);
      const hashMatch = f.raw_payload_hash && f.raw_payload_hash.toLowerCase().includes(q);
      return bodyMatch || chatMatch || senderMatch || hashMatch;
    }
    return true;
  });

  const latestRun = runs.length > 0 ? runs[0] : null;

  return (
    <CaseWorkspacePage>
      <div className="space-y-6">
        {/* Top Action & Overview Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-xl bg-forensic-900/80 border border-forensic-800 shadow-md">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono tracking-wider uppercase text-accent-cyan font-bold">
                R2 Forensic Engine
              </span>
              <span className="text-xs text-forensic-500">•</span>
              <span className="text-xs text-forensic-400">Non-Destructive Physical Carving</span>
            </div>
            <h2 className="text-xl font-bold font-mono text-forensic-50">
              Deleted Message Physical Recovery
            </h2>
            <p className="text-xs text-forensic-400 mt-1 max-w-2xl">
              Extracts residual messages and historical records from SQLite Write-Ahead Logs (WAL),
              unallocated freelist pages, and B-tree cell slack space without altering evidence binaries.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleRunRecovery}
              disabled={runningRecovery}
              className="btn-primary inline-flex items-center gap-2 px-4 py-2.5 font-mono text-xs shadow-lg shadow-accent-cyan/10"
            >
              <RefreshCw className={`w-4 h-4 ${runningRecovery ? 'animate-spin text-accent-cyan' : ''}`} />
              {runningRecovery ? 'Carving Physical Evidence...' : 'Execute Physical Carving'}
            </button>
          </div>
        </div>

        {error && (
          <div className="p-4 rounded-lg bg-accent-rose/10 border border-accent-rose/30 text-accent-rose text-sm flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Statistical Metrics Row */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="p-3.5 rounded-lg bg-forensic-900/60 border border-forensic-800">
            <div className="text-[11px] font-mono text-forensic-400 uppercase">Total Carved</div>
            <div className="text-xl font-bold font-mono text-forensic-100 mt-1">
              {findings.length}
            </div>
          </div>
          <div className="p-3.5 rounded-lg bg-forensic-900/60 border border-accent-emerald/20">
            <div className="text-[11px] font-mono text-accent-emerald uppercase">Recovered</div>
            <div className="text-xl font-bold font-mono text-accent-emerald mt-1">
              {findings.filter((f) => f.validation_status === 'RECOVERED').length}
            </div>
          </div>
          <div className="p-3.5 rounded-lg bg-forensic-900/60 border border-accent-amber/20">
            <div className="text-[11px] font-mono text-accent-amber uppercase">Candidates</div>
            <div className="text-xl font-bold font-mono text-accent-amber mt-1">
              {findings.filter((f) => f.validation_status === 'CANDIDATE').length}
            </div>
          </div>
          <div className="p-3.5 rounded-lg bg-forensic-900/60 border border-purple-500/20">
            <div className="text-[11px] font-mono text-purple-300 uppercase">WAL Pages</div>
            <div className="text-xl font-bold font-mono text-purple-200 mt-1">
              {latestRun?.wal_pages_analyzed || 0}
            </div>
          </div>
          <div className="p-3.5 rounded-lg bg-forensic-900/60 border border-blue-500/20">
            <div className="text-[11px] font-mono text-blue-300 uppercase">Freelist Pages</div>
            <div className="text-xl font-bold font-mono text-blue-200 mt-1">
              {latestRun?.freelist_pages_analyzed || 0}
            </div>
          </div>
          <div className="p-3.5 rounded-lg bg-forensic-900/60 border border-teal-500/20">
            <div className="text-[11px] font-mono text-teal-300 uppercase">Slack Spans</div>
            <div className="text-xl font-bold font-mono text-teal-200 mt-1">
              {latestRun?.slack_spans_analyzed || 0}
            </div>
          </div>
        </div>

        {/* Filter Toolbar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3 rounded-lg bg-forensic-900/60 border border-forensic-800">
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <Search className="w-4 h-4 text-forensic-500 ml-1" />
            <input
              type="text"
              placeholder="Search body, chat JID, sender, or payload hash..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-transparent border-none text-xs text-forensic-100 placeholder-forensic-500 focus:outline-none w-full sm:w-64"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto justify-end flex-wrap">
            <div className="flex items-center gap-1.5 text-xs text-forensic-400">
              <Filter className="w-3.5 h-3.5 text-forensic-500" />
              <span>Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-forensic-800 border border-forensic-700 text-forensic-200 text-xs rounded px-2 py-1 focus:outline-none"
              >
                <option value="ALL">All Statuses</option>
                <option value="RECOVERED">Recovered</option>
                <option value="PARTIALLY_RECONSTRUCTED">Partial</option>
                <option value="CANDIDATE">Candidate</option>
                <option value="UNVALIDATED">Unvalidated</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5 text-xs text-forensic-400 ml-2">
              <span>Method:</span>
              <select
                value={methodFilter}
                onChange={(e) => setMethodFilter(e.target.value)}
                className="bg-forensic-800 border border-forensic-700 text-forensic-200 text-xs rounded px-2 py-1 focus:outline-none"
              >
                <option value="ALL">All Methods</option>
                <option value="wal">WAL Frame</option>
                <option value="freelist">Freelist</option>
                <option value="slack">Cell Slack</option>
              </select>
            </div>
          </div>
        </div>

        {/* Workstation Split View: Table + Detail Inspector */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Findings Table (Left 7 cols) */}
          <div className="lg:col-span-7 bg-forensic-900/60 border border-forensic-800 rounded-xl overflow-hidden shadow-sm flex flex-col">
            <div className="px-4 py-3 border-b border-forensic-800 bg-forensic-900/80 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileCode className="w-4 h-4 text-accent-cyan" />
                <span className="text-xs font-mono font-bold text-forensic-200 uppercase">
                  Physically Carved Findings ({filteredFindings.length})
                </span>
              </div>
              <span className="text-[11px] text-forensic-500 font-mono">
                Click row to inspect hex dump & provenance
              </span>
            </div>

            <div className="overflow-x-auto flex-1 max-h-[620px] overflow-y-auto divide-y divide-forensic-800/60">
              {filteredFindings.length === 0 ? (
                <div className="p-12 text-center text-forensic-500">
                  <Database className="w-8 h-8 mx-auto mb-3 opacity-30 text-forensic-400" />
                  <p className="text-sm font-mono">No carved deleted records match filters.</p>
                  <p className="text-xs text-forensic-600 mt-1">
                    Click "Execute Physical Carving" to run WAL, freelist, and slack space analysis.
                  </p>
                </div>
              ) : (
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-forensic-900/90 text-forensic-400 font-mono uppercase text-[10px] sticky top-0 z-10 border-b border-forensic-800">
                    <tr>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3">Method</th>
                      <th className="py-2.5 px-3">Offset / Page</th>
                      <th className="py-2.5 px-3">App / Chat</th>
                      <th className="py-2.5 px-3">Message Body</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-forensic-850 font-mono">
                    {filteredFindings.map((f) => {
                      const isSelected = selectedFinding?.id === f.id;
                      return (
                        <tr
                          key={f.id}
                          onClick={() => setSelectedFinding(f)}
                          className={`cursor-pointer transition-colors ${
                            isSelected
                              ? 'bg-accent-cyan/10 border-l-2 border-l-accent-cyan'
                              : 'hover:bg-forensic-850/50'
                          }`}
                        >
                          <td className="py-2.5 px-3 whitespace-nowrap">
                            {getStatusBadge(f.validation_status)}
                          </td>
                          <td className="py-2.5 px-3 whitespace-nowrap">
                            {getMethodBadge(f.method)}
                          </td>
                          <td className="py-2.5 px-3 whitespace-nowrap text-forensic-400 text-[11px]">
                            <div>P.{f.page_number}</div>
                            <div className="text-[10px] text-forensic-500">0x{f.byte_offset.toString(16)}</div>
                          </td>
                          <td className="py-2.5 px-3 whitespace-nowrap text-forensic-300 max-w-[140px] truncate">
                            <span className="capitalize text-accent-cyan text-[11px] mr-1.5">
                              {f.source_app}
                            </span>
                            <span className="text-forensic-400 text-[11px] truncate">
                              {f.chat_id || 'Unknown'}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-forensic-200 font-sans max-w-[200px] truncate">
                            {f.body || (
                              <span className="text-forensic-500 italic font-mono text-xs">
                                [Binary / Fragment]
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </div>

          {/* Detail Inspector Panel (Right 5 cols) */}
          <div className="lg:col-span-5 bg-forensic-900/60 border border-forensic-800 rounded-xl p-5 shadow-sm space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-forensic-800">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-accent-cyan" />
                <h3 className="font-mono text-xs font-bold uppercase tracking-wider text-forensic-100">
                  Forensic Finding Inspector
                </h3>
              </div>
              {selectedFinding && getStatusBadge(selectedFinding.validation_status)}
            </div>

            {selectedFinding ? (
              <div className="space-y-4 text-xs font-mono">
                {/* Reconstructed Attributes Card */}
                <div className="p-3.5 rounded-lg bg-forensic-850/60 border border-forensic-800 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-forensic-500 text-[11px]">Source Platform:</span>
                    <span className="text-accent-cyan font-bold capitalize">
                      {selectedFinding.source_app}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-forensic-500 text-[11px]">Carving Method:</span>
                    <span>{getMethodBadge(selectedFinding.method)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-forensic-500 text-[11px]">Physical Location:</span>
                    <span className="text-forensic-300">
                      Page {selectedFinding.page_number} (Byte Offset: 0x{selectedFinding.byte_offset.toString(16)})
                    </span>
                  </div>
                  {selectedFinding.chat_id && (
                    <div className="flex items-center justify-between">
                      <span className="text-forensic-500 text-[11px]">Chat / Dialog:</span>
                      <span className="text-forensic-200 truncate max-w-[200px]">
                        {selectedFinding.chat_id}
                      </span>
                    </div>
                  )}
                  {selectedFinding.sender_id && (
                    <div className="flex items-center justify-between">
                      <span className="text-forensic-500 text-[11px]">Sender ID:</span>
                      <span className="text-forensic-200">{selectedFinding.sender_id}</span>
                    </div>
                  )}
                  {selectedFinding.timestamp && (
                    <div className="flex items-center justify-between">
                      <span className="text-forensic-500 text-[11px]">Timestamp:</span>
                      <span className="text-accent-emerald">
                        {new Date(selectedFinding.timestamp * 1000).toISOString()}
                      </span>
                    </div>
                  )}
                </div>

                {/* Reconstructed Body */}
                <div className="space-y-1.5">
                  <div className="text-[11px] text-forensic-400 uppercase tracking-wider font-bold">
                    Reconstructed Message Content:
                  </div>
                  <div className="p-3.5 rounded-lg bg-forensic-950 border border-forensic-800 text-forensic-100 font-sans text-sm leading-relaxed select-text">
                    {selectedFinding.body || (
                      <span className="text-forensic-500 italic font-mono text-xs">
                        [No textual body identified — binary payload only]
                      </span>
                    )}
                  </div>
                </div>

                {/* Raw Hex / ASCII Preview Box */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-[11px] text-forensic-400 uppercase tracking-wider font-bold">
                    <span>Raw Carved Bytes (Hex & ASCII):</span>
                    <button
                      onClick={() =>
                        copyToClipboard(selectedFinding.raw_payload_preview, 'hex')
                      }
                      className="text-forensic-400 hover:text-accent-cyan inline-flex items-center gap-1 text-[10px]"
                    >
                      {copiedHash === 'hex' ? (
                        <Check className="w-3 h-3 text-accent-emerald" />
                      ) : (
                        <Copy className="w-3 h-3" />
                      )}
                      Copy
                    </button>
                  </div>
                  <pre className="p-3 rounded-lg bg-black/80 border border-forensic-800/80 text-[10px] text-forensic-300 overflow-x-auto leading-tight select-text font-mono max-h-44">
                    {selectedFinding.raw_payload_preview || 'No raw hex preview recorded'}
                  </pre>
                </div>

                {/* Provenance & Cryptographic Linkage */}
                <div className="p-3.5 rounded-lg bg-forensic-900/90 border border-forensic-800 space-y-2">
                  <div className="flex items-center gap-1.5 text-[11px] font-bold text-accent-cyan uppercase">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Cryptographic Provenance</span>
                  </div>

                  <div className="space-y-1 text-[10px] text-forensic-400">
                    <div className="flex items-center justify-between">
                      <span>Payload SHA-256:</span>
                      <span className="font-mono text-forensic-200">
                        {selectedFinding.raw_payload_hash.slice(0, 16)}...
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Parent Evidence ID:</span>
                      <span className="text-forensic-200">
                        #{selectedFinding.evidence_id}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Carving Algorithm:</span>
                      <span className="text-forensic-200">
                        {selectedFinding.provenance?.algorithm_version || '2.0.0-r2'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Forensic Limitations Warning */}
                {selectedFinding.limitations && selectedFinding.limitations.length > 0 && (
                  <div className="p-3 rounded-lg bg-amber-950/20 border border-amber-500/30 text-amber-300 text-[11px] space-y-1">
                    <div className="flex items-center gap-1.5 font-bold uppercase text-[10px]">
                      <Info className="w-3.5 h-3.5 text-amber-400" />
                      <span>Forensic Qualifications & Limitations</span>
                    </div>
                    <ul className="list-disc pl-4 space-y-0.5 text-[10px] text-amber-200/80">
                      {selectedFinding.limitations.map((lim, idx) => (
                        <li key={idx}>{lim}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-12 text-center text-forensic-500">
                <FileText className="w-8 h-8 mx-auto mb-2 opacity-30 text-forensic-400" />
                <p className="text-xs font-mono">Select a carved finding to inspect details</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </CaseWorkspacePage>
  );
}
