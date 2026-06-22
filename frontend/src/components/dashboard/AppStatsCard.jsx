import { formatDistanceToNow } from 'date-fns';
import { MessageSquare, Users, Layers } from 'lucide-react';

const AppStats = ({ app, stats }) => {
  if (!stats) return null;

  return (
    <div className="border rounded-lg p-4">
      <h3 className="font-semibold text-lg mb-3 capitalize">{app}</h3>
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-gray-600">
            <MessageSquare className="h-4 w-4" />
            <span className="text-sm">Messages</span>
          </div>
          <span className="font-medium">{stats.message_count?.toLocaleString() ?? 0}</span>
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-gray-600">
            <Users className="h-4 w-4" />
            <span className="text-sm">Contacts</span>
          </div>
          <span className="font-medium">{stats.contact_count?.toLocaleString() ?? 0}</span>
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-gray-600">
            <Layers className="h-4 w-4" />
            <span className="text-sm">Groups</span>
          </div>
          <span className="font-medium">{stats.group_count?.toLocaleString() ?? 0}</span>
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-gray-600">
            <span className="text-sm">Media</span>
          </div>
          <span className="font-medium">{stats.media_count?.toLocaleString() ?? 0}</span>
        </div>
        {stats.first_activity && (
          <div className="pt-2 border-t text-xs text-gray-500">
            Active: {formatDistanceToNow(new Date(stats.first_activity), { addSuffix: true })}
          </div>
        )}
      </div>
    </div>
  );
};

export default AppStats;