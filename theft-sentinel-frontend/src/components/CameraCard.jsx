import { VideoCameraIcon, PencilIcon, TrashIcon, EyeIcon } from '@heroicons/react/24/outline';
import CameraFeed from './CameraFeed';

const CameraCard = ({ camera, onViewFeed, onEdit, onDelete, showFeed = false, showActions = false }) => {
  // CORRECTED: Status values are now ONLINE/OFFLINE
  const statusColors = {
    ONLINE: 'bg-green-100 text-green-800 border-green-300',
    OFFLINE: 'bg-red-100 text-red-800 border-red-300',
  };

  const statusColor = statusColors[camera.status] || 'bg-gray-100 text-gray-800 border-gray-300';

  return (
    <div
      className={`bg-white rounded-lg shadow-md overflow-hidden border-l-4 ${
        camera.status === 'ONLINE' ? 'border-green-500' : 'border-red-500'
      } hover:shadow-lg transition-shadow`}
    >
      {/* Live Feed Preview */}
      {showFeed && camera.status === 'ONLINE' && (
        <div 
          onClick={() => onViewFeed && onViewFeed(camera)}
          className="cursor-pointer"
        >
          <CameraFeed cameraId={camera.id} height="200px" />
        </div>
      )}
      
      <div className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className="bg-secondary p-3 rounded-lg">
              <VideoCameraIcon className="h-8 w-8 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">{camera.name}</h3>
              <p className="text-sm text-gray-600">{camera.location}</p>
            </div>
          </div>
          <span
            className={`px-3 py-1 rounded-full text-xs font-semibold border ${statusColor}`}
          >
            {camera.status}
          </span>
        </div>
      
        <div className="mt-4 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Zone:</span>
            <span className="font-medium text-gray-900">{camera.zone || 'N/A'}</span>
          </div>
          {camera.rtsp_url && (
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Stream:</span>
              <span className="font-mono text-xs text-gray-900 truncate max-w-[200px]">
                {camera.rtsp_url}
              </span>
            </div>
          )}
          {camera.created_at && (
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Added:</span>
              <span className="font-medium text-gray-900">
                {new Date(camera.created_at).toLocaleDateString()}
              </span>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="mt-4 pt-4 border-t border-gray-200 flex flex-col space-y-2">
          {/* View Feed Button - Always visible for ONLINE cameras */}
          {camera.status === 'ONLINE' && (
            <button
              onClick={() => onViewFeed && onViewFeed(camera)}
              className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors"
            >
              <EyeIcon className="h-4 w-4" />
              <span>View Feed</span>
            </button>
          )}

          {/* Admin Actions */}
          {showActions && (
            <div className="flex space-x-2">
              {onEdit && (
                <button
                  onClick={() => onEdit(camera)}
                  className="flex-1 flex items-center justify-center space-x-2 px-4 py-2 bg-yellow-500 text-white rounded-md hover:bg-yellow-600 transition-colors"
                >
                  <PencilIcon className="h-4 w-4" />
                  <span>Edit</span>
                </button>
              )}
              {onDelete && (
                <button
                  onClick={() => onDelete(camera)}
                  className="flex-1 flex items-center justify-center space-x-2 px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 transition-colors"
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

export default CameraCard;

