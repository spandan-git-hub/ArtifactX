import { formatDistanceToNow } from 'date-fns';
import { Clock, Zap } from 'lucide-react';

const RecentEvents = ({ events }) => {
  if (!events || events.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <Clock className="h-12 w-12 mx-auto mb-2 text-gray-300" />
        <p>No timeline events yet.</p>
        <p className="text-sm">Build the timeline to see recent activity.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {events.map((event) => (
        <div key={event.id} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
          <div className="flex-shrink-0 mt-0.5">
            <Zap className="h-4 w-4 text-yellow-500" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-700 capitalize">
                {event.source_app}
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-gray-200 text-gray-700">
                {event.event_type}
              </span>
            </div>
            <p className="text-sm text-gray-900 truncate">
              {event.description || `Event: ${event.event_type}`}
            </p>
            {event.normalized_timestamp && (
              <p className="text-xs text-gray-500 mt-1">
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