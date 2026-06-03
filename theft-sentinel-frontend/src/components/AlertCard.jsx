import { BellAlertIcon, TrashIcon } from '@heroicons/react/24/outline';

const AlertCard = ({ alert, onClick, onDelete, showDelete = false }) => {
  // Dark theme severity colors
  const severityColors = {
    medium: 'border-status-warning bg-status-warning/10',
    high: 'border-status-error bg-status-error/10',
  };

  const severityBadgeColors = {
    medium: 'bg-status-warning/20 text-status-warning border border-status-warning/50',
    high: 'bg-status-error/20 text-status-error border border-status-error/50',
  };

  const severityKey = alert.severity?.toLowerCase();
  const borderColor = severityColors[severityKey] || 'border-dark-border bg-dark-card';
  const badgeColor = severityBadgeColors[severityKey] || 'bg-dark-card text-dark-text-muted border border-dark-border';

  // Check if alert is acknowledged (status can be ACKED or acknowledged field)
  const isAcknowledged = alert.status === 'ACKED' || alert.status === 'RESOLVED' || alert.acknowledged;

  return (
    <div
      onClick={() => onClick && onClick(alert)}
      className={`glass rounded-xl p-6 border-l-4 ${borderColor} hover:shadow-glow-ai transition-all duration-300 cursor-pointer transform hover:scale-[1.02] ${
        !isAcknowledged ? 'ring-2 ring-status-error/50 shadow-glow-error' : ''
      }`}
    >
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div className="flex items-center space-x-3 min-w-0">
          <div className={`p-3 rounded-lg ${isAcknowledged ? 'bg-dark-card' : 'bg-status-error'}`}>
            <BellAlertIcon className="h-6 w-6 text-white" />
          </div>
          <div className="min-w-0">
            <h3 className="text-lg font-semibold text-dark-text-primary truncate">{alert.alert_type}</h3>
            <p className="text-sm text-dark-text-muted">{alert.description || 'No description'}</p>
          </div>
        </div>
        <div className="flex flex-row sm:flex-col items-start sm:items-end gap-2">
          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${badgeColor}`}>
            {alert.severity?.toUpperCase() || 'UNKNOWN'}
          </span>
          {!isAcknowledged && (
            <span className="px-2 py-1 bg-status-error/20 text-status-error rounded-full text-xs font-semibold border border-status-error/50">
              NEW
            </span>
          )}
        </div>
      </div>

      <div className="mt-4 space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-dark-text-muted">Camera:</span>
          <span className="font-medium text-dark-text-primary">{alert.camera_name || 'Unknown'}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-dark-text-muted">Time:</span>
          <span className="font-medium text-dark-text-primary">
            {new Date(alert.timestamp).toLocaleString()}
          </span>
        </div>
        {isAcknowledged && (
          <div className="flex justify-between text-sm">
            <span className="text-dark-text-muted">Status:</span>
            <span className="font-medium text-status-success">✓ {alert.status || 'Acknowledged'}</span>
          </div>
        )}
      </div>

      {showDelete && (
        <div className="mt-4 pt-4 border-t border-dark-border">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete && onDelete(alert.id);
            }}
            className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-status-error text-white rounded-lg hover:bg-status-error/90 transition-all duration-200 font-semibold"
          >
            <TrashIcon className="h-4 w-4" />
            <span>Dismiss Alert</span>
          </button>
        </div>
      )}
    </div>
  );
};

export default AlertCard;

