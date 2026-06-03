import { ArrowTrendingUpIcon, ArrowTrendingDownIcon } from '@heroicons/react/24/outline';

const StatsCard = ({ title, value, icon: Icon, color = 'bg-ai-blue', trend, subtitle }) => {
  const getColorClasses = (color) => {
    const colorMap = {
      'bg-blue-500': 'bg-status-info/20 text-status-info border-status-info/50',
      'bg-red-500': 'bg-status-error/20 text-status-error border-status-error/50',
      'bg-yellow-500': 'bg-status-warning/20 text-status-warning border-status-warning/50',
      'bg-green-500': 'bg-status-success/20 text-status-success border-status-success/50',
      'bg-ai-blue': 'bg-ai-blue/20 text-ai-blue border-ai-blue/50',
    };
    return colorMap[color] || 'bg-ai-blue/20 text-ai-blue border-ai-blue/50';
  };

  return (
    <div className="glass rounded-xl p-6 hover:shadow-glow-ai transition-all duration-300 transform hover:scale-[1.02] border border-dark-border">
      <div className="flex items-center justify-between mb-4">
        <div className="flex-1">
          <p className="text-xs font-medium text-dark-text-muted uppercase tracking-wider mb-1">
            {title}
          </p>
          <div className="flex items-baseline space-x-2">
            <p className="text-3xl font-bold text-dark-text-primary">{value}</p>
            {trend !== undefined && (
              <div className={`flex items-center space-x-1 text-sm ${
                trend >= 0 ? 'text-status-success' : 'text-status-error'
              }`}>
                {trend >= 0 ? (
                  <ArrowTrendingUpIcon className="h-4 w-4" />
                ) : (
                  <ArrowTrendingDownIcon className="h-4 w-4" />
                )}
                <span>{Math.abs(trend)}%</span>
              </div>
            )}
          </div>
          {subtitle && (
            <p className="text-xs text-dark-text-muted mt-1">{subtitle}</p>
          )}
        </div>
        <div className={`${getColorClasses(color)} p-3 rounded-lg border`}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </div>
  );
};

export default StatsCard;
