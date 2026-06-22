import { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import {
  MessageSquare,
  Users,
  Image,
  Video,
  Music,
  FileText,
  ChevronDown,
  ChevronRight,
  Loader2,
} from 'lucide-react';

const SearchResults = ({ results, loading, error, query }) => {
  const [expandedSection, setExpandedSection] = useState('messages');

  const toggleSection = (section) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-3 text-gray-600">Searching...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        {error}
      </div>
    );
  }

  if (!query) {
    return (
      <div className="text-center py-12 text-gray-500">
        <Search className="h-12 w-12 mx-auto mb-4 text-gray-300" />
        <p>Enter a search query to find messages, contacts, and media.</p>
      </div>
    );
  }

  const hasResults =
    (results.messages && results.messages.length > 0) ||
    (results.contacts && results.contacts.length > 0) ||
    (results.media && results.media.length > 0);

  if (!hasResults) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>No results found for "{query}".</p>
        <p className="mt-2 text-sm">Try different keywords or remove filters.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="bg-gray-50 rounded-lg p-4">
        <p className="text-sm text-gray-600">
          Found{' '}
          <span className="font-semibold">
            {results.messages?.length || 0} messages
          </span>
          ,{' '}
          <span className="font-semibold">
            {results.contacts?.length || 0} contacts
          </span>
          , and{' '}
          <span className="font-semibold">
            {results.media?.length || 0} media
          </span>{' '}
          matching "{query}"
        </p>
      </div>

      {/* Messages Section */}
      {results.messages && results.messages.length > 0 && (
        <div className="border rounded-lg overflow-hidden">
          <button
            onClick={() => toggleSection('messages')}
            className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition"
          >
            <div className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-blue-600" />
              <span className="font-medium">Messages</span>
              <span className="text-sm text-gray-500">
                ({results.messages.length})
              </span>
            </div>
            {expandedSection === 'messages' ? (
              <ChevronDown className="h-5 w-5 text-gray-400" />
            ) : (
              <ChevronRight className="h-5 w-5 text-gray-400" />
            )}
          </button>

          {expandedSection === 'messages' && (
            <div className="divide-y">
              {results.messages.map((msg, idx) => (
                <div key={msg.id || idx} className="p-4 hover:bg-gray-50">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-700">
                          {msg.app}
                        </span>
                        {msg.chat_jid && (
                          <span className="text-xs text-gray-500 truncate">
                            {msg.chat_jid.split('@')[0]}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-900 mb-1">
                        {msg.body || '(No text content)'}
                      </p>
                    </div>
                    <div className="text-right ml-4">
                      {msg.timestamp && (
                        <span className="text-xs text-gray-500">
                          {formatDistanceToNow(new Date(msg.timestamp), {
                            addSuffix: true,
                          })}
                        </span>
                      )}
                      {msg.media_type && (
                        <div className="mt-1 flex items-center gap-1">
                          {msg.media_type === 'image' && (
                            <Image className="h-4 w-4 text-green-600" />
                          )}
                          {msg.media_type === 'video' && (
                            <Video className="h-4 w-4 text-purple-600" />
                          )}
                          {msg.media_type === 'audio' && (
                            <Music className="h-4 w-4 text-orange-600" />
                          )}
                          <span className="text-xs text-gray-500">
                            {msg.media_type}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Contacts Section */}
      {results.contacts && results.contacts.length > 0 && (
        <div className="border rounded-lg overflow-hidden">
          <button
            onClick={() => toggleSection('contacts')}
            className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition"
          >
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5 text-green-600" />
              <span className="font-medium">Contacts</span>
              <span className="text-sm text-gray-500">
                ({results.contacts.length})
              </span>
            </div>
            {expandedSection === 'contacts' ? (
              <ChevronDown className="h-5 w-5 text-gray-400" />
            ) : (
              <ChevronRight className="h-5 w-5 text-gray-400" />
            )}
          </button>

          {expandedSection === 'contacts' && (
            <div className="divide-y">
              {results.contacts.map((contact, idx) => (
                <div key={contact.id || idx} className="p-4 hover:bg-gray-50">
                  <div className="flex items-center gap-3">
                    <div className="flex-shrink-0 h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center">
                      <Users className="h-5 w-5 text-gray-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs px-2 py-0.5 rounded bg-green-100 text-green-700">
                          {contact.app}
                        </span>
                        <p className="font-medium text-gray-900 truncate">
                          {contact.display_name || 'Unknown'}
                        </p>
                      </div>
                      <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                        {contact.phone && <span>{contact.phone}</span>}
                        {contact.jid && <span>{contact.jid}</span>}
                        {contact.username && <span>@{contact.username}</span>}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Media Section */}
      {results.media && results.media.length > 0 && (
        <div className="border rounded-lg overflow-hidden">
          <button
            onClick={() => toggleSection('media')}
            className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition"
          >
            <div className="flex items-center gap-2">
              <Image className="h-5 w-5 text-purple-600" />
              <span className="font-medium">Media</span>
              <span className="text-sm text-gray-500">({results.media.length})</span>
            </div>
            {expandedSection === 'media' ? (
              <ChevronDown className="h-5 w-5 text-gray-400" />
            ) : (
              <ChevronRight className="h-5 w-5 text-gray-400" />
            )}
          </button>

          {expandedSection === 'media' && (
            <div className="p-4 grid grid-cols-2 md:grid-cols-4 gap-4">
              {results.media.map((item, idx) => (
                <div
                  key={item.id || idx}
                  className="border rounded-lg p-2 hover:bg-gray-50 transition"
                >
                  <div className="aspect-square bg-gray-100 rounded flex items-center justify-center mb-2">
                    {item.media_type === 'image' && (
                      <Image className="h-8 w-8 text-green-600" />
                    )}
                    {item.media_type === 'video' && (
                      <Video className="h-8 w-8 text-purple-600" />
                    )}
                    {item.media_type === 'audio' && (
                      <Music className="h-8 w-8 text-orange-600" />
                    )}
                    {!item.media_type && (
                      <FileText className="h-8 w-8 text-gray-400" />
                    )}
                  </div>
                  <p className="text-xs text-gray-600 truncate" title={item.file_path}>
                    {item.file_path.split('/').pop()?.substring(0, 20) || 'Unknown'}
                  </p>
                  <p className="text-xs text-gray-400 capitalize">
                    {item.media_type || 'file'}
                    {item.is_orphan && (
                      <span className="ml-1 text-orange-500">(orphan)</span>
                    )}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SearchResults;