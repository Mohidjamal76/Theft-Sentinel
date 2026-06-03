import { useState, useCallback } from 'react';
import {
  analyzeFrame,
  processCamera,
  getAIHealth,
  getModelInfo,
  getInferenceHistory,
  runFullPipeline,
} from '../api/aiEngine';

/**
 * Custom Hook for AI Engine Operations
 * Provides state management and API calls for AI functionality
 */
export const useAIEngine = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  /**
   * Analyze a frame for theft detection
   * @param {Object} data - Frame data
   * @returns {Promise} Analysis result
   */
  const analyze = useCallback(async (data) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await analyzeFrame(data);
      setResult(response.data);
      return response.data;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 
                      err.response?.data?.error || 
                      err.message || 
                      'Failed to analyze frame';
      setError(errorMsg);
      throw new Error(errorMsg);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Process camera stream
   * @param {string} cameraId - Camera ID
   * @param {Object} options - Additional options
   * @returns {Promise} Analysis result
   */
  const processStream = useCallback(async (cameraId, options = {}) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await processCamera({
        camera_id: cameraId,
        ...options,
      });
      setResult(response.data);
      return response.data;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 
                      err.response?.data?.error || 
                      err.message || 
                      'Failed to process camera';
      setError(errorMsg);
      throw new Error(errorMsg);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Check AI service health
   * @returns {Promise} Health status
   */
  const checkHealth = useCallback(async () => {
    try {
      const response = await getAIHealth();
      return response.data;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 
                      err.message || 
                      'Failed to check health';
      throw new Error(errorMsg);
    }
  }, []);

  /**
   * Get AI model information
   * @returns {Promise} Model info
   */
  const fetchModelInfo = useCallback(async () => {
    try {
      const response = await getModelInfo();
      return response.data;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 
                      err.message || 
                      'Failed to fetch model info';
      throw new Error(errorMsg);
    }
  }, []);

  /**
   * Get inference history
   * @param {Object} params - Query parameters
   * @returns {Promise} Inference history
   */
  const fetchHistory = useCallback(async (params = {}) => {
    try {
      const response = await getInferenceHistory(params);
      return response.data;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 
                      err.message || 
                      'Failed to fetch history';
      throw new Error(errorMsg);
    }
  }, []);

  /**
   * Run full AI pipeline
   * @param {Object} data - Frame data
   * @returns {Promise} Full pipeline result
   */
  const runPipeline = useCallback(async (data) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await runFullPipeline(data);
      setResult(response.data);
      return response.data;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 
                      err.response?.data?.error || 
                      err.message || 
                      'Failed to run pipeline';
      setError(errorMsg);
      throw new Error(errorMsg);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Reset state
   */
  const reset = useCallback(() => {
    setResult(null);
    setError(null);
    setLoading(false);
  }, []);

  return {
    loading,
    error,
    result,
    analyze,
    processStream,
    checkHealth,
    fetchModelInfo,
    fetchHistory,
    runPipeline,
    reset,
  };
};

