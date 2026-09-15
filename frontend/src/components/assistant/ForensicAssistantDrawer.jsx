import { useState, useEffect, useRef } from 'react';
import {
  Bot,
  X,
  Send,
  Sparkles,
  AlertTriangle,
  ShieldAlert,
  ShieldCheck,
  Flame,
  Search,
  CheckCircle2,
  Clock,
  ArrowRight,
  TrendingUp,
  DollarSign,
  Trash2,
  Lock,
  MessageSquare,
  Loader2,
  RotateCcw,
} from 'lucide-react';
import useAiAssistant from '../../hooks/useAiAssistant';

const QUICK_PROMPTS = [
  { label: 'Scan for Financial Demands', query: 'Find any messages demanding money, crypto, ransom, or wire transfers' },
  { label: 'Detect Coercion & Threats', query: 'Identify coercive threats, blackmail, intimidation, or aggressive phrasing' },
  { label: 'Find Deletion Mentions', query: 'Detect mentions of deleting chats, clearing history, or disappearing messages' },
  { label: 'Check Covert Apps', query: 'Identify references to Signal, Telegram secret chat, burner phones, or offline meetings' },
  { label: 'Summarize Suspect Behavior', query: 'Summarize overall suspicious patterns and evasive tone across this case' },
];

const ForensicAssistantDrawer = ({
  isOpen,
  onClose,
  caseId,
  activeJid = null,
  activeThreadName = null,
  onSelectCitation = null,
}) => {
  const {
    queryHistory,
    loadingQuery,
    queryError,
    submitQuery,
    sentimentData,
    loadingSentiment,
    loadSentiment,
    clearHistory,
  } = useAiAssistant(caseId);

  const [inputQuery, setInputQuery] = useState('');
  const [activeTab, setActiveTab] = useState('copilot'); // 'copilot' | 'breakdown'
  const chatEndRef = useRef(null);

  // Load sentiment data when drawer opens
  useEffect(() => {
    if (isOpen && caseId) {
      loadSentiment(activeJid || undefined);
    }
  }, [isOpen, caseId, activeJid, loadSentiment]);

  // Scroll to bottom when new query arrives
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [queryHistory, loadingQuery]);

  if (!isOpen) return null;

  const handleSend = async (textToSend) => {
    const q = textToSend || inputQuery;
    if (!q?.trim() || loadingQuery) return;
    setInputQuery('');
    await submitQuery(q, activeJid || undefined);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const aggregate = sentimentData?.aggregate || {
    total_analyzed: 0,
    average_suspicion_score: 0,
    highest_suspicion_score: 0,
    tone_distribution: {},
    intention_counts: {},
    high_risk_message_count: 0,
  };

  const toneColors = {
    Aggressive: 'text-accent-rose bg-accent-rose/10 border-accent-rose/30',
    Suspicious: 'text-amber-400 bg-amber-400/10 border-amber-400/30',
    Deceptive: 'text-purple-400 bg-purple-400/10 border-purple-400/30',
    Urgent: 'text-orange-400 bg-orange-400/10 border-orange-400/30',
    Evasive: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30',
    Neutral: 'text-forensic-400 bg-forensic-800/40 border-forensic-700',
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      {/* Backdrop click to close */}
      <div className="flex-1" onClick={onClose} />

      {/* Drawer Container */}
      <div className="w-full max-w-2xl bg-forensic-900 border-l border-forensic-700 shadow-2xl flex flex-col h-full animate-in slide-in-from-right duration-300">
        {/* ======================================================== */}
        {/* DRAWER HEADER */}
        {/* ======================================================== */}
        <div className="p-4 border-b border-forensic-800 bg-forensic-950/90 flex flex-col gap-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-accent-cyan/20 border border-accent-cyan/40 flex items-center justify-center text-accent-cyan shadow-sm">
                <Bot className="w-5 h-5" />
              </div>
              <div>
                <h2 className="font-bold text-sm text-forensic-100 flex items-center gap-2">
                  Forensic AI Copilot
                  <span className="badge badge-cyan text-[10px] uppercase font-mono">
                    Investigative Aid
                  </span>
                </h2>
                <p className="text-xs text-forensic-400 font-mono">
                  {activeThreadName ? `Context: ${activeThreadName}` : `Case #${caseId} Evidence Scope`}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {queryHistory.length > 0 && (
                <button
                  onClick={clearHistory}
                  title="Clear conversation"
                  className="p-1.5 rounded-lg text-forensic-400 hover:text-forensic-200 hover:bg-forensic-800 transition-colors text-xs inline-flex items-center gap-1"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline text-[11px]">Clear</span>
                </button>
              )}
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg text-forensic-400 hover:text-forensic-100 hover:bg-forensic-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* CRITICAL LEGAL ISOLATION DISCLAIMER BADGE */}
          <div className="px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px] font-mono flex items-center gap-2 shadow-inner">
            <ShieldAlert className="w-4 h-4 flex-shrink-0 text-amber-400" />
            <span className="leading-tight">
              <strong>Internal Investigative Aid Only</strong> — Excluded from Legal Court Reports to preserve judicial admissibility.
            </span>
          </div>

          {/* Sub-Tabs: Copilot Query vs Sentiment Breakdown */}
          <div className="flex items-center gap-2 pt-1 border-t border-forensic-800/80">
            <button
              onClick={() => setActiveTab('copilot')}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors flex items-center gap-1.5 ${
                activeTab === 'copilot'
                  ? 'bg-accent-cyan/20 text-accent-cyan border border-accent-cyan/30'
                  : 'text-forensic-400 hover:text-forensic-200 hover:bg-forensic-800'
              }`}
            >
              <Bot className="w-3.5 h-3.5" />
              Investigator Copilot
            </button>
            <button
              onClick={() => setActiveTab('breakdown')}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors flex items-center gap-1.5 ${
                activeTab === 'breakdown'
                  ? 'bg-accent-cyan/20 text-accent-cyan border border-accent-cyan/30'
                  : 'text-forensic-400 hover:text-forensic-200 hover:bg-forensic-800'
              }`}
            >
              <TrendingUp className="w-3.5 h-3.5" />
              Sentiment & Intent Analysis ({aggregate.total_analyzed})
            </button>
          </div>
        </div>

        {/* ======================================================== */}
        {/* DRAWER BODY */}
        {/* ======================================================== */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {activeTab === 'breakdown' ? (
            /* ==================================================== */
            /* TAB 2: SENTIMENT & INTENTION BREAKDOWN WIDGET */
            /* ==================================================== */
            <div className="space-y-4 animate-in fade-in">
              {loadingSentiment ? (
                <div className="p-8 text-center text-forensic-400 text-xs">
                  <Loader2 className="w-6 h-6 animate-spin text-accent-cyan mx-auto mb-2" />
                  Calculating sentiment distribution and intention markers...
                </div>
              ) : (
                <>
                  {/* Top Stats Overview */}
                  <div className="grid grid-cols-3 gap-3">
                    <div className="card p-3 bg-forensic-950/80 border-forensic-800">
                      <div className="text-[11px] text-forensic-400 font-mono mb-1">Messages Analyzed</div>
                      <div className="text-xl font-bold font-mono text-forensic-100">
                        {aggregate.total_analyzed}
                      </div>
                    </div>
                    <div className="card p-3 bg-forensic-950/80 border-forensic-800">
                      <div className="text-[11px] text-forensic-400 font-mono mb-1">Avg Suspicion</div>
                      <div className="text-xl font-bold font-mono text-accent-cyan">
                        {aggregate.average_suspicion_score}%
                      </div>
                    </div>
                    <div className="card p-3 bg-forensic-950/80 border-accent-rose/30">
                      <div className="text-[11px] text-accent-rose font-mono mb-1">Peak Suspicion</div>
                      <div className="text-xl font-bold font-mono text-accent-rose">
                        {aggregate.highest_suspicion_score}%
                      </div>
                    </div>
                  </div>

                  {/* Emotional Tone Distribution */}
                  <div className="card p-4 bg-forensic-950/80 border-forensic-800 space-y-3">
                    <h3 className="font-semibold text-xs text-forensic-200 uppercase tracking-wider font-mono flex items-center justify-between">
                      <span>Emotional Tone Classification</span>
                      <span className="text-[10px] text-forensic-500 font-normal">NLP Lexical Analysis</span>
                    </h3>

                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                      {Object.entries(aggregate.tone_distribution || {}).map(([tone, count]) => {
                        const style = toneColors[tone] || toneColors.Neutral;
                        const pct = aggregate.total_analyzed
                          ? Math.round((count / aggregate.total_analyzed) * 100)
                          : 0;

                        return (
                          <div key={tone} className={`p-2.5 rounded-lg border flex flex-col justify-between ${style}`}>
                            <div className="flex items-center justify-between text-xs font-medium">
                              <span>{tone}</span>
                              <span className="font-mono text-xs">{count}</span>
                            </div>
                            <div className="text-[10px] opacity-75 font-mono mt-1">
                              {pct}% of messages
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Intention Markers Detection Widget */}
                  <div className="card p-4 bg-forensic-950/80 border-forensic-800 space-y-3">
                    <h3 className="font-semibold text-xs text-forensic-200 uppercase tracking-wider font-mono flex items-center justify-between">
                      <span>Detected Intention Markers</span>
                      <span className="text-[10px] text-forensic-500 font-normal">Forensic Indicators</span>
                    </h3>

                    <div className="space-y-2.5">
                      <div className="flex items-center justify-between p-2.5 rounded-lg bg-forensic-900 border border-forensic-800">
                        <div className="flex items-center gap-2 text-xs">
                          <DollarSign className="w-4 h-4 text-emerald-400" />
                          <span className="text-forensic-200 font-medium">Financial Demands & Crypto Cues</span>
                        </div>
                        <span className="badge badge-emerald font-mono text-xs">
                          {aggregate.intention_counts?.financial_demand || 0} flagged
                        </span>
                      </div>

                      <div className="flex items-center justify-between p-2.5 rounded-lg bg-forensic-900 border border-forensic-800">
                        <div className="flex items-center gap-2 text-xs">
                          <Flame className="w-4 h-4 text-accent-rose" />
                          <span className="text-forensic-200 font-medium">Coercion, Blackmail & Threat Language</span>
                        </div>
                        <span className="badge badge-rose font-mono text-xs">
                          {aggregate.intention_counts?.coercion || 0} flagged
                        </span>
                      </div>

                      <div className="flex items-center justify-between p-2.5 rounded-lg bg-forensic-900 border border-forensic-800">
                        <div className="flex items-center gap-2 text-xs">
                          <Trash2 className="w-4 h-4 text-amber-400" />
                          <span className="text-forensic-200 font-medium">Deletion & Chat Wiping Awareness</span>
                        </div>
                        <span className="badge badge-amber font-mono text-xs">
                          {aggregate.intention_counts?.deletion_awareness || 0} flagged
                        </span>
                      </div>

                      <div className="flex items-center justify-between p-2.5 rounded-lg bg-forensic-900 border border-forensic-800">
                        <div className="flex items-center gap-2 text-xs">
                          <Lock className="w-4 h-4 text-purple-400" />
                          <span className="text-forensic-200 font-medium">Covert Communication & Burner Channels</span>
                        </div>
                        <span className="badge badge-purple font-mono text-xs">
                          {aggregate.intention_counts?.covert_communication || 0} flagged
                        </span>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          ) : (
            /* ==================================================== */
            /* TAB 1: CONVERSATIONAL COPILOT FEED */
            /* ==================================================== */
            <div className="space-y-4">
              {/* Welcome / Quick Prompts */}
              {queryHistory.length === 0 && (
                <div className="space-y-3">
                  <div className="p-4 rounded-xl bg-forensic-950 border border-forensic-800 text-xs text-forensic-300 space-y-2">
                    <p className="font-semibold text-forensic-100 flex items-center gap-1.5 text-sm">
                      <Sparkles className="w-4 h-4 text-accent-cyan" />
                      Investigative Assistant Ready
                    </p>
                    <p className="text-forensic-400 leading-relaxed">
                      Ask natural language questions to search through decrypted WhatsApp and Telegram transcripts, detect criminal intent, inspect extortion attempts, and isolate high-risk chat sequences.
                    </p>
                  </div>

                  <div>
                    <span className="text-[11px] font-mono text-forensic-500 uppercase tracking-wider block mb-2">
                      Suggested Inquiries
                    </span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {QUICK_PROMPTS.map((qp, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleSend(qp.query)}
                          className="text-left p-2.5 rounded-lg bg-forensic-950 border border-forensic-800 hover:border-accent-cyan/50 hover:bg-forensic-800/40 transition-colors group"
                        >
                          <span className="text-xs text-forensic-200 font-medium group-hover:text-accent-cyan flex items-center justify-between">
                            {qp.label}
                            <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                          </span>
                          <span className="text-[11px] text-forensic-500 line-clamp-1 mt-0.5 font-mono">
                            {qp.query}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Chat History Messages */}
              {queryHistory.map((item) => (
                <div key={item.id} className="space-y-3 animate-in fade-in">
                  {/* Investigator Prompt */}
                  <div className="flex items-start gap-2.5 justify-end">
                    <div className="max-w-[85%] p-3 rounded-xl rounded-tr-none bg-accent-cyan/15 border border-accent-cyan/30 text-xs text-forensic-100 font-medium shadow-sm">
                      <p className="whitespace-pre-wrap">{item.query}</p>
                      <span className="text-[10px] text-accent-cyan/70 font-mono block text-right mt-1">
                        {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>

                  {/* Assistant Copilot Response */}
                  {item.loading ? (
                    <div className="flex items-center gap-2 p-3.5 rounded-xl bg-forensic-950 border border-forensic-800 text-xs text-forensic-400">
                      <Loader2 className="w-4 h-4 animate-spin text-accent-cyan" />
                      <span>Scanning message transcripts, analyzing sentiment tones and intentions...</span>
                    </div>
                  ) : item.error ? (
                    <div className="p-3.5 rounded-xl bg-accent-rose/10 border border-accent-rose/30 text-xs text-accent-rose">
                      {item.error}
                    </div>
                  ) : item.response ? (
                    <div className="p-4 rounded-xl bg-forensic-950 border border-forensic-800 space-y-3.5 shadow-md">
                      {/* Response Header & Risk Badge */}
                      <div className="flex items-center justify-between border-b border-forensic-800 pb-2">
                        <div className="flex items-center gap-2">
                          <Bot className="w-4 h-4 text-accent-cyan" />
                          <span className="font-semibold text-xs text-forensic-100 font-mono">
                            Forensic Finding ({item.response.total_matches} match{item.response.total_matches === 1 ? '' : 'es'})
                          </span>
                        </div>
                        <span
                          className={`badge text-[10px] font-mono ${
                            item.response.risk_level === 'CRITICAL'
                              ? 'badge-rose'
                              : item.response.risk_level === 'HIGH'
                              ? 'badge-amber'
                              : item.response.risk_level === 'MODERATE'
                              ? 'badge-cyan'
                              : 'badge-gray'
                          }`}
                        >
                          RISK: {item.response.risk_level}
                        </span>
                      </div>

                      {/* Summary Analysis */}
                      <p className="text-xs text-forensic-200 leading-relaxed font-sans">
                        {item.response.summary}
                      </p>

                      {/* Recommended Actions */}
                      {item.response.recommended_actions?.length > 0 && (
                        <div className="p-2.5 rounded-lg bg-forensic-900 border border-forensic-800/80 space-y-1.5">
                          <span className="text-[10px] font-mono text-accent-cyan uppercase tracking-wider flex items-center gap-1 font-semibold">
                            <CheckCircle2 className="w-3 h-3" /> Recommended Investigative Next Steps:
                          </span>
                          <ul className="list-disc list-inside text-[11px] text-forensic-300 space-y-1">
                            {item.response.recommended_actions.map((act, i) => (
                              <li key={i}>{act}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Citations List */}
                      {item.response.findings?.length > 0 && (
                        <div className="space-y-2 pt-1">
                          <span className="text-[10px] font-mono text-forensic-400 uppercase tracking-wider block">
                            Citations & Identified Transcripts
                          </span>
                          <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                            {item.response.findings.map((f, fIdx) => (
                              <div
                                key={f.id || fIdx}
                                onClick={() => onSelectCitation && onSelectCitation(f)}
                                className="p-2.5 rounded-lg bg-forensic-900/90 border border-forensic-800 hover:border-accent-cyan/40 transition-colors cursor-pointer text-xs space-y-1.5"
                              >
                                <div className="flex items-center justify-between text-[10px] text-forensic-400 font-mono">
                                  <span className="text-accent-cyan font-medium flex items-center gap-1 truncate max-w-[200px]">
                                    <MessageSquare className="w-3 h-3" />
                                    {f.sender || f.chat_jid}
                                  </span>
                                  <div className="flex items-center gap-2">
                                    <span className={`px-1.5 py-0.2 rounded text-[10px] border ${toneColors[f.tone] || toneColors.Neutral}`}>
                                      {f.tone}
                                    </span>
                                    <span className="text-accent-rose font-semibold">
                                      {f.suspicion_score}% Suspicion
                                    </span>
                                  </div>
                                </div>

                                <p className="text-xs text-forensic-100 font-sans italic bg-forensic-950/60 p-2 rounded border border-forensic-800/40">
                                  "{f.body}"
                                </p>

                                {f.intentions?.length > 0 && (
                                  <div className="flex flex-wrap gap-1 pt-0.5">
                                    {f.intentions.map((intent) => (
                                      <span key={intent} className="badge badge-gray text-[9px] uppercase font-mono">
                                        {intent.replace('_', ' ')}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : null}
                </div>
              ))}

              <div ref={chatEndRef} />
            </div>
          )}
        </div>

        {/* ======================================================== */}
        {/* DRAWER FOOTER: INPUT BOX */}
        {/* ======================================================== */}
        {activeTab === 'copilot' && (
          <div className="p-3 border-t border-forensic-800 bg-forensic-950/90 flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask copilot: e.g. 'Show messages demanding cash or bitcoin'..."
                className="input text-xs flex-1 py-2 font-mono"
                disabled={loadingQuery}
              />
              <button
                onClick={() => handleSend()}
                disabled={loadingQuery || !inputQuery.trim()}
                className="btn-primary py-2 px-3 text-xs inline-flex items-center gap-1.5"
              >
                {loadingQuery ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <Send className="w-3.5 h-3.5" />
                    <span>Ask</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ForensicAssistantDrawer;
