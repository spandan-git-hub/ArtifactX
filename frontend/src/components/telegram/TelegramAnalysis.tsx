import { useState, useEffect } from 'react';
import { useTelegram } from '../../hooks/useTelegram';
import { Loader2, Play, MessageSquare, Users, Radio, Image } from 'lucide-react';

const TelegramMessages = ({ evidenceId, messages }) => {
  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <MessageSquare className="h-5 w-5 text-accent-blue" />
        <span className="font-semibold text-forensic-100">Messages</span>
        <span className="badge badge-blue">{messages.length}</span>
      </div>

      {messages.length === 0 ? (
        <div className="text-center py-8">
          <MessageSquare className="h-12 w-12 text-forensic-600 mx-auto mb-3" />
          <p className="text-forensic-500">No Telegram messages found.</p>
          <p className="text-sm text-forensic-600 mt-1">Analyze evidence to extract messages.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>From</th>
                <th>Message</th>
                <th>Type</th>
              </tr>
            </thead>
            <tbody>
              {messages.slice(0, 100).map((msg, idx) => (
                <tr key={msg.message_id || msg.id || idx}>
                  <td className="text-forensic-400">
                    {msg.timestamp ? new Date(msg.timestamp * 1000).toLocaleString() : 'Unknown'}
                  </td>
                  <td className="text-forensic-300">{msg.sender_id || 'Unknown'}</td>
                  <td className="text-forensic-200 max-w-[300px] truncate">{msg.body || '(No text)'}</td>
                  <td>
                    <span className="badge badge-blue">{msg.media_type || msg.message_type || 'text'}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {messages.length > 100 && (
        <p className="mt-2 text-xs text-forensic-500 text-right">Showing 100 of {messages.length}</p>
      )}
    </div>
  );
};

const TelegramContacts = ({ evidenceId, contacts }) => {
  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <Users className="h-5 w-5 text-accent-emerald" />
        <span className="font-semibold text-forensic-100">Contacts</span>
        <span className="badge badge-emerald">{contacts.length}</span>
      </div>

      {contacts.length === 0 ? (
        <div className="text-center py-8">
          <Users className="h-12 w-12 text-forensic-600 mx-auto mb-3" />
          <p className="text-forensic-500">No Telegram contacts found.</p>
          <p className="text-sm text-forensic-600 mt-1">Analyze evidence to extract contacts.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Username</th>
                <th>Phone</th>
                <th>User ID</th>
              </tr>
            </thead>
            <tbody>
              {contacts.map((contact) => (
                <tr key={contact.user_id || contact.id}>
                  <td className="text-forensic-100">
                    {contact.first_name || ''} {contact.last_name || ''}
                  </td>
                  <td className="text-forensic-400">{contact.username ? `@${contact.username}` : '—'}</td>
                  <td className="text-forensic-400">{contact.phone || '—'}</td>
                  <td className="text-forensic-500 font-mono text-sm">{contact.user_id || 'Unknown'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

const TelegramGroups = ({ evidenceId, groups }) => {
  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <Radio className="h-5 w-5 text-accent-violet" />
        <span className="font-semibold text-forensic-100">Groups & Channels</span>
        <span className="badge badge-violet">{groups.length}</span>
      </div>

      {groups.length === 0 ? (
        <div className="text-center py-8">
          <Radio className="h-12 w-12 text-forensic-600 mx-auto mb-3" />
          <p className="text-forensic-500">No Telegram groups or channels found.</p>
          <p className="text-sm text-forensic-600 mt-1">Analyze evidence to extract groups.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Username</th>
                <th>Type</th>
                <th>Group ID</th>
              </tr>
            </thead>
            <tbody>
              {groups.map((group) => (
                <tr key={group.group_id || group.id}>
                  <td className="text-forensic-100 font-medium">{group.title || 'Unnamed'}</td>
                  <td className="text-forensic-400">{group.username ? `@${group.username}` : '—'}</td>
                  <td>
                    <span className={`badge ${group.type === 'channel' ? 'badge-violet' : 'badge-cyan'}`}>
                      {group.type || 'group'}
                    </span>
                  </td>
                  <td className="text-forensic-500 font-mono text-sm">{group.group_id || 'Unknown'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

const TelegramMedia = ({ evidenceId, media }) => {
  const getMediaIcon = (mediaType) => {
    switch (mediaType) {
      case 'image':
        return <Image className="h-6 w-6 text-accent-emerald" />;
      case 'video':
        return <Image className="h-6 w-6 text-accent-violet" />;
      case 'audio':
        return <Image className="h-6 w-6 text-accent-amber" />;
      default:
        return <Image className="h-6 w-6 text-forensic-500" />;
    }
  };

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <Image className="h-5 w-5 text-accent-violet" />
        <span className="font-semibold text-forensic-100">Media References</span>
        <span className="badge badge-violet">{media.length}</span>
      </div>

      {media.length === 0 ? (
        <div className="text-center py-8">
          <Image className="h-12 w-12 text-forensic-600 mx-auto mb-3" />
          <p className="text-forensic-500">No Telegram media references found.</p>
          <p className="text-sm text-forensic-600 mt-1">Analyze evidence to extract media.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Path</th>
                <th>Size</th>
              </tr>
            </thead>
            <tbody>
              {media.map((m, idx) => (
                <tr key={m.message_id || m.id || idx}>
                  <td>
                    <div className="flex items-center gap-2">
                      {getMediaIcon(m.media_type)}
                      <span className="capitalize text-forensic-300">{m.media_type || 'file'}</span>
                    </div>
                  </td>
                  <td className="text-forensic-400 truncate max-w-[300px]">{m.media_path || '—'}</td>
                  <td className="text-forensic-400 font-mono text-sm">
                    {m.file_size ? `${(m.file_size / 1024).toFixed(1)} KB` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

const TelegramAnalysis = ({ evidenceId }) => {
  const {
    messages,
    contacts,
    groups,
    media,
    loading: hookLoading,
    error,
    analyzeEvidence,
    loadMessages,
    loadContacts,
    loadGroups,
    loadMedia
  } = useTelegram();
  const [activeTab, setActiveTab] = useState('messages');
  const [dataLoading, setDataLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  useEffect(() => {
    if (evidenceId) {
      const loadData = async () => {
        setDataLoading(true);
        try {
          await Promise.all([
            loadMessages(evidenceId),
            loadContacts(evidenceId),
            loadGroups(evidenceId),
            loadMedia(evidenceId)
          ]);
        } catch (err) {
          // Errors handled by hook
        } finally {
          setDataLoading(false);
        }
      };
      loadData();
    }
  }, [evidenceId, loadMessages, loadContacts, loadGroups, loadMedia]);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    try {
      await analyzeEvidence(evidenceId);
    } catch (err) {
      // Error handled by hook
    } finally {
      setAnalyzing(false);
    }
  };

  const tabs = [
    { id: 'messages', label: 'Messages', count: messages.length, icon: MessageSquare },
    { id: 'contacts', label: 'Contacts', count: contacts.length, icon: Users },
    { id: 'groups', label: 'Groups', count: groups.length, icon: Radio },
    { id: 'media', label: 'Media', count: media.length, icon: Image },
  ];

  if (hookLoading && !evidenceId) {
    return (
      <div className="p-6 text-center">
        <Loader2 className="h-6 w-6 animate-spin text-accent-blue mx-auto" />
        <span className="text-forensic-400 mt-2 block">Loading Telegram analysis...</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent-blue/20 flex items-center justify-center">
            <svg className="h-5 w-5 text-accent-blue" viewBox="0 0 24 24" fill="currentColor">
              <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
            </svg>
          </div>
          <div>
            <h3 className="font-semibold text-forensic-100">Telegram Analysis</h3>
            <p className="text-xs text-forensic-500">Extract messages, contacts, groups, and media</p>
          </div>
        </div>
        <button onClick={handleAnalyze} disabled={analyzing} className="btn-primary">
          {analyzing ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Play className="h-4 w-4" />
              Analyze
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="alert alert-error">
          <span>{error}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-1 bg-forensic-800/50 p-1 rounded-lg">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`tab-button flex items-center gap-2 ${activeTab === tab.id ? 'tab-button-active' : ''}`}
          >
            {tab.icon && <tab.icon className="h-4 w-4" />}
            {tab.label}
            <span className="badge badge-gray ml-1">{tab.count}</span>
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="border-t border-forensic-800 pt-4">
        {dataLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-accent-blue" />
            <span className="ml-2 text-forensic-400">Loading Telegram data...</span>
          </div>
        ) : (
          <>
            {activeTab === 'messages' && (
              <TelegramMessages evidenceId={evidenceId} messages={messages} />
            )}
            {activeTab === 'contacts' && (
              <TelegramContacts evidenceId={evidenceId} contacts={contacts} />
            )}
            {activeTab === 'groups' && (
              <TelegramGroups evidenceId={evidenceId} groups={groups} />
            )}
            {activeTab === 'media' && (
              <TelegramMedia evidenceId={evidenceId} media={media} />
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default TelegramAnalysis;