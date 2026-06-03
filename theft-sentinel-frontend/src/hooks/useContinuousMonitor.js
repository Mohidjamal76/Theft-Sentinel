/**
 * useContinuousMonitor
 *
 * Custom hook for controlling per-camera AI monitoring.
 *
 * Key design decisions (after fixing the "stuck ON" bugs):
 *
 * 1. NO auto-restart on mount.
 *    Previously, fetchStatus() would silently call start() if
 *    ai_monitoring_enabled=true in DB but no process was running.
 *    This created a race condition: user clicked Stop → but auto-start
 *    was already in-flight → stop() hit a 404 (monitor not in dict yet)
 *    → frontend exception → toggle permanently stuck ON.
 *    Fix: fetchStatus now only READS state, never starts anything.
 *
 * 2. Optimistic UI with guaranteed reversion.
 *    start() and stop() flip the toggle IMMEDIATELY, then confirm with the
 *    API.  On any API error the toggle snaps back to its previous state and
 *    a toast notification shows the backend error message.
 *
 * 3. API-in-flight guard.
 *    While start() or stop() is awaiting the API response, background
 *    fetchStatus() calls are skipped.  This prevents the 1-Hz or 10-s poll
 *    from overriding an optimistic update that hasn't been confirmed yet.
 *
 * 4. Global Recoil atom (survives component unmounts / navigation).
 *    Initial value is synced from the backend on every mount via fetchStatus().
 *    On page refresh the atom resets to false; fetchStatus() reconciles it.
 *
 * 5. Cross-user sync via 10-s background poll.
 *    If User A (Admin) toggles monitoring, User B (Security Incharge) sees
 *    the change within 10 seconds without a page refresh.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { useRecoilState } from 'recoil';
import toast from 'react-hot-toast';
import { cameraMonitoringState } from '../store/monitoringStore';
import { startContinuousMonitoring, getMonitorStatus, stopContinuousMonitoring } from '../api/aiEngine';

export const useContinuousMonitor = (cameraId) => {
  // ── Global state (survives component unmount / navigation) ─────────────────
  const [isMonitoring, setIsMonitoring] = useRecoilState(
    cameraMonitoringState(String(cameraId)),
  );

  // ── Local UI state ─────────────────────────────────────────────────────────
  const [stats,   setStats]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);

  const mountedRef     = useRef(true);
  const intervalRef    = useRef(null);
  const bgIntervalRef  = useRef(null);

  // Guard: while start() or stop() is in-flight, skip background fetchStatus
  // calls so they don't race against the optimistic UI update.
  const apiInFlightRef = useRef(false);

  // ── Start monitoring (optimistic) ──────────────────────────────────────────
  const start = useCallback(async () => {
    if (!cameraId || apiInFlightRef.current) return;

    // 1. Optimistic update: flip toggle ON immediately
    setIsMonitoring(true);
    setLoading(true);
    setError(null);
    apiInFlightRef.current = true;

    try {
      const response = await startContinuousMonitoring(cameraId);

      if (!response.data.success) {
        throw new Error(response.data.error || 'Failed to start monitoring');
      }
      // Success confirmed — optimistic state is already correct
    } catch (err) {
      // ── Revert optimistic update on any failure ──
      if (mountedRef.current) {
        setIsMonitoring(false);   // snap back to OFF
        const msg =
          err.response?.data?.detail ||   // 403 from DRF
          err.response?.data?.error  ||
          err.message                ||
          'Failed to start AI monitoring';
        setError(msg);
        toast.error(`AI monitoring: ${msg}`);
      }
    } finally {
      apiInFlightRef.current = false;
      if (mountedRef.current) setLoading(false);
    }
  }, [cameraId, setIsMonitoring]);

  // ── Stop monitoring (optimistic) ───────────────────────────────────────────
  const stop = useCallback(async () => {
    if (!cameraId || apiInFlightRef.current) return;

    // 1. Optimistic update: flip toggle OFF immediately
    setIsMonitoring(false);
    setStats(null);
    setLoading(true);
    setError(null);
    apiInFlightRef.current = true;

    try {
      const response = await stopContinuousMonitoring(cameraId);

      // The backend now always returns 200 for stop (even "was not running"),
      // so reaching here means the desired state (stopped) is confirmed.
      if (!response.data.success) {
        // Unexpected — surface a warning but do NOT revert, monitoring IS stopped
        console.warn('[useContinuousMonitor] stop response success=false:', response.data);
      }
    } catch (err) {
      // ── Revert optimistic update on genuine API failures (4xx / 5xx) ──
      if (mountedRef.current) {
        setIsMonitoring(true);    // snap back to ON
        const msg =
          err.response?.data?.detail ||   // 403 from DRF
          err.response?.data?.error  ||
          err.message                ||
          'Failed to stop AI monitoring';
        setError(msg);
        toast.error(`AI monitoring: ${msg}`);
      }
    } finally {
      apiInFlightRef.current = false;
      if (mountedRef.current) setLoading(false);
    }
  }, [cameraId, setIsMonitoring]);

  // ── Toggle ─────────────────────────────────────────────────────────────────
  const toggle = useCallback(() => {
    if (isMonitoring) stop(); else start();
  }, [isMonitoring, start, stop]);

  // ── fetchStatus: READ-ONLY sync — never starts or stops anything ───────────
  //
  // Decision table (simplified — no auto-restart):
  //   monitor.is_running = true  → set isMonitoring true  (another user started it)
  //   monitor absent / false     → set isMonitoring false (process is not running)
  //
  // The ai_monitoring_enabled DB flag is ignored here.  It is only written by
  // start() / stop() and consumed by the camera serializer for persistence.
  // Removing the auto-restart eliminates the race condition that caused the
  // toggle to get permanently stuck in the ON position.
  const fetchStatus = useCallback(async () => {
    if (!mountedRef.current || !cameraId) return;
    // Skip while a user-initiated API call is in-flight (prevent poll override)
    if (apiInFlightRef.current) return;

    try {
      const response = await getMonitorStatus(cameraId);
      if (!mountedRef.current || apiInFlightRef.current) return;

      const { monitor } = response.data;

      if (monitor && monitor.is_running) {
        setStats(monitor);
        setError(null);
        setIsMonitoring(true);
      } else {
        setStats(null);
        setIsMonitoring(false);
      }
    } catch (err) {
      if (!mountedRef.current) return;
      if (err.response?.status === 404) {
        setIsMonitoring(false);
        setStats(null);
      }
      // Other errors (network, 5xx) are silently ignored in the poll —
      // they will surface on the next tick.
    }
  }, [cameraId, setIsMonitoring]);

  // ── Mount: one-time sync with backend ─────────────────────────────────────
  useEffect(() => {
    mountedRef.current = true;
    fetchStatus();

    return () => {
      mountedRef.current = false;
      if (intervalRef.current)   clearInterval(intervalRef.current);
      if (bgIntervalRef.current) clearInterval(bgIntervalRef.current);
    };
    // fetchStatus identity is stable; this intentionally runs once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Fast poll: 1 Hz while monitoring is active (keeps stats fresh) ─────────
  useEffect(() => {
    if (!isMonitoring) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    intervalRef.current = setInterval(fetchStatus, 1000);
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isMonitoring, fetchStatus]);

  // ── Slow background poll: 10 s (cross-user state sync) ─────────────────────
  // If another authorized user changes monitoring state, all open clients
  // reflect the change within 10 seconds without a page refresh.
  useEffect(() => {
    bgIntervalRef.current = setInterval(fetchStatus, 10000);
    return () => {
      if (bgIntervalRef.current) {
        clearInterval(bgIntervalRef.current);
        bgIntervalRef.current = null;
      }
    };
  }, [fetchStatus]);

  return { isMonitoring, stats, loading, error, start, stop, toggle };
};
