import { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { listCameras } from '../../api/cameras';
import ContinuousMonitorCard from './ContinuousMonitorCard';

/**
 * Camera Grid AI Component
 * Grid view of cameras with continuous AI monitoring at 30 FPS
 */
const CameraGridAI = () => {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchCameras();
  }, []);

  const fetchCameras = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await listCameras({ status: 'ONLINE' });
      setCameras(response.data.results || response.data || []);
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to load cameras';
      setError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mb-4"></div>
          <p className="text-gray-600">Loading cameras...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error}</p>
          <button
            onClick={fetchCameras}
            className="px-6 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (cameras.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center text-gray-500">
          <p className="text-lg mb-2">No online cameras found</p>
          <p className="text-sm">Add cameras to start AI monitoring</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">AI Continuous Monitoring</h1>
        <p className="text-gray-600">Real-time theft detection at 30 FPS</p>
        <div className="mt-2 flex items-center gap-2 text-sm">
          <span className="inline-block w-2 h-2 bg-green-500 rounded-full"></span>
          <span className="text-gray-600">
            {cameras.length} camera{cameras.length !== 1 ? 's' : ''} available • Continuous processing at 30 FPS
          </span>
        </div>
      </div>

      {/* Camera Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {cameras.map((camera) => (
          <ContinuousMonitorCard
            key={camera.id}
            camera={camera}
          />
        ))}
      </div>
    </div>
  );
};

export default CameraGridAI;

