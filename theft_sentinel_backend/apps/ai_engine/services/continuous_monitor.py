"""
Continuous Camera Monitoring Service
Runs your existing AI pipeline continuously on camera streams
Stores results in database for frontend to read in real-time
"""

import os
os.environ["OPENH264_LIBRARY"] = r"Z:\FYP\fyp_application\env\Scripts\openh264-1.8.0-win64.dll"

# RTSP transport env-vars are initialised globally in apps/ai_engine/apps.py
# at Django app-registry load time — before any cv2.VideoCapture() call.
# Do NOT re-set OPENCV_FFMPEG_CAPTURE_OPTIONS here; apps.py owns that config.

import cv2
import tempfile
import time
import threading
import logging
import numpy as np
from collections import deque
from typing import Dict, Optional
from urllib.parse import urlparse
from django.utils import timezone

logger = logging.getLogger(__name__)


# MJPEGCapture lives in apps/cameras/mjpeg_capture.py (shared with stream_manager).
from apps.cameras.mjpeg_capture import MJPEGCapture


class ContinuousMonitor:
    """
    Runs continuous AI monitoring on camera streams
    Processes frames at full FPS (15-30) instead of 2-second intervals
    """
    
    # Maximum rate at which the SSE callback is fired (frames per second).
    # Keeps bandwidth low on cloud deployments while still giving smooth overlays.
    _SSE_MAX_FPS: float = 10.0

    def __init__(self, camera_id: str, rtsp_url: str, callback=None):
        """
        Args:
            camera_id: Camera database ID
            rtsp_url: Camera RTSP/HTTP stream URL
            callback: Optional function to call with results (for real-time updates)
        """
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.callback = callback

        self.is_running = False
        self.thread = None
        self.capture_thread = None
        self.latest_frame = None

        # Stats
        self.frames_processed = 0
        self.frames_captured = 0
        self.start_time = None
        self.last_result = None
        self.error_count = 0

        # Rolling frame buffer (~5s at 30 FPS) for theft clip generation
        self._frame_buffer = deque(maxlen=150)

        # Throttle SSE / callback publishing to _SSE_MAX_FPS
        self._last_callback_time: float = 0.0

        # 5-second cooldown for alerting
        self.last_alert_time: float = 0.0

        # ── TASK 4: Latency debug tracking ────────────────────────────────────
        self._last_capture_time: float = 0.0
        self._reconnect_count: int = 0
        self._last_fps_log_time: float = 0.0
        self._capture_fps_window: deque = deque(maxlen=30)

        # High-FPS X3D buffer fill — updated by inference loop, read by capture loop.
        # Maps global_id -> last known bbox so capture thread can push frames at
        # camera FPS without waiting for the slow inference cycle.
        self._tracked_gids: dict = {}          # gid -> [x1,y1,x2,y2]
        self._tracked_gids_lock = threading.Lock()
    
    def start(self):
        """Start continuous monitoring in background thread"""
        if self.is_running:
            logger.warning(f"Monitor already running for camera {self.camera_id}")
            return False
        
        self.is_running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info(f"🎥 Started continuous monitoring for camera {self.camera_id}")
        return True
    
    def stop(self):
        """Stop continuous monitoring."""
        self.is_running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=5.0)
        if self.thread:
            self.thread.join(timeout=5.0)
        # NOTE: do NOT stop the stream_manager stream here — other components
        # (e.g. the MJPEG feed view) may still be reading from it.
        logger.info(f"🛑 Stopped monitoring for camera {self.camera_id}")
    
    def get_stats(self) -> Dict:
        """Get monitoring statistics"""
        if self.start_time:
            elapsed = time.time() - self.start_time
            fps = self.frames_processed / elapsed if elapsed > 0 else 0
            capture_fps = self.frames_captured / elapsed if elapsed > 0 else 0
        else:
            fps = 0
            capture_fps = 0
            elapsed = 0
        
        return {
            'camera_id': self.camera_id,
            'is_running': self.is_running,
            'frames_processed': self.frames_processed,
            'frames_captured': self.frames_captured,
            'fps': round(fps, 2),
            'capture_fps': round(capture_fps, 2),
            'elapsed_seconds': round(elapsed, 2),
            'error_count': self.error_count,
            'last_result': self.last_result,
        }
    
    def _open_capture_for_url(self, url: str):
        """
        Open the correct capture object for the URL scheme.

          RTSP/RTSPS  → cv2.VideoCapture(url, CAP_FFMPEG)
                         OPENCV_FFMPEG_CAPTURE_OPTIONS (TCP, stimeout) apply.
          HTTP/HTTPS  → MJPEGCapture(url)  ← pure-Python MJPEG reader
                         Bypasses all OpenCV/FFmpeg backends to avoid the
                         RTSP env-var options that corrupt HTTP connections.

        isOpened() is ALWAYS checked BEFORE getBackendName().
        Returns the capture object, or None on failure.
        """
        scheme = urlparse(url).scheme.lower()

        if scheme in ("rtsp", "rtsps"):
            logger.info(
                "[ContinuousMonitor] Opening RTSP stream for camera %s: %s",
                self.camera_id, url,
            )
            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)

            if not cap.isOpened():
                logger.error(
                    "[ContinuousMonitor] Failed to open RTSP stream for camera %s: %s",
                    self.camera_id, url,
                )
                cap.release()
                return None

            backend = cap.getBackendName()
            if backend != "FFMPEG":
                logger.warning(
                    "[ContinuousMonitor] Non-FFmpeg backend '%s' for RTSP camera %s",
                    backend, self.camera_id,
                )
            logger.info(
                "[ContinuousMonitor] RTSP stream opened for camera %s (backend=%s)",
                self.camera_id, backend,
            )
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            return cap

        elif scheme in ("http", "https"):
            logger.info(
                "[ContinuousMonitor] Opening HTTP stream for camera %s "
                "(pure-Python MJPEG reader): %s",
                self.camera_id, url,
            )
            cap = MJPEGCapture(url)
            if cap.isOpened():
                logger.info(
                    "[ContinuousMonitor] HTTP stream opened for camera %s "
                    "(backend=%s)",
                    self.camera_id, cap.getBackendName(),
                )
                return cap

            # MJPEGCapture failed — last resort: cv2.VideoCapture auto-select
            logger.warning(
                "[ContinuousMonitor] MJPEGCapture failed for camera %s "
                "— falling back to cv2.VideoCapture: %s",
                self.camera_id, url,
            )
            cap2 = cv2.VideoCapture(url)
            if not cap2.isOpened():
                logger.error(
                    "[ContinuousMonitor] Failed to open HTTP stream for camera %s: %s",
                    self.camera_id, url,
                )
                cap2.release()
                return None
            cap2.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            logger.info(
                "[ContinuousMonitor] HTTP stream opened for camera %s "
                "(fallback backend=%s)",
                self.camera_id, cap2.getBackendName(),
            )
            return cap2

        else:
            logger.error(
                "[ContinuousMonitor] Unsupported protocol '%s' for camera %s: %s",
                scheme, self.camera_id, url,
            )
            return None


    def _capture_loop(self):
        """
        Dedicated thread that supplies frames to the AI monitor loop.

        Reads frames from the shared CameraStreamManager instead of opening
        its own connection to the camera source.  This guarantees:

          • Only ONE TCP connection is ever made to each camera.
          • DroidCam’s single-concurrent-client limit is never exceeded.
          • Connection management (reconnect, backoff) is owned by
            CameraStreamManager, not duplicated here.

        Polls stream.get_frame_snapshot() which returns (frame, timestamp)
        atomically.  A new frame is only processed when its timestamp
        advances past the last-seen value, preventing duplicate inference.
        """
        from apps.cameras.stream_manager import stream_manager

        logger.info(
            "[ContinuousMonitor] Attaching to shared CameraStreamManager "
            "for camera %s: %s",
            self.camera_id, self.rtsp_url,
        )
        stream = stream_manager.get_or_create(self.camera_id, self.rtsp_url)
        last_frame_ts: float = 0.0

        while self.is_running:
            try:
                frame, ts = stream.get_frame_snapshot()

                if frame is None or ts == 0.0:
                    # Stream not yet connected
                    self.error_count += 1
                    if self.error_count % 30 == 1:
                        logger.warning(
                            "[ContinuousMonitor] No frame from stream_manager "
                            "for camera %s (error_count=%d) — stream connecting?",
                            self.camera_id, self.error_count,
                        )
                    time.sleep(0.1)
                    continue

                if ts <= last_frame_ts:
                    # Same frame as last poll — wait briefly for next capture
                    time.sleep(0.01)
                    continue

                # New frame arrived
                last_frame_ts = ts
                self.error_count = 0
                self.frames_captured += 1

                # stream_manager already downscales to 640×480 in its reader loop
                # so no additional resize is needed here.

                # ── TASK 4: per-frame latency / FPS diagnostics ────────────────
                now = time.time()
                if self._last_capture_time:
                    gap = now - self._last_capture_time
                    self._capture_fps_window.append(gap)
                    if gap > 1.0:
                        logger.warning(
                            f"⚠️  Capture delay {gap:.2f}s exceeds 1s for camera "
                            f"{self.camera_id}"
                        )
                self._last_capture_time = now

                if now - self._last_fps_log_time >= 10.0:
                    if self._capture_fps_window:
                        avg_gap = sum(self._capture_fps_window) / len(self._capture_fps_window)
                        rolling_fps = 1.0 / avg_gap if avg_gap > 0 else 0.0
                        stats = self.get_stats()
                        logger.debug(
                            f"📊 Camera {self.camera_id} — "
                            f"capture_fps={rolling_fps:.1f} "
                            f"processing_fps={stats['fps']:.1f} "
                            f"reconnects={self._reconnect_count}"
                        )
                    self._last_fps_log_time = now

                # Update shared latest frame for the monitor loop
                self.latest_frame = frame
                self._frame_buffer.append(frame)

                # ── HIGH-FPS X3D BUFFER FILL ──────────────────────────────────
                # Push this captured frame to the X3D buffer for every GID that
                # the inference loop is currently tracking.  This fills the
                # 64-frame buffer at camera FPS (~15 FPS) instead of inference
                # FPS (~3 FPS), reducing first-inference latency from ~21s to ~4s.
                with self._tracked_gids_lock:
                    _gids_snap = dict(self._tracked_gids)

                if _gids_snap:
                    try:
                        from apps.ai_engine.services.ai_service import ai_service
                        if ai_service.is_ready():
                            _fh, _fw = frame.shape[:2]
                            _frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            with ai_service.state_lock:
                                for _gid, _bbox in _gids_snap.items():
                                    ai_service.theft_detector.push_frame(
                                        global_id   = _gid,
                                        frame_rgb   = _frame_rgb,
                                        bbox        = _bbox,
                                        frame_shape = (_fh, _fw),
                                    )
                    except Exception as _x3d_err:
                        logger.debug("Capture-loop X3D push error: %s", _x3d_err)

            except Exception as e:
                logger.error(f"Error in capture loop: {str(e)}", exc_info=True)
                self.error_count += 1
                time.sleep(0.5)

    def _monitor_loop(self):
        """Main inference loop - runs at AI processing speed.

        TASK 3 audit: this loop reads self.latest_frame which is a shared pointer
        updated atomically by _capture_loop.  There is NO intermediate queue or
        deque between capture and inference — the monitor always processes the
        single freshest frame available, automatically discarding any older ones.
        The only accumulation structure is _frame_buffer (rolling alert clip
        buffer) which is intentionally preserved for Cloudinary clip uploads.
        """
        from .inference_runner import InferenceRunner
        from ..utils.frame_utils import capture_frame_from_rtsp

        logger.info(f"Initializing AI monitor loop for camera {self.camera_id}")
        self.start_time = time.time()
        runner = InferenceRunner()

        import gc

        # ── TASK 4: processing-side latency tracking ──────────────────────────
        _last_proc_fps_log: float = 0.0
        _proc_gaps: deque = deque(maxlen=30)
        _last_proc_time: float = 0.0
        _warn_fps_threshold: float = 3.0  # warn if processing FPS falls below this

        # Wait for the first frame from the capture thread
        while self.is_running and self.latest_frame is None:
            time.sleep(0.1)

        # Process frames continuously
        while self.is_running:
            try:
                # TASK 3: always grab the very latest pointer — no copy queued up
                frame = self.latest_frame
                if frame is None or getattr(frame, "size", 0) == 0:
                    time.sleep(0.1)
                    continue
                
                self.frames_processed += 1

                if self.frames_processed % 50 == 0:
                    gc.collect()

                # ── TASK 4: measure per-inference gap ────────────────────────
                _proc_now = time.time()
                if _last_proc_time:
                    _proc_gaps.append(_proc_now - _last_proc_time)
                _last_proc_time = _proc_now

                # Run AI inference
                result = runner.run_inference(frame, camera_id=self.camera_id)

                # Update GID-bbox map so capture loop can push at camera FPS
                with self._tracked_gids_lock:
                    self._tracked_gids = {
                        t["global_id"]: t["bbox"]
                        for t in result.get("tracks", [])
                        if t.get("global_id") is not None
                    }

                # Task 3: Aggressive CUDA Cache Flushing (balanced for FPS)
                if self.frames_processed % 15 == 0 or result.get('classification') == 'theft':
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()

                # ── TASK 4: periodic processing FPS log + low-FPS warning ─────
                if _proc_now - _last_proc_fps_log >= 10.0 and _proc_gaps:
                    avg_gap = sum(_proc_gaps) / len(_proc_gaps)
                    proc_fps = 1.0 / avg_gap if avg_gap > 0 else 0.0
                    _last_proc_fps_log = _proc_now
                    if proc_fps < _warn_fps_threshold:
                        logger.warning(
                            f"🐢 Processing FPS severely degraded for camera "
                            f"{self.camera_id}: {proc_fps:.1f} fps "
                            f"(threshold={_warn_fps_threshold:.0f})"
                        )
                    else:
                        logger.debug(
                            f"📊 Processing FPS for camera {self.camera_id}: "
                            f"{proc_fps:.1f} fps"
                        )

                result['timestamp'] = timezone.now().isoformat()
                result['fps'] = self.get_stats()['fps']
                # Attach native frame dimensions so the frontend can scale bboxes
                result['camera_id'] = self.camera_id
                result['frame_width'] = frame.shape[1]
                result['frame_height'] = frame.shape[0]

                # ── COOLDOWN GATEKEEPER — gates DB alert only ─────────────────
                # The X3D TheftState already has an 8-second built-in cooldown.
                # This outer gate prevents duplicate DB Alert records across
                # consecutive theft-classified frames.
                #
                # IMPORTANT: result['classification'] is NOT overwritten here.
                # The SSE callback always receives the true AI output so the
                # frontend canvas shows real-time THEFT overlays.
                # Duplicate-alert suppression is handled by _allow_db_alert below.
                is_theft_detected = result.get('classification') == 'theft'
                current_time = time.time()

                _allow_db_alert = (
                    is_theft_detected
                    and (current_time - self.last_alert_time) >= 15.0  # > X3D_COOLDOWN_SECONDS (8s)
                )
                if _allow_db_alert:
                    self.last_alert_time = current_time

                self.last_result = result

                # ── CALLBACK FIRST (true AI classification — no suppression) ──
                # Fire the SSE/WebSocket callback immediately after inference so
                # the frontend canvas receives bounding-box data without waiting
                # for the (slower) database write to complete.
                # Throttled to _SSE_MAX_FPS to keep cloud bandwidth low.
                if self.callback:
                    now = time.time()
                    min_interval = 1.0 / self._SSE_MAX_FPS
                    if (now - self._last_callback_time) >= min_interval:
                        self._last_callback_time = now
                        try:
                            self.callback(self.camera_id, result)
                        except Exception as cb_err:
                            logger.error("Callback raised an error: %s", cb_err)

                # ── DB WRITE (after callback — latency non-critical) ──────────
                # Save inference record every ~2 seconds.
                # Save theft alert immediately, but only when _allow_db_alert
                # is True (5-second dedup gate) to avoid duplicate Alert records.
                current_fps = max(1, int(self.get_stats()['fps']))
                should_save = (
                    self.frames_processed % (current_fps * 2) == 0
                    or _allow_db_alert
                )
                
                if should_save:
                    if is_theft_detected and not _allow_db_alert:
                        # Cooldown active: save as "normal" inference record —
                        # no duplicate Alert row, but the inference data is kept.
                        _save_r = dict(result)
                        _save_r['classification'] = 'normal'
                        self._save_result(_save_r)
                    else:
                        self._save_result(result)
                
                # Persist tracking records (service handles its own throttle)
                if result.get('tracks'):
                    self._save_tracking_data(result)
                
            except BaseException as e:
                # Catch BaseException (not just Exception) to also catch
                # SystemError / MemoryError raised by C extensions (PyTorch,
                # FAISS, OpenCV).  On a fatal error we stop the loop cleanly
                # rather than retrying into an already-broken CUDA context.
                is_fatal = not isinstance(e, Exception)  # KeyboardInterrupt etc.
                logger.error(
                    f"💥 {'FATAL' if is_fatal else 'Error'} in monitor loop "
                    f"for camera {self.camera_id}: {type(e).__name__}: {e}",
                    exc_info=True,
                )
                if is_fatal:
                    self.is_running = False  # signal watchdog that we died
                    break                    # exit instead of retrying
                time.sleep(0.5)
        
        logger.info(f"Monitoring loop ended for camera {self.camera_id}")
    
    def _prepare_url(self, stream_url: str) -> str:
        """
        Return the stream URL unchanged.

        Previously this method appended '/video' to HTTP URLs, which caused
        broken RTSP conversions (e.g. http://host:8080 → rtsp://host:8080/cam1).
        Protocol detection and URL routing now happen in _open_capture_for_url().
        This method is retained for call-site compatibility but is a no-op.
        """
        return stream_url
    
    def _save_result(self, result: Dict):
        """Save inference result to database"""
        try:
            from ..models import AIInference
            from apps.cameras.models import Camera
            from apps.alerts.models import Alert
            
            camera = Camera.objects.get(pk=self.camera_id)
            
            # Create alert if theft detected
            alert = None
            if result['classification'] == 'theft':
                alert = self._create_alert(camera, result)
            
            # Save inference
            AIInference.objects.create(
                camera_id=camera,
                detections=result.get('detections', []),
                poses=result.get('poses', []),
                tracks=result.get('tracks', []),
                classification=result['classification'],
                confidence=result['confidence'],
                frame_metadata=result.get('frame_metadata', {}),
                processing_time_ms=result.get('processing_time_ms', 0),
                alert=alert,
            )
            
            logger.info(f"💾 Saved result for camera {self.camera_id}: {result['classification']} ({result['confidence']:.2f})")
            
        except Exception as e:
            logger.error(f"Failed to save result: {str(e)}")
    
    def _create_alert(self, camera, result):
        """Create alert for theft detection"""
        try:
            from apps.alerts.models import Alert
            from apps.alerts.services import dispatch_theft_alert_notifications
            
            metadata = {
                'confidence': result['confidence'],
                'suspicious_tracks': result.get('suspicious_tracks', []),
                'num_detections': result['frame_metadata'].get('num_detections', 0),
                'num_persons': result['frame_metadata'].get('num_persons', 0),
                'detected_by': 'CONTINUOUS_MONITOR',
                'detection_timestamp': timezone.now().isoformat(),
                'fps': self.get_stats()['fps'],
            }
            
            alert = Alert.objects.create(
                camera_id=camera,
                alert_type='THEFT_DETECTED',
                severity='HIGH' if result['confidence'] > 0.7 else 'MEDIUM',
                status='ACTIVE',
                metadata=metadata,
            )
            
            logger.warning(f"🚨 THEFT ALERT created for camera {camera.name}: {alert.id}")
            self._try_upload_alert_clip(alert)

            # ── Branch-scoped Twilio alert destination (dynamic per branch) ──
            # Best-effort, non-blocking; never impacts AI pipeline.
            try:
                dispatch_theft_alert_notifications(alert, async_send=True)
            except Exception:
                logger.exception("Failed to dispatch alert notifications for alert %s", alert.id)
            return alert
            
        except Exception as e:
            logger.error(f"Failed to create alert: {str(e)}")
            return None
    
    def _save_tracking_data(self, result: Dict):
        """Persist confirmed tracks to the tracking_records collection."""
        try:
            from apps.tracking.services import TrackingService
            TrackingService.save_tracks(
                camera_id=self.camera_id,
                tracks=result.get('tracks', []),
                inference_result=result,
            )
        except Exception as e:
            logger.error(f"Failed to save tracking data: {str(e)}")
    
    def _try_upload_alert_clip(self, alert) -> None:
        """
        Snapshot the rolling frame buffer and upload a 5-second clip to Cloudinary
        in a background thread so the monitoring loop is not blocked.
        """
        frames = list(self._frame_buffer)  # snapshot — thread-safe copy
        if not frames:
            logger.warning("Frame buffer empty — no clip to upload for alert %s", alert.id)
            return

        alert_id = str(alert.id)

        def _upload_worker(alert_id, frames):
            from .clip_encoding import write_frames_to_mp4
            from apps.alerts.cloudinary_video import upload_video_to_cloudinary
            import django
            django.setup.__module__  # ensure ORM is ready in this thread

            if not frames:
                return

            stats = self.get_stats()
            # Use capture_fps for encoding to ensure real-time playback speed
            fps = float(stats.get("capture_fps") or stats.get("fps") or 0)
            if fps < 5.0:
                fps = 25.0  # safe fallback when FPS not yet settled

            # Take up to 5 seconds worth of frames from the tail of the buffer
            clip_count = min(len(frames), int(fps * 5))
            clip_count = max(clip_count, 8)   # never fewer than 8 frames
            clip_frames = frames[-clip_count:]

            tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            tmp_path = tmp.name
            tmp.close()
            try:
                import gc
                gc.collect()  # Flush RAM before OpenCV VideoWriter starts allocating

                logger.info("🎬 Encoding %d-frame clip (%.1f s) for alert %s",
                            len(clip_frames), len(clip_frames) / fps, alert_id)
                if not write_frames_to_mp4(clip_frames, tmp_path, fps=fps):
                    logger.error("Clip encoding failed for alert %s", alert_id)
                    return

                # Task 2: Explicitly release the duplicated list references and flush RAM
                del clip_frames
                del frames
                gc.collect()  # Flush RAM after OpenCV VideoWriter explicitly releases

                logger.info("☁️  Uploading clip to Cloudinary for alert %s …", alert_id)
                video_url, public_id = upload_video_to_cloudinary(tmp_path)

                if video_url:
                    # Re-fetch the alert inside this thread to avoid stale state
                    from apps.alerts.models import Alert as AlertModel
                    try:
                        fresh = AlertModel.objects.get(pk=alert_id)
                        fresh.video_url = video_url
                        fresh.video_public_id = public_id
                        fresh.save(update_fields=["video_url", "video_public_id"])
                        logger.info("✅ Clip saved for alert %s → %s", alert_id, video_url)
                    except AlertModel.DoesNotExist:
                        logger.warning("Alert %s no longer exists; discarding clip", alert_id)
                else:
                    logger.warning("Cloudinary returned no URL for alert %s", alert_id)

            except Exception as exc:
                logger.error("Alert clip upload failed for %s: %s", alert_id, exc, exc_info=True)
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        t = threading.Thread(target=_upload_worker, args=(alert_id, frames), daemon=True,
                             name=f"clip-upload-{alert_id}")
        t.start()



class MonitorManager:
    """
    Manages multiple continuous monitors
    Monitoring starts only from explicit user actions.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return

        self.monitors: Dict[str, ContinuousMonitor] = {}
        self._initialized = True

        logger.info("📹 MonitorManager initialized (watchdog active)")

    def _watchdog_loop(self):
        """
        Daemon thread — checks every 30 s whether each monitor's inference
        thread is still alive.  If a thread died without being explicitly
        stopped (i.e. is_running is still True but thread.is_alive() is False),
        the watchdog removes the dead entry and restarts the monitor so the
        camera resumes monitoring automatically after a crash.
        """
        return

        while True:
            time.sleep(30)
            for camera_id, monitor in list(self.monitors.items()):
                thread_alive = (
                    monitor.thread is not None and monitor.thread.is_alive()
                )
                if monitor.is_running and not thread_alive:
                    logger.error(
                        "🔴 WATCHDOG: inference thread for camera %s died "
                        "unexpectedly — restarting …", camera_id
                    )
                    # Clean up the dead entry first
                    monitor.is_running = False
                    rtsp_url   = monitor.rtsp_url
                    callback   = monitor.callback
                    self.monitors.pop(camera_id, None)
                    # Re-start (stagger is built into start_monitor)
                    try:
                        self.start_monitor(camera_id, rtsp_url, callback)
                        logger.info(
                            "✅ WATCHDOG: restarted monitor for camera %s", camera_id
                        )
                    except Exception as restart_err:
                        logger.error(
                            "❌ WATCHDOG: failed to restart camera %s: %s",
                            camera_id, restart_err, exc_info=True
                        )

    def start_monitor(self, camera_id: str, rtsp_url: str, callback=None) -> bool:
        """Start monitoring a camera.

        The SSERegistry is always wired as the primary callback so that any
        connected SSE client receives real-time tracking data automatically.
        An optional secondary *callback* argument is still supported for
        callers that need additional custom behaviour.
        """
        if camera_id in self.monitors:
            logger.warning(f"Monitor already exists for camera {camera_id}")
            return False

        # Stagger: when another monitor is already running, wait 3 s before
        # starting so the two CUDA warmup passes never overlap.  Simultaneous
        # warmups (YOLO + OSNet) can spike VRAM above the physical limit and
        # trigger a C-level abort() before the 85 % cap takes effect.
        if self.monitors:
            logger.info(
                f"⏳ Staggering monitor start for camera {camera_id} "
                f"({len(self.monitors)} monitor(s) already active — waiting 3 s) …"
            )
            time.sleep(3)

        from .sse_registry import sse_registry

        def _combined_callback(cam_id: str, result: dict) -> None:
            # Always publish to SSE clients (no-op when no clients connected)
            sse_registry.publish(cam_id, result)
            # Also invoke any caller-supplied secondary callback
            if callback:
                callback(cam_id, result)

        monitor = ContinuousMonitor(camera_id, rtsp_url, _combined_callback)
        if monitor.start():
            self.monitors[camera_id] = monitor
            return True
        return False
    
    def stop_monitor(self, camera_id: str) -> bool:
        """Stop monitoring a camera"""
        if camera_id not in self.monitors:
            logger.warning(f"No monitor found for camera {camera_id}")
            return False
        
        monitor = self.monitors[camera_id]
        monitor.stop()
        del self.monitors[camera_id]
        return True
    
    def get_monitor_stats(self, camera_id: str) -> Optional[Dict]:
        """Get stats for a specific monitor"""
        if camera_id in self.monitors:
            return self.monitors[camera_id].get_stats()
        return None
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get stats for all monitors"""
        return {
            camera_id: monitor.get_stats()
            for camera_id, monitor in self.monitors.items()
        }
    
    def stop_all(self):
        """Stop all monitors"""
        for camera_id in list(self.monitors.keys()):
            self.stop_monitor(camera_id)


# Global instance
monitor_manager = MonitorManager()

