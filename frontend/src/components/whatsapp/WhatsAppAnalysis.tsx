import { useState, useEffect } from 'react';
import { useWhatsApp } from '../../hooks/useWhatsApp';
import MessagesList from './MessagesList';
import ContactsList from './ContactsList';
import GroupsList from './GroupsList';
import MediaList from './MediaList';
import { Loader2, Play, MessageSquare } from 'lucide-react';

const WhatsAppAnalysis = ({ evidenceId }) => {
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
  } = useWhatsApp();
  const [activeTab, setActiveTab] = useState('messages');
  const [dataLoading, setDataLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  // Load data when evidenceId changes
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
          // Errors are handled by the hook
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
    { id: 'contacts', label: 'Contacts', count: contacts.length },
    { id: 'groups', label: 'Groups', count: groups.length },
    { id: 'media', label: 'Media', count: media.length },
  ];

  if (hookLoading && !evidenceId) {
    return (
      <div className="p-6 text-center">
        <Loader2 className="h-6 w-6 animate-spin text-accent-cyan mx-auto" />
        <span className="text-forensic-400 mt-2 block">Loading WhatsApp analysis...</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with Analyze button */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent-emerald/20 flex items-center justify-center">
            <svg className="h-5 w-5 text-accent-emerald" viewBox="0 0 24 24" fill="currentColor">
              <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413"/>
            </svg>
          </div>
          <div>
            <h3 className="font-semibold text-forensic-100">WhatsApp Analysis</h3>
            <p className="text-xs text-forensic-500">Extract messages, contacts, groups, and media</p>
          </div>
        </div>
        <button
          onClick={handleAnalyze}
          disabled={analyzing}
          className="btn-primary"
        >
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
            className={`tab-button flex items-center gap-2 ${
              activeTab === tab.id ? 'tab-button-active' : ''
            }`}
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
            <Loader2 className="h-6 w-6 animate-spin text-accent-cyan" />
            <span className="ml-2 text-forensic-400">Loading WhatsApp data...</span>
          </div>
        ) : (
          <>
            {activeTab === 'messages' && (
              <MessagesList
                evidenceId={evidenceId}
                messages={messages}
              />
            )}
            {activeTab === 'contacts' && (
              <ContactsList
                evidenceId={evidenceId}
                contacts={contacts}
              />
            )}
            {activeTab === 'groups' && (
              <GroupsList
                evidenceId={evidenceId}
                groups={groups}
              />
            )}
            {activeTab === 'media' && (
              <MediaList
                evidenceId={evidenceId}
                media={media}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default WhatsAppAnalysis;