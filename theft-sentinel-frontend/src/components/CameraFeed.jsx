import PropTypes from 'prop-types';

const CameraFeed = ({ cameraId, width = 'auto', height = 'auto', className = '' }) => {
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  return (
    <div className={`relative ${className}`}>
      <img
        src={`${API_BASE_URL}/api/cameras/${cameraId}/feed/`}
        alt="Live Camera Feed"
        style={{ width, height }}
        className="rounded-lg shadow-md"
        onError={(e) => {
          e.target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="300"%3E%3Crect fill="%23ddd" width="400" height="300"/%3E%3Ctext fill="%23999" x="50%25" y="50%25" text-anchor="middle" dy=".3em"%3ECamera Feed Unavailable%3C/text%3E%3C/svg%3E';
          e.target.onerror = null; // Prevent infinite loop
        }}
      />
      <div className="absolute top-2 right-2 bg-red-600 text-white px-2 py-1 rounded text-xs font-semibold flex items-center space-x-1">
        <span className="w-2 h-2 bg-white rounded-full animate-pulse"></span>
        <span>LIVE</span>
      </div>
    </div>
  );
};

CameraFeed.propTypes = {
  cameraId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  width: PropTypes.string,
  height: PropTypes.string,
  className: PropTypes.string,
};

export default CameraFeed;

