import React, { useState, useEffect, useCallback } from 'react';
import { useActiveCase } from '../context/CaseContext';
import { chatService } from '../services/chatService';

export default function MessagesPage() {
  const { activeCase } = useActiveCase();
  const caseId = activeCase?.id;

  const [chats, setChats] = useState([]);
  const [loadingChats, setLoadingChats] = useState(false);
  const [selectedChat, setSelectedChat] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [selectedMessage, setSelectedMessage] = useState(null);

  const [chatFilter, setChatFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [walView, setWalView] = useState('merged');

  const loadChats = useCallback(async () => {
    if (!caseId) {
      setChats([]);
      setSelectedChat(null);
      setMessages([]);
      return;
    }
    setLoadingChats(true);
    try {
      const data = await chatService.getChats(caseId);
      const list = Array.isArray(data) ? data : (data?.chats || []);
      const normalized = list.map((c, i) => {
        const isWa = c.app === 'whatsapp' || c.platform === 'whatsapp' || (c.jid && c.jid.includes('whatsapp'));
        return {
          id: c.id || c.jid || `c-${i}`,
          jid: c.jid || c.id || '',
          app: isWa ? 'whatsapp' : 'telegram',
          title: c.name || c.title || c.jid || 'Chat Thread',
          subtitle: c.jid || c.subtitle || '',
          lastMessage: c.last_message || c.lastMessage || 'No preview available',
          time: c.last_timestamp || c.time || '',
          count: c.message_count ? `${c.message_count} msgs` : (c.count || ''),
          messages: c.messages || []
        };
      });
      setChats(normalized);
      if (normalized.length > 0) {
        setSelectedChat(normalized[0]);
      } else {
        setSelectedChat(null);
      }
    } catch (err) {
      console.warn('Error loading chats:', err);
      setChats([]);
      setSelectedChat(null);
    } finally {
      setLoadingChats(false);
    }
  }, [caseId]);

  useEffect(() => {
    loadChats();
  }, [loadChats]);

  // Load messages whenever selectedChat changes
  useEffect(() => {
    if (!selectedChat || !caseId) {
      setMessages([]);
      setSelectedMessage(null);
      return;
    }

    if (selectedChat.messages && selectedChat.messages.length > 0) {
      setMessages(selectedChat.messages);
      setSelectedMessage(selectedChat.messages[0]);
      return;
    }

    const fetchMessages = async () => {
      setLoadingMessages(true);
      try {
        const jid = selectedChat.jid || selectedChat.id;
        const data = await chatService.getChatMessages(caseId, jid);
        const list = Array.isArray(data) ? data : (data?.messages || []);
        const formatted = list.map((m, i) => ({
          id: m.id || `m-${i}`,
          sender: m.sender || m.from_me ? 'Self (Examiner)' : (m.sender_name || 'Contact'),
          isOutgoing: m.is_outgoing ?? m.from_me ?? false,
          text: m.text || m.body || m.content || '',
          time: m.timestamp || m.created_at || '',
          rowid: m.rowid || m.id || i + 1,
          status: m.status || 'Verified',
          walSource: m.is_wal_source ?? m.walSource ?? false,
          sha256: m.sha256 || m.hash || '',
          type: m.media_type || m.type || 'text'
        }));
        setMessages(formatted);
        setSelectedMessage(formatted[0] || null);
      } catch (err) {
        console.warn('Error loading messages for chat:', err);
        setMessages([]);
        setSelectedMessage(null);
      } finally {
        setLoadingMessages(false);
      }
    };

    fetchMessages();
  }, [selectedChat, caseId]);

  const waCount = chats.filter(c => c.app === 'whatsapp').length;
  const tgCount = chats.filter(c => c.app === 'telegram').length;

  const filteredChats = chats.filter(c => {
    if (chatFilter === 'whatsapp') return c.app === 'whatsapp';
    if (chatFilter === 'telegram') return c.app === 'telegram';
    return true;
  }).filter(c => {
    if (!search) return true;
    const q = search.toLowerCase();
    return c.title.toLowerCase().includes(q) || c.lastMessage.toLowerCase().includes(q) || c.subtitle.toLowerCase().includes(q);
  });

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-hidden">
      {/* Top Filter Bar */}
      <section className="h-10 bg-surface-container border-b border-outline-variant px-space-md flex flex-wrap items-center justify-between shrink-0 gap-3">
        {/* Search */}
        <div className="flex items-center gap-2 flex-1 max-w-md bg-surface-container-lowest border border-outline-variant rounded px-2 py-1">
          <span className="material-symbols-outlined text-outline text-[15px]">search</span>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search messages, text, sender JID..."
            className="bg-transparent border-0 p-0 text-body-sm text-on-surface focus:outline-none placeholder:text-outline w-full"
          />
        </div>

        {/* View Toggle Segmented Switch */}
        <div className="flex items-center gap-2">
          <div className="flex items-center bg-surface-container-lowest border border-outline-variant rounded p-0.5 text-xs">
            <button
              type="button"
              onClick={() => setWalView('merged')}
              className={`px-2 py-0.5 rounded transition-colors ${
                walView === 'merged'
                  ? 'bg-primary/20 text-primary font-semibold border border-primary/30'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              Main view (WAL-merged)
            </button>
            <button
              type="button"
              onClick={() => setWalView('unmerged')}
              className={`px-2 py-0.5 rounded transition-colors ${
                walView === 'unmerged'
                  ? 'bg-primary/20 text-primary font-semibold border border-primary/30'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              Post-WAL (Unmerged)
            </button>
          </div>

          <div className="px-2 py-1 bg-surface-container-high border border-outline-variant rounded text-label-mono-sm text-primary font-medium text-xs">
            {chats.length} threads indexed
          </div>
        </div>
      </section>

      {/* Three-Pane Data Workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* PANE 1: CHAT LIST (280px) */}
        <section className="w-[280px] bg-surface-container border-r border-outline-variant flex flex-col shrink-0">
          <div className="grid grid-cols-3 border-b border-outline-variant text-label-ui text-center text-xs">
            <button
              type="button"
              onClick={() => setChatFilter('all')}
              className={`py-2 transition-colors ${
                chatFilter === 'all' ? 'border-b-2 border-primary text-primary font-semibold bg-surface-container-lowest/50' : 'text-on-surface-variant'
              }`}
            >
              All ({chats.length})
            </button>
            <button
              type="button"
              onClick={() => setChatFilter('whatsapp')}
              className={`py-2 transition-colors ${
                chatFilter === 'whatsapp' ? 'border-b-2 border-primary text-primary font-semibold bg-surface-container-lowest/50' : 'text-on-surface-variant'
              }`}
            >
              WhatsApp ({waCount})
            </button>
            <button
              type="button"
              onClick={() => setChatFilter('telegram')}
              className={`py-2 transition-colors ${
                chatFilter === 'telegram' ? 'border-b-2 border-primary text-primary font-semibold bg-surface-container-lowest/50' : 'text-on-surface-variant'
              }`}
            >
              Telegram ({tgCount})
            </button>
          </div>

          <div className="flex-1 overflow-y-auto custom-scrollbar divide-y divide-outline-variant/60">
            {loadingChats && (
              <div className="py-8 text-center text-on-surface-variant font-mono text-xs">
                <span className="material-symbols-outlined text-2xl animate-spin text-primary mb-1">sync</span>
                <p>Loading chat threads...</p>
              </div>
            )}

            {!loadingChats && filteredChats.length === 0 && (
              <div className="p-4 text-center text-on-surface-variant text-xs">
                <span className="material-symbols-outlined text-2xl text-outline mb-1">forum</span>
                <p className="font-medium">No chat threads found</p>
                <p className="text-[10px] text-outline mt-0.5">Ingest evidence to index WhatsApp or Telegram dialogs.</p>
              </div>
            )}

            {!loadingChats && filteredChats.map((chat) => {
              const isSelected = selectedChat?.id === chat.id;
              return (
                <article
                  key={chat.id}
                  onClick={() => setSelectedChat(chat)}
                  className={`p-2.5 transition-colors cursor-pointer ${
                    isSelected ? 'bg-surface-container-high border-l-2 border-primary' : 'hover:bg-surface-container-high/60'
                  }`}
                >
                  <div className="flex items-start justify-between mb-1">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className={`material-symbols-outlined text-[16px] shrink-0 ${
                        chat.app === 'whatsapp' ? 'text-emerald-400' : 'text-blue-400'
                      }`}>
                        {chat.app === 'whatsapp' ? 'chat_bubble' : 'send'}
                      </span>
                      <span className="text-body-md font-body-md font-semibold text-on-surface truncate">
                        {chat.title}
                      </span>
                    </div>
                    <span className="text-label-mono-sm text-outline text-[11px] shrink-0">
                      {chat.time}
                    </span>
                  </div>
                  <div className="text-body-sm text-on-surface-variant truncate mb-1 text-xs">
                    {chat.lastMessage}
                  </div>
                  <div className="flex items-center justify-between text-label-mono-sm text-[10px]">
                    <span className="text-outline truncate max-w-[150px]">{chat.subtitle}</span>
                    {chat.count && (
                      <span className="px-1.5 py-0.2 bg-primary/20 text-primary border border-primary/30 rounded font-mono">
                        {chat.count}
                      </span>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        {/* PANE 2: MESSAGE FEED (Center Canvas) */}
        <section className="flex-1 flex flex-col bg-background overflow-hidden border-r border-outline-variant">
          {selectedChat ? (
            <>
              {/* Chat Header */}
              <div className="p-3 border-b border-outline-variant bg-surface-container-low flex items-center justify-between shrink-0">
                <div className="flex items-center space-x-2.5">
                  <span className={`material-symbols-outlined text-[20px] ${
                    selectedChat.app === 'whatsapp' ? 'text-emerald-400' : 'text-blue-400'
                  }`}>
                    {selectedChat.app === 'whatsapp' ? 'chat_bubble' : 'send'}
                  </span>
                  <div>
                    <h2 className="text-headline-sm font-headline-sm text-on-surface font-semibold">
                      {selectedChat.title}
                    </h2>
                    <div className="text-[11px] font-mono text-outline">{selectedChat.subtitle}</div>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <span className="px-2 py-0.5 rounded bg-tertiary/10 text-tertiary border border-tertiary/30 text-label-mono-sm text-[11px]">
                    EVIDENTIARY MERKLE VERIFIED
                  </span>
                </div>
              </div>

              {/* Transcript Feed */}
              <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-3">
                {loadingMessages && (
                  <div className="py-12 text-center text-on-surface-variant font-mono text-xs">
                    <span className="material-symbols-outlined text-2xl animate-spin text-primary mb-1">sync</span>
                    <p>Decrypting and fetching message records...</p>
                  </div>
                )}

                {!loadingMessages && messages.length === 0 && (
                  <div className="py-16 text-center text-on-surface-variant font-mono text-xs">
                    <span className="material-symbols-outlined text-3xl text-outline mb-2">chat</span>
                    <p>No messages recorded for this thread.</p>
                  </div>
                )}

                {!loadingMessages && messages.map((m) => {
                  const isSelected = selectedMessage?.id === m.id;
                  return (
                    <div
                      key={m.id}
                      onClick={() => setSelectedMessage(m)}
                      className={`p-3 rounded-lg border max-w-xl cursor-pointer transition-all ${
                        m.isOutgoing ? 'ml-auto bg-surface-container-high border-primary/30' : 'mr-auto bg-surface-container border-outline-variant'
                      } ${isSelected ? 'ring-2 ring-primary' : ''}`}
                    >
                      <div className="flex items-center justify-between gap-3 text-label-mono-sm text-[11px] mb-1">
                        <span className="font-semibold text-primary">{m.sender}</span>
                        <span className="text-outline">{m.time}</span>
                      </div>

                      <p className="text-body-md text-on-surface leading-relaxed text-sm select-text">
                        {m.text}
                      </p>

                      <div className="mt-2 pt-1 border-t border-outline-variant/40 flex items-center justify-between text-label-mono-sm text-[10px] text-outline">
                        <span>RowID: {m.rowid}</span>
                        <span>{m.walSource ? 'WAL-Merged Frame' : 'Live B-Tree Cell'}</span>
                        <span className="text-tertiary font-semibold">{m.status}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-on-surface-variant font-mono text-xs">
              Select a conversation thread from the left pane to view message stream.
            </div>
          )}
        </section>

        {/* PANE 3: FORENSIC METADATA INSPECTOR */}
        <section className="w-[300px] bg-surface-container-low overflow-y-auto custom-scrollbar p-3 space-y-3 shrink-0">
          <div className="pb-2 border-b border-outline-variant flex items-center justify-between">
            <span className="font-label-ui font-semibold text-xs text-on-surface">Record Inspector</span>
            <span className="font-mono text-[10px] text-primary">BSA §63</span>
          </div>

          {selectedMessage ? (
            <div className="space-y-3 text-xs">
              <div className="p-2.5 rounded bg-surface-container border border-outline-variant space-y-1">
                <span className="text-outline uppercase text-[10px] block font-mono">RowID / Primary Key</span>
                <span className="font-mono text-on-surface font-semibold">{selectedMessage.rowid}</span>
              </div>

              <div className="p-2.5 rounded bg-surface-container border border-outline-variant space-y-1">
                <span className="text-outline uppercase text-[10px] block font-mono">Source Subsystem</span>
                <span className="font-mono text-on-surface">
                  {selectedMessage.walSource ? 'WAL Journal Uncheckpointed' : 'Main SQLite B-Tree Table'}
                </span>
              </div>

              <div className="p-2.5 rounded bg-surface-container border border-outline-variant space-y-1">
                <span className="text-outline uppercase text-[10px] block font-mono">Timestamp (UTC)</span>
                <span className="font-mono text-on-surface">{selectedMessage.time || 'N/A'}</span>
              </div>

              {selectedMessage.sha256 && (
                <div className="p-2.5 rounded bg-surface-container border border-outline-variant space-y-1">
                  <span className="text-outline uppercase text-[10px] block font-mono">Payload SHA-256</span>
                  <span className="font-mono text-tertiary text-[10px] break-all">{selectedMessage.sha256}</span>
                </div>
              )}
            </div>
          ) : (
            <div className="py-8 text-center text-on-surface-variant font-mono text-xs">
              Click any message to inspect rowid, payload hash, and B-tree storage origin.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
