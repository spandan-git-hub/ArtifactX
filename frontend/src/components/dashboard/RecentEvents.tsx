import { formatDistanceToNow } from 'date-fns';
import { Clock, Zap } from 'lucide-react';

const RecentEvents = ({ events }) => {
  if (!events || events.length === 0) {
    return (
      <div className="text-center py-8">
        <Clock className="h-12 w-12 mx-auto mb-2 text-forensic-600" />
        <p className="text-forensic-500">No timeline events yet.</p>
        <p className="text-sm text-forensic-600">Build the timeline to see recent activity.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3 max-h-72 overflow-y-auto">
      {events.map((event) => (
        <div key={event.id} className="flex items-start gap-3 p-3 bg-forensic-800/50 rounded-lg">
          <div className="flex-shrink-0 mt-0.5">
            <Zap className="h-4 w-4 text-accent-amber" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className={`text-xs px-2 py-0.5 rounded capitalize ${
                event.source_app === 'whatsapp'
                  ? 'bg-accent-emerald/15 text-accent-emerald'
                  : 'bg-accent-blue/15 text-accent-blue'
              }`}>
                {event.source_app || 'unknown'}
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-forensic-700 text-forensic-400">
                {event.event_type}
              </span>
            </div>
            <p className="text-sm text-forensic-200 truncate">
              {event.description || `Event: ${event.event_type}`}
            </p>
            {event.normalized_timestamp && (
              <p className="text-xs text-forensic-500 mt-1">
                {formatDistanceToNow(new Date(event.normalized_timestamp), { addSuffix: true })}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

export default RecentEvents;