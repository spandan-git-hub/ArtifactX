import { useState } from 'react';

const GroupsList = ({ evidenceId, groups }) => {
  return (
    <div className="bg-white p-4 rounded-lg shadow">
      <div className="flex justify-between items-start mb-4">
        <h2 className="font-semibold">WhatsApp Groups</h2>
      </div>

      {groups.length === 0 ? (
        <p className="text-gray-500 text-center py-6">No WhatsApp groups found.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Group Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Group JID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Creator
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Created
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {groups.map((group) => (
                <tr key={group.group_jid || group.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {group.subject || 'Unnamed Group'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 break-all">
                    {group.group_jid || 'Unknown'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {group.creator_jid || 'Unknown'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {group.creation_timestamp ? (
                      new Date(group.creation_timestamp * 1000).toLocaleString()
                    ) : 'Unknown'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="mt-2 text-xs text-gray-500 text-right">
          Showing {groups.length} group{groups.length !== 1 ? 's' : ''}
        </p>
      )}
    </div>
  );
};

export default GroupsList;>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {group.creator_jid || 'Unknown'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {group.creation_timestamp ? (
                      new Date(group.creation_timestamp * 1000).toLocaleString()
                    ) : 'Unknown'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="mt-2 text-xs text-gray-500 text-right">
          Showing {groups.length} group{groups.length !== 1 ? 's' : ''}
        </p>
      )}
    </div>
  );
};

export default GroupsList;