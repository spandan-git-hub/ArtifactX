import { Link2, MessageSquare, Image, GitCompare } from 'lucide-react';

const CorrelationSummary = ({ stats }) => {
  if (!stats) return null;

  return (
    <div className="card">
      <h3 className="font-semibold text-forensic-100 mb-4">Correlation Analysis</h3>
      <div className="space-y-3">
        <div className="flex items-center justify-between p-4 bg-accent-cyan/10 rounded-lg border border-accent-cyan/20">
          <div className="flex items-center gap-2">
            <Link2 className="h-5 w-5 text-accent-cyan" />
            <span className="text-sm font-medium text-forensic-200">Total Links</span>
          </div>
          <span className="text-2xl font-bold font-mono text-accent-cyan">
            {stats.total_edges?.toLocaleString() ?? 0}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div className="p-3 bg-forensic-800/50 rounded-lg text-center border border-forensic-700/50">
            <MessageSquare className="h-4 w-4 mx-auto mb-1 text-forensic-500" />
            <p className="text-lg font-bold font-mono text-forensic-100">
              {stats.message_contact_links?.toLocaleString() ?? 0}
            </p>
            <p className="text-xs text-forensic-500">Message → Contact</p>
          </div>
          <div className="p-3 bg-forensic-800/50 rounded-lg text-center border border-forensic-700/50">
            <Image className="h-4 w-4 mx-auto mb-1 text-forensic-500" />
            <p className="text-lg font-bold font-mono text-forensic-100">
              {stats.message_media_links?.toLocaleString() ?? 0}
            </p>
            <p className="text-xs text-forensic-500">Message → Media</p>
          </div>
        </div>

        <div className="p-3 bg-accent-violet/10 rounded-lg border border-accent-violet/20">
          <div className="flex items-center gap-2 mb-2">
            <GitCompare className="h-4 w-4 text-accent-violet" />
            <span className="text-sm font-medium text-forensic-200">Cross-App Links</span>
          </div>
          <p className="text-center">
            <span className="text-2xl font-bold font-mono text-accent-violet">
              {stats.cross_app_links?.toLocaleString() ?? 0}
            </span>
            <span className="text-sm text-forensic-400 ml-2">WhatsApp ↔ Telegram</span>
          </p>
        </div>
      </div>
    </div>
  );
};

export default CorrelationSummary;