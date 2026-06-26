import { formatDistanceToNow } from 'date-fns';
import { MessageSquare, Users, Layers, Image } from 'lucide-react';

const AppStatsCard = ({ app, stats }) => {
  if (!stats) return null;

  const appColors = {
    WhatsApp: 'text-accent-emerald',
    Telegram: 'text-accent-blue',
  };

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg font-semibold capitalize text-forensic-100">{app}</span>
        <span className={`badge ${app === 'WhatsApp' ? 'badge-emerald' : 'badge-blue'}`}>
          {app === 'WhatsApp' ? 'WhatsApp' : 'Telegram'}
        </span>
      </div>
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-forensic-400">
            <MessageSquare className="h-4 w-4" />
            <span className="text-sm">Messages</span>
          </div>
          <span className="font-medium font-mono text-forensic-100">
            {stats.message_count?.toLocaleString() ?? 0}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-forensic-400">
            <Users className="h-4 w-4" />
            <span className="text-sm">Contacts</span>
          </div>
          <span className="font-medium font-mono text-forensic-100">
            {stats.contact_count?.toLocaleString() ?? 0}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-forensic-400">
            <Layers className="h-4 w-4" />
            <span className="text-sm">Groups</span>
          </div>
          <span className="font-medium font-mono text-forensic-100">
            {stats.group_count?.toLocaleString() ?? 0}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-forensic-400">
            <Image className="h-4 w-4" />
            <span className="text-sm">Media</span>
          </div>
          <span className="font-medium font-mono text-forensic-100">
            {stats.media_count?.toLocaleString() ?? 0}
          </span>
        </div>
        {stats.first_activity && (
          <div className="pt-2 border-t border-forensic-700 text-xs text-forensic-500">
            Active: {formatDistanceToNow(new Date(stats.first_activity), { addSuffix: true })}
          </div>
        )}
      </div>
    </div>
  );
};

export default AppStatsCard;