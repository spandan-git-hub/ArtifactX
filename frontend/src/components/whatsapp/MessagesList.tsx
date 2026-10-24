import { useState } from 'react';
import { formatDistanceToNow, format } from 'date-fns';
import {
  Image,
  Video,
  Music,
  FileText,
  ChevronDown,
  ChevronUp,
  Eye,
} from 'lucide-react';

const MessagesList = ({ evidenceId, messages }) => {
  const [showDetails, setShowDetails] = useState(false);
  const [expandedMessages, setExpandedMessages] = useState([]);

  const toggleMessage = (idx) => {
    setExpandedMessages((prev) =>
      prev.includes(idx) ? prev.filter((i) => i !== idx) : [...prev, idx]
    );
  };

  const getMediaIcon = (mediaType) => {
    switch (mediaType) {
      case 'image':
        return <Image className="h-4 w-4 text-accent-emerald" />;
      case 'video':
        return <Video className="h-4 w-4 text-accent-violet" />;
      case 'audio':
        return <Music className="h-4 w-4 text-accent-amber" />;
      default:
        return <FileText className="h-4 w-4 text-forensic-500" />;
    }
  };

  const formatTimestamp = (ts) => {
    if (!ts) return 'Unknown';
    const date = new Date(ts * 1000);
    return format(date, 'MMM d, yyyy HH:mm');
  };

  return (
    <div className="card">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <span className="badge badge-cyan">{messages.length}</span>
          <span className="text-sm text-forensic-500">messages</span>
        </div>
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="btn-ghost text-sm"
        >
          {showDetails ? (
            <>
              <ChevronUp className="h-4 w-4" />
              Hide Details
            </>
          ) : (
            <>
              <Eye className="h-4 w-4" />
              Show Details
            </>
          )}
        </button>
      </div>

      {messages.length === 0 ? (
        <div className="text-center py-8">
          <MessageSquare className="h-12 w-12 text-forensic-600 mx-auto mb-3" />
          <p className="text-forensic-500">No WhatsApp messages found.</p>
          <p className="text-sm text-forensic-600 mt-1">Upload and analyze WhatsApp data.</p>
        </div>
      ) : (
        <div className="space-y-2 max-h-[500px] overflow-y-auto pr-2">
          {messages.slice(0, 100).map((msg, idx) => (
            <div
              key={msg.message_id || msg.id || idx}
              className={`p-3 rounded-lg border transition-colors cursor-pointer ${
                expandedMessages.includes(idx)
                  ? 'bg-forensic-800 border-forensic-600'
                  : 'bg-forensic-900/50 border-forensic-800 hover:border-forensic-700'
              }`}
              onClick={() => toggleMessage(idx)}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="text-xs px-2 py-0.5 rounded bg-forensic-700 text-forensic-300">
                      {msg.participant_jid?.split('@')[0] || msg.sender_jid?.split('@')[0] || 'Unknown'}
                    </span>
                    {msg.media_type && (
                      <div className="flex items-center gap-1">
                        {getMediaIcon(msg.media_type)}
                        <span className="text-xs text-forensic-500">{msg.media_type}</span>
                      </div>
                    )}
                    {showDetails && (
                      <>
                        <span className="text-xs text-forensic-500">
                          {msg.message_type || 'text'}
                        </span>
                        <span className="text-xs text-forensic-500">
                          {msg.status || 'unknown'}
                        </span>
                      </>
                    )}
                  </div>
                  <p className={`text-sm ${msg.body ? 'text-forensic-200' : 'text-forensic-500 italic'}`}>
                    {msg.body || '(No text content)'}
                  </p>
                </div>
                <div className="text-right flex-shrink-0">
                  <span className="text-xs text-forensic-500 whitespace-nowrap">
                    {formatTimestamp(msg.timestamp)}
                  </span>
                </div>
              </div>

              {expandedMessages.includes(idx) && showDetails && (
                <div className="mt-3 pt-3 border-t border-forensic-700 grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-forensic-500">Message ID:</span>
                    <span className="ml-2 text-forensic-400 font-mono">{msg.message_id || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-forensic-500">Chat:</span>
                    <span className="ml-2 text-forensic-400 font-mono truncate">{msg.key_remote_jid || 'N/A'}</span>
                  </div>
                  {msg.media_path && (
                    <div className="col-span-2">
                      <span className="text-forensic-500">Media Path:</span>
                      <span className="ml-2 text-forensic-400 font-mono text-xs break-all">{msg.media_path}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {messages.length > 100 && (
        <p className="mt-4 text-xs text-forensic-500 text-center">
          Showing 100 of {messages.length} messages. Filter to see more.
        </p>
      )}
    </div>
  );
};

// Re-export MessageSquare for use in empty state
import { MessageSquare } from 'lucide-react';

export default MessagesList;