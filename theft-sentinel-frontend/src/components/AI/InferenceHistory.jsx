import { useState, useEffect } from 'react';
import { MagnifyingGlassIcon, ArrowPathIcon, FunnelIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { useAIEngine } from '../../hooks/useAIEngine';

/**
 * Inference History Component
 * Display and filter historical AI inference results
 */
const InferenceHistory = () => {
  const { fetchHistory } = useAIEngine();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showFilters, setShowFilters] = useState(false);
  
  const [filters, setFilters] = useState({
    min_confidence: 0.5,
    limit: 50,
  });
  const [totalCount, setTotalCount] = useState(0);

  const loadTotalCount = async () => {
    try {
      // Fetch total count with a high limit to get all results
      const params = {
        limit: 10000  // High limit to get all results
      };
      if (filters.min_confidence) params.min_confidence = filters.min_confidence;
      
      const data = await fetchHistory(params);
      // Count the actual results returned
      setTotalCount((data.results || []).length);
    } catch (err) {
      console.error('Failed to load total count:', err);
    }
  };

  const loadHistory = async () => {
    setLoading(true);
    setError(null);

    try {
      // Build query params for filtered results
      const params = {};
      if (filters.min_confidence) params.min_confidence = filters.min_confidence;
      
      // Set limit - use 10000 for "all" to effectively get all results
      if (filters.limit === 'all') {
        params.limit = 10000;
      } else {
        params.limit = filters.limit;
      }

      const data = await fetchHistory(params);
      setHistory(data.results || []);
    } catch (err) {
      const errorMsg = err.message || 'Failed to load inference history';
      setError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
    loadTotalCount();
  }, [filters]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const resetFilters = () => {
    setFilters({
      min_confidence: 0.5,
      limit: 50,
    });
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white mb-2">AI History</h1>
        <p className="text-dark-text-secondary">Historical AI theft detection results</p>
      </div>

      {/* Filter Controls */}
      <div className="glass rounded-xl border border-dark-border p-4 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-dark-text-primary flex items-center">
            <FunnelIcon className="h-5 w-5 mr-2" />
            Filters
          </h3>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="text-sm text-ai-blue hover:text-ai-blueDark"
          >
            {showFilters ? 'Hide' : 'Show'}
          </button>
        </div>

        {showFilters && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Min Confidence Filter */}
              <div>
                <label className="block text-sm font-medium text-dark-text-secondary mb-1">
                  Min Confidence: {(filters.min_confidence * 100).toFixed(0)}%
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={filters.min_confidence}
                  onChange={(e) => handleFilterChange('min_confidence', parseFloat(e.target.value))}
                  className="w-full"
                />
              </div>

              {/* Limit Filter */}
              <div>
                <label className="block text-sm font-medium text-dark-text-secondary mb-1">
                  Results Limit
                </label>
                <select
                  value={filters.limit}
                  onChange={(e) => handleFilterChange('limit', e.target.value === 'all' ? 'all' : Number(e.target.value))}
                  className="w-full px-3 py-2 bg-dark-card border border-dark-border rounded text-dark-text-primary focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent"
                >
                  <option value="all">All</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                  <option value={200}>200</option>
                  <option value={500}>500</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={resetFilters}
                className="px-4 py-2 text-dark-text-secondary bg-dark-card border border-dark-border rounded hover:bg-dark-surface transition"
              >
                Reset
              </button>
              <button
                onClick={loadHistory}
                className="px-4 py-2 text-white bg-ai-blue rounded hover:bg-ai-blueDark transition font-semibold"
              >
                <MagnifyingGlassIcon className="h-4 w-4 inline mr-1" />
                Search
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <ArrowPathIcon className="h-8 w-8 animate-spin text-ai-blue" />
          <span className="ml-2 text-dark-text-secondary">Loading history...</span>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-status-error/10 border border-status-error/50 rounded-lg p-4 mb-6">
          <p className="text-status-error">{error}</p>
        </div>
      )}

      {/* Results */}
      {!loading && !error && (
        <>
          <div className="mb-4 flex items-center justify-between">
            <div className="text-sm text-dark-text-secondary">
              Showing {history.length} result{history.length !== 1 ? 's' : ''}
            </div>
            <div className="text-lg font-bold text-dark-text-primary bg-ai-blue/10 border border-ai-blue/50 px-4 py-2 rounded-lg">
              Total Inferences: <span className="text-ai-blue">{totalCount}</span>
            </div>
          </div>

          {history.length === 0 ? (
            <div className="text-center py-12 text-dark-text-muted">
              <p className="text-lg mb-2">No inference records found</p>
              <p className="text-sm">Try adjusting your filters</p>
            </div>
          ) : (
            <div className="space-y-3">
              {history.map((inference) => {
                const classification = typeof inference.classification === 'string' 
                  ? inference.classification 
                  : 'unknown';
                const confidence = typeof inference.confidence === 'number' 
                  ? inference.confidence 
                  : 0;
                const cameraName = typeof inference.camera_name === 'string' 
                  ? inference.camera_name 
                  : (typeof inference.camera_id === 'string' ? inference.camera_id : 'Unknown');
                const timestamp = inference.timestamp 
                  ? new Date(inference.timestamp).toLocaleString() 
                  : 'N/A';
                const alertId = typeof inference.alert_id === 'string' 
                  ? inference.alert_id 
                  : null;
                
                // Check both flattened format and nested frame_metadata format
                const persons = typeof inference.persons === 'number' 
                  ? inference.persons 
                  : (typeof inference.frame_metadata?.num_persons === 'number' 
                      ? inference.frame_metadata.num_persons 
                      : 0);
                
                const objects = typeof inference.objects === 'number' 
                  ? inference.objects 
                  : (typeof inference.frame_metadata?.num_detections === 'number' 
                      ? inference.frame_metadata.num_detections 
                      : 0);
                
                const tracks = typeof inference.tracks === 'number' 
                  ? inference.tracks 
                  : (typeof inference.frame_metadata?.num_tracks === 'number' 
                      ? inference.frame_metadata.num_tracks 
                      : 0);

                return (
                  <div
                    key={inference.id || Math.random()}
                    className={`glass rounded-xl border-l-4 p-4 border border-dark-border ${
                      classification === 'theft'
                        ? 'border-status-error'
                        : 'border-status-success'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      {/* Left Side - Info */}
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span className={`px-3 py-1 rounded-full text-sm font-semibold border ${
                            classification === 'theft'
                              ? 'bg-status-error/20 text-status-error border-status-error/50'
                              : 'bg-status-success/20 text-status-success border-status-success/50'
                          }`}>
                            {classification.toUpperCase()}
                          </span>
                          <span className="text-sm font-medium text-dark-text-primary">
                            Confidence: {(confidence * 100).toFixed(1)}%
                          </span>
                        </div>

                        <div className="text-sm text-dark-text-secondary space-y-1">
                          <div>
                            <span className="font-medium text-dark-text-primary">Camera:</span> <span className="text-dark-text-secondary">{cameraName}</span>
                          </div>
                          <div>
                            <span className="font-medium text-dark-text-primary">Time:</span> <span className="text-dark-text-secondary">{timestamp}</span>
                          </div>
                          {alertId && (
                            <div className="text-status-error font-medium">
                              Alert ID: {alertId}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Right Side - Stats */}
                      <div className="text-right text-sm text-dark-text-secondary">
                        <div><span className="text-dark-text-primary font-medium">Persons:</span> {persons}</div>
                        <div><span className="text-dark-text-primary font-medium">Objects:</span> {objects}</div>
                        <div><span className="text-dark-text-primary font-medium">Tracks:</span> {tracks}</div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default InferenceHistory;

