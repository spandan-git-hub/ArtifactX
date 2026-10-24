import { FolderOpen, Plus, RefreshCw } from 'lucide-react';

const EmptyState = ({
  icon: Icon = FolderOpen,
  title = 'No Data',
  description = 'There is nothing to display here yet.',
  action,
  onRefresh,
  actionLabel,
  onAction
}) => {
  return (
    <div className="card text-center py-16">
      <div className="w-16 h-16 rounded-2xl bg-forensic-800 flex items-center justify-center mx-auto mb-4">
        <Icon className="h-8 w-8 text-forensic-500" />
      </div>
      <h3 className="text-lg font-semibold text-forensic-100 mb-2">{title}</h3>
      <p className="text-forensic-500 mb-6 max-w-sm mx-auto">{description}</p>

      {(action || onRefresh || onAction) && (
        <div className="flex items-center justify-center gap-3">
          {action}
          {onAction && (
            <button
              onClick={onAction}
              className="btn-primary inline-flex items-center gap-2"
            >
              <Plus className="h-4 w-4" />
              {actionLabel || 'Get Started'}
            </button>
          )}
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="btn-ghost inline-flex items-center gap-2"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default EmptyState;