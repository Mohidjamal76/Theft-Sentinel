import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createFeedback } from '../../api/feedback';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';
import CenteredModal from '../../components/CenteredModal';
import { useModal } from '../../hooks/useModal';
import { validateMessage } from '../../utils/validation';

const Create = () => {
  const navigate = useNavigate();
  const { modalState, showSuccess, showError, hideModal } = useModal();
  const [formData, setFormData] = useState({
    type: 'GENERAL',
    message: '',
  });
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const messageCheck = validateMessage(formData.message);
    if (!messageCheck.valid) {
      showError(messageCheck.message);
      return;
    }
    setLoading(true);

    try {
      await createFeedback({
        type: formData.type,
        message: formData.message.trim()
      });
      showSuccess('Feedback submitted successfully');
      setTimeout(() => {
        navigate('/feedback/my');
      }, 1500);
    } catch (error) {
      console.error('Error submitting feedback:', error);
      const errorMsg = error.response?.data?.detail || error.response?.data?.error || 'Failed to submit feedback';
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
          onClick={() => navigate(-1)}
          className="p-2 glass rounded-lg hover:bg-dark-card transition-colors"
        >
          <ArrowLeftIcon className="h-6 w-6 text-dark-text-primary" />
        </button>
        <div>
          <h1 className="text-4xl font-bold text-dark-text-primary">
            Submit <span className="text-gradient-ai">Feedback</span>
          </h1>
          <p className="text-dark-text-muted">Share your observations and help improve the system</p>
        </div>
      </div>

      <div className="glass rounded-xl border border-dark-border p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="type" className="block text-sm font-medium text-dark-text-primary mb-2">
              Feedback Type *
            </label>
            <select
              id="type"
              name="type"
              value={formData.type}
              onChange={handleChange}
              className="w-full px-4 py-3 bg-dark-card border border-dark-border rounded-lg text-dark-text-primary focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent transition-all duration-200"
            >
              <option value="GENERAL">General Feedback</option>
              <option value="INCIDENT">Incident Related</option>
              <option value="FALSE_POSITIVE">False Positive Alert</option>
              <option value="TRUE_POSITIVE">True Positive Alert</option>
            </select>
          </div>

          <div>
            <label htmlFor="message" className="block text-sm font-medium text-dark-text-primary mb-2">
              Message *
            </label>
            <textarea
              id="message"
              name="message"
              required
              rows="8"
              value={formData.message}
              onChange={handleChange}
              className="w-full px-4 py-3 bg-dark-card border border-dark-border rounded-lg text-dark-text-primary placeholder-dark-text-muted focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent transition-all duration-200 resize-none"
              placeholder="Please provide detailed feedback about the incident, alert, or system behavior..."
            ></textarea>
          </div>

          <div className="flex justify-end space-x-4 pt-4">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="px-6 py-2 glass border border-dark-border rounded-lg text-dark-text-primary hover:bg-dark-card transition-all duration-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2 bg-ai-blue text-dark-bg rounded-lg hover:bg-cyan-400 transition-all duration-200 disabled:opacity-50 font-semibold shadow-glow-ai hover:shadow-glow-ai-lg"
            >
              {loading ? 'Submitting...' : 'Submit Feedback'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Create;

