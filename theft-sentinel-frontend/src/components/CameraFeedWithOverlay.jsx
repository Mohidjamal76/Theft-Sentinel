/**
 * CameraFeedWithOverlay
 *
 * Renders the raw MJPEG camera feed in an <img> and overlays an HTML5
 * <canvas> on top.  When the AI pipeline fires an alert or flags suspicious
 * persons the canvas draws LERP-smoothed bounding boxes labelled with the
 * re-ID global ID — 100 % client-side, zero extra backend bandwidth.
 *
 * ┌──────────────────────────────────────────┐
 * │  <img>  z-index:1   raw MJPEG feed       │
 * │  <canvas> z-index:10  (pointer-events:   │
 * │            none — click-through)         │
 * │  LIVE badge / AI badge   z-index:20      │
 * │  [Stop Tracking] — full mode only here   │
 * └──────────────────────────────────────────┘
 * │  [Stop Tracking] — grid mode: block flow │   ← below the video box
 */
import { useRef, useEffect, useCallback, useState, memo } from 'react';
import PropTypes from 'prop-types';
import useRealtimeTracking from '../hooks/useRealtimeTracking';

// ── Tunable constants ─────────────────────────────────────────────────────────

/** X3D score ≥ this threshold qualifies as suspicious. */
const SUSPICIOUS_THRESHOLD = 0.5;

/**
 * LERP factor applied every rAF tick (~60 Hz).
 * 0.0 = frozen,  1.0 = instant snap.
 */
const LERP_FACTOR = 0.2;

// ─────────────────────────────────────────────────────────────────────────────

const CameraFeedWithOverlay = memo(({
  cameraId,
  cameraName,
  width         = '100%',
  height        = 'auto',
  className     = '',
  enableOverlay = true,
  viewMode      = 'full',   // 'full' | 'grid'
}) => {
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const isGridMode   = viewMode === 'grid';

  // DOM refs
  const imgRef    = useRef(null);
  const canvasRef = useRef(null);
  const rafRef    = useRef(null);

  // ── Frame-level metadata (alert status, frame dims, suspicious IDs) ────────
  const frameMetaRef = useRef({
    alert_triggered: false,
    classification:  'normal',
    confidence:      0,
    frame_width:     640,
    frame_height:    480,
    suspicious_ids:  new Set(),
  });

  // ── Map-based Suspect LERP State ───────────────────────────────────────────
  const knownThievesRef = useRef(new Set());
  const latchedSuspectsRef = useRef(new Map());
  const visualBoxRef = useRef({});
  const targetBoxRef = useRef({}); 

  // ── Tracking & Alert UI State ──────────────────────────────────────────────
  const [isTrackingActive, setIsTrackingActive] = useState(false);
  const [currentFrameAlert, setCurrentFrameAlert] = useState(false);

  // ── SSE hook ───────────────────────────────────────────────────────────────
  const { trackingData, connected } = useRealtimeTracking(cameraId, enableOverlay);

  // ── Process every incoming SSE event ──────────────────────────────────────
  useEffect(() => {
    if (!trackingData) return;

    frameMetaRef.current = {
      alert_triggered: Boolean(trackingData.alert_triggered),
      classification:  trackingData.classification ?? 'normal',
      confidence:      trackingData.confidence      ?? 0,
      frame_width:     trackingData.frame_width     || 640,
      frame_height:    trackingData.frame_height    || 480,
      suspicious_ids:  new Set(trackingData.suspicious_ids || []),
    };

    const now = performance.now();
    const tracks = trackingData.tracks || [];

    for (const track of tracks) {
      // DEBUG: Print the raw track object to the F12 Developer Console
      console.log("🕵️ RAW TRACK RECEIVED:", JSON.stringify(track));

      const rawId = track.global_id != null ? track.global_id : track.track_id;
      const id = String(rawId);

      // Safely check every possible spelling/nesting of the suspicious flag
      const flagSnake = track.is_suspicious;
      const flagCamel = track.isSuspicious;

      // Fallback: If the global alarm is ringing, assume the person with the high score is the thief
      const isHighScoringTarget = trackingData.alert_triggered && (track.x3d_score >= 0.70);

      const isBackendSuspicious = 
          flagSnake === true || String(flagSnake).toLowerCase() === 'true' || flagSnake === 1 ||
          flagCamel === true || String(flagCamel).toLowerCase() === 'true' || flagCamel === 1 ||
          isHighScoringTarget;

      // 1. Check if they are ALREADY a known thief in permanent memory
      const isKnownThief = knownThievesRef.current.has(id);

      // 3. Process new or returning thieves
      if (isBackendSuspicious || isKnownThief) {

          // If this is a BRAND NEW thief detection
          if (isBackendSuspicious && !isKnownThief) {
              knownThievesRef.current.add(id); // Permanently memorize them

              if (track.global_id != null && cameraName) {
                  console.log(`🚨 [FRONTEND] NEW THIEF LATCHED: Global ID ${track.global_id}`);
                  window.dispatchEvent(new CustomEvent('ai-suspect-detected', {
                      detail: { globalId: track.global_id, cameraName }
                  }));
              }
          } else if (isKnownThief) {
              // Notify the Node Graph of this camera visit so the path graph updates
              // (handles revisits: Cam A → Cam B → Cam A).
              // The Node Graph deduplicates consecutive same-camera entries itself.
              console.log(`👀 [FRONTEND] RETURNING THIEF RECOGNIZED: ID ${id}`);
              if (track.global_id != null && cameraName) {
                  window.dispatchEvent(new CustomEvent('ai-suspect-detected', {
                      detail: { globalId: track.global_id, cameraName }
                  }));
              }
          }

          // Latch them for the drawing loop
          latchedSuspectsRef.current.set(id, now);

          const gid = track.global_id ?? '?';
          targetBoxRef.current[id] = {
              bbox: track.bbox, 
              label: `THIEF G:${gid}`,
              score: `${((track.x3d_score ?? 0) * 100).toFixed(0)}%`,
              color: '#FF1111' 
          };

          if (!visualBoxRef.current[id]) {
              visualBoxRef.current[id] = [...track.bbox];
          }
      }
    }

    // Sync React state for alert badge
    setCurrentFrameAlert(Boolean(trackingData.alert_triggered));

  }, [trackingData, cameraName]);

  // ── Sync with global Stop Tracking event ───────────────────────────────────
  useEffect(() => {
    const handleSuspectCleared = (e) => {
      const globalId = String(e.detail.globalId);
      // 1. Remove from permanent thief memory
      knownThievesRef.current.delete(globalId);
      // 2. Unconditionally clear all ref entries keyed by globalId
      latchedSuspectsRef.current.delete(globalId);
      delete targetBoxRef.current[globalId];
      delete visualBoxRef.current[globalId];
      // 3. Fallback scan: clear any track-ID-keyed entry whose label matches this globalId
      for (const [key, target] of Object.entries(targetBoxRef.current)) {
        if (target.label === `THIEF G:${globalId}`) {
          latchedSuspectsRef.current.delete(key);
          delete targetBoxRef.current[key];
          delete visualBoxRef.current[key];
        }
      }
    };
    window.addEventListener('ai-suspect-cleared', handleSuspectCleared);
    return () => window.removeEventListener('ai-suspect-cleared', handleSuspectCleared);
  }, []);



  // ── Canvas drawing loop (requestAnimationFrame) ────────────────────────────
  const drawLoop = useCallback(() => {
    const canvas = canvasRef.current;
    const img    = imgRef.current;

    if (!canvas || !img) {
      rafRef.current = requestAnimationFrame(drawLoop);
      return;
    }

    const ctx = canvas.getContext('2d');

    const imgRect = img.getBoundingClientRect();
    const bufW    = Math.round(imgRect.width);
    const bufH    = Math.round(imgRect.height);
    if (canvas.width !== bufW || canvas.height !== bufH) {
      canvas.width  = bufW;
      canvas.height = bufH;
    }

    // Task 3: Single-Clear Render Loop - Called exactly ONCE at the top.
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const now = performance.now();

    const drawList = [];

    for (const [keyId, timestamp] of latchedSuspectsRef.current.entries()) {
      const trackId = String(keyId);
      const target = targetBoxRef.current[trackId];
      const visual = visualBoxRef.current[trackId];

      if (target && visual) {
        if (now - timestamp > 3500) {
          // Off-Screen Cleanup: Person left the frame and TTL expired
          latchedSuspectsRef.current.delete(trackId);
          delete targetBoxRef.current[trackId];
          delete visualBoxRef.current[trackId];
          continue;
        }

        // Strict guard against NaN poisoning
        if (target && target.bbox && target.bbox.length === 4 && !target.bbox.some(isNaN)) {
          // Safe to calculate LERP
          visual[0] += (target.bbox[0] - visual[0]) * 0.2;
          visual[1] += (target.bbox[1] - visual[1]) * 0.2;
          visual[2] += (target.bbox[2] - visual[2]) * 0.2;
          visual[3] += (target.bbox[3] - visual[3]) * 0.2;
        }

        // Guard the actual drawing step
        if (visual && visual.length === 4 && !visual.some(isNaN)) {
          const x = visual[0];
          const y = visual[1];
          const w = visual[2]; // Directly use width
          const h = visual[3]; // Directly use height

          if (w > 0 && h > 0) {
            drawList.push({ target, x, y, w, h });
          }
        } else {
          // If poisoned, forcefully reset it from the target next frame
          delete visualBoxRef.current[trackId];
        }
      }
    }

    for (const { target, x, y, w, h } of drawList) {
      const meta     = frameMetaRef.current;
      const nativeW  = meta.frame_width || 640;
      const nativeH  = meta.frame_height || 480;
      const displayW = canvas.clientWidth  || bufW;
      const displayH = canvas.clientHeight || bufH;
      const scaleX   = displayW / nativeW;
      const scaleY   = displayH / nativeH;

      const drawX = x * scaleX;
      const drawY = y * scaleY;
      const drawW = w * scaleX;
      const drawH = h * scaleY;

      ctx.save();
      ctx.strokeStyle = target.color || '#FF8800';
      ctx.lineWidth   = 2.5;
      ctx.shadowColor = target.color || '#FF8800';
      ctx.shadowBlur  = 6;
      ctx.strokeRect(drawX, drawY, drawW, drawH);
      ctx.restore();

      const label = target.label || 'SUSPECT';
      ctx.font = 'bold 12px "Courier New", monospace';
      const textW = ctx.measureText(label).width;

      const badgeColor = target.color === '#FF1111' ? 'rgba(220,0,0,0.85)' : 'rgba(200,100,0,0.85)';
      
      ctx.fillStyle = badgeColor;
      ctx.beginPath();
      if (ctx.roundRect) {
        ctx.roundRect(drawX, drawY - 22, textW + 10, 22, [3, 3, 0, 0]);
      } else {
        ctx.rect(drawX, drawY - 22, textW + 10, 22);
      }
      ctx.fill();

      ctx.fillStyle = '#FFFFFF';
      ctx.fillText(label, drawX + 5, drawY - 6);

      const score = target.score || '0%';
      const scoreW = ctx.measureText(score).width;

      ctx.fillStyle = badgeColor;
      ctx.beginPath();
      if (ctx.roundRect) {
        ctx.roundRect(drawX, drawY + drawH, scoreW + 10, 18, [0, 0, 3, 3]);
      } else {
        ctx.rect(drawX, drawY + drawH, scoreW + 10, 18);
      }
      ctx.fill();

      ctx.fillStyle = '#FFFFFF';
      ctx.font      = '11px "Courier New", monospace';
      ctx.fillText(score, drawX + 5, drawY + drawH + 13);
    }

    // Task 3: Ensure requestAnimationFrame schedules itself regardless of drawing
    rafRef.current = requestAnimationFrame(drawLoop);
  }, []); // stable — reads refs, never captures React state

  // Start / stop rAF loop
  useEffect(() => {
    if (!enableOverlay) return undefined;
    rafRef.current = requestAnimationFrame(drawLoop);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [drawLoop, enableOverlay]);



  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <>
      <div
        className={`${className}`}
        style={{
          position:   'relative',
          width,
          display:    'block',
          lineHeight: 0,
        }}
      >
        {/* Raw MJPEG feed */}
        <img
          ref={imgRef}
          src={`${API_BASE_URL}/api/cameras/${cameraId}/feed/`}
          alt="Live Camera Feed"
          style={{
            width:    '100%',
            height,
            display:  'block',
            position: 'relative',
            zIndex:   1,
          }}
          className="rounded-lg shadow-md"
          onError={(e) => {
            e.target.onerror = null;
            e.target.src =
              'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg"' +
              ' width="640" height="360"%3E%3Crect fill="%23111827" width="640"' +
              ' height="360"/%3E%3Ctext fill="%236B7280" font-family="sans-serif"' +
              ' font-size="18" x="50%25" y="50%25" text-anchor="middle"' +
              ' dy=".35em"%3ECamera Feed Unavailable%3C/text%3E%3C/svg%3E';
          }}
        />

        {/* Canvas overlay */}
        {enableOverlay && (
          <canvas
            ref={canvasRef}
            style={{
              position:      'absolute',
              top:           0,
              left:          0,
              width:         '100%',
              height:        '100%',
              pointerEvents: 'none',
              zIndex:        10,
            }}
          />
        )}

        {/* Real-Time Alert UI Badge */}
        {enableOverlay && (
          <div
            style={{ zIndex: 20 }}
            className={`absolute top-2 left-2 flex items-center space-x-1 px-3 py-1 rounded text-xs font-bold shadow-md transition-colors ${
              currentFrameAlert ? 'bg-red-600 text-white animate-pulse' : 'bg-green-600 text-white'
            }`}
          >
            <span>{currentFrameAlert ? 'THEFT DETECTED' : 'NORMAL'}</span>
          </div>
        )}

        {/* LIVE badge */}
        <div
          style={{ zIndex: 20 }}
          className="absolute top-2 right-2 flex items-center space-x-1
                     bg-red-600 text-white px-2 py-0.5 rounded text-xs font-semibold"
        >
          <span className="w-2 h-2 bg-white rounded-full animate-pulse" />
          <span>LIVE</span>
        </div>

        {/* AI connection badge */}
        {enableOverlay && (
          <div
            style={{ zIndex: 20 }}
            className={`absolute bottom-2 right-2 px-2 py-0.5 rounded text-xs
                        font-semibold transition-colors ${
                          connected
                            ? 'bg-green-600 text-white'
                            : 'bg-yellow-400 text-gray-900'
                        }`}
          >
            {connected ? '● AI LIVE' : '◌ AI…'}
          </div>
        )}

      </div>
    </>
  );
});

CameraFeedWithOverlay.displayName = 'CameraFeedWithOverlay';

CameraFeedWithOverlay.propTypes = {
  cameraId:      PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  cameraName:    PropTypes.string,
  width:         PropTypes.string,
  height:        PropTypes.string,
  className:     PropTypes.string,
  enableOverlay: PropTypes.bool,
  viewMode:      PropTypes.oneOf(['full', 'grid']),
};

export default CameraFeedWithOverlay;
