import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useRecoilValue } from 'recoil';
import { isAuthenticatedState } from '../../store/authStore';
import { getMyFeedback } from '../../api/feedback';
import { PlusIcon, ChatBubbleLeftRightIcon, ClockIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';

const MyFeedback = () => {
  const navigate = useNavigate();
  const isAuthenticated = useRecoilValue(isAuthenticatedState);
  const [feedbacks, setFeedbacks] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchFeedbacks = useCallback(async () => {
    if (!isAuthenticated) return;
    
    setLoading(true);
    try {
      const response = await getMyFeedback();
      setFeedbacks(response.data.results || response.data || []);
    } catch (error) {
      if (error.response?.status === 401) {
        console.log('Unauthorized - redirecting to login');
        return;
      }
      console.error('Error fetching feedback:', error);
      toast.error('Failed to load feedback');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    fetchFeedbacks();
  }, [fetchFeedbacks]);

  const getTypeColor = (type) => {
    switch (type) {
      case 'FALSE_POSITIVE':
        return 'bg-status-warning/20 text-status-warning border-status-warning/50';
      case 'TRUE_POSITIVE':
        return 'bg-status-success/20 text-status-success border-status-success/50';
      case 'INCIDENT':
        return 'bg-status-error/20 text-status-error border-status-error/50';
      default:
        return 'bg-ai-blue/20 text-ai-blue border-ai-blue/50';
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-32 skeleton rounded-xl"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-4xl font-bold text-dark-text-primary mb-2">
            My <span className="text-gradient-ai">Feedback</span>
          </h1>
          <p className="text-dark-text-muted">View and manage your submitted feedback</p>
        </div>
        <button
          onClick={() => navigate('/feedback/create')}
          className="flex items-center gap-2 px-6 py-3 bg-ai-blue text-dark-bg rounded-lg hover:bg-cyan-400 transition-all duration-300 font-semibold shadow-glow-ai hover:shadow-glow-ai-lg"
        >
          <PlusIcon className="h-5 w-5" />
          <span>Submit Feedback</span>
        </button>
      </div>

      {feedbacks.length === 0 ? (
        <div className="glass rounded-xl border border-dark-border p-12 text-center">
          <ChatBubbleLeftRightIcon className="h-16 w-16 text-dark-text-muted mx-auto mb-4 opacity-50" />
          <h2 className="text-xl font-semibold text-dark-text-primary mb-2">No Feedback Submitted</h2>
          <p className="text-dark-text-muted mb-6">
            Help us improve the system by sharing your thoughts, suggestions, or reporting any issues you encounter.
          </p>
          <button
            onClick={() => navigate('/feedback/create')}
            className="inline-flex items-center gap-2 px-6 py-3 bg-ai-blue text-dark-bg rounded-lg hover:bg-cyan-400 transition-all duration-300 font-semibold shadow-glow-ai hover:shadow-glow-ai-lg"
          >
            <PlusIcon className="h-5 w-5" />
            <span>Submit Your First Feedback</span>
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {feedbacks.map((feedback) => (
            <div key={feedback.id} className="glass rounded-xl border border-dark-border p-6 hover:border-ai-blue/50 transition-all duration-300">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className={`px-3 py-1 rounded-lg text-xs font-semibold border ${getTypeColor(feedback.type)}`}>
                    {feedback.type?.replace('_', ' ') || 'GENERAL'}
                  </div>
                  <div className="flex items-center gap-2 text-sm text-dark-text-muted">
                    <ClockIcon className="h-4 w-4" />
                    <span>{new Date(feedback.created_at).toLocaleString()}</span>
                  </div>
                </div>
              </div>
              <p className="text-dark-text-primary leading-relaxed whitespace-pre-wrap">
                {feedback.message}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default MyFeedback;

