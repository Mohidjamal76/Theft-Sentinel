import { useState, useEffect } from 'react';
import { CpuChipIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { useAIEngine } from '../../hooks/useAIEngine';

/**
 * AI Model Info Component
 * Displays information about loaded AI models
 */
const AIModelInfo = () => {
  const { fetchModelInfo } = useAIEngine();
  const [modelInfo, setModelInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchInfo = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await fetchModelInfo();
      setModelInfo(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInfo();
  }, []);

  if (loading && !modelInfo) {
    return (
      <div className="glass rounded-xl border border-dark-border p-6">
        <div className="flex items-center justify-center">
          <ArrowPathIcon className="h-6 w-6 animate-spin text-ai-blue" />
          <span className="ml-2 text-dark-text-secondary">Loading model info...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass rounded-xl border border-dark-border p-6">
        <div className="text-center text-status-error">
          <p className="mb-2">{error}</p>
          <button
            onClick={fetchInfo}
            className="px-4 py-2 bg-ai-blue text-white rounded hover:bg-ai-blueDark transition font-semibold"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="glass rounded-xl border border-dark-border p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center">
          <CpuChipIcon className="h-8 w-8 text-ai-blue" />
          <h3 className="ml-3 text-xl font-bold text-dark-text-primary">AI Model Information</h3>
        </div>
        <button
          onClick={fetchInfo}
          disabled={loading}
          className="p-2 text-dark-text-muted hover:text-dark-text-primary transition"
          title="Refresh"
        >
          <ArrowPathIcon className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="space-y-4">
        {/* Detection Model */}
        <div className="border-b border-dark-border pb-3">
          <p className="text-xs font-medium text-dark-text-muted uppercase mb-1">Detection Model</p>
          <p className="text-sm font-mono text-dark-text-primary break-all">
            {modelInfo?.detection_model || 'N/A'}
          </p>
        </div>

        {/* Pose Model */}
        <div className="border-b border-dark-border pb-3">
          <p className="text-xs font-medium text-dark-text-muted uppercase mb-1">Pose Model</p>
          <p className="text-sm font-mono text-dark-text-primary break-all">
            {modelInfo?.pose_model || 'N/A'}
          </p>
        </div>

        {/* ML Classifier */}
        <div className="border-b border-dark-border pb-3">
          <p className="text-xs font-medium text-dark-text-muted uppercase mb-1">ML Classifier</p>
          <p className="text-sm font-mono text-dark-text-primary break-all">
            {modelInfo?.ml_classifier || 'N/A'}
          </p>
        </div>

        {/* Device Info */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs font-medium text-dark-text-muted uppercase mb-1">Device</p>
            <p className="text-sm font-semibold text-dark-text-primary">
              {modelInfo?.device || 'Unknown'}
            </p>
          </div>
          <div>
            <p className="text-xs font-medium text-dark-text-muted uppercase mb-1">CUDA Available</p>
            <p className={`text-sm font-semibold ${modelInfo?.cuda_available ? 'text-status-success' : 'text-status-error'}`}>
              {modelInfo?.cuda_available ? '✓ Yes' : '✗ No'}
            </p>
          </div>
        </div>

        {/* Load Status */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs font-medium text-dark-text-muted uppercase mb-1">Models Loaded</p>
            <p className={`text-sm font-semibold ${modelInfo?.models_loaded ? 'text-status-success' : 'text-status-error'}`}>
              {modelInfo?.models_loaded ? '✓ Loaded' : '✗ Not Loaded'}
            </p>
          </div>
          <div>
            <p className="text-xs font-medium text-dark-text-muted uppercase mb-1">ML Classifier</p>
            <p className={`text-sm font-semibold ${modelInfo?.ml_classifier_loaded ? 'text-status-success' : 'text-status-error'}`}>
              {modelInfo?.ml_classifier_loaded ? '✓ Loaded' : '✗ Not Loaded'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIModelInfo;

