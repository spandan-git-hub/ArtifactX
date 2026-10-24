import { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';

const GroupsList = ({ evidenceId, groups }) => {
  return (
    <div className="card">
      <div className="flex justify-between items-start mb-4">
        <h2 className="font-semibold text-forensic-100">WhatsApp Groups</h2>
        <span className="badge badge-cyan">{groups.length}</span>
      </div>

      {groups.length === 0 ? (
        <p className="text-forensic-500 text-center py-6">No WhatsApp groups found.</p>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Group Name</th>
                <th>Group JID</th>
                <th>Creator</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {groups.map((group) => (
                <tr key={group.group_jid || group.id}>
                  <td className="text-forensic-100 font-medium">
                    {group.subject || 'Unnamed Group'}
                  </td>
                  <td className="hash-text">
                    {group.group_jid || 'Unknown'}
                  </td>
                  <td className="text-forensic-400">
                    {group.creator_jid || 'Unknown'}
                  </td>
                  <td className="text-forensic-400">
                    {group.creation_timestamp ? (
                      formatDistanceToNow(new Date(group.creation_timestamp * 1000), { addSuffix: true })
                    ) : 'Unknown'}
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

export default GroupsList;