import { useEffect } from 'react';
import { CheckCircleIcon, XCircleIcon, ExclamationTriangleIcon, InformationCircleIcon, XMarkIcon } from '@heroicons/react/24/outline';

const CenteredModal = ({ show, type = 'info', message, onClose, autoClose = true, duration = 3000 }) => {
  useEffect(() => {
    if (show && autoClose) {
      const timer = setTimeout(() => {
        onClose();
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [show, autoClose, duration, onClose]);

  if (!show) return null;

  const icons = {
    success: <CheckCircleIcon className="h-16 w-16 text-green-500" />,
    error: <XCircleIcon className="h-16 w-16 text-red-500" />,
    warning: <ExclamationTriangleIcon className="h-16 w-16 text-yellow-500" />,
    info: <InformationCircleIcon className="h-16 w-16 text-blue-500" />,
  };

  const colors = {
    success: 'border-green-500',
    error: 'border-red-500',
    warning: 'border-yellow-500',
    info: 'border-blue-500',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 px-4 py-6 overflow-y-auto">
      <div className={`bg-white rounded-lg shadow-2xl max-w-md w-full max-h-[90vh] overflow-y-auto border-t-4 ${colors[type]} animate-fadeIn`}>
        <div className="p-6">
          <div className="flex justify-end mb-2">
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              aria-label="Close"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>
          <div className="flex flex-col items-center text-center">
            <div className="mb-4">
              {icons[type]}
            </div>
            <p className="text-lg font-semibold text-gray-800 mb-2">
              {type === 'success' && 'Success!'}
              {type === 'error' && 'Error!'}
              {type === 'warning' && 'Warning!'}
              {type === 'info' && 'Information'}
            </p>
            <p className="text-gray-600 text-sm">
              {message}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CenteredModal;

