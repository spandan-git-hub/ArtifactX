import { MessageSquare, Users, Image, Trash2, Layers } from 'lucide-react';

const StatsCard = ({ title, value, icon: Icon, description, color = 'blue' }) => {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600 border-blue-200',
    green: 'bg-green-50 text-green-600 border-green-200',
    purple: 'bg-purple-50 text-purple-600 border-purple-200',
    orange: 'bg-orange-50 text-orange-600 border-orange-200',
    red: 'bg-red-50 text-red-600 border-red-200',
    gray: 'bg-gray-50 text-gray-600 border-gray-200',
  };

  return (
    <div className={`rounded-lg border p-4 ${colorClasses[color]}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-2xl font-bold mt-1">{value?.toLocaleString() ?? 0}</p>
          {description && (
            <p className="text-xs mt-1 opacity-75">{description}</p>
          )}
        </div>
        {Icon && (
          <div className="p-3 rounded-full bg-white/50">
            <Icon className="h-6 w-6" />
          </div>
        )}
      </div>
    </div>
  );
};

export default StatsCard;