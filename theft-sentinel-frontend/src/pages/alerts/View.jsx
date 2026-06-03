import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { getAlert, acknowledgeAlert } from '../../api/alerts';
import { listUsers } from '../../api/auth';
import { useRecoilValue } from 'recoil';
import { authUserState } from '../../store/authStore';
import toast from 'react-hot-toast';
import { ArrowLeftIcon, CheckCircleIcon } from '@heroicons/react/24/outline';

const View = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const user = useRecoilValue(authUserState);
  const [alert, setAlert] = useState(null);
  const [loading, setLoading] = useState(true);
  const [acknowledging, setAcknowledging] = useState(false);
  const [guards, setGuards] = useState([]);
  const [selectedGuard, setSelectedGuard] = useState('');
  const [comment, setComment] = useState('');
  const canAcknowledge = user?.role === 'ADMIN' || user?.role === 'SECURITY_INCHARGE';

  useEffect(() => {
    fetchAlert();
    if (canAcknowledge) fetchGuards();
  }, [id, canAcknowledge]);

  const fetchAlert = async () => {
    try {
      const response = await getAlert(id);
      setAlert(response.data);
    } catch (error) {
      console.error('Error fetching alert:', error);
      toast.error('Failed to load alert details');
      navigate('/alerts');
    } finally {
      setLoading(false);
    }
  };

  const fetchGuards = async () => {
    try {
      const response = await listUsers({ role: 'SECURITY_GUARD' });
      // Handle paginated response: {count, results, next, previous} or direct array
      const guardsList = response.data?.results || response.data || [];
      setGuards(Array.isArray(guardsList) ? guardsList : []);
    } catch (error) {
      console.error('Error fetching guards:', error);
      console.error('Error details:', error.response?.data || error.message);
      // Set empty array on error to prevent undefined issues
      setGuards([]);
    }
  };

  const handleAcknowledge = async () => {
    if (!selectedGuard) {
      toast.error('Please select a guard to assign');
      return;
    }

    setAcknowledging(true);
    try {
      // Acknowledge alert with guard assignment and optional comment
      await acknowledgeAlert(id, 'ACKED', selectedGuard, comment);
      toast.success('Alert acknowledged and incident created successfully');
      fetchAlert();
      setSelectedGuard('');
      setComment('');
    } catch (error) {
      console.error('Error acknowledging alert:', error);
      const errorMsg = error.response?.data?.error || error.response?.data?.detail || 'Failed to acknowledge alert';
      toast.error(errorMsg);
    } finally {
      setAcknowledging(false);
    }
  };

  if (loading) {
    return <div className="animate-pulse h-96 bg-dark-card rounded-lg border border-dark-border"></div>;
  }

  if (!alert) return null;

  const severityColors = {
    medium: 'bg-status-warning/20 text-status-warning border border-status-warning/50',
    high: 'bg-status-error/20 text-status-error border border-status-error/50',
  };
  const severityKey = alert.severity?.toLowerCase();

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center space-x-4 min-w-0">
          <button
            onClick={() => navigate('/alerts')}
            className="p-2 hover:bg-dark-card rounded-full transition-colors"
          >
            <ArrowLeftIcon className="h-6 w-6 text-dark-text-secondary" />
          </button>
          <h1 className="text-3xl font-bold text-dark-text-primary truncate">Alert Details</h1>
        </div>
        {canAcknowledge && alert.status !== 'ACKED' && alert.status !== 'RESOLVED' && (
          <button
            onClick={handleAcknowledge}
            disabled={acknowledging || !selectedGuard}
            className="px-6 py-2 bg-status-success text-white rounded-md hover:bg-status-success/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 font-semibold"
          >
            <CheckCircleIcon className="h-5 w-5" />
            <span>{acknowledging ? 'Acknowledging...' : 'Acknowledge & Assign'}</span>
          </button>
        )}
      </div>

      <div className="glass rounded-xl border border-dark-border p-6">
        <div className="space-y-6">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 pb-6 border-b border-dark-border">
            <div className="min-w-0">
              <h2 className="text-2xl font-bold text-dark-text-primary">{alert.alert_type}</h2>
              <p className="text-dark-text-secondary mt-2">{alert.description || 'No description available'}</p>
            </div>
            <span
              className={`px-4 py-2 rounded-full text-sm font-semibold ${
                severityColors[severityKey] || 'bg-dark-card text-dark-text-muted border border-dark-border'
              }`}
            >
              {alert.severity?.toUpperCase() || 'UNKNOWN'}
            </span>
          </div>

          {/* Details Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-sm font-medium text-dark-text-muted">Camera</h3>
              <p className="text-lg font-semibold text-dark-text-primary mt-1">
                {alert.camera_name || 'Unknown'}
              </p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-dark-text-muted">Timestamp</h3>
              <p className="text-lg font-semibold text-dark-text-primary mt-1">
                {new Date(alert.timestamp).toLocaleString()}
              </p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-dark-text-muted">Status</h3>
              <p className="text-lg font-semibold mt-1">
                <span
                  className={`px-3 py-1 rounded-full text-sm font-semibold ${
                    alert.status === 'ACKED' || alert.status === 'RESOLVED'
                      ? 'bg-status-success/20 text-status-success border border-status-success/50'
                      : 'bg-status-warning/20 text-status-warning border border-status-warning/50'
                  }`}
                >
                  {alert.status === 'ACKED' || alert.status === 'RESOLVED' ? 'Acknowledged' : 'Pending'}
                </span>
              </p>
            </div>
          </div>

          {/* AI Frame */}
          {alert.ai_frame && (
            <div>
              <h3 className="text-lg font-semibold text-dark-text-primary mb-3">AI Detection Frame</h3>
              <img
                src={alert.ai_frame}
                alt="Alert frame"
                className="w-full max-w-2xl rounded-lg shadow-md border border-dark-border"
              />
            </div>
          )}

          {/* Detection Video Clip */}
          <div>
            <h3 className="text-lg font-semibold text-dark-text-primary mb-3 flex items-center gap-2">
              <span>🎬</span> Detection Clip
              {alert.video_url && (
                <span className="text-xs font-normal px-2 py-0.5 rounded-full bg-status-success/20 text-status-success border border-status-success/40">
                  Available
                </span>
              )}
            </h3>

            {alert.video_url ? (
              <div className="rounded-xl overflow-hidden border border-dark-border bg-black shadow-lg">
                <video
                  controls
                  autoPlay={false}
                  playsInline
                  preload="metadata"
                  className="w-full max-h-[480px] object-contain"
                  style={{ background: '#000' }}
                >
                  <source src={alert.video_url} type="video/mp4" />
                  <source src={alert.video_url} type="video/webm" />
                  Your browser does not support the video element.
                </video>
                <div className="flex items-center justify-between px-4 py-2 bg-dark-card border-t border-dark-border">
                  <span className="text-xs text-dark-text-muted">
                    📹 ~5 second clip captured around detection event
                  </span>
                  <a
                    href={alert.video_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-ai-blue hover:underline font-medium"
                  >
                    Open in new tab ↗
                  </a>
                </div>
              </div>
            ) : (
              <div className="rounded-xl border border-dark-border border-dashed bg-dark-card p-8 flex flex-col items-center justify-center gap-3 text-center">
                <span className="text-4xl">⏳</span>
                <p className="text-dark-text-secondary font-medium">
                  {alert.status === 'ACTIVE'
                    ? 'Clip is being processed & uploaded…'
                    : 'No clip available for this alert'}
                </p>
                <p className="text-xs text-dark-text-muted max-w-xs">
                  {alert.status === 'ACTIVE'
                    ? 'Cloudinary upload runs in the background. Refresh in a few seconds.'
                    : 'A 5-second clip is captured automatically when theft is detected. Older alerts may not have one.'}
                </p>
                {alert.status === 'ACTIVE' && (
                  <button
                    onClick={fetchAlert}
                    className="mt-1 px-4 py-1.5 text-sm bg-ai-blue/20 text-ai-blue border border-ai-blue/40 rounded-md hover:bg-ai-blue/30 transition-colors font-medium"
                  >
                    Refresh
                  </button>
                )}
              </div>
            )}
          </div>


          {/* Additional Info */}
          {alert.metadata && (
            <div>
              <h3 className="text-lg font-semibold text-dark-text-primary mb-3">Additional Information</h3>
              <div className="bg-dark-card rounded-lg p-6 space-y-4 border border-dark-border">
                {/* AI Detection Stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {typeof alert.metadata.confidence === 'number' && (
                    <div className="bg-dark-surface p-3 rounded border border-dark-border">
                      <p className="text-xs text-dark-text-muted uppercase">Confidence</p>
                      <p className="text-xl font-bold text-dark-text-primary">
                        {(alert.metadata.confidence * 100).toFixed(1)}%
                      </p>
                    </div>
                  )}
                  {typeof alert.metadata.num_persons === 'number' && (
                    <div className="bg-dark-surface p-3 rounded border border-dark-border">
                      <p className="text-xs text-dark-text-muted uppercase">Persons</p>
                      <p className="text-xl font-bold text-dark-text-primary">
                        {alert.metadata.num_persons}
                      </p>
                    </div>
                  )}
                  {typeof alert.metadata.num_detections === 'number' && (
                    <div className="bg-dark-surface p-3 rounded border border-dark-border">
                      <p className="text-xs text-dark-text-muted uppercase">Objects</p>
                      <p className="text-xl font-bold text-dark-text-primary">
                        {alert.metadata.num_detections}
                      </p>
                    </div>
                  )}
                  {typeof alert.metadata.fps === 'number' && (
                    <div className="bg-dark-surface p-3 rounded border border-dark-border">
                      <p className="text-xs text-dark-text-muted uppercase">FPS</p>
                      <p className="text-xl font-bold text-dark-text-primary">
                        {alert.metadata.fps.toFixed(1)}
                      </p>
                    </div>
                  )}
                </div>

                {/* Detection Source */}
                {alert.metadata.detected_by && (
                  <div className="bg-dark-surface p-3 rounded border border-dark-border">
                    <p className="text-xs text-dark-text-muted uppercase mb-1">Detected By</p>
                    <p className="text-sm font-semibold text-dark-text-primary">
                      {alert.metadata.detected_by}
                    </p>
                  </div>
                )}

                {/* Detection Timestamp */}
                {alert.metadata.detection_timestamp && (
                  <div className="bg-dark-surface p-3 rounded border border-dark-border">
                    <p className="text-xs text-dark-text-muted uppercase mb-1">Detection Time</p>
                    <p className="text-sm font-semibold text-dark-text-primary">
                      {new Date(alert.metadata.detection_timestamp).toLocaleString()}
                    </p>
                  </div>
                )}

                {/* Suspicious Tracks */}
                {Array.isArray(alert.metadata.suspicious_tracks) && alert.metadata.suspicious_tracks.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-dark-text-primary mb-2">
                      ⚠️ Suspicious Tracks Detected ({alert.metadata.suspicious_tracks.length})
                    </h4>
                    <div className="space-y-2">
                      {alert.metadata.suspicious_tracks.map((track, idx) => {
                        const trackId = track?.track_id ?? idx + 1;
                        const mlScore = typeof track?.ml_score === 'number' ? track.ml_score : 0;
                        const behavior = track?.behavior || {};
                        
                        return (
                          <div key={idx} className="bg-status-warning/10 border border-status-warning/50 rounded p-3">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-semibold text-dark-text-primary">Track #{trackId}</span>
                              <span className="text-sm font-semibold text-status-warning bg-status-warning/20 border border-status-warning/50 px-2 py-1 rounded">
                                Score: {(mlScore * 100).toFixed(1)}%
                              </span>
                            </div>
                            <div className="grid grid-cols-2 gap-2 text-xs text-dark-text-secondary">
                              {typeof behavior.hand_in_bag === 'number' && (
                                <div>Hand in bag: <span className="font-semibold text-dark-text-primary">{behavior.hand_in_bag}</span> frames</div>
                              )}
                              {typeof behavior.hand_in_torso === 'number' && (
                                <div>Hand in torso: <span className="font-semibold text-dark-text-primary">{behavior.hand_in_torso}</span> frames</div>
                              )}
                              {typeof behavior.fast_wrist === 'number' && (
                                <div>Fast wrist: <span className="font-semibold text-dark-text-primary">{behavior.fast_wrist}</span> frames</div>
                              )}
                              {typeof behavior.near_object === 'number' && (
                                <div>Near object: <span className="font-semibold text-dark-text-primary">{behavior.near_object}</span> frames</div>
                              )}
                              {typeof behavior.concealment_events === 'number' && (
                                <div>Concealment: <span className="font-semibold text-dark-text-primary">{behavior.concealment_events}</span> events</div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Acknowledge Form - Only show if alert is not acknowledged */}
          {canAcknowledge && alert.status !== 'ACKED' && alert.status !== 'RESOLVED' && (
            <div className="border-t border-dark-border pt-6">
              <h3 className="text-lg font-semibold text-dark-text-primary mb-4">Acknowledge & Assign to Guard</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-dark-text-secondary mb-2">
                    Select Guard <span className="text-status-error">*</span>
                  </label>
                  <select
                    value={selectedGuard}
                    onChange={(e) => setSelectedGuard(e.target.value)}
                    className="w-full px-4 py-2 bg-dark-card border border-dark-border rounded-md text-dark-text-primary focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent"
                    required
                  >
                    <option value="">-- Select Guard --</option>
                    {guards
                      .filter((guard) => guard.email) // Only show guards with email
                      .map((guard) => (
                        <option key={guard.email} value={guard.email}>
                          {guard.username || guard.email} ({guard.email})
                        </option>
                      ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-dark-text-secondary mb-2">
                    Optional Comment
                  </label>
                  <textarea
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    rows="3"
                    className="w-full px-4 py-2 bg-dark-card border border-dark-border rounded-md text-dark-text-primary placeholder-dark-text-muted focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent"
                    placeholder="Add any additional details or notes..."
                  ></textarea>
                </div>
              </div>
            </div>
          )}

          {/* Acknowledgement Info */}
          {(alert.status === 'ACKED' || alert.status === 'RESOLVED') && (
            <div className="bg-status-success/10 border border-status-success/50 p-4 rounded-lg">
              <h3 className="text-lg font-semibold text-status-success mb-2">
                {alert.status === 'ACKED' ? 'Acknowledged' : 'Resolved'}
              </h3>
              <div className="space-y-1 text-sm text-dark-text-secondary">
                {alert.acknowledged_by && (
                  <p><span className="text-dark-text-muted">By:</span> <span className="text-dark-text-primary font-medium">{alert.acknowledged_by_name || alert.acknowledged_by}</span></p>
                )}
                {alert.acknowledged_at && (
                  <p><span className="text-dark-text-muted">At:</span> <span className="text-dark-text-primary font-medium">{new Date(alert.acknowledged_at).toLocaleString()}</span></p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default View;

