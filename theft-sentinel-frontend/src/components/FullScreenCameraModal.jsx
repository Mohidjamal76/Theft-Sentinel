import { XMarkIcon } from '@heroicons/react/24/outline';
import CameraFeedWithOverlay from './CameraFeedWithOverlay';

/**
 * FullScreenCameraModal
 * Opens the camera feed in a full-screen overlay.
 * The canvas bounding-box overlay is always enabled here: if an AI monitor is
 * running for this camera the SSE stream delivers tracking data automatically;
 * if no monitor is running nothing is drawn and there is no visible change.
 */
const FullScreenCameraModal = ({ show, camera, onClose }) => {
  if (!show || !camera) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black flex items-center justify-center">
      {/* Close Button */}
      <button
        onClick={onClose}
        className="absolute top-4 right-4 z-[60] bg-white bg-opacity-20 hover:bg-opacity-30 text-white p-3 rounded-full transition-all"
        aria-label="Close"
      >
        <XMarkIcon className="h-8 w-8" />
      </button>

      {/* Camera Info Header */}
      <div className="absolute top-4 left-4 right-20 sm:right-auto z-[60] bg-black bg-opacity-70 text-white px-4 py-2 rounded-lg min-w-0">
        <h2 className="text-lg sm:text-xl font-bold truncate">{camera.name}</h2>
        <p className="text-sm text-gray-300">{camera.location}</p>
      </div>

      {/* Full Screen Feed — canvas overlay always active in full-screen mode */}
      <div className="w-full h-full flex items-center justify-center">
        <CameraFeedWithOverlay
          cameraId={camera.id}
          width="100%"
          height="100%"
          className="w-full h-full"
          enableOverlay={true}
          viewMode="full"
        />
      </div>
    </div>
  );
};

export default FullScreenCameraModal;

