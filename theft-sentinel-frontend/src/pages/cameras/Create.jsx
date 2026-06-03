import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createCamera } from '../../api/cameras';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';
import CenteredModal from '../../components/CenteredModal';
import { useModal } from '../../hooks/useModal';
import {
  firstInvalid,
  scrollToFirstInvalid,
  trimInput,
  validateCameraLocation,
  validateCameraName,
  validateStreamUrl,
} from '../../utils/validation';

const Create = () => {
  const navigate = useNavigate();
  const { modalState, showSuccess, showError, hideModal } = useModal();
  const [formData, setFormData] = useState({
    name: '',
    rtsp_url: '',
    location: '',
    zone: '',
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    if (errors[e.target.name]) setErrors((prev) => ({ ...prev, [e.target.name]: '' }));
  };

  const validateForm = () => {
    const checks = [
      ['name', validateCameraName(formData.name)],
      ['location', validateCameraLocation(formData.location)],
      ['rtsp_url', validateStreamUrl(formData.rtsp_url)],
    ];
    const nextErrors = {};
    checks.forEach(([field, check]) => {
      if (!check.valid) nextErrors[field] = check.message;
    });
    setErrors(nextErrors);
    return firstInvalid(checks.map(([, check]) => check)).valid;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) {
      showError('Please fix the validation errors before submitting');
      scrollToFirstInvalid();
      return;
    }
    setLoading(true);

    try {
      console.log('📤 [CreateCamera] Sending camera data:', formData);
      const payload = Object.fromEntries(
        Object.entries(formData).map(([key, value]) => [key, trimInput(value)])
      );
      const response = await createCamera(payload);
      console.log('✅ [CreateCamera] Camera created successfully:', response.data);
      showSuccess('Camera created successfully');
      setTimeout(() => {
        navigate('/cameras/control-room');
      }, 1500);
    } catch (error) {
      console.error('❌ [CreateCamera] Error creating camera:', error);
      console.error('❌ [CreateCamera] Error response:', error.response?.data);
      console.error('❌ [CreateCamera] Error status:', error.response?.status);

      // Handle validation errors
      const errorData = error.response?.data;
      let errorMsg = 'Failed to create camera';

      if (errorData) {
        if (errorData.name) {
          errorMsg = `Name: ${errorData.name[0]}`;
        } else if (errorData.rtsp_url) {
          errorMsg = `RTSP URL: ${errorData.rtsp_url[0]}`;
        } else if (errorData.location) {
          errorMsg = `Location: ${errorData.location[0]}`;
        } else if (errorData.zone) {
          errorMsg = `Zone: ${errorData.zone[0]}`;
        } else if (errorData.status) {
          errorMsg = `Status: ${errorData.status[0]}`;
        } else if (errorData.detail) {
          errorMsg = errorData.detail;
        } else {
          errorMsg = JSON.stringify(errorData);
        }
      }

      showError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <CenteredModal
        show={modalState.show}
        type={modalState.type}
        message={modalState.message}
        onClose={hideModal}
      />

      <div className="flex items-center space-x-4">
        <button
          onClick={() => navigate('/cameras/control-room')}
          className="p-2 hover:bg-dark-card rounded-full transition-colors"
        >
          <ArrowLeftIcon className="h-6 w-6 text-dark-text-secondary" />
        </button>
        <h1 className="text-3xl font-bold text-white">Add Camera</h1>
      </div>

      <div className="glass rounded-xl border border-dark-border p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-dark-text-secondary">
                Camera Name *
              </label>
              <input
                type="text"
                id="name"
                name="name"
                required
                value={formData.name}
                onChange={handleChange}
                aria-invalid={!!errors.name}
                className={`mt-1 block w-full px-3 py-2 bg-dark-card border rounded-md text-dark-text-primary placeholder-dark-text-muted focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent ${errors.name ? 'border-status-error' : 'border-dark-border'}`}
                placeholder="e.g., Main Entrance Camera"
              />
              {errors.name && <p className="mt-1 text-sm text-status-error">{errors.name}</p>}
            </div>

            <div>
              <label htmlFor="location" className="block text-sm font-medium text-dark-text-secondary">
                Location *
              </label>
              <input
                type="text"
                id="location"
                name="location"
                required
                value={formData.location}
                onChange={handleChange}
                aria-invalid={!!errors.location}
                className={`mt-1 block w-full px-3 py-2 bg-dark-card border rounded-md text-dark-text-primary placeholder-dark-text-muted focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent ${errors.location ? 'border-status-error' : 'border-dark-border'}`}
                placeholder="e.g., Building A - Floor 1"
              />
              {errors.location && <p className="mt-1 text-sm text-status-error">{errors.location}</p>}
            </div>

            <div>
              <label htmlFor="rtsp_url" className="block text-sm font-medium text-dark-text-secondary">
                RTSP URL *
              </label>
              <input
                type="text"
                id="rtsp_url"
                name="rtsp_url"
                required
                value={formData.rtsp_url}
                onChange={handleChange}
                aria-invalid={!!errors.rtsp_url}
                className={`mt-1 block w-full px-3 py-2 bg-dark-card border rounded-md text-dark-text-primary placeholder-dark-text-muted focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent ${errors.rtsp_url ? 'border-status-error' : 'border-dark-border'}`}
                placeholder="rtsp://192.168.1.100:554/stream"
              />
              {errors.rtsp_url && <p className="mt-1 text-sm text-status-error">{errors.rtsp_url}</p>}
            </div>

            <div>
              <label htmlFor="zone" className="block text-sm font-medium text-dark-text-secondary">
                Zone
              </label>
              <input
                type="text"
                id="zone"
                name="zone"
                value={formData.zone}
                onChange={handleChange}
                className="mt-1 block w-full px-3 py-2 bg-dark-card border border-dark-border rounded-md text-dark-text-primary placeholder-dark-text-muted focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent"
                placeholder="e.g., Zone A, Parking, etc."
              />
            </div>

          </div>

          <div className="flex justify-end space-x-4">
            <button
              type="button"
              onClick={() => navigate('/cameras/control-room')}
              className="px-6 py-2 border border-dark-border rounded-md text-dark-text-secondary hover:bg-dark-card transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2 bg-ai-blue text-white rounded-md hover:bg-ai-blueDark transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
            >
              {loading ? 'Creating...' : 'Create Camera'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Create;

