import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

const IncidentCard = ({ incident, onClick }) => {
  const statusColors = {
    CREATED: 'border-status-warning bg-status-warning/10',
    ASSIGNED: 'border-status-info bg-status-info/10',
    ACKNOWLEDGED: 'border-ai-purple bg-ai-purple/10',
    RESOLVED: 'border-status-success bg-status-success/10',
  };

  const statusBadgeColors = {
    CREATED: 'bg-status-warning/20 text-status-warning border border-status-warning/50',
    ASSIGNED: 'bg-status-info/20 text-status-info border border-status-info/50',
    ACKNOWLEDGED: 'bg-ai-purple/20 text-ai-purple border border-ai-purple/50',
    RESOLVED: 'bg-status-success/20 text-status-success border border-status-success/50',
  };

  const borderColor = statusColors[incident.status] || 'border-dark-border bg-dark-card';
  const badgeColor = statusBadgeColors[incident.status] || 'bg-dark-card text-dark-text-muted border border-dark-border';

  // Get camera name, zone, and timestamp from alert_details
  const cameraName = incident.alert_details?.camera_name || 'Unknown Camera';
  const zone = incident.alert_details?.camera_details?.zone || 'N/A';
  const timestamp = incident.alert_details?.timestamp || incident.created_at;

  return (
    <div
      onClick={() => onClick && onClick(incident)}
      className={`glass rounded-xl p-6 border-l-4 ${borderColor} hover:shadow-glow-ai transition-all duration-300 cursor-pointer overflow-hidden`}
    >
      <div className="flex items-start gap-3">
        <div className="flex items-center space-x-3 min-w-0 flex-1">
          <div className="bg-ai-blue p-3 rounded-lg flex-shrink-0">
            <ExclamationTriangleIcon className="h-6 w-6 text-white" />
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="text-lg font-semibold text-dark-text-primary truncate">
              Incident #{incident.id}
            </h3>
            <p className="text-sm text-dark-text-secondary truncate">{cameraName} - Zone: {zone}</p>
          </div>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap flex-shrink-0 ${badgeColor}`}>
          {incident.status?.replace('_', ' ') || 'Unknown'}
        </span>
      </div>

      <div className="mt-4 space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-dark-text-muted">Timestamp:</span>
          <span className="font-medium text-dark-text-primary">
            {new Date(timestamp).toLocaleString()}
          </span>
        </div>
        {incident.assigned_to_details?.username && (
          <div className="flex justify-between text-sm">
            <span className="text-dark-text-muted">Assigned To:</span>
            <span className="font-medium text-dark-text-primary">{incident.assigned_to_details.username}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default IncidentCard;

