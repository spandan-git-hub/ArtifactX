import { Users } from 'lucide-react';

const ContactsList = ({ evidenceId, contacts }) => {
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
          <p className="text-forensic-500">No WhatsApp contacts found.</p>
          <p className="text-sm text-forensic-600 mt-1">Analyze evidence to extract contacts.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>JID</th>
                <th>Phone</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {contacts.map((contact) => (
                <tr key={contact.jid || contact.id}>
                  <td className="text-forensic-100 font-medium">
                    {contact.display_name || 'Unnamed'}
                  </td>
                  <td className="hash-text">
                    {contact.jid || 'Unknown'}
                  </td>
                  <td className="text-forensic-400">
                    {contact.phone_number || 'N/A'}
                  </td>
                  <td>
                    <span className={`badge ${
                      contact.status === 'new' ? 'badge-emerald' :
                      contact.status === 'completed' ? 'badge-cyan' :
                      'badge-gray'
                    }`}>
                      {contact.status || 'Unknown'}
                    </span>
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

export default ContactsList;