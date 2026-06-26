import {
  MessageSquare,
  Users,
  Image,
  Trash2,
  Layers,
  BarChart3,
} from 'lucide-react';

const StatsCard = ({ title, value, icon: Icon, description, color = 'cyan' }) => {
  const colorMap = {
    cyan: 'text-accent-cyan bg-accent-cyan/10',
    emerald: 'text-accent-emerald bg-accent-emerald/10',
    violet: 'text-accent-violet bg-accent-violet/10',
    amber: 'text-accent-amber bg-accent-amber/10',
    rose: 'text-accent-rose bg-accent-rose/10',
    blue: 'text-accent-blue bg-accent-blue/10',
  };
  const classes = colorMap[color] || colorMap.cyan;

  return (
    <div className="card card-hover">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-forensic-500">{title}</p>
          <p className="text-3xl font-bold font-mono mt-1 text-forensic-50">
            {value?.toLocaleString() ?? 0}
          </p>
          {description && (
            <p className="text-xs mt-1 text-forensic-500">{description}</p>
          )}
        </div>
        {Icon && (
          <div className={`p-3 rounded-xl ${classes}`}>
            <Icon className="h-6 w-6" />
          </div>
        )}
      </div>
    </div>
  );
};

export default StatsCard;