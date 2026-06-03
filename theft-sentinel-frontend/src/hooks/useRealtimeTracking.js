/**
 * useRealtimeTracking
 *
 * Connects to the backend SSE endpoint
 *   GET /api/ai/cameras/<cameraId>/realtime-tracking/
 *
 * and streams real-time bounding-box data for the canvas overlay.
 *
 * The hook is intentionally stateless regarding video frames: it only manages
 * the SSE connection lifecycle and exposes the latest tracking payload.
 *
 * @param {string|number} cameraId   - Camera database ID
 * @param {boolean}       [enabled]  - Set false to skip connecting (default true)
 * @returns {{ trackingData, connected, error, subscriberCount }}
 */
import { useState, useEffect, useRef, useCallback } from 'react';

const RECONNECT_BASE_DELAY_MS = 2000;
const MAX_RECONNECT_ATTEMPTS   = 8;

const useRealtimeTracking = (cameraId, enabled = true) => {
  const [trackingData, setTrackingData]     = useState(null);
  const [connected,    setConnected]        = useState(false);
  const [error,        setError]            = useState(null);

  const esRef               = useRef(null);
  const reconnectTimerRef   = useRef(null);
  const attemptsRef         = useRef(0);
  const mountedRef          = useRef(true);
  const delayRef            = useRef(RECONNECT_BASE_DELAY_MS);

  const cleanup = useCallback(() => {
    clearTimeout(reconnectTimerRef.current);
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!mountedRef.current || !cameraId || !enabled) return;

    cleanup();

    const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const url = `${API_BASE_URL}/api/ai/cameras/${cameraId}/realtime-tracking/`;

    const es = new EventSource(url);
    esRef.current = es;

    es.onopen = () => {
      if (!mountedRef.current) return;
      setConnected(true);
      setError(null);
      attemptsRef.current = 0;
      delayRef.current    = RECONNECT_BASE_DELAY_MS;
    };

    es.onmessage = (event) => {
      if (!mountedRef.current) return;
      try {
        const data = JSON.parse(event.data);
        // Ignore initial handshake event
        if (data.type === 'connected') return;

        // Diagnostic: confirm tracks are arriving from the backend
        console.debug(
          `[SSE cam=${data.camera_id}]`
          + ` alert=${data.alert_triggered}`
          + ` cls=${data.classification}`
          + ` conf=${data.confidence?.toFixed(3)}`
          + ` tracks=${Array.isArray(data.tracks) ? data.tracks.length : '?'}`
          + ` suspIds=${Array.isArray(data.suspicious_ids) ? data.suspicious_ids.length : '?'}`
          + ` ${data.frame_width}×${data.frame_height}`,
          data.tracks,
        );

        setTrackingData(data);
      } catch {
        // ignore malformed JSON
      }
    };

    es.onerror = () => {
      if (!mountedRef.current) return;
      setConnected(false);
      es.close();
      esRef.current = null;

      if (attemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
        setError('Real-time tracking unavailable. Please refresh the page.');
        return;
      }

      attemptsRef.current += 1;
      setError(`Reconnecting… (${attemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})`);

      // Exponential back-off capped at 30 s
      const delay = Math.min(delayRef.current * 1.5, 30_000);
      delayRef.current = delay;
      reconnectTimerRef.current = setTimeout(connect, delay);
    };
  }, [cameraId, enabled, cleanup]);

  useEffect(() => {
    mountedRef.current = true;
    if (enabled && cameraId) {
      connect();
    }
    return () => {
      mountedRef.current = false;
      cleanup();
    };
  }, [cameraId, enabled, connect, cleanup]);

  return { trackingData, connected, error };
};

export default useRealtimeTracking;
