import { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import {
  MessageSquare,
  Users,
  Image,
  Video,
  Music,
  FileText,
  FolderOpen,
  ChevronDown,
  ChevronRight,
  Loader2,
  Search,
} from 'lucide-react';

const SearchResults = ({ results, loading, error, query }) => {
  const [expandedSection, setExpandedSection] = useState('messages');

  const toggleSection = (section) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-accent-cyan" />
        <span className="ml-3 text-forensic-400">Searching...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert alert-error">
        <FileText className="h-5 w-5 flex-shrink-0" />
        <div>
          <p className="font-semibold">Search Failed</p>
          <p className="text-sm opacity-80">{error}</p>
        </div>
      </div>
    );
  }

  if (!query) {
    return (
      <div className="card text-center py-16">
        <Search className="h-16 w-16 text-forensic-600 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-forensic-300 mb-2">
          Search Evidence
        </h3>
        <p className="text-forensic-500">
          Enter a search query to find messages, contacts, and media.
        </p>
      </div>
    );
  }

  const hasResults =
    (results.messages && results.messages.length > 0) ||
    (results.contacts && results.contacts.length > 0) ||
    (results.media && results.media.length > 0);

  if (!hasResults) {
    return (
      <div className="card text-center py-16">
        <FolderOpen className="h-16 w-16 text-forensic-600 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-forensic-300 mb-2">
          No Results Found
        </h3>
        <p className="text-forensic-500">
          No matches found for "{query}". Try different keywords or remove filters.
        </p>
      </div>
    );
  }

  const messageCount = results.messages?.length || 0;
  const contactCount = results.contacts?.length || 0;
  const mediaCount = results.media?.length || 0;

  return (
    <div className="space-y-4 animate-in">
      {/* Summary */}
      <div className="card bg-forensic-800/50">
        <p className="text-sm text-forensic-400">
          Found{' '}
          <span className="text-accent-cyan font-semibold">
            {messageCount} messages
          </span>
          ,{' '}
          <span className="text-accent-emerald font-semibold">
            {contactCount} contacts
          </span>
          , and{' '}
          <span className="text-accent-violet font-semibold">
            {mediaCount} media
          </span>{' '}
          matching "{query}"
        </p>
      </div>

      {/* Messages Section */}
      {messageCount > 0 && (
        <div className="card overflow-hidden p-0">
          <button
            onClick={() => toggleSection('messages')}
            className="w-full flex items-center justify-between p-4 hover:bg-forensic-800/50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-accent-cyan/20 flex items-center justify-center">
                <MessageSquare className="h-5 w-5 text-accent-cyan" />
              </div>
              <div className="text-left">
                <span className="font-semibold text-forensic-100">Messages</span>
                <span className="text-sm text-forensic-500 ml-2">
                  ({messageCount})
                </span>
              </div>
            </div>
            {expandedSection === 'messages' ? (
              <ChevronDown className="h-5 w-5 text-forensic-500" />
            ) : (
              <ChevronRight className="h-5 w-5 text-forensic-500" />
            )}
          </button>

          {expandedSection === 'messages' && (
            <div className="border-t border-forensic-700 divide-y divide-forensic-800">
              {results.messages.slice(0, 50).map((msg, idx) => (
                <div key={msg.id || idx} className="p-4 hover:bg-forensic-800/30 transition-colors">
                  <div className="flex justify-between items-start gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="badge badge-cyan text-xs">
                          {msg.app || 'unknown'}
                        </span>
                        {msg.chat_jid && (
                          <span className="text-xs text-forensic-500 truncate">
                            {msg.chat_jid.split('@')[0]}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-forensic-200 mb-1 line-clamp-2">
                        {msg.body || '(No text content)'}
                      </p>
                    </div>
                    <div className="text-right flex-shrink-0">
                      {msg.timestamp && (
                        <span className="text-xs text-forensic-500">
                          {formatDistanceToNow(new Date(msg.timestamp * 1000 || msg.timestamp), {
                            addSuffix: true,
                          })}
                        </span>
                      )}
                      {msg.media_type && (
                        <div className="mt-1 flex items-center justify-end gap-1">
                          {msg.media_type === 'image' && <Image className="h-4 w-4 text-accent-emerald" />}
                          {msg.media_type === 'video' && <Video className="h-4 w-4 text-accent-violet" />}
                          {msg.media_type === 'audio' && <Music className="h-4 w-4 text-accent-amber" />}
                          <span className="text-xs text-forensic-500">
                            {msg.media_type}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              {messageCount > 50 && (
                <div className="p-3 text-center text-sm text-forensic-500 border-t border-forensic-700">
                  Showing 50 of {messageCount} messages. Use filters to narrow results.
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Contacts Section */}
      {contactCount > 0 && (
        <div className="card overflow-hidden p-0">
          <button
            onClick={() => toggleSection('contacts')}
            className="w-full flex items-center justify-between p-4 hover:bg-forensic-800/50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-accent-emerald/20 flex items-center justify-center">
                <Users className="h-5 w-5 text-accent-emerald" />
              </div>
              <div className="text-left">
                <span className="font-semibold text-forensic-100">Contacts</span>
                <span className="text-sm text-forensic-500 ml-2">
                  ({contactCount})
                </span>
              </div>
            </div>
            {expandedSection === 'contacts' ? (
              <ChevronDown className="h-5 w-5 text-forensic-500" />
            ) : (
              <ChevronRight className="h-5 w-5 text-forensic-500" />
            )}
          </button>

          {expandedSection === 'contacts' && (
            <div className="border-t border-forensic-700 divide-y divide-forensic-800">
              {results.contacts.slice(0, 50).map((contact, idx) => (
                <div key={contact.id || idx} className="p-4 hover:bg-forensic-800/30 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-forensic-700 flex items-center justify-center flex-shrink-0">
                      <Users className="h-5 w-5 text-forensic-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="badge badge-emerald text-xs">
                          {contact.app || 'unknown'}
                        </span>
                        <p className="font-medium text-forensic-100 truncate">
                          {contact.display_name || contact.first_name || 'Unknown'}
                        </p>
                      </div>
                      <div className="flex items-center gap-4 mt-1 text-sm text-forensic-500">
                        {contact.phone && <span>{contact.phone}</span>}
                        {contact.jid && <span className="font-mono text-xs">{contact.jid}</span>}
                        {contact.username && <span>@{contact.username}</span>}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              {contactCount > 50 && (
                <div className="p-3 text-center text-sm text-forensic-500 border-t border-forensic-700">
                  Showing 50 of {contactCount} contacts. Use filters to narrow results.
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Media Section */}
      {mediaCount > 0 && (
        <div className="card overflow-hidden p-0">
          <button
            onClick={() => toggleSection('media')}
            className="w-full flex items-center justify-between p-4 hover:bg-forensic-800/50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-accent-violet/20 flex items-center justify-center">
                <Image className="h-5 w-5 text-accent-violet" />
              </div>
              <div className="text-left">
                <span className="font-semibold text-forensic-100">Media</span>
                <span className="text-sm text-forensic-500 ml-2">({mediaCount})</span>
              </div>
            </div>
            {expandedSection === 'media' ? (
              <ChevronDown className="h-5 w-5 text-forensic-500" />
            ) : (
              <ChevronRight className="h-5 w-5 text-forensic-500" />
            )}
          </button>

          {expandedSection === 'media' && (
            <div className="border-t border-forensic-700">
              <div className="p-4 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                {results.media.slice(0, 24).map((item, idx) => (
                  <div
                    key={item.id || idx}
                    className="border border-forensic-700 rounded-lg p-3 hover:bg-forensic-800/50 transition-colors"
                  >
                    <div className="aspect-square bg-forensic-800 rounded flex items-center justify-center mb-2">
                      {item.media_type === 'image' && <Image className="h-8 w-8 text-accent-emerald" />}
                      {item.media_type === 'video' && <Video className="h-8 w-8 text-accent-violet" />}
                      {item.media_type === 'audio' && <Music className="h-8 w-8 text-accent-amber" />}
                      {!item.media_type && <FileText className="h-8 w-8 text-forensic-500" />}
                    </div>
                    <p className="text-xs text-forensic-300 truncate" title={item.file_path}>
                      {item.file_path?.split('/').pop()?.substring(0, 20) || 'Unknown'}
                    </p>
                    <div className="flex items-center justify-between mt-1">
                      <p className="text-xs text-forensic-500 capitalize">
                        {item.media_type || 'file'}
                      </p>
                      {item.is_orphan && (
                        <span className="badge badge-amber text-xs">orphan</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              {mediaCount > 24 && (
                <div className="p-3 text-center text-sm text-forensic-500 border-t border-forensic-700">
                  Showing 24 of {mediaCount} media files. Use filters to narrow results.
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SearchResults;