import { useState, useEffect, useCallback } from 'react';
import { deleteCamera, listCameras, updateCameraStatus } from '../../api/cameras';
import { useRecoilValue } from 'recoil';
import { isAuthenticatedState, authUserState } from '../../store/authStore';
import { useNavigate } from 'react-router-dom';
import CameraCardWithAI from '../../components/CameraCardWithAI';
import FullScreenCameraModal from '../../components/FullScreenCameraModal';
import LiveTrackingNodeGraph from '../../components/LiveTrackingNodeGraph';
import { VideoCameraIcon, ArrowPathIcon, PlusIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import ConfirmationModal from '../../components/ConfirmationModal';

/**
 * Guard Control Room - Read-only camera feed viewer
 * Guards can view live camera feeds but cannot add/edit/delete cameras
 */
const ControlRoom = () => {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showLiveFeeds, setShowLiveFeeds] = useState(true);
  const [filters, setFilters] = useState({
    search: '',
    status: '',
    zone: '',
  });
  const [fullScreenCamera, setFullScreenCamera] = useState(null);
  const [deleteConfirmation, setDeleteConfirmation] = useState({ show: false, camera: null });
  const [deleting, setDeleting] = useState(false);
  const isAuthenticated = useRecoilValue(isAuthenticatedState);
  const currentUser = useRecoilValue(authUserState);
  const navigate = useNavigate();
  const isAdmin = currentUser?.role === 'ADMIN';

  // Memoize fetch function to prevent unnecessary re-renders
  const fetchCameras = useCallback(async () => {
    if (!isAuthenticated) return;

    setLoading(true);
    try {
      const response = await listCameras({
        search: filters.search,
        status: filters.status,
        zone: filters.zone,
      });
      setCameras(response.data.results || response.data);
    } catch (error) {
      // Handle 401 gracefully
      if (error.response?.status === 401) {
        console.log('Unauthorized - redirecting to login');
        return;
      }
      console.error('Error fetching cameras:', error);
      toast.error('Failed to load cameras');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, filters.search, filters.status, filters.zone]);

  useEffect(() => {
    fetchCameras();
  }, [fetchCameras]);

  // Auto-refresh camera list every 30 seconds
  useEffect(() => {
    if (!isAuthenticated) return;

    const interval = setInterval(() => {
      fetchCameras();
    }, 30000); // 30 seconds

    return () => clearInterval(interval);
  }, [fetchCameras, isAuthenticated]);

  const handleViewFeed = (camera) => {
    setFullScreenCamera(camera);
  };

  const handleCloseFullScreen = () => {
    setFullScreenCamera(null);
  };

  const handleEdit = (camera) => {
    navigate(`/cameras/edit/${camera.id}`);
  };

  const handleDelete = (camera) => {
    setDeleteConfirmation({ show: true, camera });
  };

  const handleDeleteConfirm = async () => {
    const camera = deleteConfirmation.camera;
    if (!camera) return;

    setDeleting(true);
    try {
      await deleteCamera(camera.id);
      toast.success('Camera deleted successfully');
      setDeleteConfirmation({ show: false, camera: null });
      await fetchCameras();
    } catch (error) {
      const errorMsg =
        error.response?.data?.error ||
        error.response?.data?.detail ||
        'Failed to delete camera';
      toast.error(errorMsg);
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    if (deleting) return;
    setDeleteConfirmation({ show: false, camera: null });
  };

  const handleStatusChange = async (camera, status) => {
    try {
      const response = await updateCameraStatus(camera.id, status);
      toast.success(
        response.data?.message ||
          (status === 'ONLINE' ? 'Camera turned on successfully' : 'Camera turned off successfully')
      );
      fetchCameras();
    } catch (error) {
      const errorMsg = error.response?.data?.error || 'Failed to update camera status';
      toast.error(errorMsg);
      fetchCameras();
    }
  };

  // Filter cameras
  const filteredCameras = cameras.filter((camera) => {
    const matchesSearch = !filters.search ||
      camera.name.toLowerCase().includes(filters.search.toLowerCase()) ||
      camera.location.toLowerCase().includes(filters.search.toLowerCase());
    const matchesStatus = !filters.status || camera.status === filters.status;
    const matchesZone = !filters.zone || camera.zone === filters.zone;
    return matchesSearch && matchesStatus && matchesZone;
  });

  // Get unique zones for filter
  const zones = [...new Set(cameras.map(c => c.zone).filter(Boolean))];

  if (loading && cameras.length === 0) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-96 skeleton rounded-xl"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 px-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-4xl font-bold text-dark-text-primary mb-2">
            Control <span className="text-gradient-ai">Room</span>
          </h1>
          <p className="text-dark-text-muted">Live camera feeds and monitoring</p>
        </div>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full sm:w-auto">
          {/* Add Camera (Admin only) */}
          {isAdmin && (
            <button
              onClick={() => navigate('/cameras/create')}
              className="flex items-center gap-2 px-4 py-2 rounded-lg font-semibold bg-ai-blue/20 text-ai-blue border border-ai-blue/50 hover:bg-ai-blue/30 transition-all duration-200"
            >
              <PlusIcon className="h-5 w-5" />
              <span className="hidden sm:inline">Add Camera</span>
            </button>
          )}
          {/* Live Feeds Toggle */}
          <button
            onClick={() => setShowLiveFeeds(!showLiveFeeds)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold transition-all duration-300 ${showLiveFeeds
                ? 'bg-status-success/20 text-status-success border border-status-success/50 shadow-glow-success'
                : 'glass border border-dark-border text-dark-text-muted hover:bg-dark-card'
              }`}
          >
            <div className={`w-2 h-2 rounded-full ${showLiveFeeds ? 'bg-status-success animate-pulse' : 'bg-gray-500'}`} />
            <span>Live Feeds {showLiveFeeds ? 'ON' : 'OFF'}</span>
          </button>
          {/* Refresh Button */}
          <button
            onClick={fetchCameras}
            className="glass px-4 py-2 rounded-lg border border-dark-border text-dark-text-primary hover:bg-dark-card hover:border-ai-blue/50 transition-all duration-200 flex items-center gap-2"
          >
            <ArrowPathIcon className="h-5 w-5" />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="glass p-4 rounded-xl border border-dark-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-dark-text-muted mb-1">Total Cameras</p>
              <p className="text-2xl font-bold text-dark-text-primary">{cameras.length}</p>
            </div>
            <VideoCameraIcon className="h-8 w-8 text-ai-blue opacity-50" />
          </div>
        </div>
        <div className="glass p-4 rounded-xl border border-dark-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-dark-text-muted mb-1">Online</p>
              <p className="text-2xl font-bold text-status-success">
                {cameras.filter(c => c.status === 'ONLINE').length}
              </p>
            </div>
            <div className="w-3 h-3 bg-status-success rounded-full animate-pulse" />
          </div>
        </div>
        <div className="glass p-4 rounded-xl border border-dark-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-dark-text-muted mb-1">Offline</p>
              <p className="text-2xl font-bold text-status-error">
                {cameras.filter(c => c.status === 'OFFLINE').length}
              </p>
            </div>
            <div className="w-3 h-3 bg-status-error rounded-full" />
          </div>
        </div>
        <div className="glass p-4 rounded-xl border border-dark-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-dark-text-muted mb-1">Zones</p>
              <p className="text-2xl font-bold text-dark-text-primary">{zones.length}</p>
            </div>
            <div className="w-3 h-3 bg-ai-blue rounded-full" />
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="glass p-4 rounded-xl border border-dark-border">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <input
            type="text"
            placeholder="Search cameras..."
            value={filters.search}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            className="px-4 py-2 bg-dark-card border border-dark-border rounded-lg text-dark-text-primary placeholder-dark-text-muted focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent transition-all duration-200"
          />
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            className="px-4 py-2 bg-dark-card border border-dark-border rounded-lg text-dark-text-primary focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent transition-all duration-200"
          >
            <option value="">All Status</option>
            <option value="ONLINE">Online</option>
            <option value="OFFLINE">Offline</option>
          </select>
          <select
            value={filters.zone}
            onChange={(e) => setFilters({ ...filters, zone: e.target.value })}
            className="px-4 py-2 bg-dark-card border border-dark-border rounded-lg text-dark-text-primary focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent transition-all duration-200"
          >
            <option value="">All Zones</option>
            {zones.map((zone) => (
              <option key={zone} value={zone}>
                {zone}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Cameras Grid */}
      {filteredCameras.length === 0 ? (
        <div className="glass p-12 rounded-xl border border-dark-border text-center">
          <VideoCameraIcon className="h-16 w-16 text-dark-text-muted mx-auto mb-4 opacity-50" />
          <h3 className="text-xl font-semibold text-dark-text-primary mb-2">No Cameras Found</h3>
          <p className="text-dark-text-muted">Try adjusting your filters or check back later.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {filteredCameras.map((camera) => (
            <CameraCardWithAI
              key={camera.id}
              camera={camera}
              onViewFeed={handleViewFeed}
              onEdit={isAdmin ? handleEdit : undefined}
              onDelete={isAdmin ? handleDelete : undefined}
              onStatusChange={isAdmin ? handleStatusChange : undefined}
              showFeed={showLiveFeeds}
              showActions={isAdmin} // Only admins can edit/delete
            />
          ))}
        </div>
      )}

      {/* Live Tracking Node Graph Footer */}
      <LiveTrackingNodeGraph />

      {/* Full Screen Camera Modal */}
      <FullScreenCameraModal
        show={fullScreenCamera !== null}
        camera={fullScreenCamera}
        onClose={handleCloseFullScreen}
      />

      <ConfirmationModal
        show={deleteConfirmation.show}
        title="Delete Camera"
        message={`Delete "${deleteConfirmation.camera?.name || 'this camera'}"? Active monitoring and live stream runtime state will be stopped first.`}
        onConfirm={handleDeleteConfirm}
        onCancel={handleDeleteCancel}
        confirmText={deleting ? 'Deleting...' : 'Delete'}
        cancelText="Cancel"
        type="danger"
      />
    </div>
  );
};

export default ControlRoom;

