import { useState, useEffect } from 'react';
import { useWhatsApp } from '../hooks/useWhatsApp';
import MessagesList from './MessagesList';
import ContactsList from './ContactsList';
import GroupsList from './GroupsList';
import MediaList from './MediaList';

const WhatsAppAnalysis = ({ evidenceId }) => {
  const {
    messages,
    contacts,
    groups,
    media,
    loading,
    error,
    analyzeEvidence,
    loadMessages,
    loadContacts,
    loadGroups,
    loadMedia
  } = useWhatsApp();
  const [activeTab, setActiveTab] = useState('messages');
  const [dataLoading, setDataLoading] = useState(false);

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

  if (loading === true) {
    return <div className="p-6 text-center">Loading WhatsApp analysis tools...</div>;
  }

  if (error) {
    return <div className="p-6 text-red-600 text-center">Error: {error}</div>;
  }

  return (
    <div className="space-y-6">
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">WhatsApp Analysis</h2>
          <button
            onClick={() => analyzeEvidence(evidenceId)}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            Analyze Evidence
          </button>
        </div>
        <p className="text-sm text-gray-500">
          Extract and analyze WhatsApp messages, contacts, groups, and media from the selected evidence.
        </p>
      </div>

      <div className="bg-white p-4 rounded-lg shadow">
        <div className="flex justify-center mb-4">
          <button
            onClick={() => setActiveTab('messages')}
            className={`px-4 py-2 rounded-tl-lg rounded-tr-lg ${
              activeTab === 'messages'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700'
            } hover:bg-blue-700`}
          >
            Messages
          </button>
          <button
            onClick={() => setActiveTab('contacts')}
            className={`px-4 py-2 rounded-tl-lg rounded-tr-lg ${
              activeTab === 'contacts'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700'
            } hover:bg-blue-700`}
          >
            Contacts
          </button>
          <button
            onClick={() => setActiveTab('groups')}
            className={`px-4 py-2 rounded-tl-lg rounded-tr-lg ${
              activeTab === 'groups'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700'
            } hover:bg-blue-700`}
          >
            Groups
          </button>
          <button
            onClick={() => setActiveTab('media')}
            className={`px-4 py-2 rounded-tl-lg rounded-tr-lg ${
              activeTab === 'media'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700'
            } hover:bg-blue-700`}
          >
            Media
          </button>
        </div>

        <div className="border-t border-gray-200">
          {dataLoading && messages.length === 0 && contacts.length === 0 && groups.length === 0 && media.length === 0 ? (
            <p className="text-center py-8">Loading WhatsApp data...</p>
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
    </div>
  );
};

export default WhatsAppAnalysis;