import { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import CaseWorkspacePage from './CaseWorkspacePage';
import chatService from '../services/chatService';
import ExifMetadataDrawer from '../components/evidence/ExifMetadataDrawer';
import ForensicAssistantDrawer from '../components/assistant/ForensicAssistantDrawer';
import useAiAssistant from '../hooks/useAiAssistant';
import {
  MessageSquare,
  Search,
  AlertTriangle,
  FileText,
  Image as ImageIcon,
  Video,
  Music,
  Paperclip,
  Camera,
  Copy,
  Check,
  ShieldCheck,
  Loader2,
  AlertCircle,
  Clock,
  User,
  Hash,
  ChevronRight,
  Code,
  Info,
  Sparkles,
  Bot,
  Activity,
  Flame,
  ShieldAlert,
  DollarSign,
  Trash2,
  Lock,
} from 'lucide-react';

const TONE_BADGES = {
  Aggressive: { label: 'Aggressive', bg: 'bg-accent-rose/15 text-accent-rose border-accent-rose/30' },
  Suspicious: { label: 'Suspicious', bg: 'bg-amber-400/15 text-amber-400 border-amber-400/30' },
  Deceptive: { label: 'Deceptive', bg: 'bg-purple-400/15 text-purple-400 border-purple-400/30' },
  Urgent: { label: 'Urgent', bg: 'bg-orange-400/15 text-orange-400 border-orange-400/30' },
  Evasive: { label: 'Evasive', bg: 'bg-yellow-400/15 text-yellow-400 border-yellow-400/30' },
  Neutral: { label: 'Neutral', bg: 'bg-forensic-800 text-forensic-400 border-forensic-700' },
};

const ChatViewerPage = () => {
  const { caseId } = useParams();

  // State for threads
  const [threads, setThreads] = useState([]);
  const [loadingThreads, setLoadingThreads] = useState(true);
  const [threadsError, setThreadsError] = useState(null);

  // Filters & selection
  const [searchQuery, setSearchQuery] = useState('');
  const [appFilter, setAppFilter] = useState('all'); // 'all', 'whatsapp', 'telegram'
  const [selectedJid, setSelectedJid] = useState(null);

  // Phase 15: AI Assistant & Sentiment Overlay State
  const [showSentimentOverlay, setShowSentimentOverlay] = useState(false);
  const [isAssistantOpen, setIsAssistantOpen] = useState(false);
  const {
    sentimentData,
    loadingSentiment,
    loadSentiment,
  } = useAiAssistant(caseId);

  // Active message stream
  const [activeThreadInfo, setActiveThreadInfo] = useState(null);
  const [messageStream, setMessageStream] = useState([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [messagesError, setMessagesError] = useState(null);

  // Selected message for right inspector pane
  const [selectedMessage, setSelectedMessage] = useState(null);

  // EXIF Drawer State
  const [exifDrawerState, setExifDrawerState] = useState({
    isOpen: false,
    evidenceId: null,
    fileId: null,
    fileName: null,
  });

  // Copy state
  const [copiedHash, setCopiedHash] = useState(false);
  const messagesEndRef = useRef(null);

  // Fetch threads on mount
  useEffect(() => {
    let isMounted = true;
    const fetchThreads = async () => {
      try {
        setLoadingThreads(true);
        setThreadsError(null);
        const data = await chatService.getChats(caseId);
        if (!isMounted) return;
        setThreads(data || []);
        if (data && data.length > 0) {
          setSelectedJid(data[0].jid);
        }
      } catch (err) {
        if (!isMounted) return;
        console.error('Failed to load chat threads:', err);
        setThreadsError(err.response?.data?.detail || err.message || 'Failed to fetch chat threads');
      } finally {
        if (isMounted) setLoadingThreads(false);
      }
    };

    if (caseId) {
      fetchThreads();
    }
    return () => {
      isMounted = false;
    };
  }, [caseId]);

  // Fetch messages when selectedJid changes
  useEffect(() => {
    if (!caseId || !selectedJid) {
      setActiveThreadInfo(null);
      setMessageStream([]);
      setSelectedMessage(null);
      return;
    }

    let isMounted = true;
    const fetchMessages = async () => {
      try {
        setLoadingMessages(true);
        setMessagesError(null);
        const data = await chatService.getChatMessages(caseId, selectedJid);
        if (!isMounted) return;
        setActiveThreadInfo(data.thread);
        setMessageStream(data.messages || []);

        // Select first non-marker message for inspector
        const firstMsg = (data.messages || []).find((m) => !m.is_deletion_marker);
        setSelectedMessage(firstMsg || null);
      } catch (err) {
        if (!isMounted) return;
        console.error('Failed to load thread messages:', err);
        setMessagesError(err.response?.data?.detail || err.message || 'Failed to load thread messages');
      } finally {
        if (isMounted) setLoadingMessages(false);
      }
    };

    fetchMessages();
    return () => {
      isMounted = false;
    };
  }, [caseId, selectedJid]);

  // Scroll to bottom when messageStream updates
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messageStream]);

  // Load sentiment data when overlay is toggled on or thread changes
  useEffect(() => {
    if (showSentimentOverlay && caseId && selectedJid) {
      loadSentiment(selectedJid);
    }
  }, [showSentimentOverlay, caseId, selectedJid, loadSentiment]);

  const handleSelectCitation = (finding) => {
    if (finding.chat_jid && finding.chat_jid !== selectedJid) {
      setSelectedJid(finding.chat_jid);
    }
    const found = messageStream.find(
      (m) => m.id === finding.id || m.message_id === finding.message_id
    );
    if (found) {
      setSelectedMessage(found);
    }
  };

  // Filter threads
  const filteredThreads = threads.filter((thread) => {
    const matchesApp = appFilter === 'all' || thread.source_app === appFilter;
    const matchesSearch =
      !searchQuery ||
      thread.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      thread.jid.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (thread.last_message_body && thread.last_message_body.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesApp && matchesSearch;
  });

  const handleCopySignature = (sig) => {
    if (!sig) return;
    navigator.clipboard.writeText(sig);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  const handleOpenExif = (mediaInfo) => {
    if (!mediaInfo) return;
    setExifDrawerState({
      isOpen: true,
      evidenceId: mediaInfo.evidence_id,
      fileId: mediaInfo.file_id,
      fileName: mediaInfo.media_path ? mediaInfo.media_path.split('/').pop() : 'Attachment Media',
    });
  };

  const formatTimestamp = (ts) => {
    if (!ts) return '—';
    try {
      const date = new Date(ts);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return String(ts);
    }
  };

  const formatDateHeader = (ts) => {
    if (!ts) return '';
    try {
      const date = new Date(ts);
      return date.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
      return '';
    }
  };

  return (
    <CaseWorkspacePage activeTab="chat" onOpenCopilot={() => setIsAssistantOpen(true)}>
      <div className="h-[calc(100vh-180px)] flex flex-col lg:flex-row gap-4 bg-forensic-950 text-forensic-100 animate-in">
        {/* ======================================================== */}
        {/* LEFT PANE: Thread List Sidebar */}
        {/* ======================================================== */}
        <div className="w-full lg:w-80 flex flex-col bg-forensic-900 border border-forensic-800 rounded-xl overflow-hidden shadow-lg flex-shrink-0">
          {/* Sidebar Header & Filters */}
          <div className="p-3.5 border-b border-forensic-800 space-y-3 bg-forensic-950/60">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-accent-cyan" />
                <span className="font-semibold text-sm">Extracted Threads</span>
              </div>
              <span className="badge badge-cyan text-[11px] font-mono">{threads.length} Threads</span>
            </div>

            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-forensic-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search contact, JID, message..."
                className="input pl-8 py-1.5 text-xs w-full bg-forensic-900 border-forensic-800"
              />
            </div>

            {/* App Toggles */}
            <div className="flex items-center gap-1 bg-forensic-950 p-1 rounded-lg border border-forensic-800 text-xs">
              <button
                onClick={() => setAppFilter('all')}
                className={`flex-1 py-1 rounded font-medium transition-colors text-center ${
                  appFilter === 'all' ? 'bg-forensic-800 text-accent-cyan shadow' : 'text-forensic-400 hover:text-forensic-200'
                }`}
              >
                All
              </button>
              <button
                onClick={() => setAppFilter('whatsapp')}
                className={`flex-1 py-1 rounded font-medium transition-colors text-center flex items-center justify-center gap-1 ${
                  appFilter === 'whatsapp' ? 'bg-accent-emerald/20 text-accent-emerald font-semibold shadow' : 'text-forensic-400 hover:text-forensic-200'
                }`}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-accent-emerald" />
                WhatsApp
              </button>
              <button
                onClick={() => setAppFilter('telegram')}
                className={`flex-1 py-1 rounded font-medium transition-colors text-center flex items-center justify-center gap-1 ${
                  appFilter === 'telegram' ? 'bg-accent-cyan/20 text-accent-cyan font-semibold shadow' : 'text-forensic-400 hover:text-forensic-200'
                }`}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-accent-cyan" />
                Telegram
              </button>
            </div>
          </div>

          {/* Thread List Items */}
          <div className="flex-1 overflow-y-auto divide-y divide-forensic-800/50">
            {loadingThreads ? (
              <div className="p-8 text-center text-forensic-500 text-xs">
                <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2 text-accent-cyan" />
                Loading extracted chats...
              </div>
            ) : threadsError ? (
              <div className="p-4 text-xs text-accent-rose bg-accent-rose/5">{threadsError}</div>
            ) : filteredThreads.length === 0 ? (
              <div className="p-8 text-center text-forensic-500 text-xs">No chat threads found matching query.</div>
            ) : (
              filteredThreads.map((thread) => {
                const isSelected = selectedJid === thread.jid;
                const isWhatsApp = thread.source_app === 'whatsapp';

                return (
                  <button
                    key={thread.jid}
                    onClick={() => setSelectedJid(thread.jid)}
                    className={`w-full text-left p-3 flex items-start gap-3 transition-colors ${
                      isSelected
                        ? 'bg-forensic-800/80 border-l-4 border-accent-cyan'
                        : 'hover:bg-forensic-800/40'
                    }`}
                  >
                    {/* App Badge Avatar */}
                    <div
                      className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 font-bold text-xs ${
                        isWhatsApp
                          ? 'bg-accent-emerald/20 text-accent-emerald border border-accent-emerald/30'
                          : 'bg-accent-cyan/20 text-accent-cyan border border-accent-cyan/30'
                      }`}
                    >
                      {isWhatsApp ? 'WA' : 'TG'}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1 mb-0.5">
                        <span className="font-semibold text-xs text-forensic-100 truncate">{thread.name}</span>
                        <span className="text-[10px] text-forensic-500 font-mono">
                          {formatTimestamp(thread.last_message_timestamp)}
                        </span>
                      </div>

                      <p className="text-[11px] text-forensic-400 truncate mb-1.5 font-mono">
                        {thread.last_message_body || 'No text preview'}
                      </p>

                      <div className="flex items-center justify-between gap-1">
                        <span className="text-[10px] text-forensic-500 font-mono truncate max-w-[120px]">
                          {thread.jid}
                        </span>

                        <div className="flex items-center gap-1">
                          {thread.deletion_count > 0 && (
                            <span className="px-1.5 py-0.2 rounded bg-accent-rose/20 text-accent-rose text-[10px] font-mono border border-accent-rose/30 flex items-center gap-0.5" title={`${thread.deletion_count} missing messages detected`}>
                              <AlertTriangle className="w-2.5 h-2.5" />
                              {thread.deletion_count} Del
                            </span>
                          )}
                          <span className="badge badge-gray text-[10px] px-1.5 py-0">
                            {thread.message_count} msgs
                          </span>
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* ======================================================== */}
        {/* CENTER PANE: Interactive Message Stream */}
        {/* ======================================================== */}
        <div className="flex-1 flex flex-col bg-forensic-900 border border-forensic-800 rounded-xl overflow-hidden shadow-lg min-w-0">
          {/* Thread Header */}
          {activeThreadInfo ? (
            <div className="p-3.5 border-b border-forensic-800 flex items-center justify-between bg-forensic-950/80">
              <div className="flex items-center gap-3">
                <div
                  className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-xs ${
                    activeThreadInfo.source_app === 'whatsapp'
                      ? 'bg-accent-emerald/20 text-accent-emerald border border-accent-emerald/30'
                      : 'bg-accent-cyan/20 text-accent-cyan border border-accent-cyan/30'
                  }`}
                >
                  {activeThreadInfo.source_app === 'whatsapp' ? 'WA' : 'TG'}
                </div>
                <div>
                  <h3 className="font-bold text-sm text-forensic-100 flex items-center gap-2">
                    {activeThreadInfo.name}
                    <span
                      className={`badge text-[10px] ${
                        activeThreadInfo.source_app === 'whatsapp' ? 'badge-emerald' : 'badge-cyan'
                      }`}
                    >
                      {activeThreadInfo.source_app.toUpperCase()}
                    </span>
                  </h3>
                  <p className="text-xs text-forensic-400 font-mono">{activeThreadInfo.jid}</p>
                </div>
              </div>

              <div className="flex items-center gap-2.5 text-xs flex-wrap">
                <span className="text-forensic-400 font-mono hidden sm:inline">
                  Total: <strong className="text-forensic-100">{activeThreadInfo.total_messages}</strong> msgs
                </span>
                {activeThreadInfo.total_deletions > 0 && (
                  <span className="badge badge-rose text-xs flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3 text-accent-rose" />
                    {activeThreadInfo.total_deletions} Del
                  </span>
                )}

                {/* Phase 15: Sentiment Overlay Toggle */}
                <button
                  onClick={() => {
                    const next = !showSentimentOverlay;
                    setShowSentimentOverlay(next);
                    if (next && selectedJid) loadSentiment(selectedJid);
                  }}
                  className={`py-1 px-2.5 rounded-lg border text-xs font-mono transition-colors flex items-center gap-1.5 ${
                    showSentimentOverlay
                      ? 'bg-accent-cyan/20 border-accent-cyan text-accent-cyan shadow-sm'
                      : 'bg-forensic-900 border-forensic-700 text-forensic-400 hover:text-forensic-200'
                  }`}
                  title="Toggle emotional tone badges and suspicion indicators on chat messages"
                >
                  <Activity className="w-3.5 h-3.5" />
                  <span className="hidden md:inline">Sentiment Overlay</span>
                  <span className={`text-[9px] px-1 py-0.2 rounded font-bold ${
                    showSentimentOverlay ? 'bg-accent-cyan text-forensic-950' : 'bg-forensic-800 text-forensic-500'
                  }`}>
                    {showSentimentOverlay ? 'ON' : 'OFF'}
                  </span>
                </button>

                {/* Phase 15: AI Forensic Copilot Trigger */}
                <button
                  onClick={() => setIsAssistantOpen(true)}
                  className="btn-primary py-1 px-2.5 text-xs inline-flex items-center gap-1.5 shadow-sm"
                  title="Open AI Forensic Assistant Copilot"
                >
                  <Bot className="w-3.5 h-3.5" />
                  <span>AI Copilot</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="p-4 border-b border-forensic-800 text-xs text-forensic-400">
              Select a thread to view message stream
            </div>
          )}

          {/* Message Stream Body */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-forensic-950/40">
            {loadingMessages ? (
              <div className="flex flex-col items-center justify-center h-full py-16">
                <Loader2 className="w-7 h-7 animate-spin text-accent-cyan mb-2" />
                <span className="text-xs font-mono text-forensic-400">Decrypting & loading message stream...</span>
              </div>
            ) : messagesError ? (
              <div className="card border-accent-rose/30 bg-accent-rose/5 p-4 text-xs text-accent-rose">
                {messagesError}
              </div>
            ) : messageStream.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-forensic-500 text-xs">
                <MessageSquare className="w-10 h-10 mb-2 opacity-40" />
                <span>No messages found in this chat thread.</span>
              </div>
            ) : (
              messageStream.map((item, index) => {
                // RENDER INLINE DELETION INDICATOR MARKER
                if (item.is_deletion_marker) {
                  return (
                    <div key={item.id || index} className="my-4 animate-in fade-in">
                      <div className="card border-accent-rose/40 bg-accent-rose/10 p-3 max-w-xl mx-auto flex items-start gap-3 shadow-md">
                        <div className="p-2 rounded-lg bg-accent-rose/20 text-accent-rose flex-shrink-0">
                          <AlertTriangle className="w-5 h-5 animate-pulse" />
                        </div>
                        <div className="flex-1 text-xs">
                          <div className="flex items-center justify-between font-mono font-bold text-accent-rose mb-1">
                            <span>[DELETED MESSAGE SEQUENCE DETECTED]</span>
                            <span className="badge badge-rose text-[10px]">
                              Confidence: {Math.round((item.confidence_score || 0.85) * 100)}%
                            </span>
                          </div>
                          <p className="text-forensic-300 font-mono text-[11px] mb-1">
                            Detection Method: <span className="text-forensic-100">{item.detection_method}</span>
                          </p>
                          <div className="flex items-center gap-4 text-[10px] text-forensic-400 font-mono border-t border-accent-rose/20 pt-1.5">
                            <span>Estimated Missing: <strong className="text-accent-rose">{item.missing_count || 1}</strong> message(s)</span>
                            {item.gap_start && item.gap_end && (
                              <span>
                                Gap window: {formatTimestamp(item.gap_start)} – {formatTimestamp(item.gap_end)}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                }

                // RENDER STANDARD CHAT BUBBLE
                const isSelected = selectedMessage?.id === item.id;
                const isMedia = item.media_info || item.message_type === 'media';

                return (
                  <div
                    key={item.id}
                    onClick={() => setSelectedMessage(item)}
                    className={`flex flex-col max-w-2xl cursor-pointer group transition-all ${
                      isSelected ? 'ring-2 ring-accent-cyan rounded-xl' : ''
                    }`}
                  >
                    {/* Chat Bubble Container */}
                    <div
                      className={`p-3 rounded-xl border transition-colors ${
                        isSelected
                          ? 'bg-forensic-800 border-accent-cyan shadow-lg'
                          : 'bg-forensic-900/90 border-forensic-800 hover:border-forensic-700'
                      }`}
                    >
                      {/* Bubble Header */}
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-xs text-accent-cyan flex items-center gap-1">
                            <User className="w-3 h-3" />
                            {item.sender_name}
                          </span>
                          <span className="text-[10px] text-forensic-500 font-mono">({item.sender_jid})</span>
                        </div>
                        <span className="text-[10px] text-forensic-500 font-mono">
                          {formatTimestamp(item.timestamp)}
                        </span>
                      </div>

                      {/* Body Text */}
                      {item.body && (
                        <p className="text-xs text-forensic-100 leading-relaxed font-sans whitespace-pre-wrap mb-2">
                          {item.body}
                        </p>
                      )}

                      {/* Phase 15: Chat Sentiment & Intention Overlay */}
                      {showSentimentOverlay && sentimentData?.messages?.[item.id] && (() => {
                        const s = sentimentData.messages[item.id];
                        const badgeStyle = TONE_BADGES[s.tone] || TONE_BADGES.Neutral;
                        return (
                          <div className="mt-1.5 pt-1.5 border-t border-forensic-800/80 space-y-1.5 animate-in fade-in">
                            <div className="flex items-center justify-between gap-2 flex-wrap text-[10px]">
                              <div className="flex items-center gap-1.5">
                                <span className={`px-2 py-0.5 rounded font-mono font-medium border ${badgeStyle.bg}`}>
                                  {s.tone}
                                </span>
                                {s.suspicion_score > 0 && (
                                  <span className={`px-1.5 py-0.5 rounded font-mono font-semibold ${
                                    s.suspicion_score >= 70
                                      ? 'text-accent-rose bg-accent-rose/15 border border-accent-rose/30'
                                      : s.suspicion_score >= 40
                                      ? 'text-amber-400 bg-amber-400/15 border border-amber-400/30'
                                      : 'text-forensic-400 bg-forensic-800/40 border border-forensic-700/40'
                                  }`}>
                                    Suspicion: {s.suspicion_score}%
                                  </span>
                                )}
                              </div>

                              {s.confidence_level && (
                                <span className="text-forensic-500 font-mono text-[9px]">
                                  Confidence: {s.confidence_level}
                                </span>
                              )}
                            </div>

                            {s.intentions?.length > 0 && (
                              <div className="flex flex-wrap gap-1 pt-0.5">
                                {s.intentions.map((intent) => (
                                  <span
                                    key={intent}
                                    className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-forensic-950 text-accent-cyan border border-accent-cyan/20 flex items-center gap-1"
                                  >
                                    {intent === 'financial_demand' && <DollarSign className="w-2.5 h-2.5 text-emerald-400" />}
                                    {intent === 'coercion' && <Flame className="w-2.5 h-2.5 text-accent-rose" />}
                                    {intent === 'deletion_awareness' && <Trash2 className="w-2.5 h-2.5 text-amber-400" />}
                                    {intent === 'covert_communication' && <Lock className="w-2.5 h-2.5 text-purple-400" />}
                                    {intent.replace('_', ' ')}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })()}

                      {/* Attachment Preview Box */}
                      {isMedia && item.media_info && (
                        <div className="card p-2.5 bg-forensic-950 border-forensic-800 rounded-lg space-y-2 my-1">
                          <div className="flex items-center justify-between text-xs">
                            <div className="flex items-center gap-2 text-accent-cyan">
                              <ImageIcon className="w-4 h-4" />
                              <span className="font-mono font-medium truncate max-w-[200px]">
                                {item.media_info.media_path ? item.media_info.media_path.split('/').pop() : 'Attached Media'}
                              </span>
                            </div>
                            {item.media_info.file_size && (
                              <span className="text-[10px] text-forensic-500 font-mono">
                                {(item.media_info.file_size / 1024).toFixed(1)} KB
                              </span>
                            )}
                          </div>

                          {/* EXIF Trigger Button */}
                          <div className="flex items-center justify-end pt-1">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleOpenExif(item.media_info);
                              }}
                              className="btn-secondary py-1 px-2.5 text-[11px] inline-flex items-center gap-1.5"
                            >
                              <Camera className="w-3.5 h-3.5 text-accent-cyan" />
                              Inspect EXIF Metadata
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Bubble Footer Signature Badge */}
                      <div className="flex items-center justify-between text-[10px] text-forensic-500 font-mono border-t border-forensic-800/60 pt-1.5 mt-1">
                        <span className="flex items-center gap-1 text-forensic-400">
                          <ShieldCheck className="w-3 h-3 text-accent-emerald" />
                          SHA256: {item.sha256_signature?.substring(0, 16)}...
                        </span>
                        <span className="uppercase text-forensic-500">{item.status || 'delivered'}</span>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* ======================================================== */}
        {/* RIGHT PANE: Message Raw Metadata & Cryptographic Drawer */}
        {/* ======================================================== */}
        <div className="w-full lg:w-80 flex flex-col bg-forensic-900 border border-forensic-800 rounded-xl overflow-hidden shadow-lg flex-shrink-0">
          <div className="p-3.5 border-b border-forensic-800 flex items-center gap-2 bg-forensic-950/80">
            <Info className="w-4 h-4 text-accent-violet" />
            <span className="font-semibold text-sm">Forensic Message Inspector</span>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {selectedMessage ? (
              <>
                {/* Forensic Signature Card */}
                <div className="card bg-forensic-950/80 border-accent-cyan/30 p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-accent-cyan flex items-center gap-1.5">
                      <ShieldCheck className="w-4 h-4" />
                      Cryptographic Signature
                    </span>
                    <button
                      onClick={() => handleCopySignature(selectedMessage.sha256_signature)}
                      className="p-1 text-forensic-400 hover:text-accent-cyan transition-colors"
                      title="Copy SHA-256 Signature"
                    >
                      {copiedHash ? <Check className="w-3.5 h-3.5 text-accent-emerald" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                  <div className="bg-forensic-900 p-2 rounded border border-forensic-800 font-mono text-[11px] text-accent-cyan break-all">
                    {selectedMessage.sha256_signature}
                  </div>
                  <p className="text-[10px] text-forensic-500 font-mono">
                    SHA-256 payload digest verified against case evidence database.
                  </p>
                </div>

                {/* Phase 15: AI Sentiment & Intent Analysis Card */}
                <div className="card bg-forensic-950/80 border-accent-cyan/20 p-3 space-y-2.5">
                  <div className="flex items-center justify-between border-b border-forensic-800 pb-2">
                    <span className="text-xs font-semibold text-forensic-100 flex items-center gap-1.5 font-mono">
                      <Sparkles className="w-3.5 h-3.5 text-accent-cyan" />
                      AI Sentiment & Intent
                    </span>
                    <span className="badge badge-cyan text-[9px] uppercase font-mono">Investigative</span>
                  </div>

                  {/* Legal Court Exclusion Disclaimer */}
                  <div className="p-1.5 rounded bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[10px] font-mono flex items-center gap-1.5">
                    <ShieldAlert className="w-3.5 h-3.5 flex-shrink-0 text-amber-400" />
                    <span className="leading-tight">Internal Aid Only — Excluded from Court Reports</span>
                  </div>

                  {sentimentData?.messages?.[selectedMessage.id] ? (() => {
                    const s = sentimentData.messages[selectedMessage.id];
                    const badgeStyle = TONE_BADGES[s.tone] || TONE_BADGES.Neutral;
                    return (
                      <div className="space-y-2 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="text-forensic-400 text-[11px]">Emotional Tone:</span>
                          <span className={`px-2 py-0.5 rounded text-[11px] font-mono font-medium border ${badgeStyle.bg}`}>
                            {s.tone}
                          </span>
                        </div>

                        <div>
                          <div className="flex items-center justify-between text-[11px] mb-1">
                            <span className="text-forensic-400">Suspicion Score:</span>
                            <span className={`font-mono font-bold ${
                              s.suspicion_score >= 70 ? 'text-accent-rose' : s.suspicion_score >= 40 ? 'text-amber-400' : 'text-accent-cyan'
                            }`}>
                              {s.suspicion_score}% ({s.confidence_level} Confidence)
                            </span>
                          </div>
                          <div className="w-full h-1.5 bg-forensic-900 rounded-full overflow-hidden border border-forensic-800">
                            <div
                              className={`h-full transition-all duration-300 ${
                                s.suspicion_score >= 70 ? 'bg-accent-rose' : s.suspicion_score >= 40 ? 'bg-amber-400' : 'bg-accent-cyan'
                              }`}
                              style={{ width: `${s.suspicion_score}%` }}
                            />
                          </div>
                        </div>

                        {s.intentions?.length > 0 && (
                          <div>
                            <span className="text-forensic-400 text-[11px] block mb-1">Detected Intentions:</span>
                            <div className="flex flex-wrap gap-1">
                              {s.intentions.map((intent) => (
                                <span key={intent} className="badge badge-gray text-[10px] uppercase font-mono">
                                  {intent.replace('_', ' ')}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {s.highlights?.length > 0 && (
                          <div>
                            <span className="text-forensic-400 text-[11px] block mb-1">Lexical Triggers:</span>
                            <div className="flex flex-wrap gap-1">
                              {s.highlights.map((h, i) => (
                                <span key={i} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-forensic-900 border border-forensic-800 text-forensic-300">
                                  "{h}"
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })() : (
                    <div className="text-center py-2">
                      <button
                        onClick={() => loadSentiment(selectedJid, [selectedMessage.id])}
                        disabled={loadingSentiment}
                        className="btn-secondary py-1 px-2.5 text-[11px] inline-flex items-center gap-1.5"
                      >
                        {loadingSentiment ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Sparkles className="w-3.5 h-3.5 text-accent-cyan" />
                        )}
                        Analyze This Message
                      </button>
                    </div>
                  )}
                </div>

                {/* Message Attributes */}
                <div className="card bg-forensic-950/60 border-forensic-800 p-3 space-y-3">
                  <span className="text-xs font-semibold text-forensic-200 border-b border-forensic-800 pb-1 block">
                    Message Attributes
                  </span>

                  <div className="space-y-2 text-xs">
                    <div>
                      <span className="text-forensic-500 text-[11px] block">Message ID</span>
                      <span className="font-mono text-forensic-100 font-medium">{selectedMessage.message_id}</span>
                    </div>

                    <div>
                      <span className="text-forensic-500 text-[11px] block">Sender Name & JID</span>
                      <span className="font-mono text-accent-cyan block font-medium">{selectedMessage.sender_name}</span>
                      <span className="font-mono text-[11px] text-forensic-400">{selectedMessage.sender_jid}</span>
                    </div>

                    <div>
                      <span className="text-forensic-500 text-[11px] block">Source Application</span>
                      <span className="badge badge-cyan text-[11px] uppercase">{selectedMessage.source_app}</span>
                    </div>

                    <div>
                      <span className="text-forensic-500 text-[11px] block">Capture Timestamp</span>
                      <span className="font-mono text-forensic-100 block">{selectedMessage.timestamp_iso || '—'}</span>
                      <span className="font-mono text-[10px] text-forensic-500">Epoch: {selectedMessage.timestamp}</span>
                    </div>

                    <div>
                      <span className="text-forensic-500 text-[11px] block">Message Type & Status</span>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="badge badge-gray text-[10px] capitalize">{selectedMessage.message_type}</span>
                        <span className="badge badge-emerald text-[10px] uppercase">{selectedMessage.status}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Media Attachment Card (if present) */}
                {selectedMessage.media_info && (
                  <div className="card bg-forensic-950/60 border-forensic-800 p-3 space-y-2">
                    <span className="text-xs font-semibold text-accent-emerald flex items-center gap-1.5">
                      <Paperclip className="w-3.5 h-3.5" />
                      Attachment Metadata
                    </span>

                    <div className="text-xs space-y-1 font-mono text-forensic-300">
                      <div>
                        <span className="text-forensic-500 text-[11px]">Type:</span> {selectedMessage.media_info.media_type}
                      </div>
                      {selectedMessage.media_info.sha256 && (
                        <div>
                          <span className="text-forensic-500 text-[11px]">SHA-256:</span>{' '}
                          <span className="text-accent-cyan">{selectedMessage.media_info.sha256.substring(0, 16)}...</span>
                        </div>
                      )}
                    </div>

                    <button
                      onClick={() => handleOpenExif(selectedMessage.media_info)}
                      className="btn-primary w-full py-1.5 text-xs inline-flex items-center justify-center gap-1.5 mt-2"
                    >
                      <Camera className="w-3.5 h-3.5" />
                      Open Full EXIF Inspector
                    </button>
                  </div>
                )}

                {/* Raw JSON Data Accordion */}
                <details className="card bg-forensic-950/60 border-forensic-800 p-3 text-xs">
                  <summary className="font-mono font-medium text-forensic-400 cursor-pointer hover:text-forensic-200 flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <Code className="w-3.5 h-3.5 text-accent-violet" />
                      Raw JSON Message Payload
                    </span>
                    <ChevronRight className="w-3.5 h-3.5 transition-transform group-open:rotate-90" />
                  </summary>
                  <pre className="mt-3 p-2 bg-forensic-900 rounded border border-forensic-800 font-mono text-[10px] text-forensic-300 overflow-x-auto">
                    {JSON.stringify(selectedMessage, null, 2)}
                  </pre>
                </details>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-forensic-500 text-xs text-center py-12">
                <Info className="w-8 h-8 mb-2 opacity-30" />
                <span>Select any message bubble to inspect its cryptographic signature and raw forensic metadata.</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* EXIF Drawer Component */}
      <ExifMetadataDrawer
        isOpen={exifDrawerState.isOpen}
        onClose={() => setExifDrawerState({ ...exifDrawerState, isOpen: false })}
        evidenceId={exifDrawerState.evidenceId}
        fileId={exifDrawerState.fileId}
        fileName={exifDrawerState.fileName}
      />

      {/* Phase 15: Forensic AI Assistant & Copilot Drawer */}
      <ForensicAssistantDrawer
        isOpen={isAssistantOpen}
        onClose={() => setIsAssistantOpen(false)}
        caseId={caseId}
        activeJid={selectedJid}
        activeThreadName={activeThreadInfo?.name}
        onSelectCitation={handleSelectCitation}
      />
    </CaseWorkspacePage>
  );
};

export default ChatViewerPage;
