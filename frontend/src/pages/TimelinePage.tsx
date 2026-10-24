import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useActiveCase } from '../context/CaseContext';
import { timelineService } from '../services/timelineService';

// --- Helper Formatter Functions ---

/** Formats contact references and raw JIDs into clean human-readable names */
export const formatContactLabel = (rawRef) => {
  if (!rawRef) return 'System / Unassigned';
  const str = String(rawRef).trim();
  if (str === 'me' || str === 'from_me') return 'Me (Device Owner)';
  if (str === 'status@broadcast') return 'WhatsApp Status (Broadcast)';
  if (str.startsWith('tg_dialog_')) return `Telegram Dialog #${str.replace('tg_dialog_', '')}`;
  if (str.startsWith('tg_user_')) return `Telegram User #${str.replace('tg_user_', '')}`;
  if (str === '-1') return 'Unassigned Contact';
  
  // Format WhatsApp numbers: e.g. 19195790479@s.whatsapp.net -> +1 (919) 579-0479
  if (str.endsWith('@s.whatsapp.net')) {
    const digits = str.replace('@s.whatsapp.net', '');
    if (digits.length === 11 && digits.startsWith('1')) {
      return `+1 (${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7)}`;
    }
    if (digits.length === 12 && digits.startsWith('91')) {
      return `+91 ${digits.slice(2, 7)} ${digits.slice(7)}`;
    }
    return `+${digits}`;
  }
  if (str.includes('@g.us')) {
    const base = str.replace('@g.us', '');
    const parts = base.split('-');
    return `WhatsApp Group (${parts[0] ? `+${parts[0]}` : base.slice(0, 12)}...)`;
  }
  return str;
};

/** Formats UTC milliseconds into structured date, time, and day-group key */
export const formatEventDateTime = (utcMs?: any, rawTs?: any, normTs?: any) => {
  let ms = utcMs;
  if (!ms && normTs) {
    const d = new Date(normTs);
    if (!isNaN(d.getTime())) ms = d.getTime();
  }
  if (!ms && rawTs) {
    if (typeof rawTs === 'number') {
      ms = rawTs > 100000000000 ? rawTs : rawTs * 1000;
    } else if (typeof rawTs === 'string') {
      const parsed = Date.parse(rawTs);
      if (!isNaN(parsed)) ms = parsed;
    }
  }

  if (!ms || isNaN(ms)) {
    return {
      time: 'Undated',
      dateLabel: 'Undated Events',
      fullIso: 'Undated',
      dateKey: 'undated',
      ms: 0,
    };
  }

  const d = new Date(ms);
  const timeStr = d.toISOString().substring(11, 19) + ' UTC';
  const fullIso = d.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
  const dateKey = d.toISOString().substring(0, 10);
  const dateLabel = d.toLocaleDateString('en-US', {
    timeZone: 'UTC',
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });

  return { time: timeStr, dateLabel, fullIso, dateKey, ms };
};

/** Checks if an event is an outgoing message from the device owner */
export const isOutgoingEvent = (event) => {
  const actor = String(event.actor_ref || '').toLowerCase();
  if (actor === 'me' || actor === 'from_me' || actor === 'self') return true;
  if (event.metadata_?.from_me === 1 || event.metadata_?.from_me === true) return true;
  if (event.metadata_?.is_outgoing === true) return true;
  return false;
};

export default function TimelinePage() {
  const { activeCase } = useActiveCase();
  const caseId = activeCase?.id;

  // --- Core State ---
  const [events, setEvents] = useState([]);
  const [errorMessage, setErrorMessage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);

  // --- Filtering & Navigation State ---
  const [platformTab, setPlatformTab] = useState('all'); // 'all' | 'whatsapp' | 'telegram' | 'system'
  const [selectedThread, setSelectedThread] = useState('all'); // 'all' | threadKey
  const [threadSearch, setThreadSearch] = useState('');
  const [messageSearch, setMessageSearch] = useState('');
  const [eventTypeFilter, setEventTypeFilter] = useState('all'); // 'all' | 'message' | 'revocation' | 'edit' | 'media'
  const [sortOrder, setSortOrder] = useState('asc'); // 'asc' = chronological (oldest to newest)
  const [viewMode, setViewMode] = useState('dialogue'); // 'dialogue' | 'ledger'
  const [expandedEventId, setExpandedEventId] = useState(null);

  const feedBottomRef = useRef(null);

  // --- Fetch Events ---
  const loadTimeline = useCallback(async () => {
    if (!caseId) {
      setEvents([]);
      return;
    }
    setLoading(true);
    setErrorMessage(null);
    try {
      await timelineService.buildTimeline(caseId);
      const data = await timelineService.getTimeline(caseId);
      const list = Array.isArray(data) ? data : (data?.events || []);
      setEvents(list);

      // Auto-rebuild if empty or only system events
      if (list.length === 0 || list.every((e) => e.event_type === 'system')) {
        try {
          await timelineService.buildTimeline(caseId);
          const rebuilt = await timelineService.getTimeline(caseId);
          setEvents(Array.isArray(rebuilt) ? rebuilt : (rebuilt?.events || []));
        } catch {
          // ignore auto-build errors
        }
      }
    } catch (err) {
      console.warn('Error fetching timeline events:', err);
      setErrorMessage(err.response?.data?.detail || 'Timeline could not be rebuilt. Check evidence integrity and retry.');
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    loadTimeline();
  }, [loadTimeline]);

  const handleRebuild = async () => {
    if (!caseId) return;
    setRebuilding(true);
    try {
      await timelineService.buildTimeline(caseId);
      await loadTimeline();
    } catch (err) {
      console.error('Failed to rebuild timeline:', err);
      setErrorMessage(err.response?.data?.detail || 'Timeline rebuild failed.');
    } finally {
      setRebuilding(false);
    }
  };

  // --- Platform Breakdown Counts ---
  const platformCounts = useMemo(() => {
    let whatsapp = 0;
    let telegram = 0;
    let system = 0;

    events.forEach((e) => {
      const app = (e.source_app || e.app || (e.source_type?.toLowerCase().includes('wa') ? 'whatsapp' : 'telegram')).toLowerCase();
      if (app.includes('wa')) whatsapp++;
      else if (app.includes('tg') || app.includes('telegram')) telegram++;
      else system++;
    });

    return {
      all: events.length,
      whatsapp,
      telegram,
      system,
    };
  }, [events]);

  // --- Conversation Threads Aggregation (User-wise) ---
  const conversationThreads = useMemo(() => {
    const threadMap = new Map();

    events.forEach((e) => {
      const app = (e.source_app || e.app || (e.source_type?.toLowerCase().includes('wa') ? 'whatsapp' : 'telegram')).toLowerCase();
      const platform = app.includes('wa') ? 'whatsapp' : (app.includes('tg') || app.includes('telegram')) ? 'telegram' : 'system';
      
      const threadKey = e.chat_ref || (platform === 'system' ? '__system__' : (e.actor_ref || 'unknown'));
      const formattedName = platform === 'system' ? 'System Forensic Exhibits' : formatContactLabel(threadKey);

      if (!threadMap.has(threadKey)) {
        threadMap.set(threadKey, {
          key: threadKey,
          name: formattedName,
          platform,
          messageCount: 0,
          revocationCount: 0,
          editCount: 0,
          earliestMs: Infinity,
          latestMs: -Infinity,
          latestSummary: '',
          participants: new Set(),
        });
      }

      const t = threadMap.get(threadKey);
      t.messageCount++;

      const type = (e.event_type || e.kind || '').toLowerCase();
      if (type.includes('revocation')) t.revocationCount++;
      if (type.includes('edit')) t.editCount++;

      const dt = formatEventDateTime(e.utc_ms, e.raw_timestamp || e.timestamp, e.normalized_timestamp);
      if (dt.ms > 0) {
        if (dt.ms < t.earliestMs) t.earliestMs = dt.ms;
        if (dt.ms >= t.latestMs) {
          t.latestMs = dt.ms;
          t.latestSummary = e.summary || e.description || '';
        }
      }

      if (e.actor_ref && e.actor_ref !== 'me') {
        t.participants.add(e.actor_ref);
      }
    });

    return Array.from(threadMap.values()).sort((a, b) => b.latestMs - a.latestMs);
  }, [events]);

  // Filter conversation threads by platform and thread search
  const visibleThreads = useMemo(() => {
    return conversationThreads.filter((t) => {
      // Platform filter
      if (platformTab === 'whatsapp' && t.platform !== 'whatsapp') return false;
      if (platformTab === 'telegram' && t.platform !== 'telegram') return false;
      if (platformTab === 'system' && t.platform !== 'system') return false;

      // Text search in thread title or key
      if (threadSearch.trim()) {
        const query = threadSearch.toLowerCase();
        if (!t.name.toLowerCase().includes(query) && !t.key.toLowerCase().includes(query)) {
          return false;
        }
      }

      return true;
    });
  }, [conversationThreads, platformTab, threadSearch]);

  // --- Filtered and Chronologically Sorted Events ---
  const filteredEvents = useMemo(() => {
    const list = events.filter((e) => {
      const app = (e.source_app || e.app || (e.source_type?.toLowerCase().includes('wa') ? 'whatsapp' : 'telegram')).toLowerCase();
      const platform = app.includes('wa') ? 'whatsapp' : (app.includes('tg') || app.includes('telegram')) ? 'telegram' : 'system';

      // 1. Platform Filter
      if (platformTab === 'whatsapp' && platform !== 'whatsapp') return false;
      if (platformTab === 'telegram' && platform !== 'telegram') return false;
      if (platformTab === 'system' && platform !== 'system') return false;

      // 2. Conversation / User Thread Filter
      if (selectedThread !== 'all') {
        const threadKey = e.chat_ref || (platform === 'system' ? '__system__' : (e.actor_ref || 'unknown'));
        if (threadKey !== selectedThread) return false;
      }

      // 3. Event Type Filter
      if (eventTypeFilter !== 'all') {
        const type = (e.event_type || e.kind || '').toLowerCase();
        if (eventTypeFilter === 'message' && !type.includes('message')) return false;
        if (eventTypeFilter === 'revocation' && !type.includes('revocation')) return false;
        if (eventTypeFilter === 'edit' && !type.includes('edit')) return false;
        if (eventTypeFilter === 'media' && !type.includes('media') && !type.includes('location')) return false;
      }

      // 4. Message Content / Actor Search
      if (messageSearch.trim()) {
        const q = messageSearch.toLowerCase();
        const content = (e.summary || e.description || e.content || '').toLowerCase();
        const actor = (e.actor_ref || '').toLowerCase();
        const chat = (e.chat_ref || '').toLowerCase();
        const eventId = (e.event_id || '').toLowerCase();
        if (!content.includes(q) && !actor.includes(q) && !chat.includes(q) && !eventId.includes(q)) {
          return false;
        }
      }

      return true;
    });

    // Total Deterministic Chronological Ordering (Rule R11)
    return list.sort((a, b) => {
      const aTime = a.utc_ms || a.timestamp || 0;
      const bTime = b.utc_ms || b.timestamp || 0;
      if (aTime !== bTime) {
        return sortOrder === 'asc' ? aTime - bTime : bTime - aTime;
      }
      // Tie-breaker: canonical event_id
      return String(a.event_id || a.id).localeCompare(String(b.event_id || b.id));
    });
  }, [events, platformTab, selectedThread, eventTypeFilter, messageSearch, sortOrder]);

  // --- Group Events by Calendar Day for Dialogue View ---
  const groupedEventsByDay = useMemo(() => {
    const groups = [];
    let currentGroup = null;

    filteredEvents.forEach((ev, idx) => {
      const dt = formatEventDateTime(ev.utc_ms, ev.raw_timestamp || ev.timestamp, ev.normalized_timestamp);
      const groupKey = dt.dateKey;

      if (!currentGroup || currentGroup.dateKey !== groupKey) {
        currentGroup = {
          dateKey: groupKey,
          dateLabel: dt.dateLabel,
          events: [],
        };
        groups.push(currentGroup);
      }

      currentGroup.events.push({
        event: ev,
        dt,
        index: idx,
      });
    });

    return groups;
  }, [filteredEvents]);

  // Selected Thread Details
  const activeThreadObj = useMemo(() => {
    if (selectedThread === 'all') return null;
    return conversationThreads.find((t) => t.key === selectedThread);
  }, [selectedThread, conversationThreads]);

  const scrollToBottom = () => {
    feedBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden">
      {errorMessage && <div role="alert" className="p-3 text-red-600">{String(errorMessage)}</div>}
      {/* Top Header & Platform Switcher Bar */}
      <header className="border-b border-outline-variant bg-surface-container px-4 py-2.5 space-y-2 shrink-0">
        <div className="flex flex-wrap justify-between items-center gap-3">
          {/* Title and Case Context */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
              <span className="material-symbols-outlined text-xl">forum</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-semibold text-on-surface tracking-tight">
                  Chronological Conversation &amp; Timeline Reconstruction
                </h1>
                <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-primary/15 border border-primary/30 text-primary font-semibold">
                  Case #{activeCase?.id || caseId || 'N/A'}
                </span>
                {events.length > 0 && (
                  <span className="px-2 py-0.5 text-[11px] font-mono rounded bg-tertiary/15 border border-tertiary/30 text-tertiary font-medium flex items-center gap-1">
                    <span className="material-symbols-outlined text-[13px]">verified</span>
                    {events.length} Events Sequenced
                  </span>
                )}
              </div>
              <p className="text-[11px] text-on-surface-variant">
                Arranged chronologically by interlocutor dialogue, platform source, and deterministic audit chain.
              </p>
            </div>
          </div>

          {/* Top Actions: Sort, Ledger/Dialogue Toggle, Rebuild */}
          <div className="flex items-center gap-2">
            {/* View Mode Toggle */}
            <div className="flex items-center bg-surface-container-lowest border border-outline-variant rounded p-0.5 text-xs">
              <button
                type="button"
                onClick={() => setViewMode('dialogue')}
                className={`px-2.5 py-1 rounded flex items-center gap-1.5 transition-all font-medium text-xs ${
                  viewMode === 'dialogue'
                    ? 'bg-primary text-on-primary shadow-sm'
                    : 'text-on-surface-variant hover:text-on-surface'
                }`}
                title="Conversational Speech Bubble View"
              >
                <span className="material-symbols-outlined text-[14px]">chat_bubble</span>
                <span>Chat Dialogue</span>
              </button>
              <button
                type="button"
                onClick={() => setViewMode('ledger')}
                className={`px-2.5 py-1 rounded flex items-center gap-1.5 transition-all font-medium text-xs ${
                  viewMode === 'ledger'
                    ? 'bg-primary text-on-primary shadow-sm'
                    : 'text-on-surface-variant hover:text-on-surface'
                }`}
                title="Forensic Audit Table View"
              >
                <span className="material-symbols-outlined text-[14px]">table_rows</span>
                <span>Audit Ledger</span>
              </button>
            </div>

            {/* Chronological Sort Direction Toggle */}
            <button
              type="button"
              onClick={() => setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))}
              className="btn-secondary text-xs h-7.5 px-2.5 flex items-center gap-1"
              title={sortOrder === 'asc' ? 'Chronological: Oldest First' : 'Reverse: Newest First'}
            >
              <span className="material-symbols-outlined text-[14px] text-primary">
                {sortOrder === 'asc' ? 'arrow_downward' : 'arrow_upward'}
              </span>
              <span className="font-mono text-[11px]">
                {sortOrder === 'asc' ? 'Oldest → Newest' : 'Newest → Oldest'}
              </span>
            </button>

            {/* Rebuild Timeline Button */}
            <button
              type="button"
              disabled={rebuilding || !caseId}
              onClick={handleRebuild}
              className="btn-primary text-xs h-7.5 px-3 flex items-center gap-1.5"
            >
              <span className={`material-symbols-outlined text-[14px] ${rebuilding ? 'animate-spin' : ''}`}>
                sync
              </span>
              <span>{rebuilding ? 'Sequencing...' : 'Rebuild Timeline'}</span>
            </button>
          </div>
        </div>

        {/* Platform Selector Tabs */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-1 border-t border-outline-variant/60">
          <div className="flex items-center gap-1.5 bg-surface-container-lowest p-1 rounded-lg border border-outline-variant">
            <button
              type="button"
              onClick={() => {
                setPlatformTab('all');
                setSelectedThread('all');
              }}
              className={`px-3 py-1 rounded text-xs font-medium flex items-center gap-1.5 transition-all ${
                platformTab === 'all'
                  ? 'bg-surface-container-highest text-on-surface border border-outline-variant shadow-sm'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              <span className="material-symbols-outlined text-[14px] text-primary">hub</span>
              <span>All Platforms</span>
              <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-surface-container border border-outline-variant">
                {platformCounts.all}
              </span>
            </button>

            <button
              type="button"
              onClick={() => {
                setPlatformTab('whatsapp');
                setSelectedThread('all');
              }}
              className={`px-3 py-1 rounded text-xs font-medium flex items-center gap-1.5 transition-all ${
                platformTab === 'whatsapp'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm'
                  : 'text-on-surface-variant hover:text-emerald-300'
              }`}
            >
              <span className="material-symbols-outlined text-[14px] text-emerald-400">chat</span>
              <span>WhatsApp</span>
              <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-emerald-500/15 border border-emerald-500/30 text-emerald-300">
                {platformCounts.whatsapp}
              </span>
            </button>

            <button
              type="button"
              onClick={() => {
                setPlatformTab('telegram');
                setSelectedThread('all');
              }}
              className={`px-3 py-1 rounded text-xs font-medium flex items-center gap-1.5 transition-all ${
                platformTab === 'telegram'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                  : 'text-on-surface-variant hover:text-cyan-300'
              }`}
            >
              <span className="material-symbols-outlined text-[14px] text-cyan-400">send</span>
              <span>Telegram</span>
              <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-cyan-500/15 border border-cyan-500/30 text-cyan-300">
                {platformCounts.telegram}
              </span>
            </button>

            <button
              type="button"
              onClick={() => {
                setPlatformTab('system');
                setSelectedThread('all');
              }}
              className={`px-3 py-1 rounded text-xs font-medium flex items-center gap-1.5 transition-all ${
                platformTab === 'system'
                  ? 'bg-slate-500/20 text-slate-200 border border-slate-500/40 shadow-sm'
                  : 'text-on-surface-variant hover:text-slate-200'
              }`}
            >
              <span className="material-symbols-outlined text-[14px] text-slate-400">inventory_2</span>
              <span>System Exhibits</span>
              <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-slate-500/15 border border-slate-500/30 text-slate-300">
                {platformCounts.system}
              </span>
            </button>
          </div>

          {/* Quick Filter: Event Type & Global Search */}
          <div className="flex items-center gap-2">
            <select
              value={eventTypeFilter}
              onChange={(e) => setEventTypeFilter(e.target.value)}
              className="h-7 px-2 rounded bg-surface-container-lowest border border-outline-variant text-[11px] text-on-surface focus:outline-none focus:border-primary cursor-pointer"
            >
              <option value="all">All Types</option>
              <option value="message">Messages Only</option>
              <option value="revocation">Revocations (Deleted)</option>
              <option value="edit">Edits Only</option>
              <option value="media">Media &amp; Locations</option>
            </select>

            <div className="relative flex items-center">
              <span className="material-symbols-outlined absolute left-2 text-[14px] text-outline">search</span>
              <input
                type="text"
                value={messageSearch}
                onChange={(e) => setMessageSearch(e.target.value)}
                placeholder="Search messages, participants..."
                className="h-7 pl-7 pr-3 rounded bg-surface-container-lowest border border-outline-variant text-on-surface placeholder:text-outline text-[11px] focus:outline-none focus:border-primary w-52"
              />
            </div>
          </div>
        </div>
      </header>

      {/* Two-Pane Workspace Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Pane: Conversations & Interlocutors (User-Wise List) */}
        <aside className="w-80 border-r border-outline-variant bg-surface-container flex flex-col shrink-0 overflow-hidden">
          {/* Interlocutor Search & Header */}
          <div className="p-2.5 border-b border-outline-variant/60 space-y-2 bg-surface-container-low shrink-0">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-on-surface flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[15px] text-primary">groups</span>
                Conversations / Users
              </span>
              <span className="font-mono text-[10px] text-on-surface-variant bg-surface-container px-1.5 py-0.5 rounded border border-outline-variant">
                {visibleThreads.length} Threads
              </span>
            </div>

            <div className="relative flex items-center">
              <span className="material-symbols-outlined absolute left-2 text-[13px] text-outline">search</span>
              <input
                type="text"
                value={threadSearch}
                onChange={(e) => setThreadSearch(e.target.value)}
                placeholder="Filter interlocutors..."
                className="h-6.5 w-full pl-6.5 pr-2 rounded bg-surface-container-lowest border border-outline-variant text-on-surface placeholder:text-outline text-[11px] focus:outline-none focus:border-primary"
              />
            </div>
          </div>

          {/* Interlocutors Scrollable List */}
          <div className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1">
            {/* Option: All Interlocutors (Unified Feed) */}
            <button
              type="button"
              onClick={() => setSelectedThread('all')}
              className={`w-full text-left p-2 rounded-lg transition-all border flex items-center gap-2.5 ${
                selectedThread === 'all'
                  ? 'bg-primary/10 border-primary/40 shadow-sm'
                  : 'bg-surface-container-lowest/60 border-transparent hover:border-outline-variant hover:bg-surface-container-lowest'
              }`}
            >
              <div className="w-8 h-8 rounded-full bg-primary/15 border border-primary/30 flex items-center justify-center text-primary shrink-0">
                <span className="material-symbols-outlined text-[16px]">all_inbox</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-1">
                  <span className="text-xs font-semibold text-on-surface truncate">
                    All Interlocutors
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-surface-container text-on-surface-variant border border-outline-variant">
                    {filteredEvents.length}
                  </span>
                </div>
                <p className="text-[10px] text-on-surface-variant truncate">
                  Unified chronological sequence
                </p>
              </div>
            </button>

            {/* Individual Conversation Cards */}
            {visibleThreads.map((thread) => {
              const isSelected = selectedThread === thread.key;
              const isWa = thread.platform === 'whatsapp';
              const isTg = thread.platform === 'telegram';
              const isSys = thread.platform === 'system';

              const lastDt = thread.latestMs > 0 ? formatEventDateTime(thread.latestMs) : null;

              return (
                <button
                  key={thread.key}
                  type="button"
                  onClick={() => setSelectedThread(thread.key)}
                  className={`w-full text-left p-2 rounded-lg transition-all border space-y-1 ${
                    isSelected
                      ? 'bg-primary/15 border-primary/50 shadow-sm'
                      : 'bg-surface-container-lowest/70 border-outline-variant/40 hover:border-outline-variant hover:bg-surface-container-lowest'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {/* Platform Badge Avatar */}
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 border ${
                        isWa
                          ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                          : isTg
                          ? 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30'
                          : 'bg-slate-500/15 text-slate-300 border-slate-500/30'
                      }`}
                    >
                      <span className="material-symbols-outlined text-[15px]">
                        {isWa ? 'chat' : isTg ? 'send' : 'inventory_2'}
                      </span>
                    </div>

                    {/* Contact Name & Last Time */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1">
                        <span className="text-xs font-semibold text-on-surface truncate" title={thread.name}>
                          {thread.name}
                        </span>
                        {lastDt && (
                          <span className="text-[9px] font-mono text-outline shrink-0">
                            {lastDt.dateKey.substring(5)}
                          </span>
                        )}
                      </div>

                      {/* Message Count & Activity */}
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-[10px] font-mono px-1 py-0.2 rounded bg-surface-container border border-outline-variant text-on-surface-variant">
                          {thread.messageCount} msgs
                        </span>
                        {thread.revocationCount > 0 && (
                          <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-red-500/20 text-red-300 border border-red-500/30">
                            🚫 {thread.revocationCount} rev
                          </span>
                        )}
                        {thread.editCount > 0 && (
                          <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                            ✏️ {thread.editCount} edit
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Snippet Preview */}
                  {thread.latestSummary && (
                    <p className="text-[10px] text-on-surface-variant truncate pl-10 border-l border-outline-variant/30 ml-4 italic">
                      "{thread.latestSummary}"
                    </p>
                  )}
                </button>
              );
            })}

            {visibleThreads.length === 0 && (
              <div className="p-6 text-center text-on-surface-variant text-xs space-y-2">
                <span className="material-symbols-outlined text-2xl text-outline">search_off</span>
                <p>No conversation threads found for this filter.</p>
              </div>
            )}
          </div>
        </aside>

        {/* Right Pane: Main Chronological Conversation Workspace */}
        <main className="flex-1 flex flex-col bg-background overflow-hidden">
          {/* Active Conversation Banner */}
          <div className="px-4 py-2 border-b border-outline-variant bg-surface-container-low flex flex-wrap items-center justify-between gap-2 shrink-0">
            <div className="flex items-center gap-2.5">
              <span className="material-symbols-outlined text-primary text-lg">
                {selectedThread === 'all' ? 'hub' : 'forum'}
              </span>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-xs font-semibold text-on-surface">
                    {activeThreadObj ? activeThreadObj.name : 'Unified Chronological Stream (All Conversations)'}
                  </h2>
                  {activeThreadObj && (
                    <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold uppercase tracking-wider ${
                      activeThreadObj.platform === 'whatsapp'
                        ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                        : activeThreadObj.platform === 'telegram'
                        ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30'
                        : 'bg-slate-500/15 text-slate-300 border border-slate-500/30'
                    }`}>
                      {activeThreadObj.platform}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 font-mono text-[10px] text-outline">
                  <span>Displaying {filteredEvents.length} chronological events</span>
                  {activeThreadObj && activeThreadObj.earliestMs > 0 && (
                    <span>
                      • Active: {formatEventDateTime(activeThreadObj.earliestMs).dateLabel} → {formatEventDateTime(activeThreadObj.latestMs).dateLabel}
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={scrollToBottom}
                className="h-6 px-2 rounded bg-surface-container border border-outline-variant text-[10px] text-on-surface-variant hover:text-on-surface flex items-center gap-1"
                title="Scroll to bottom"
              >
                <span className="material-symbols-outlined text-[13px]">vertical_align_bottom</span>
                <span>Latest</span>
              </button>
            </div>
          </div>

          {/* Conversation Body Viewport */}
          <div className="flex-1 overflow-y-auto custom-scrollbar p-4 md:p-6">
            {loading && (
              <div className="py-20 text-center font-mono text-sm text-on-surface-variant space-y-3">
                <span className="material-symbols-outlined text-3xl animate-spin text-primary">sync</span>
                <p>Sequencing conversation dialogue and timeline entries in chronological order...</p>
              </div>
            )}

            {!loading && filteredEvents.length === 0 && (
              <div className="py-20 text-center border border-dashed border-outline-variant rounded-xl bg-surface-container-low max-w-lg mx-auto p-8 space-y-3">
                <span className="material-symbols-outlined text-4xl text-outline">schedule</span>
                <h3 className="text-sm font-semibold text-on-surface">No Events Found</h3>
                <p className="text-xs text-on-surface-variant">
                  No chronological conversation records match the current platform or user filter.
                </p>
                {caseId && (
                  <button
                    type="button"
                    onClick={handleRebuild}
                    className="btn-primary text-xs h-8 inline-flex items-center gap-1.5"
                  >
                    <span className="material-symbols-outlined text-[14px]">play_arrow</span>
                    Rebuild Conversation Timeline Now
                  </button>
                )}
              </div>
            )}

            {/* --- VIEW 1: Conversational Chat Dialogue Bubbles --- */}
            {!loading && viewMode === 'dialogue' && (
              <div className="max-w-3xl mx-auto space-y-6">
                {groupedEventsByDay.map((group) => (
                  <div key={group.dateKey} className="space-y-3">
                    {/* Sticky / Centered Date Divider */}
                    <div className="flex items-center justify-center my-4 sticky top-1 z-10">
                      <div className="px-3 py-1 rounded-full bg-surface-container-highest/90 backdrop-blur border border-outline-variant/80 text-[11px] font-mono font-medium text-on-surface shadow-sm flex items-center gap-1.5">
                        <span className="material-symbols-outlined text-[13px] text-primary">calendar_today</span>
                        <span>{group.dateLabel}</span>
                        <span className="text-[10px] text-outline">({group.events.length})</span>
                      </div>
                    </div>

                    {/* Chronological Message Stream for the day */}
                    <div className="space-y-3">
                      {group.events.map(({ event: item, dt, index }) => {
                        const eventId = item.event_id || item.id || `ev-${index}`;
                        const app = (item.source_app || item.app || (item.source_type?.toLowerCase().includes('wa') ? 'whatsapp' : 'telegram')).toLowerCase();
                        const isWa = app.includes('wa');
                        const isTg = app.includes('tg') || app.includes('telegram');
                        const isSys = app.includes('system');

                        const eventType = (item.event_type || item.kind || item.type || 'message').toLowerCase();
                        const isRevocation = eventType.includes('revocation');
                        const isEdit = eventType.includes('edit');
                        const isMedia = eventType.includes('media') || eventType.includes('location');
                        const isCarved = item.isCarved || item.is_carved || eventType.includes('carved');

                        const outgoing = isOutgoingEvent(item);
                        const actorLabel = outgoing ? 'Me (Device Owner)' : formatContactLabel(item.actor_ref || item.entity_id || 'Remote Contact');
                        const content = item.summary || item.description || item.content || '[No message body]';
                        const confidenceScore = item.confidence_score !== undefined ? item.confidence_score : 1.0;
                        const isExpanded = expandedEventId === eventId;

                        // Case 1: System Exhibit Ingestion Banner
                        if (isSys || eventType === 'system') {
                          return (
                            <div
                              key={eventId}
                              className="mx-auto max-w-xl p-3 rounded-lg border border-outline-variant bg-surface-container-high/80 text-center space-y-1 my-3 shadow-xs"
                            >
                              <div className="flex items-center justify-center gap-1.5 text-xs font-semibold text-on-surface">
                                <span className="material-symbols-outlined text-[16px] text-slate-400">inventory_2</span>
                                <span>{content}</span>
                              </div>
                              <div className="flex items-center justify-center gap-3 font-mono text-[10px] text-outline">
                                <span>{dt.fullIso}</span>
                                <span>•</span>
                                <span>100% Deterministic Evidence Ingest</span>
                              </div>
                            </div>
                          );
                        }

                        // Case 2: Message Revocation / Deletion Alert Card
                        if (isRevocation) {
                          return (
                            <div
                              key={eventId}
                              className="mx-auto max-w-xl p-3.5 rounded-lg border border-red-500/40 bg-red-950/20 text-red-200 space-y-2 shadow-sm my-2"
                            >
                              <div className="flex items-center justify-between border-b border-red-500/30 pb-2">
                                <div className="flex items-center gap-2">
                                  <span className="material-symbols-outlined text-red-400 text-lg">delete_forever</span>
                                  <span className="text-xs font-bold text-red-300 uppercase tracking-wide">
                                    Message Revoked ("Deleted For Everyone")
                                  </span>
                                </div>
                                <span className="font-mono text-[10px] text-red-300/80">{dt.time}</span>
                              </div>
                              <p className="text-xs leading-relaxed text-red-100">
                                {content}
                              </p>
                              <div className="flex items-center justify-between pt-1 border-t border-red-500/20 font-mono text-[10px] text-red-300/70">
                                <span>Actor: {actorLabel}</span>
                                <span>Tier 1/2 Explicit Revocation Record</span>
                              </div>
                            </div>
                          );
                        }

                        // Case 3: Message Edit Notification Card
                        if (isEdit) {
                          return (
                            <div
                              key={eventId}
                              className="mx-auto max-w-xl p-3 rounded-lg border border-amber-500/40 bg-amber-950/20 text-amber-200 space-y-1.5 shadow-sm my-2"
                            >
                              <div className="flex items-center justify-between border-b border-amber-500/30 pb-1.5">
                                <div className="flex items-center gap-1.5">
                                  <span className="material-symbols-outlined text-amber-400 text-sm">edit_note</span>
                                  <span className="text-xs font-semibold text-amber-300">Message Edited Post-Delivery</span>
                                </div>
                                <span className="font-mono text-[10px] text-amber-300/80">{dt.time}</span>
                              </div>
                              <p className="text-xs text-amber-100 font-medium">{content}</p>
                              {item.metadata_?.old_text && (
                                <p className="text-[11px] text-amber-300/70 line-through">
                                  Prior: "{item.metadata_.old_text}"
                                </p>
                              )}
                            </div>
                          );
                        }

                        // Case 4: Standard Conversational Speech Bubble (Incoming vs Outgoing)
                        return (
                          <div
                            key={eventId}
                            className={`flex flex-col ${outgoing ? 'items-end' : 'items-start'} my-1.5`}
                          >
                            {/* Speech Bubble Container */}
                            <div
                              className={`max-w-[85%] md:max-w-[75%] rounded-2xl p-3 border transition-all shadow-xs ${
                                outgoing
                                  ? isWa
                                    ? 'bg-emerald-950/30 border-emerald-500/40 text-on-surface rounded-tr-xs'
                                    : 'bg-cyan-950/30 border-cyan-500/40 text-on-surface rounded-tr-xs'
                                  : 'bg-surface-container-high border-outline-variant text-on-surface rounded-tl-xs'
                              } ${isCarved ? 'border-orange-500/40 bg-orange-950/20' : ''}`}
                            >
                              {/* Bubble Top Metadata Header */}
                              <div className="flex items-center justify-between gap-3 mb-1 pb-1 border-b border-outline-variant/30 text-[10px]">
                                <div className="flex items-center gap-1.5">
                                  {/* Platform Tiny Icon */}
                                  <span
                                    className={`material-symbols-outlined text-[13px] ${
                                      isWa ? 'text-emerald-400' : isTg ? 'text-cyan-400' : 'text-primary'
                                    }`}
                                  >
                                    {isWa ? 'chat' : isTg ? 'send' : 'comment'}
                                  </span>
                                  <span className={`font-semibold ${outgoing ? 'text-primary' : 'text-on-surface'}`}>
                                    {actorLabel}
                                  </span>
                                </div>

                                <span className="font-mono text-[10px] text-on-surface-variant">
                                  {dt.time}
                                </span>
                              </div>

                              {/* Message Text Payload */}
                              <div className="text-xs md:text-sm text-on-surface leading-relaxed whitespace-pre-wrap break-words select-text">
                                {content}
                              </div>

                              {/* Bubble Footer Badges & Expandable Audit */}
                              <div className="flex items-center justify-between gap-2 mt-2 pt-1 border-t border-outline-variant/30 text-[10px] font-mono text-outline">
                                <div className="flex items-center gap-1.5">
                                  <span className="px-1 py-0.2 rounded bg-surface-container text-on-surface-variant border border-outline-variant">
                                    {(confidenceScore * 100).toFixed(0)}% Det
                                  </span>
                                  {outgoing && (
                                    <span className="material-symbols-outlined text-[13px] text-primary" title="Delivered / Read">
                                      done_all
                                    </span>
                                  )}
                                </div>

                                <button
                                  type="button"
                                  onClick={() => setExpandedEventId(isExpanded ? null : eventId)}
                                  className="hover:text-primary transition-colors flex items-center gap-0.5"
                                  title="Inspect forensic metadata"
                                >
                                  <span>Audit</span>
                                  <span className="material-symbols-outlined text-[12px]">
                                    {isExpanded ? 'expand_less' : 'expand_more'}
                                  </span>
                                </button>
                              </div>

                              {/* Expandable Forensic Ledger Info */}
                              {isExpanded && (
                                <div className="mt-2 pt-2 border-t border-outline-variant/50 text-[10px] font-mono space-y-1 bg-surface-container-lowest/80 p-2 rounded">
                                  <div className="flex justify-between">
                                    <span className="text-outline">Event ID:</span>
                                    <span className="text-on-surface truncate max-w-[200px]" title={item.event_id}>
                                      {item.event_id || item.id}
                                    </span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-outline">Epoch UTC:</span>
                                    <span className="text-on-surface">{dt.ms} ms</span>
                                  </div>
                                  {item.source_table && (
                                    <div className="flex justify-between">
                                      <span className="text-outline">Source Table:</span>
                                      <span className="text-on-surface">{item.source_table}</span>
                                    </div>
                                  )}
                                  {item.chat_ref && (
                                    <div className="flex justify-between">
                                      <span className="text-outline">Raw Chat Ref:</span>
                                      <span className="text-on-surface truncate max-w-[200px]">{item.chat_ref}</span>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}

                <div ref={feedBottomRef} />
              </div>
            )}

            {/* --- VIEW 2: Forensic Audit Ledger Table --- */}
            {!loading && viewMode === 'ledger' && (
              <div className="border border-outline-variant rounded-lg overflow-hidden bg-surface-container-lowest shadow-sm">
                <div className="overflow-x-auto custom-scrollbar">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead className="bg-surface-container border-b border-outline-variant text-[11px] font-semibold text-on-surface-variant font-mono">
                      <tr>
                        <th className="py-2.5 px-3">#</th>
                        <th className="py-2.5 px-3">UTC Timestamp</th>
                        <th className="py-2.5 px-3">Platform</th>
                        <th className="py-2.5 px-3">Type</th>
                        <th className="py-2.5 px-3">Actor / Sender</th>
                        <th className="py-2.5 px-3">Chat / Thread</th>
                        <th className="py-2.5 px-3 min-w-[260px]">Content Payload</th>
                        <th className="py-2.5 px-3">Confidence</th>
                        <th className="py-2.5 px-3">Event ID</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-outline-variant/50 font-mono text-[11px]">
                      {filteredEvents.map((item, idx) => {
                        const eventId = item.event_id || item.id || `ev-${idx}`;
                        const app = (item.source_app || item.app || (item.source_type?.toLowerCase().includes('wa') ? 'whatsapp' : 'telegram')).toLowerCase();
                        const isWa = app.includes('wa');
                        const isTg = app.includes('tg') || app.includes('telegram');
                        const isSys = app.includes('system');
                        const dt = formatEventDateTime(item.utc_ms, item.raw_timestamp || item.timestamp, item.normalized_timestamp);
                        const outgoing = isOutgoingEvent(item);
                        const confidence = item.confidence_score !== undefined ? item.confidence_score : 1.0;

                        return (
                          <tr key={eventId} className="hover:bg-surface-container-low transition-colors">
                            <td className="py-2 px-3 text-outline text-[10px]">{idx + 1}</td>
                            <td className="py-2 px-3 whitespace-nowrap text-on-surface font-medium">{dt.fullIso}</td>
                            <td className="py-2 px-3">
                              <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold uppercase ${
                                isWa ? 'bg-emerald-500/15 text-emerald-400' : isTg ? 'bg-cyan-500/15 text-cyan-400' : 'bg-slate-500/15 text-slate-300'
                              }`}>
                                {isWa ? 'WhatsApp' : isTg ? 'Telegram' : 'System'}
                              </span>
                            </td>
                            <td className="py-2 px-3">
                              <span className="px-1.5 py-0.2 rounded bg-surface-container text-on-surface-variant border border-outline-variant text-[10px]">
                                {item.event_type || item.kind || 'message'}
                              </span>
                            </td>
                            <td className="py-2 px-3 font-sans">
                              <span className={outgoing ? 'text-primary font-semibold' : 'text-on-surface'}>
                                {outgoing ? 'Me (Owner)' : formatContactLabel(item.actor_ref)}
                              </span>
                            </td>
                            <td className="py-2 px-3 font-sans truncate max-w-[160px]" title={item.chat_ref}>
                              {formatContactLabel(item.chat_ref)}
                            </td>
                            <td className="py-2 px-3 font-sans text-on-surface max-w-sm truncate" title={item.summary || item.description}>
                              {item.summary || item.description || '[No payload]'}
                            </td>
                            <td className="py-2 px-3">
                              <span className="px-1.5 py-0.2 rounded bg-tertiary/15 text-tertiary font-semibold text-[10px]">
                                {(confidence * 100).toFixed(0)}%
                              </span>
                            </td>
                            <td className="py-2 px-3 text-outline text-[10px] truncate max-w-[100px]" title={eventId}>
                              {eventId.substring(0, 12)}...
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
