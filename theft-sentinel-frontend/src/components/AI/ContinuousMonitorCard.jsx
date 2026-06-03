import PropTypes from 'prop-types';
import { PlayIcon, StopIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { useContinuousMonitor } from '../../hooks/useContinuousMonitor';
import CameraFeedWithOverlay from '../CameraFeedWithOverlay';

/**
 * Continuous Monitor Card Component
 * Real-time camera monitoring with 30 FPS continuous processing
 */
const ContinuousMonitorCard = ({ camera }) => {
  const {
    isMonitoring,
    stats,
    loading,
    error,
    start,
    stop,
  } = useContinuousMonitor(camera.id);

  const lastResult = stats?.last_result;

  const getStatusColor = () => {
    if (error) return 'border-red-300 bg-red-50';
    if (!isMonitoring) return 'border-gray-300 bg-white';
    if (lastResult?.classification === 'theft') return 'border-red-500 bg-red-50';
    return 'border-green-300 bg-green-50';
  };

  return (
    <div className={`rounded-lg border-2 shadow transition overflow-hidden ${getStatusColor()}`}>

      {/* ── Camera feed with canvas bounding-box overlay ─────────────────── */}
      <CameraFeedWithOverlay
        cameraId={camera.id}
        width="100%"
        enableOverlay={isMonitoring}
        className="rounded-t-lg"
        viewMode="grid"
      />

      {/* ── Stats & controls ──────────────────────────────────────────────── */}
      <div className="p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="font-semibold text-gray-900">{camera.name}</h3>
          <p className="text-xs text-gray-500">{camera.location}</p>
        </div>
        <div className="flex items-center gap-2">
          {isMonitoring && stats && typeof stats.fps === 'number' && (
            <div className="flex items-center gap-1 text-xs">
              <span className="inline-block w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
              <span className="font-semibold text-green-600">
                {stats.fps.toFixed(1)} FPS
              </span>
            </div>
          )}
          <button
            onClick={isMonitoring ? stop : start}
            disabled={loading}
            className={`px-3 py-1 rounded text-sm font-medium transition disabled:opacity-50 ${
              isMonitoring
                ? 'bg-red-500 text-white hover:bg-red-600'
                : 'bg-blue-500 text-white hover:bg-blue-600'
            }`}
          >
            {loading ? (
              <ArrowPathIcon className="h-4 w-4 animate-spin" />
            ) : isMonitoring ? (
              <span className="flex items-center">
                <StopIcon className="h-4 w-4 mr-1" />
                Stop
              </span>
            ) : (
              <span className="flex items-center">
                <PlayIcon className="h-4 w-4 mr-1" />
                Start
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="mb-3 text-red-600 text-sm bg-red-100 border border-red-300 rounded p-2">
          <p className="font-medium">Error:</p>
          <p className="text-xs">{error}</p>
        </div>
      )}

      {/* Monitoring Status */}
      {isMonitoring && !lastResult && !error && (
        <div className="text-gray-500 text-sm py-4 text-center">
          <ArrowPathIcon className="h-5 w-5 animate-spin mx-auto mb-1" />
          Initializing continuous monitoring...
        </div>
      )}

      {/* Results */}
      {isMonitoring && lastResult && (
        <div className="space-y-3">
          {/* Classification */}
          <div className={`text-lg font-bold ${
            lastResult.classification === 'theft' ? 'text-red-600' : 'text-green-600'
          }`}>
            {lastResult.classification === 'theft' ? '🚨 THEFT DETECTED' : '✓ Normal'}
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-gray-600">Confidence:</span>
              <span className="ml-1 font-semibold">
                {typeof lastResult.confidence === 'number' ? (lastResult.confidence * 100).toFixed(1) : '0'}%
              </span>
            </div>
            <div>
              <span className="text-gray-600">Persons:</span>
              <span className="ml-1 font-semibold">
                {lastResult.frame_metadata?.num_persons ?? 0}
              </span>
            </div>
            <div>
              <span className="text-gray-600">Detections:</span>
              <span className="ml-1 font-semibold">
                {lastResult.frame_metadata?.num_detections ?? 0}
              </span>
            </div>
            <div>
              <span className="text-gray-600">Tracks:</span>
              <span className="ml-1 font-semibold">
                {Array.isArray(lastResult.tracks)
                  ? lastResult.tracks.length
                  : (lastResult.frame_metadata?.num_tracks ?? 0)}
              </span>
            </div>
          </div>

          {/* Suspicious Tracks Alert */}
          {Array.isArray(lastResult.suspicious_tracks) && lastResult.suspicious_tracks.length > 0 && (
            <div className="bg-yellow-100 border border-yellow-400 rounded p-2 text-xs">
              <span className="font-semibold text-yellow-800">
                ⚠️ {lastResult.suspicious_tracks.length} suspicious track(s) detected
              </span>
            </div>
          )}

          {/* Performance Metrics */}
          <div className="text-xs text-gray-600 space-y-1 pt-2 border-t">
            <div className="flex items-center justify-between">
              <span>Frames Processed:</span>
              <span className="font-semibold">
                {typeof stats.frames_processed === 'number' ? stats.frames_processed.toLocaleString() : '0'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span>Processing Time:</span>
              <span className="font-semibold">
                {typeof lastResult.processing_time_ms === 'number' ? lastResult.processing_time_ms.toFixed(0) : '0'}ms
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span>Uptime:</span>
              <span className="font-semibold">
                {typeof stats.elapsed_seconds === 'number' ? Math.floor(stats.elapsed_seconds) : '0'}s
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span>Last Update:</span>
              <span className="font-semibold">
                {lastResult.timestamp ? new Date(lastResult.timestamp).toLocaleTimeString() : '--:--:--'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Idle State */}
      {!isMonitoring && !error && (
        <div className="text-gray-400 text-sm py-4 text-center">
          <p>Click Start to begin continuous monitoring</p>
          <p className="text-xs mt-1">Processing at 30 FPS · canvas overlay enabled</p>
        </div>
      )}
      </div>{/* end stats & controls */}
    </div>
  );
};

ContinuousMonitorCard.propTypes = {
  camera: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    name: PropTypes.string.isRequired,
    location: PropTypes.string,
  }).isRequired,
};

export default ContinuousMonitorCard;

