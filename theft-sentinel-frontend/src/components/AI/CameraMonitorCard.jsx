import PropTypes from 'prop-types';
import { PlayIcon, StopIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { useCameraMonitor } from '../../hooks/useCameraMonitor';

/**
 * Camera Monitor Card Component
 * Individual camera card for real-time AI monitoring
 */
const CameraMonitorCard = ({ camera, intervalMs = 2000 }) => {
  const {
    isMonitoring,
    currentResult,
    error,
    lastUpdate,
    start,
    stop,
    refresh,
  } = useCameraMonitor(camera.id, intervalMs);

  const getStatusColor = () => {
    if (error) return 'border-red-300 bg-red-50';
    if (!isMonitoring) return 'border-gray-300 bg-white';
    if (currentResult?.classification === 'theft') return 'border-red-500 bg-red-50';
    return 'border-green-300 bg-green-50';
  };

  const formatLastUpdate = () => {
    if (!lastUpdate) return 'Never';
    const seconds = Math.floor((new Date() - lastUpdate) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    return `${minutes}m ago`;
  };

  return (
    <div className={`rounded-lg border-2 shadow p-4 transition ${getStatusColor()}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="font-semibold text-gray-900">{camera.name}</h3>
          <p className="text-xs text-gray-500">{camera.location}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={refresh}
            disabled={isMonitoring}
            className="p-2 text-gray-600 hover:text-gray-900 transition disabled:opacity-50"
            title="Refresh"
          >
            <ArrowPathIcon className="h-4 w-4" />
          </button>
          <button
            onClick={isMonitoring ? stop : start}
            className={`px-3 py-1 rounded text-sm font-medium transition ${
              isMonitoring
                ? 'bg-red-500 text-white hover:bg-red-600'
                : 'bg-blue-500 text-white hover:bg-blue-600'
            }`}
          >
            {isMonitoring ? (
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
        <div className="mb-3 text-red-600 text-sm">
          <p className="font-medium">Error:</p>
          <p className="text-xs">{error}</p>
        </div>
      )}

      {/* Monitoring Status */}
      {isMonitoring && !currentResult && !error && (
        <div className="text-gray-500 text-sm py-4 text-center">
          <ArrowPathIcon className="h-5 w-5 animate-spin mx-auto mb-1" />
          Waiting for data...
        </div>
      )}

      {/* Results */}
      {currentResult && (
        <div className="space-y-2">
          {/* Classification */}
          <div className={`text-lg font-bold ${
            currentResult.classification === 'theft' ? 'text-red-600' : 'text-green-600'
          }`}>
            {currentResult.classification === 'theft' ? '🚨 THEFT DETECTED' : '✓ Normal'}
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-gray-600">Confidence:</span>
              <span className="ml-1 font-semibold">
                {(currentResult.confidence * 100).toFixed(1)}%
              </span>
            </div>
            <div>
              <span className="text-gray-600">Persons:</span>
              <span className="ml-1 font-semibold">
                {currentResult.persons || 0}
              </span>
            </div>
            <div>
              <span className="text-gray-600">Objects:</span>
              <span className="ml-1 font-semibold">
                {currentResult.objects || 0}
              </span>
            </div>
            <div>
              <span className="text-gray-600">Tracks:</span>
              <span className="ml-1 font-semibold">
                {currentResult.tracks || 0}
              </span>
            </div>
          </div>

          {/* Suspicious Tracks Alert */}
          {currentResult.suspicious_tracks && currentResult.suspicious_tracks.length > 0 && (
            <div className="bg-yellow-100 border border-yellow-400 rounded p-2 text-xs">
              <span className="font-semibold text-yellow-800">
                ⚠️ {currentResult.suspicious_tracks.length} suspicious track(s) detected
              </span>
            </div>
          )}

          {/* Last Update */}
          <div className="text-xs text-gray-500 pt-2 border-t">
            Last update: {formatLastUpdate()}
          </div>
        </div>
      )}

      {/* Idle State */}
      {!isMonitoring && !currentResult && !error && (
        <div className="text-gray-400 text-sm py-4 text-center">
          Click Start to begin monitoring
        </div>
      )}
    </div>
  );
};

CameraMonitorCard.propTypes = {
  camera: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    name: PropTypes.string.isRequired,
    location: PropTypes.string,
  }).isRequired,
  intervalMs: PropTypes.number,
};

export default CameraMonitorCard;

