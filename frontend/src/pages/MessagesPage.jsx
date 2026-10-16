import React, { useState } from 'react';
import { useActiveCase } from '../context/CaseContext';

const CHATS = [
  {
    id: 'c-01',
    app: 'whatsapp',
    title: 'Nexus Core Operational',
    subtitle: '120363024819284@g.us',
    lastMessage: 'Target coordinates confirmed: 28.6139° N, 77.2090° E. Deploying field unit now.',
    time: '10:14:01',
    count: '1,428 msgs',
    messages: [
      {
        id: 'm-101',
        sender: '+91 98765 43210 (K. Patel)',
        isOutgoing: false,
        text: 'Initial staged archive sha256 checksum sent to secure enclaves.',
        time: '10:11:04 UTC',
        rowid: 84920,
        status: 'Delivered',
        walSource: true,
        sha256: '7fa0218b9412e84c9012a8120b33411ae3b0c44298fc1c149afbf4c8996fb924',
        type: 'text'
      },
      {
        id: 'm-102',
        sender: 'Target Subject (+91 98111 22334)',
        isOutgoing: true,
        text: 'Decrypt token accepted. Do not commit logs until Section 63 schedule drafted.',
        time: '10:12:45 UTC',
        rowid: 84921,
        status: 'Read',
        walSource: false,
        sha256: '9b4a11f082e4c9012a8120b33411a7fa0218b9412e84c9012a8120b33411a7fa',
        type: 'text'
      },
      {
        id: 'm-103',
        sender: '+91 98765 43210 (K. Patel)',
        isOutgoing: false,
        text: 'Target coordinates confirmed: 28.6139° N, 77.2090° E. Deploying field unit now.',
        time: '10:14:01 UTC',
        rowid: 84922,
        status: 'Read',
        walSource: true,
        sha256: '8a72cf19d45e08b1a32f91bc740192e8fa312904bc78e120aa45192803bba221',
        type: 'location'
      }
    ]
  },
  {
    id: 'c-02',
    app: 'telegram',
    title: 'Falcon Channel [Private]',
    subtitle: '-100184920194',
    lastMessage: 'File crypt15 staged on node 04 for batch recovery.',
    time: '09:42:15',
    count: '842 msgs',
    messages: [
      {
        id: 'm-201',
        sender: '@falcon_lead (Commander)',
        isOutgoing: false,
        text: 'Channel re-keyed. All members update cache4.db references.',
        time: '09:40:12 UTC',
        rowid: 4120,
        status: 'Delivered',
        walSource: true,
        sha256: '01f5e88d11ac293847291048b291048572910485729104857291048572910485',
        type: 'text'
      },
      {
        id: 'm-202',
        sender: '@examiner_unit',
        isOutgoing: true,
        text: 'File crypt15 staged on node 04 for batch recovery.',
        time: '09:42:15 UTC',
        rowid: 4121,
        status: 'Read',
        walSource: false,
        sha256: '4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c',
        type: 'text'
      }
    ]
  },
  {
    id: 'c-03',
    app: 'whatsapp',
    title: 'K. Patel (Field Ops)',
    subtitle: '+91 98440 11223',
    lastMessage: 'Image attachment verified with SHA-256 match.',
    time: '08:19:00',
    count: '214 msgs',
    messages: [
      {
        id: 'm-301',
        sender: 'K. Patel',
        isOutgoing: false,
        text: 'Image attachment verified with SHA-256 match.',
        time: '08:19:00 UTC',
        rowid: 1204,
        status: 'Read',
        walSource: true,
        sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        type: 'text'
      }
    ]
  }
];

export default function MessagesPage() {
  const { activeCase } = useActiveCase();

  const [chatFilter, setChatFilter] = useState('all');
  const [selectedChat, setSelectedChat] = useState(CHATS[0]);
  const [selectedMessage, setSelectedMessage] = useState(CHATS[0].messages[0]);
  const [search, setSearch] = useState('');
  const [walView, setWalView] = useState('merged');

  const filteredChats = CHATS.filter(c => {
    if (chatFilter === 'whatsapp') return c.app === 'whatsapp';
    if (chatFilter === 'telegram') return c.app === 'telegram';
    return true;
  }).filter(c => c.title.toLowerCase().includes(search.toLowerCase()) || c.lastMessage.toLowerCase().includes(search.toLowerCase()));

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
          <span className="text-label-mono-sm text-outline bg-surface-container px-1 rounded text-[10px]">
            ⌘F
          </span>
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
            12,842 indexed messages
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
              All (142)
            </button>
            <button
              type="button"
              onClick={() => setChatFilter('whatsapp')}
              className={`py-2 transition-colors ${
                chatFilter === 'whatsapp' ? 'border-b-2 border-primary text-primary font-semibold bg-surface-container-lowest/50' : 'text-on-surface-variant'
              }`}
            >
              WhatsApp (98)
            </button>
            <button
              type="button"
              onClick={() => setChatFilter('telegram')}
              className={`py-2 transition-colors ${
                chatFilter === 'telegram' ? 'border-b-2 border-primary text-primary font-semibold bg-surface-container-lowest/50' : 'text-on-surface-variant'
              }`}
            >
              Telegram (44)
            </button>
          </div>

          <div className="flex-1 overflow-y-auto custom-scrollbar divide-y divide-outline-variant/60">
            {filteredChats.map((chat) => {
              const isSelected = selectedChat.id === chat.id;
              return (
                <article
                  key={chat.id}
                  onClick={() => {
                    setSelectedChat(chat);
                    setSelectedMessage(chat.messages[0]);
                  }}
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
                    <span className="px-1.5 py-0.2 bg-primary/20 text-primary border border-primary/30 rounded font-mono">
                      {chat.count}
                    </span>
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        {/* PANE 2: MESSAGE FEED (Center Canvas) */}
        <section className="flex-1 flex flex-col bg-background overflow-hidden border-r border-outline-variant">
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
            {selectedChat.messages.map((m) => {
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
        </section>

        {/* PANE 3: FORENSIC MESSAGE INSPECTOR DRAWER (320px) */}
        {selectedMessage && (
          <aside className="w-[320px] bg-surface-container border-l border-outline-variant flex flex-col justify-between overflow-y-auto custom-scrollbar p-4 space-y-4 shrink-0">
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-outline-variant">
                <span className="font-label-ui uppercase tracking-wider text-xs font-semibold text-outline">
                  Message Inspector
                </span>
                <span className="px-1.5 py-0.2 rounded bg-primary/20 text-primary text-[10px] font-mono">
                  {selectedMessage.id}
                </span>
              </div>

              {/* SQLite Row Details */}
              <div className="space-y-2 text-xs">
                <div className="text-label-ui uppercase tracking-wider text-outline font-semibold">
                  Database Origin
                </div>
                <div className="p-2.5 rounded bg-surface-container-low border border-outline-variant space-y-1.5 font-mono text-[11px]">
                  <div className="flex justify-between">
                    <span className="text-on-surface-variant">SQLite rowid:</span>
                    <span className="text-on-surface">{selectedMessage.rowid}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-on-surface-variant">Frame Type:</span>
                    <span className="text-primary">{selectedMessage.walSource ? 'WAL Journal' : 'Live SQLite'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-on-surface-variant">Delivery:</span>
                    <span className="text-tertiary font-semibold">{selectedMessage.status}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-on-surface-variant">Timestamp:</span>
                    <span className="text-on-surface">{selectedMessage.time}</span>
                  </div>
                </div>
              </div>

              {/* Cryptographic SHA-256 */}
              <div className="space-y-2 text-xs">
                <div className="text-label-ui uppercase tracking-wider text-outline font-semibold">
                  Cryptographic Message Hash
                </div>
                <div className="p-2 rounded bg-surface-container-low border border-outline-variant space-y-1">
                  <div className="flex justify-between items-center text-[10px] text-on-surface-variant">
                    <span className="font-semibold text-primary">SHA-256 Digest</span>
                    <button
                      type="button"
                      onClick={() => navigator.clipboard?.writeText(selectedMessage.sha256)}
                      className="text-outline hover:text-primary"
                      title="Copy"
                    >
                      <span className="material-symbols-outlined text-[13px]">content_copy</span>
                    </button>
                  </div>
                  <code className="text-[10px] font-mono text-on-surface block break-all bg-surface-container-lowest p-1.5 rounded border border-outline-variant">
                    {selectedMessage.sha256}
                  </code>
                </div>
              </div>

              {/* Raw Payload Preview */}
              <div className="space-y-2 text-xs">
                <div className="text-label-ui uppercase tracking-wider text-outline font-semibold">
                  Extracted Raw Payload
                </div>
                <div className="p-2 rounded bg-surface-container-lowest border border-outline-variant font-mono text-[11px] text-on-surface max-h-36 overflow-y-auto select-all">
                  "{selectedMessage.text}"
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="pt-2 border-t border-outline-variant space-y-2">
              <button
                type="button"
                onClick={() => navigator.clipboard?.writeText(JSON.stringify(selectedMessage, null, 2))}
                className="btn-secondary w-full text-xs"
              >
                <span className="material-symbols-outlined text-[15px]">content_copy</span>
                <span>Copy Forensic Record JSON</span>
              </button>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
