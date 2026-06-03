import { VideoCameraIcon, PencilIcon, TrashIcon, EyeIcon, ArrowPathIcon, PowerIcon } from '@heroicons/react/24/outline';
import { useRecoilValue } from 'recoil';
import CameraFeedWithOverlay from './CameraFeedWithOverlay';
import { useContinuousMonitor } from '../hooks/useContinuousMonitor';
import { authUserState, hasPermission } from '../store/authStore';

const CameraCardWithAI = ({ camera, onViewFeed, onEdit, onDelete, onStatusChange, showFeed = false, showActions = false }) => {
  // ── Auth: determine if this user can control AI monitoring ────────────────
  // ADMIN has 'all' permissions; SECURITY_INCHARGE has 'control_ai_monitoring'.
  // GUARD is read-only — they can see the toggle state but cannot change it.
  const currentUser  = useRecoilValue(authUserState);
  const canControlAI = hasPermission(currentUser, 'control_ai_monitoring');

  const {
    isMonitoring,
    stats,
    loading: aiLoading,
    error: aiError,
    start,
    stop,
  } = useContinuousMonitor(camera.id);

  const lastResult = stats?.last_result;

  // Status colors - dark theme
  const statusColors = {
    ONLINE: 'bg-status-success/20 text-status-success border-status-success/50',
    OFFLINE: 'bg-status-error/20 text-status-error border-status-error/50',
  };

  const statusColor = statusColors[camera.status] || 'bg-dark-card text-dark-text-muted border-dark-border';

  // Card border color based on AI monitoring
  const getCardBorderColor = () => {
    if (aiError) return 'border-status-error';
    if (!isMonitoring) return camera.status === 'ONLINE' ? 'border-status-success' : 'border-status-error';
    if (lastResult?.classification === 'theft') return 'border-status-error';
    return 'border-status-success';
  };

  // Card background color based on AI monitoring - dark theme
  const getCardBgColor = () => {
    if (aiError) return 'bg-status-error/10';
    if (isMonitoring && lastResult?.classification === 'theft') return 'bg-status-error/10';
    if (isMonitoring) return 'bg-status-success/10';
    return 'glass';
  };

  const handleToggleAI = () => {
    if (!canControlAI) return;   // Guard: read-only
    if (isMonitoring) stop(); else start();
  };

  return (
    <div
      className={`rounded-xl overflow-hidden border-l-4 ${getCardBorderColor()} ${getCardBgColor()} border border-dark-border hover:shadow-glow-ai transition-all`}
    >
      {/* Live Feed Preview — with canvas bounding-box overlay when AI is on */}
      {showFeed && camera.status === 'ONLINE' && (
        <div
          onClick={() => onViewFeed && onViewFeed(camera)}
          className="cursor-pointer"
        >
          <CameraFeedWithOverlay
            cameraId={camera.id}
            cameraName={camera.name}
            height="280px"
            enableOverlay={isMonitoring}
            viewMode="grid"
          />
        </div>
      )}
      
      <div className="p-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-3">
          <div className="flex items-center space-x-3 min-w-0">
            <div className="bg-ai-blue p-3 rounded-lg">
              <VideoCameraIcon className="h-8 w-8 text-white" />
            </div>
            <div className="min-w-0">
              <h3 className="text-lg font-semibold text-dark-text-primary truncate">{camera.name}</h3>
              <p className="text-sm text-dark-text-secondary truncate">{camera.location}</p>
            </div>
          </div>
          <div className="flex flex-col items-end gap-2">
            <span
              className={`px-3 py-1 rounded-full text-xs font-semibold border ${statusColor}`}
            >
              {camera.status}
            </span>
            {/* FPS Indicator */}
            {isMonitoring && stats && typeof stats.fps === 'number' && (
              <div className="flex items-center gap-1 text-xs">
                <span className="inline-block w-2 h-2 bg-status-success rounded-full animate-pulse"></span>
                <span className="font-semibold text-status-success">
                  {stats.fps.toFixed(1)} FPS
                </span>
              </div>
            )}
          </div>
        </div>
      
        {/* Camera Info */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-dark-text-muted">Zone:</span>
            <span className="font-medium text-dark-text-primary">{camera.zone || 'N/A'}</span>
          </div>
          {camera.rtsp_url && (
            <div className="flex justify-between text-sm">
              <span className="text-dark-text-muted">Stream:</span>
              <span className="font-mono text-xs text-dark-text-primary truncate max-w-[200px]">
                {camera.rtsp_url}
              </span>
            </div>
          )}
        </div>

        {/* AI Monitoring Section */}
        {(camera.status === 'ONLINE' || isMonitoring) && (
          <div className="mt-4 pt-4 border-t border-dark-border">
            {/* AI Monitoring Toggle */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex flex-col">
                <span className="text-sm font-medium text-dark-text-secondary">AI Monitoring</span>
                {!canControlAI && (
                  <span className="text-xs text-dark-text-muted">View only</span>
                )}
              </div>
              <button
                onClick={handleToggleAI}
                disabled={aiLoading || !canControlAI}
                title={!canControlAI ? 'You do not have permission to control AI monitoring' : undefined}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                  focus:outline-none focus:ring-2 focus:ring-ai-blue focus:ring-offset-2
                  disabled:opacity-50 ${!canControlAI ? 'cursor-not-allowed' : 'cursor-pointer'} ${
                  isMonitoring ? 'bg-status-success' : 'bg-dark-border'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    isMonitoring ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {/* AI Error */}
            {aiError && (
              <div className="mb-3 text-status-error text-xs bg-status-error/10 border border-status-error/50 rounded p-2">
                <p className="font-medium">Error:</p>
                <p>{aiError}</p>
              </div>
            )}

            {/* AI Results */}
            {isMonitoring && lastResult && (
              <div className="space-y-2">
                {/* Classification */}
                <div className={`text-sm font-bold ${
                  lastResult.classification === 'theft' ? 'text-status-error' : 'text-status-success'
                }`}>
                  {lastResult.classification === 'theft' ? '🚨 THEFT DETECTED' : '✓ Normal'}
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-dark-text-muted">Confidence:</span>
                    <span className="ml-1 font-semibold text-dark-text-primary">
                      {typeof lastResult.confidence === 'number' ? (lastResult.confidence * 100).toFixed(1) : '0'}%
                    </span>
                  </div>
                  <div>
                    <span className="text-dark-text-muted">Persons:</span>
                    <span className="ml-1 font-semibold text-dark-text-primary">
                      {lastResult.frame_metadata?.num_persons ?? 0}
                    </span>
                  </div>
                  <div>
                    <span className="text-dark-text-muted">Objects:</span>
                    <span className="ml-1 font-semibold text-dark-text-primary">
                      {lastResult.frame_metadata?.num_detections ?? 0}
                    </span>
                  </div>
                  <div>
                    <span className="text-dark-text-muted">Tracks:</span>
                    <span className="ml-1 font-semibold text-dark-text-primary">
                      {Array.isArray(lastResult.tracks)
                        ? lastResult.tracks.length
                        : (lastResult.frame_metadata?.num_tracks ?? 0)}
                    </span>
                  </div>
                </div>

                {/* Performance Metrics */}
                <div className="text-xs text-dark-text-muted space-y-1 pt-2 border-t border-dark-border">
                  <div className="flex justify-between">
                    <span>Frames:</span>
                    <span className="font-semibold text-dark-text-primary">
                      {typeof stats.frames_processed === 'number' ? stats.frames_processed.toLocaleString() : '0'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Uptime:</span>
                    <span className="font-semibold text-dark-text-primary">
                      {typeof stats.elapsed_seconds === 'number' ? Math.floor(stats.elapsed_seconds) : '0'}s
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Waiting for data */}
            {isMonitoring && !lastResult && !aiError && (
              <div className="text-dark-text-muted text-xs py-2 text-center">
                <ArrowPathIcon className="h-4 w-4 animate-spin mx-auto mb-1" />
                Initializing...
              </div>
            )}

            {/* Not monitoring */}
            {!isMonitoring && !aiError && (
              <div className="text-dark-text-muted text-xs py-2 text-center">
                Toggle switch to start AI monitoring
              </div>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="mt-4 pt-4 border-t border-dark-border flex flex-col space-y-2">
          {/* View Feed Button - Always visible for ONLINE cameras */}
          {camera.status === 'ONLINE' && (
            <button
              onClick={() => onViewFeed && onViewFeed(camera)}
              className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-ai-blue text-white rounded-md hover:bg-ai-blueDark transition-colors font-semibold"
            >
              <EyeIcon className="h-4 w-4" />
              <span>View Feed</span>
            </button>
          )}

          {/* Admin Actions */}
          {showActions && (
            <div className="flex flex-col sm:flex-row gap-2">
              {onStatusChange && (
                <button
                  onClick={() => onStatusChange(camera, camera.status === 'ONLINE' ? 'OFFLINE' : 'ONLINE')}
                  className={`flex-1 flex items-center justify-center space-x-2 px-4 py-2 rounded-md transition-colors font-semibold ${
                    camera.status === 'ONLINE'
                      ? 'bg-dark-card text-status-error border border-status-error/40 hover:bg-status-error/10'
                      : 'bg-status-success text-white hover:bg-status-success/90'
                  }`}
                >
                  <PowerIcon className="h-4 w-4" />
                  <span>{camera.status === 'ONLINE' ? 'Turn Off Camera' : 'Turn On Camera'}</span>
                </button>
              )}
              {onEdit && (
                <button
                  onClick={() => onEdit(camera)}
                  className="flex-1 flex items-center justify-center space-x-2 px-4 py-2 bg-status-warning text-white rounded-md hover:bg-status-warning/90 transition-colors font-semibold"
                >
                  <PencilIcon className="h-4 w-4" />
                  <span>Edit</span>
                </button>
              )}
              {onDelete && (
                <button
                  onClick={() => onDelete(camera)}
                  className="flex-1 flex items-center justify-center space-x-2 px-4 py-2 bg-status-error text-white rounded-md hover:bg-status-error/90 transition-colors font-semibold"
                >
                  <TrashIcon className="h-4 w-4" />
                  <span>Delete</span>
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CameraCardWithAI;

