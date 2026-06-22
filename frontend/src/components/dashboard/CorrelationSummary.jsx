import { Link2, MessageSquare, Image, GitCompare } from 'lucide-react';

const CorrelationSummary = ({ stats }) => {
  if (!stats) return null;

  return (
    <div className="border rounded-lg p-4">
      <h3 className="font-semibold text-lg mb-3">Correlation Analysis</h3>
      <div className="space-y-3">
        <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
          <div className="flex items-center gap-2">
            <Link2 className="h-5 w-5 text-blue-600" />
            <span className="text-sm font-medium text-blue-900">Total Links</span>
          </div>
          <span className="text-xl font-bold text-blue-600">
            {stats.total_edges?.toLocaleString() ?? 0}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div className="p-3 bg-gray-50 rounded-lg text-center">
            <MessageSquare className="h-4 w-4 mx-auto mb-1 text-gray-600" />
            <p className="text-lg font-semibold">{stats.message_contact_links?.toLocaleString() ?? 0}</p>
            <p className="text-xs text-gray-500">Message → Contact</p>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg text-center">
            <Image className="h-4 w-4 mx-auto mb-1 text-gray-600" />
            <p className="text-lg font-semibold">{stats.message_media_links?.toLocaleString() ?? 0}</p>
            <p className="text-xs text-gray-500">Message → Media</p>
          </div>
        </div>

        <div className="p-3 bg-purple-50 rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <GitCompare className="h-4 w-4 text-purple-600" />
            <span className="text-sm font-medium text-purple-900">Cross-App Links</span>
          </div>
          <p className="text-center">
            <span className="text-2xl font-bold text-purple-600">
              {stats.cross_app_links?.toLocaleString() ?? 0}
            </span>
            <span className="text-sm text-purple-700 ml-2">WhatsApp ↔ Telegram</span>
          </p>
        </div>
      </div>
    </div>
  );
};

export default CorrelationSummary;