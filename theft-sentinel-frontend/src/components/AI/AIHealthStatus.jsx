import { useState, useEffect } from 'react';
import { CheckCircleIcon, ExclamationTriangleIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { useAIEngine } from '../../hooks/useAIEngine';

/**
 * AI Health Status Component
 * Displays the current health status of the AI service
 */
const AIHealthStatus = () => {
  const { checkHealth } = useAIEngine();
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await checkHealth();
      setHealth(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchHealth, 30000);
    
    return () => clearInterval(interval);
  }, []);

  if (loading && !health) {
    return (
      <div className="glass rounded-xl border border-dark-border p-6">
        <div className="flex items-center justify-center">
          <ArrowPathIcon className="h-6 w-6 animate-spin text-ai-blue" />
          <span className="ml-2 text-dark-text-secondary">Checking AI service...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass rounded-xl border border-dark-border p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <ExclamationTriangleIcon className="h-8 w-8 text-status-error" />
            <div className="ml-3">
              <h3 className="text-lg font-semibold text-dark-text-primary">AI Service Unavailable</h3>
              <p className="text-sm text-status-error">{error}</p>
            </div>
          </div>
          <button
            onClick={fetchHealth}
            className="px-4 py-2 bg-ai-blue text-white rounded hover:bg-ai-blueDark transition font-semibold"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const isHealthy = health?.status === 'healthy';
  const statusColor = isHealthy ? 'text-status-success' : 'text-status-warning';
  const bgColor = isHealthy ? 'bg-status-success/10' : 'bg-status-warning/10';
  const borderColor = isHealthy ? 'border-status-success/50' : 'border-status-warning/50';

  return (
    <div className={`glass rounded-xl border p-6 ${borderColor}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center">
          {isHealthy ? (
            <CheckCircleIcon className="h-8 w-8 text-status-success" />
          ) : (
            <ExclamationTriangleIcon className="h-8 w-8 text-status-warning" />
          )}
          <h3 className="ml-3 text-xl font-bold text-dark-text-primary">AI Service Status</h3>
        </div>
        <button
          onClick={fetchHealth}
          disabled={loading}
          className="p-2 text-dark-text-muted hover:text-dark-text-primary transition"
          title="Refresh"
        >
          <ArrowPathIcon className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-dark-text-secondary">Status:</span>
          <span className={`text-sm font-bold ${statusColor} uppercase`}>
            {health?.status}
          </span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-dark-text-secondary">Models Loaded:</span>
          <span className={`text-sm font-semibold ${health?.models_loaded ? 'text-status-success' : 'text-status-error'}`}>
            {health?.models_loaded ? '✓ Yes' : '✗ No'}
          </span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-dark-text-secondary">Device:</span>
          <span className="text-sm font-mono bg-dark-card border border-dark-border px-2 py-1 rounded text-dark-text-primary">
            {health?.device || 'Unknown'}
          </span>
        </div>
      </div>
    </div>
  );
};

export default AIHealthStatus;

