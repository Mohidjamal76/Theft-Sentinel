import { useState, useEffect, useRef, useCallback } from 'react';
import { processCamera } from '../api/aiEngine';

/**
 * Custom Hook for Real-Time Camera Monitoring
 * Polls camera endpoint at regular intervals
 * @param {string} cameraId - Camera ID to monitor
 * @param {number} intervalMs - Polling interval in milliseconds (default: 2000)
 */
export const useCameraMonitor = (cameraId, intervalMs = 2000) => {
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [currentResult, setCurrentResult] = useState(null);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  
  const intervalRef = useRef(null);
  const mountedRef = useRef(true);

  /**
   * Process a single frame from camera
   */
  const processFrame = useCallback(async () => {
    if (!mountedRef.current) return;

    try {
      const response = await processCamera({
        camera_id: cameraId,
        save_to_db: true,
        create_alert_on_theft: true,
      });
      
      if (mountedRef.current) {
        setCurrentResult(response.data);
        setError(null);
        setLastUpdate(new Date());
      }
    } catch (err) {
      if (mountedRef.current) {
        const errorMsg = err.response?.data?.detail || 
                        err.response?.data?.error || 
                        err.message || 
                        'Failed to process camera';
        setError(errorMsg);
      }
    }
  }, [cameraId]);

  /**
   * Start monitoring
   */
  const start = useCallback(() => {
    if (!isMonitoring && cameraId) {
      setIsMonitoring(true);
      setError(null);
      
      // Process immediately
      processFrame();
      
      // Set up interval
      intervalRef.current = setInterval(processFrame, intervalMs);
    }
  }, [isMonitoring, cameraId, processFrame, intervalMs]);

  /**
   * Stop monitoring
   */
  const stop = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsMonitoring(false);
  }, []);

  /**
   * Toggle monitoring on/off
   */
  const toggle = useCallback(() => {
    if (isMonitoring) {
      stop();
    } else {
      start();
    }
  }, [isMonitoring, start, stop]);

  /**
   * Manually trigger a single frame process
   */
  const refresh = useCallback(async () => {
    await processFrame();
  }, [processFrame]);

  // Cleanup on unmount
  useEffect(() => {
    mountedRef.current = true;
    
    return () => {
      mountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  // Update interval if it changes while monitoring
  useEffect(() => {
    if (isMonitoring) {
      stop();
      start();
    }
  }, [intervalMs]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    isMonitoring,
    currentResult,
    error,
    lastUpdate,
    start,
    stop,
    toggle,
    refresh,
  };
};

