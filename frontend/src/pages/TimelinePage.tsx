import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useActiveCase } from '../context/CaseContext';
import { timelineService } from '../services/timelineService';

// --- Helper Formatter Functions ---

/** Formats contact references and raw JIDs into clean human-readable names */
export const formatContactLabel = (rawRef: any): string => {
  if (!rawRef) return 'System / Unassigned';
  const str = String(rawRef).trim();
  if (
    str === 'me' ||
    str === 'from_me' ||
    str === 'self' ||
    str === 'tg_user_1001' ||
    str === '1001'
  ) {
    return 'Me (Device Owner)';
  }
  if (str === 'status@broadcast') return 'WhatsApp Status';
  if (str === '-1') return 'Unassigned Contact';

  // Resolved Case Interlocutors & Known Dialogs
  if (str === '120363024888888@g.us') return 'Titan Operations Group';
  if (
    str === '15550199001@s.whatsapp.net' ||
    str === '15550199001' ||
    str === 'tg_dialog_2002' ||
    str === 'tg_user_2002' ||
    str === '2002'
  ) {
    return 'Alice Smith (+1 555-019-9001)';
  }
  if (
    str === '15559876543@s.whatsapp.net' ||
    str === '15559876543' ||
    str === 'tg_dialog_2003' ||
    str === 'tg_user_2003' ||
    str === '2003'
  ) {
    return 'Bob Jones (+1 555-987-6543)';
  }
  if (
    str === '15554567890@s.whatsapp.net' ||
    str === '15554567890' ||
    str === 'tg_dialog_2005' ||
    str === 'tg_user_2005' ||
    str === '2005'
  ) {
    return 'Charlie Vance (+1 555-456-7890)';
  }
  if (str === '15550001111@s.whatsapp.net' || str === '15550001111') {
    return 'Decoy Persona (+1 555-000-1111)';
  }
  if (str === 'tg_dialog_-3001' || str === 'tg_user_-3001' || str === '-3001') {
    return 'Titan Investigation TG Group';
  }

  if (str.startsWith('tg_dialog_')) return str.replace('tg_dialog_', '');
  if (str.startsWith('tg_user_')) return str.replace('tg_user_', '');

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
    return `Group Chat (${base.slice(0, 8)}...)`;
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
  const timeStr = d.toISOString().substring(11, 16); // e.g. "14:22"
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
export const isOutgoingEvent = (event: any): boolean => {
  const actor = String(event.actor_ref || '').toLowerCase();
  if (
    actor === 'me' ||
    actor === 'from_me' ||
    actor === 'self' ||
    actor === 'tg_user_1001' ||
    actor === '1001'
  ) {
    return true;
  }
  const meta = event.metadata_ || event.metadata || {};
  if (meta.from_me === 1 || meta.from_me === true) return true;
  if (meta.is_outgoing === true || meta.out === 1 || meta.out === true) return true;
  return false;
};

export const isWhatsAppEvent = (e: any): boolean => {
  const app = String(e.source_app || e.app || '').toLowerCase();
  const type = String(e.event_type || e.kind || '').toLowerCase();
  if (type === 'system' || app === 'system') return false;
  if (app.includes('wa') || app.includes('whatsapp')) return true;
  const ref = String(e.chat_ref || e.actor_ref || '').toLowerCase();
  return ref.includes('@s.whatsapp.net') || ref.includes('@g.us');
};

export const isTelegramEvent = (e: any): boolean => {
  const app = String(e.source_app || e.app || '').toLowerCase();
  const type = String(e.event_type || e.kind || '').toLowerCase();
  if (type === 'system' || app === 'system') return false;
  if (app.includes('tg') || app.includes('telegram')) return true;
  const ref = String(e.chat_ref || e.actor_ref || '').toLowerCase();
  return (
    ref.includes('tg_') ||
    ref.includes('-3001') ||
    ref === '2002' ||
    ref === '2003' ||
    ref === '2005'
  );
};

export default function TimelinePage() {
  const { activeCase, cases, switchCase } = useActiveCase();
  const caseId = activeCase?.id;

  // --- Core State ---
  const [events, setEvents] = useState<any[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);

  // --- View Switcher: 'whatsapp' | 'telegram' | 'ledger' ---
  const [activePlatform, setActivePlatform] = useState<'whatsapp' | 'telegram' | 'ledger'>('whatsapp');
  const [selectedThread, setSelectedThread] = useState<string>('all'); // 'all' | threadKey
  const [searchFilter, setSearchFilter] = useState('');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc'); // 'asc' = oldest first
  const [selectedAuditItem, setSelectedAuditItem] = useState<any | null>(null);

  const feedBottomRef = useRef<HTMLDivElement>(null);

  // --- Fetch Events ---
  const loadTimeline = useCallback(async () => {
    if (!caseId) {
      setEvents([]);
      return;
    }
    setLoading(true);
    setErrorMessage(null);
    try {
      let data: any = await timelineService.getTimeline(caseId);
      let list = Array.isArray(data) ? data : (data?.events || []);

      if (list.length === 0) {
        try {
          await timelineService.buildTimeline(caseId);
          data = await timelineService.getTimeline(caseId);
          list = Array.isArray(data) ? data : (data?.events || []);
        } catch (buildErr) {
          console.warn('Initial timeline build failed:', buildErr);
        }
      }
      setEvents(list);
    } catch (err: any) {
      console.warn('Error fetching timeline events:', err);
      setErrorMessage(err.response?.data?.detail || 'Timeline could not be loaded.');
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
    } catch (err: any) {
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
      const type = String(e.event_type || e.kind || '').toLowerCase();
      const app = String(e.source_app || e.app || '').toLowerCase();
      if (type === 'system' || app === 'system') {
        system++;
      } else if (isWhatsAppEvent(e)) {
        whatsapp++;
      } else if (isTelegramEvent(e)) {
        telegram++;
      } else {
        system++;
      }
    });

    return {
      all: events.length,
      whatsapp,
      telegram,
      system,
    };
  }, [events]);

  // --- Platform Events Set ---
  const platformEvents = useMemo(() => {
    return events.filter((e) => {
      if (activePlatform === 'whatsapp') {
        return isWhatsAppEvent(e);
      }
      if (activePlatform === 'telegram') {
        return isTelegramEvent(e);
      }
      return true; // 'ledger' shows all events
    });
  }, [events, activePlatform]);

  // --- Conversation Threads Aggregation ---
  const conversationThreads = useMemo(() => {
    const threadMap = new Map();

    platformEvents.forEach((e) => {
      const isWa = isWhatsAppEvent(e);
      const platform = isWa ? 'whatsapp' : 'telegram';
      const threadKey = e.chat_ref || e.actor_ref || 'unknown';
      const formattedName = formatContactLabel(threadKey);

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
          lastOutgoing: false,
        });
      }

      const t = threadMap.get(threadKey);
      t.messageCount++;

      const type = (e.event_type || e.kind || '').toLowerCase();
      if (type.includes('revocation')) t.revocationCount++;
      if (type.includes('edit')) t.editCount++;

      const dt = formatEventDateTime(e.utc_ms, e.raw_timestamp || e.timestamp, e.normalized_timestamp);
      if (dt.ms > 0 && dt.ms >= t.latestMs) {
        t.latestMs = dt.ms;
        t.latestSummary = e.summary || e.description || '';
        t.lastOutgoing = isOutgoingEvent(e);
      }
    });

    return Array.from(threadMap.values()).sort((a, b) => b.latestMs - a.latestMs);
  }, [platformEvents]);

  // Filter threads by search query
  const visibleThreads = useMemo(() => {
    if (!searchFilter.trim()) return conversationThreads;
    const q = searchFilter.toLowerCase();
    return conversationThreads.filter((t) => t.name.toLowerCase().includes(q) || t.latestSummary.toLowerCase().includes(q));
  }, [conversationThreads, searchFilter]);

  // Reset selectedThread when switching platform
  const handlePlatformSwitch = (platform: 'whatsapp' | 'telegram' | 'ledger') => {
    setActivePlatform(platform);
    setSelectedThread('all');
  };

  // --- Active Chat Messages ---
  const activeChatMessages = useMemo(() => {
    const threadExists = selectedThread === 'all' || conversationThreads.some((t) => t.key === selectedThread);
    const effectiveThread = threadExists ? selectedThread : 'all';

    let list = platformEvents.filter((e) => {
      if (effectiveThread !== 'all') {
        const threadKey = e.chat_ref || e.actor_ref || 'unknown';
        if (threadKey !== effectiveThread) return false;
      }
      if (searchFilter.trim()) {
        const q = searchFilter.toLowerCase();
        const content = (e.summary || e.description || '').toLowerCase();
        const actor = (e.actor_ref || '').toLowerCase();
        if (!content.includes(q) && !actor.includes(q)) return false;
      }
      return true;
    });

    return list.sort((a, b) => {
      const aTime = a.utc_ms || a.timestamp || 0;
      const bTime = b.utc_ms || b.timestamp || 0;
      if (aTime !== bTime) {
        return sortOrder === 'asc' ? aTime - bTime : bTime - aTime;
      }
      return String(a.event_id || a.id).localeCompare(String(b.event_id || b.id));
    });
  }, [platformEvents, selectedThread, conversationThreads, searchFilter, sortOrder]);

  // Group Messages by Calendar Date for Chat View Day Dividers
  const groupedMessagesByDay = useMemo(() => {
    const groups: { dateKey: string; dateLabel: string; messages: any[] }[] = [];
    let currentGroup: { dateKey: string; dateLabel: string; messages: any[] } | null = null;

    activeChatMessages.forEach((msg, idx) => {
      const dt = formatEventDateTime(msg.utc_ms, msg.raw_timestamp || msg.timestamp, msg.normalized_timestamp);
      if (!currentGroup || currentGroup.dateKey !== dt.dateKey) {
        currentGroup = {
          dateKey: dt.dateKey,
          dateLabel: dt.dateLabel,
          messages: [],
        };
        groups.push(currentGroup);
      }
      currentGroup.messages.push({ msg, dt, idx });
    });

    return groups;
  }, [activeChatMessages]);

  const activeThreadObj = useMemo(() => {
    if (selectedThread === 'all') return null;
    return conversationThreads.find((t) => t.key === selectedThread);
  }, [selectedThread, conversationThreads]);

  const scrollToBottom = () => {
    feedBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background text-on-surface overflow-hidden font-sans">
      {errorMessage && (
        <div className="p-3 bg-red-500/10 border-b border-red-500/20 text-red-600 dark:text-red-400 text-xs font-mono flex items-center justify-between">
          <span>{errorMessage}</span>
          <button onClick={() => setErrorMessage(null)} className="font-bold hover:underline">✕</button>
        </div>
      )}

      {/* Case Notification if on a case with 0 messages but Case 124 is available */}
      {events.length === 0 && !loading && cases.some((c) => String(c.id) === '124') && String(caseId) !== '124' && (
        <div className="px-4 py-2 bg-amber-500/10 border-b border-amber-500/30 text-amber-800 dark:text-amber-200 text-xs flex items-center justify-between font-mono">
          <span>The current case has no sequenced events. Switch to Case 124 (Digital Corpora Extended) to inspect the 217 forensic records.</span>
          <button
            type="button"
            onClick={() => switchCase('124')}
            className="px-2.5 py-1 rounded bg-amber-600 text-white font-bold hover:bg-amber-700"
          >
            Switch to Case 124
          </button>
        </div>
      )}

      {/* ============================================================== */}
      {/* TOP HEADER: 3 TABS (WHATSAPP, TELEGRAM, AUDIT LEDGER)           */}
      {/* ============================================================== */}
      <header className="border-b border-outline-variant bg-surface px-4 py-3 flex flex-wrap items-center justify-between gap-3 shrink-0 shadow-xs">
        <div className="flex items-center gap-3">
          {/* Main 3 View Tabs: WhatsApp | Telegram | Audit Ledger */}
          <div className="flex items-center bg-surface-container-low p-1 rounded-xl border border-outline-variant">
            {/* 1. WhatsApp Tab */}
            <button
              type="button"
              onClick={() => handlePlatformSwitch('whatsapp')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-2 transition-all ${
                activePlatform === 'whatsapp'
                  ? 'bg-emerald-600 text-white font-semibold shadow-xs'
                  : 'text-on-surface-variant hover:text-emerald-600 dark:hover:text-emerald-400 hover:bg-surface-container'
              }`}
            >
              <span className="material-symbols-outlined text-[17px]">chat</span>
              <span>WhatsApp</span>
              <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold ${
                activePlatform === 'whatsapp' ? 'bg-white/20 text-white' : 'bg-surface-container text-on-surface-variant'
              }`}>
                {platformCounts.whatsapp}
              </span>
            </button>

            {/* 2. Telegram Tab */}
            <button
              type="button"
              onClick={() => handlePlatformSwitch('telegram')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-2 transition-all ${
                activePlatform === 'telegram'
                  ? 'bg-blue-600 text-white font-semibold shadow-xs'
                  : 'text-on-surface-variant hover:text-blue-600 dark:hover:text-blue-400 hover:bg-surface-container'
              }`}
            >
              <span className="material-symbols-outlined text-[17px]">send</span>
              <span>Telegram</span>
              <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold ${
                activePlatform === 'telegram' ? 'bg-white/20 text-white' : 'bg-surface-container text-on-surface-variant'
              }`}>
                {platformCounts.telegram}
              </span>
            </button>

            {/* 3. Forensic Audit Ledger Tab (Includes exhibits, revocations, and system ingests) */}
            <button
              type="button"
              onClick={() => handlePlatformSwitch('ledger')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-2 transition-all ${
                activePlatform === 'ledger'
                  ? 'bg-primary text-on-primary font-semibold shadow-xs'
                  : 'text-on-surface-variant hover:text-primary hover:bg-surface-container'
              }`}
            >
              <span className="material-symbols-outlined text-[17px]">table_rows</span>
              <span>Audit Ledger</span>
              <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold ${
                activePlatform === 'ledger' ? 'bg-white/20 text-white' : 'bg-surface-container text-on-surface-variant'
              }`}>
                {platformCounts.all}
              </span>
            </button>
          </div>
        </div>

        {/* Global Controls: Case Badge, Chronological Order & Rebuild */}
        <div className="flex items-center gap-2">
          {/* Active Case Selector / Badge */}
          {activeCase && (
            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-surface-container text-[11px] font-mono border border-outline-variant text-on-surface">
              <span className="material-symbols-outlined text-[14px] text-primary">folder_open</span>
              <span className="font-semibold">{activeCase.caseNumber || `Case #${caseId}`}</span>
            </div>
          )}

          {/* Chronological Sort Toggle */}
          <button
            type="button"
            onClick={() => setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))}
            className="btn-secondary text-xs h-8 px-2.5 flex items-center gap-1.5"
            title={sortOrder === 'asc' ? 'Chronological: Oldest First' : 'Reverse: Newest First'}
          >
            <span className="material-symbols-outlined text-[15px] text-primary">
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
            className="btn-primary text-xs h-8 px-3 flex items-center gap-1.5"
          >
            <span className={`material-symbols-outlined text-[15px] ${rebuilding ? 'animate-spin' : ''}`}>
              sync
            </span>
            <span>{rebuilding ? 'Sequencing...' : 'Rebuild Timeline'}</span>
          </button>
        </div>
      </header>

      {/* ============================================================== */}
      {/* CONVERSATION VIEWER (WHATSAPP OR TELEGRAM INTERFACE)           */}
      {/* ============================================================== */}
      {activePlatform !== 'ledger' && (
        <div className="flex-1 flex overflow-hidden bg-background">
          {/* Left Column: Interlocutors / Conversation Threads */}
          <aside className="w-80 md:w-96 border-r border-outline-variant bg-surface flex flex-col shrink-0 overflow-hidden">
            {/* Search Filter Header */}
            <div className="p-3 border-b border-outline-variant bg-surface-container-low shrink-0 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-on-surface flex items-center gap-1.5">
                  <span className={`material-symbols-outlined text-[16px] ${
                    activePlatform === 'whatsapp' ? 'text-emerald-600 dark:text-emerald-400' : 'text-blue-600 dark:text-blue-400'
                  }`}>
                    {activePlatform === 'whatsapp' ? 'chat' : 'send'}
                  </span>
                  {activePlatform === 'whatsapp' ? 'WhatsApp Conversations' : 'Telegram Dialogs'}
                </span>
                <span className="text-[11px] font-mono text-on-surface-variant font-medium">
                  {visibleThreads.length} Threads
                </span>
              </div>

              <div className="relative flex items-center">
                <span className="material-symbols-outlined absolute left-2.5 text-[15px] text-on-surface-variant">search</span>
                <input
                  type="text"
                  value={searchFilter}
                  onChange={(e) => setSearchFilter(e.target.value)}
                  placeholder="Filter by contact or text..."
                  className="w-full bg-surface border border-outline-variant text-on-surface text-xs rounded-lg pl-8 pr-7 py-1.5 focus:border-primary focus:outline-none placeholder:text-on-surface-variant/60"
                />
                {searchFilter && (
                  <button onClick={() => setSearchFilter('')} className="absolute right-2 text-on-surface-variant hover:text-on-surface text-xs font-bold">
                    ✕
                  </button>
                )}
              </div>
            </div>

            {/* Scrollable Conversation Threads List */}
            <div className="flex-1 overflow-y-auto custom-scrollbar divide-y divide-outline-variant/40">
              {/* Option: All Conversations (Unified Stream) */}
              <div
                onClick={() => setSelectedThread('all')}
                className={`flex items-center gap-3 p-3 cursor-pointer transition-colors ${
                  selectedThread === 'all'
                    ? 'bg-surface-container-high border-l-4 border-primary'
                    : 'hover:bg-surface-container-low'
                }`}
              >
                <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 border ${
                  activePlatform === 'whatsapp'
                    ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
                    : 'bg-blue-500/15 border-blue-500/30 text-blue-600 dark:text-blue-400'
                }`}>
                  <span className="material-symbols-outlined text-[20px]">forum</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-on-surface truncate">
                      All {activePlatform === 'whatsapp' ? 'WhatsApp' : 'Telegram'} Messages
                    </span>
                    <span className="text-[11px] font-mono text-primary font-semibold">
                      {activePlatform === 'whatsapp' ? platformCounts.whatsapp : platformCounts.telegram}
                    </span>
                  </div>
                  <p className="text-[11px] text-on-surface-variant truncate mt-0.5">
                    Unified chronological sequence
                  </p>
                </div>
              </div>

              {/* Individual Contacts / Dialog Cards */}
              {visibleThreads.map((t) => {
                const isSelected = selectedThread === t.key;
                const dt = t.latestMs > 0 ? formatEventDateTime(t.latestMs) : null;
                const isWa = activePlatform === 'whatsapp';

                return (
                  <div
                    key={t.key}
                    onClick={() => setSelectedThread(t.key)}
                    className={`flex items-center gap-3 p-3 cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-surface-container-high border-l-4 border-primary'
                        : 'hover:bg-surface-container-low'
                    }`}
                  >
                    {/* Contact Avatar */}
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center text-xs font-bold shrink-0 uppercase border ${
                      isWa
                        ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-700 dark:text-emerald-300'
                        : 'bg-blue-500/15 border-blue-500/30 text-blue-700 dark:text-blue-300'
                    }`}>
                      {t.name[0] || 'C'}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-0.5">
                        <span className="text-xs font-semibold text-on-surface truncate" title={t.name}>
                          {t.name}
                        </span>
                        {dt && (
                          <span className={`text-[10px] font-mono ${t.revocationCount > 0 ? 'text-red-500 dark:text-red-400' : 'text-on-surface-variant'}`}>
                            {dt.time}
                          </span>
                        )}
                      </div>

                      <div className="flex items-center justify-between gap-1 text-[11px] text-on-surface-variant">
                        <p className="truncate flex items-center gap-1 flex-1">
                          {t.lastOutgoing && (
                            <span className="material-symbols-outlined text-[13px] text-primary">done_all</span>
                          )}
                          <span className="truncate">{t.latestSummary || '[Message payload]'}</span>
                        </p>

                        <div className="flex items-center gap-1 shrink-0">
                          {t.revocationCount > 0 && (
                            <span className="px-1.5 py-0.2 rounded-full text-[9px] bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20 font-mono font-bold">
                              🚫 {t.revocationCount}
                            </span>
                          )}
                          <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-bold font-mono ${
                            isWa
                              ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
                              : 'bg-blue-500/15 text-blue-700 dark:text-blue-300'
                          }`}>
                            {t.messageCount}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}

              {visibleThreads.length === 0 && (
                <div className="p-8 text-center text-on-surface-variant text-xs space-y-2">
                  <span className="material-symbols-outlined text-3xl opacity-50">search_off</span>
                  <p>No conversations match search filter.</p>
                </div>
              )}
            </div>
          </aside>

          {/* Right Column: Chat History Viewer Pane */}
          <main className="flex-1 flex flex-col bg-surface-container-lowest/50 overflow-hidden">
            {/* Active Conversation Top Bar */}
            <div className="h-14 px-4 bg-surface border-b border-outline-variant flex items-center justify-between shrink-0 shadow-xs">
              <div className="flex items-center gap-3">
                <div className={`w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold shrink-0 border ${
                  activePlatform === 'whatsapp'
                    ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-700 dark:text-emerald-300'
                    : 'bg-blue-500/15 border-blue-500/30 text-blue-700 dark:text-blue-300'
                }`}>
                  {activeThreadObj ? activeThreadObj.name[0] : (activePlatform === 'whatsapp' ? 'WA' : 'TG')}
                </div>
                <div>
                  <div className="text-xs font-bold text-on-surface flex items-center gap-2">
                    <span>{activeThreadObj ? activeThreadObj.name : `All ${activePlatform === 'whatsapp' ? 'WhatsApp' : 'Telegram'} Messages`}</span>
                    <span className={`px-1.5 py-0.2 rounded text-[9px] font-mono font-bold uppercase tracking-wider ${
                      activePlatform === 'whatsapp'
                        ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30'
                        : 'bg-blue-500/15 text-blue-700 dark:text-blue-300 border border-blue-500/30'
                    }`}>
                      {activePlatform}
                    </span>
                  </div>
                  <div className="text-[10px] text-on-surface-variant font-mono">
                    {activeChatMessages.length} sequenced messages in thread
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={scrollToBottom}
                  className="btn-secondary text-xs h-7.5 px-2.5 flex items-center gap-1"
                  title="Scroll to latest messages"
                >
                  <span className="material-symbols-outlined text-[14px]">vertical_align_bottom</span>
                  <span>Latest</span>
                </button>
              </div>
            </div>

            {/* Conversation Messages Stream */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-4 md:p-6 space-y-4">
              {loading && (
                <div className="py-20 text-center text-on-surface-variant font-mono text-xs space-y-2">
                  <span className="material-symbols-outlined text-3xl animate-spin text-primary">sync</span>
                  <p>Sequencing conversation dialogue...</p>
                </div>
              )}

              {!loading && activeChatMessages.length === 0 && (
                <div className="py-20 text-center max-w-sm mx-auto p-6 bg-surface border border-outline-variant rounded-2xl space-y-2 shadow-xs">
                  <span className="material-symbols-outlined text-4xl text-on-surface-variant opacity-60">chat</span>
                  <h3 className="text-xs font-bold text-on-surface">No Messages in Selected View</h3>
                  <p className="text-[11px] text-on-surface-variant">Re-run parsing or click Rebuild Timeline.</p>
                </div>
              )}

              {/* Messages Grouped by Day */}
              {!loading && groupedMessagesByDay.map((group) => (
                <div key={group.dateKey} className="space-y-3">
                  {/* Centered Day Capsule */}
                  <div className="flex justify-center my-3 sticky top-2 z-10">
                    <div className="px-3 py-1 rounded-full bg-surface border border-outline-variant text-on-surface-variant text-[11px] font-mono font-medium shadow-xs">
                      {group.dateLabel}
                    </div>
                  </div>

                  {/* Messages for this Day */}
                  <div className="space-y-2.5">
                    {group.messages.map(({ msg: item, dt, idx }) => {
                      const outgoing = isOutgoingEvent(item);
                      const eventType = (item.event_type || item.kind || '').toLowerCase();
                      const isRevocation = eventType.includes('revocation');
                      const isEdit = eventType.includes('edit');
                      const isRecovered = eventType.includes('recovered');
                      const content = item.summary || item.description || '[No payload]';
                      const isWa = activePlatform === 'whatsapp';

                      // Revocation Alert Card
                      if (isRevocation) {
                        const hasRecoveredText = content.includes('[Recovered: "') || (item.metadata_?.recovered_text);
                        const displayContent = hasRecoveredText
                          ? content.replace(/.*\[Recovered:\s*"(.*)"\].*/s, '$1') || content
                          : content;

                        return (
                          <div key={idx} className={`flex ${outgoing ? 'justify-end' : 'justify-start'} my-1`}>
                            <div className="max-w-[85%] md:max-w-[75%] rounded-xl p-3 bg-red-500/10 border border-red-500/30 text-on-surface text-xs shadow-xs space-y-2">
                              <div className="flex items-center gap-1.5 font-semibold text-red-600 dark:text-red-400">
                                <span className="material-symbols-outlined text-[16px]">delete_forever</span>
                                <span className="font-bold">This message was deleted ("Revoked for everyone")</span>
                              </div>
                              {hasRecoveredText ? (
                                <div className="p-2.5 rounded-lg bg-surface border border-outline-variant select-text space-y-1">
                                  <span className="text-[10px] font-mono font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider flex items-center gap-1">
                                    <span className="material-symbols-outlined text-[13px]">verified</span>
                                    Forensic Carved Payload Excavated
                                  </span>
                                  <p className="text-xs font-semibold text-on-surface font-sans leading-relaxed">
                                    {displayContent}
                                  </p>
                                </div>
                              ) : (
                                <div className="p-2 rounded bg-surface/60 border border-outline-variant text-[11px] font-mono text-on-surface-variant italic">
                                  Deletion marker verified in SQLite evidence. Original payload content was deleted and unrecovered.
                                </div>
                              )}
                              <div className="flex items-center justify-between text-[10px] font-mono text-on-surface-variant pt-1 border-t border-outline-variant">
                                <span>Sender: {formatContactLabel(item.actor_ref)}</span>
                                <div className="flex items-center gap-2">
                                  <span>{dt.time} UTC</span>
                                  <button
                                    type="button"
                                    onClick={() => setSelectedAuditItem(item)}
                                    className="text-primary hover:underline font-bold flex items-center gap-0.5"
                                  >
                                    <span>Audit Provenance</span>
                                    <span className="material-symbols-outlined text-[12px]">open_in_new</span>
                                  </button>
                                </div>
                              </div>
                            </div>
                          </div>
                        );
                      }

                      // Recovered Record Card (Tier 1 carved)
                      if (isRecovered) {
                        return (
                          <div key={idx} className={`flex ${outgoing ? 'justify-end' : 'justify-start'} my-1`}>
                            <div className="max-w-[85%] md:max-w-[75%] rounded-xl p-3 bg-emerald-500/10 border border-emerald-500/30 text-on-surface text-xs shadow-xs space-y-1.5">
                              <div className="flex items-center justify-between">
                                <span className="text-[10px] font-mono font-bold text-emerald-700 dark:text-emerald-300 flex items-center gap-1">
                                  <span className="material-symbols-outlined text-[14px]">psychology</span>
                                  Carved SQLite Payload (Tier-1 Record)
                                </span>
                                <span className="text-[10px] font-mono text-on-surface-variant">{dt.time}</span>
                              </div>
                              <div className="text-xs text-on-surface select-text leading-relaxed font-sans bg-surface/80 p-2 rounded border border-outline-variant">
                                {content}
                              </div>
                              <div className="flex items-center justify-between text-[10px] font-mono text-on-surface-variant">
                                <span>Thread: {formatContactLabel(item.chat_ref)}</span>
                                <button
                                  type="button"
                                  onClick={() => setSelectedAuditItem(item)}
                                  className="text-emerald-700 dark:text-emerald-300 hover:underline font-bold"
                                >
                                  [Audit Provenance]
                                </button>
                              </div>
                            </div>
                          </div>
                        );
                      }

                      // Standard Message Bubble
                      return (
                        <div key={idx} className={`flex ${outgoing ? 'justify-end' : 'justify-start'} my-1`}>
                          <div
                            className={`max-w-[85%] md:max-w-[70%] rounded-2xl p-3 text-xs md:text-sm shadow-xs relative group transition-all ${
                              outgoing
                                ? isWa
                                  ? 'bg-emerald-100 text-emerald-950 dark:bg-emerald-950/40 dark:text-emerald-100 border border-emerald-300 dark:border-emerald-700/50 rounded-tr-xs'
                                  : 'bg-blue-100 text-blue-950 dark:bg-blue-950/40 dark:text-blue-100 border border-blue-300 dark:border-blue-700/50 rounded-tr-xs'
                                : 'bg-surface border border-outline-variant text-on-surface rounded-tl-xs'
                            }`}
                          >
                            {/* Inbound Sender Label if multi-party group */}
                            {!outgoing && item.actor_ref && item.actor_ref !== 'me' && (
                              <div className={`text-[11px] font-bold mb-1 ${
                                isWa ? 'text-emerald-700 dark:text-emerald-400' : 'text-blue-700 dark:text-blue-400'
                              }`}>
                                {formatContactLabel(item.actor_ref)}
                              </div>
                            )}

                            {/* Message Text Body */}
                            <div className="whitespace-pre-wrap break-words leading-relaxed select-text font-sans">
                              {content}
                            </div>

                            {/* Message Footer: Time + Checkmarks + Audit Trigger */}
                            <div className="flex items-center justify-end gap-1.5 mt-1.5 pt-1 border-t border-current/10 text-[10px] font-mono opacity-80 select-none">
                              {isEdit && <span className="italic font-bold text-amber-600 dark:text-amber-400 text-[9px] mr-1">edited</span>}
                              <span>{dt.time}</span>
                              {outgoing && (
                                <span className="material-symbols-outlined text-[13px] text-primary" title="Delivered and Read">
                                  done_all
                                </span>
                              )}
                              <button
                                type="button"
                                onClick={() => setSelectedAuditItem(item)}
                                className="opacity-0 group-hover:opacity-100 transition-opacity ml-1.5 text-primary hover:underline font-bold"
                                title="Inspect SQLite Provenance"
                              >
                                [Audit]
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}

              <div ref={feedBottomRef} />
            </div>
          </main>
        </div>
      )}

      {/* ============================================================== */}
      {/* VIEW 3: FORENSIC AUDIT LEDGER TABLE                            */}
      {/* ============================================================== */}
      {activePlatform === 'ledger' && (
        <div className="flex-1 flex flex-col p-4 md:p-6 overflow-hidden bg-background">
          <div className="border border-outline-variant rounded-xl overflow-hidden bg-surface shadow-xs flex-1 flex flex-col">
            <div className="p-3 bg-surface-container border-b border-outline-variant flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-lg">verified</span>
                <span className="text-xs font-bold font-mono text-on-surface">
                  Comprehensive Timeline Audit Ledger ({events.length} total events)
                </span>
              </div>
              <div className="text-[11px] font-mono text-on-surface-variant">
                Full chronological sequence strictly ordered by UTC timestamp (includes exhibits, revocations, and message records).
              </div>
            </div>

            <div className="flex-1 overflow-auto custom-scrollbar">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-surface-container border-b border-outline-variant text-[11px] font-semibold text-on-surface-variant font-mono sticky top-0 z-10 shadow-xs">
                  <tr>
                    <th className="py-2.5 px-3">#</th>
                    <th className="py-2.5 px-3">UTC Timestamp</th>
                    <th className="py-2.5 px-3">Platform / Type</th>
                    <th className="py-2.5 px-3">Category</th>
                    <th className="py-2.5 px-3">Actor / Sender</th>
                    <th className="py-2.5 px-3">Chat / Thread</th>
                    <th className="py-2.5 px-3 min-w-[280px]">Content Payload</th>
                    <th className="py-2.5 px-3">Certainty</th>
                    <th className="py-2.5 px-3">Event ID</th>
                    <th className="py-2.5 px-3 text-right">Inspect</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/60 font-mono text-[11px]">
                  {events
                    .slice()
                    .sort((a, b) => {
                      const aTime = a.utc_ms || a.timestamp || 0;
                      const bTime = b.utc_ms || b.timestamp || 0;
                      return sortOrder === 'asc' ? aTime - bTime : bTime - aTime;
                    })
                    .map((item, idx) => {
                      const eventId = item.event_id || item.id || `ev-${idx}`;
                      const app = (item.source_app || item.app || '').toLowerCase();
                      const type = (item.event_type || item.kind || '').toLowerCase();
                      const isWa = isWhatsAppEvent(item);
                      const isTg = isTelegramEvent(item);
                      const dt = formatEventDateTime(item.utc_ms, item.raw_timestamp || item.timestamp, item.normalized_timestamp);
                      const outgoing = isOutgoingEvent(item);
                      const confidence = item.confidence_score !== undefined ? item.confidence_score : 1.0;

                      return (
                        <tr key={eventId} className="hover:bg-surface-container transition-colors">
                          <td className="py-2 px-3 text-on-surface-variant text-[10px]">{idx + 1}</td>
                          <td className="py-2 px-3 whitespace-nowrap text-on-surface font-medium">{dt.fullIso}</td>
                          <td className="py-2 px-3">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                              type === 'system' || app === 'system'
                                ? 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/30'
                                : isWa
                                ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30'
                                : isTg
                                ? 'bg-blue-500/10 text-blue-700 dark:text-blue-300 border border-blue-500/30'
                                : 'bg-slate-500/10 text-slate-700 dark:text-slate-300 border border-slate-500/30'
                            }`}>
                              {type === 'system' || app === 'system' ? 'System Exhibit' : isWa ? 'WhatsApp' : isTg ? 'Telegram' : 'Evidence'}
                            </span>
                          </td>
                          <td className="py-2 px-3">
                            <span className="px-1.5 py-0.2 rounded bg-surface-container text-on-surface border border-outline-variant text-[10px]">
                              {item.event_type || item.kind || 'message'}
                            </span>
                          </td>
                          <td className="py-2 px-3 font-sans">
                            <span className={outgoing ? 'text-primary font-semibold' : 'text-on-surface'}>
                              {outgoing ? 'Me (Device Owner)' : formatContactLabel(item.actor_ref)}
                            </span>
                          </td>
                          <td className="py-2 px-3 font-sans truncate max-w-[160px]" title={item.chat_ref}>
                            {formatContactLabel(item.chat_ref)}
                          </td>
                          <td className="py-2 px-3 font-sans text-on-surface max-w-sm truncate" title={item.summary || item.description}>
                            {item.summary || item.description || '[No payload]'}
                          </td>
                          <td className="py-2 px-3">
                            <span className="px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 font-semibold text-[10px] border border-emerald-500/20">
                              {(confidence * 100).toFixed(0)}%
                            </span>
                          </td>
                          <td className="py-2 px-3 text-on-surface-variant text-[10px] truncate max-w-[110px]" title={eventId}>
                            {String(eventId).substring(0, 14)}...
                          </td>
                          <td className="py-2 px-3 text-right">
                            <button
                              type="button"
                              onClick={() => setSelectedAuditItem(item)}
                              className="btn-secondary text-[10px] font-mono py-0.5 px-2 h-6"
                            >
                              Inspect
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* EVIDENCE PROVENANCE AUDIT DRAWER (Common across all views)      */}
      {/* ============================================================== */}
      {selectedAuditItem && (
        <div className="fixed inset-y-0 right-0 w-full sm:w-[460px] bg-surface border-l border-outline-variant p-6 z-50 shadow-2xl overflow-y-auto space-y-5 animate-in slide-in-from-right">
          <div className="flex items-center justify-between border-b border-outline-variant pb-3">
            <div className="flex items-center gap-2 text-on-surface font-mono font-bold text-sm">
              <span className="material-symbols-outlined text-primary text-[18px]">verified</span>
              Evidence Provenance Inspector
            </div>
            <button
              onClick={() => setSelectedAuditItem(null)}
              className="text-on-surface-variant hover:text-on-surface p-1 rounded-lg"
            >
              ✕
            </button>
          </div>

          <div className="space-y-4 text-xs font-mono text-on-surface">
            {/* Event Canonical Identification */}
            <div className="p-3 bg-surface-container rounded-xl border border-outline-variant space-y-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">CANONICAL EVENT IDENTIFIER</span>
              <div className="text-primary font-bold break-all select-all text-xs">
                {selectedAuditItem.event_id || selectedAuditItem.id}
              </div>
            </div>

            {/* Excavation Place, Source Database & File Coordinates */}
            <div className="p-3.5 bg-surface-container rounded-xl border border-primary/30 space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-mono font-bold text-primary">
                <span className="material-symbols-outlined text-[16px]">pin_drop</span>
                EXCAVATION ORIGIN &amp; DATABASE COORDINATES
              </div>
              <div className="space-y-1.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-on-surface-variant">Source Application:</span>
                  <span className="font-bold uppercase text-primary">
                    {selectedAuditItem.source_app || selectedAuditItem.app || 'unknown'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-on-surface-variant">Database / Container:</span>
                  <span className="font-bold text-emerald-600 dark:text-emerald-400">
                    {(selectedAuditItem.source_app || '').includes('wa')
                      ? 'msgstore.db (com.whatsapp.zip)'
                      : (selectedAuditItem.source_app || '').includes('tg')
                      ? 'cache4.db (org.telegram.messenger.zip)'
                      : 'Forensic Storage Archive'}
                  </span>
                </div>
                {selectedAuditItem.source_refs && selectedAuditItem.source_refs.length > 0 && selectedAuditItem.source_refs[0].source_table && (
                  <div className="flex items-center justify-between">
                    <span className="text-on-surface-variant">SQLite Table:</span>
                    <span className="font-semibold text-on-surface">{selectedAuditItem.source_refs[0].source_table}</span>
                  </div>
                )}
                {selectedAuditItem.chat_ref && (
                  <div className="flex items-center justify-between">
                    <span className="text-on-surface-variant">Raw Thread JID / ID:</span>
                    <span className="font-semibold text-on-surface truncate max-w-[200px]" title={selectedAuditItem.chat_ref}>
                      {selectedAuditItem.chat_ref}
                    </span>
                  </div>
                )}
                {selectedAuditItem.actor_ref && (
                  <div className="flex items-center justify-between">
                    <span className="text-on-surface-variant">Actor Reference:</span>
                    <span className="font-semibold text-on-surface">{formatContactLabel(selectedAuditItem.actor_ref)}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Payload Preview */}
            <div className="p-3 bg-surface-container rounded-lg border border-outline-variant space-y-1">
              <span className="text-[10px] font-mono text-on-surface-variant uppercase tracking-wider">FULL MESSAGE PAYLOAD</span>
              <div className="text-xs text-on-surface select-text whitespace-pre-wrap font-sans leading-relaxed">
                {selectedAuditItem.summary || selectedAuditItem.description || '[No content text]'}
              </div>
            </div>

            {/* Timestamp Information */}
            <div className="p-3 bg-surface-container rounded-lg border border-outline-variant space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-on-surface-variant">Normalized UTC:</span>
                <span className="text-on-surface font-semibold">
                  {formatEventDateTime(selectedAuditItem.utc_ms, selectedAuditItem.raw_timestamp || selectedAuditItem.timestamp, selectedAuditItem.normalized_timestamp).fullIso}
                </span>
              </div>
              {selectedAuditItem.utc_ms && (
                <div className="flex justify-between">
                  <span className="text-on-surface-variant">Epoch Milliseconds:</span>
                  <span className="text-on-surface">{selectedAuditItem.utc_ms} ms</span>
                </div>
              )}
            </div>

            {/* Judicial Limitations / Neutral Notes */}
            {selectedAuditItem.limitations && selectedAuditItem.limitations.length > 0 && (
              <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg text-xs space-y-1 text-on-surface">
                <span className="font-bold text-amber-600 dark:text-amber-400">Forensic Limitations &amp; Caveats:</span>
                <ul className="list-disc list-inside space-y-0.5 text-on-surface-variant">
                  {selectedAuditItem.limitations.map((lim: string, i: number) => (
                    <li key={i}>{lim}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
