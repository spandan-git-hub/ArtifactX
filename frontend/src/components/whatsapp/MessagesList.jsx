import { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';

const MessagesList = ({ evidenceId, messages }) => {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div className="bg-white p-4 rounded-lg shadow">
      <div className="flex justify-between items-start mb-4">
        <h2 className="font-semibold">WhatsApp Messages</h2>
        <div className="space-x-2">
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="btn text-xs font-semibold bg-gray-600 text-white px-3 py-1 rounded hover:bg-gray-700"
          >
            {showDetails ? 'Hide Details' : 'Show Details'}
          </button>
        </div>
      </div>

      {messages.length === 0 ? (
        <p className="text-gray-500 text-center py-6">No WhatsApp messages found.</p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Time
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    From
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Message
                  </th>
                  {showDetails && (
                    <>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Media
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Type
                      </th>
                    </>
                  )}
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {messages.map((msg) => (
                  <tr key={msg.message_id || msg.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {msg.timestamp ? (
                        <span className="text-xs">
                          {formatDistanceToNow(new Date(msg.timestamp * 1000), { addSuffix: true })}
                        </span>
                      ) : 'Unknown'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {msg.participant_jid || msg.sender_jid || 'Unknown'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 break-words">
                      {msg.body || '(No text content)'}
                    </td>
                    {showDetails && (
                      <>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-center text-gray-500">
                          {msg.media_type ? (
                            <span className="px-2 py-1 text-xs rounded">
                              {msg.media_type === 'image' ? '🖼️ Image' :
                               msg.media_type === 'video' ? '📹 Video' :
                               msg.media_type === 'audio' ? '🎵 Audio' :
                               '📎 Document'}
                            </span>
                          ) : 'None'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {msg.message_type || 'text'}
                        </td>
                      </>
                    )}
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-center text-gray-500">
                      {msg.status || 'unknown'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {messages.length > 0 && (
            <p className="mt-2 text-xs text-gray-500 text-right">
              Showing {messages.length} message{messages.length !== 1 ? 's' : ''}
            </p>
          )}
        </>
      )}
    </div>
  );
};

export default MessagesList;