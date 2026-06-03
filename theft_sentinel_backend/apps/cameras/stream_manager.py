"""
CameraStreamManager  —  Dual-Protocol Persistent Stream Architecture
======================================================================
Maintains ONE persistent cv2.VideoCapture per camera, chosen based on the
actual URL scheme stored in the database:

    HTTP/HTTPS  → cv2.VideoCapture(url)          — IP Webcam / DroidCam
    RTSP/RTSPS  → cv2.VideoCapture(url, CAP_FFMPEG) — MediaMTX VPS

A dedicated daemon reader thread continuously grabs frames and stores only
the *latest* one in memory.  All MJPEG/API clients read from this shared
frame cache — no new connections are ever opened per HTTP request.

Architecture:
    Phone/Camera Source
        ↓
    [HTTP MJPEG]  or  [RTSP via MediaMTX]
        ↓
    CameraStream  (one persistent VideoCapture, daemon reader thread)
        ↓
    Shared latest-frame cache  (thread-safe lock)
        ↓
    Multiple MJPEG / SSE / API clients  (read-only)

Key behaviours:
  • Protocol is detected from the URL scheme — never mutated.
  • OPENCV_FFMPEG_CAPTURE_OPTIONS is applied ONLY to RTSP streams.
  • isOpened() is ALWAYS checked before getBackendName().
  • Exponential back-off on reconnect: 2→4→8→16→30s max.
  • Old VideoCapture is always released before creating a new one.
  • One reconnect attempt at a time — no parallel reconnect storms.
  • Clean daemon-thread shutdown with a short join timeout.
"""

from __future__ import annotations

import cv2
import threading
import time
import logging
import os
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import numpy as np

from .mjpeg_capture import MJPEGCapture

logger = logging.getLogger(__name__)

# ── Tuning constants ────────────────────────────────────────────────────────

# Consecutive read failures before triggering a reconnect
_MAX_CONSECUTIVE_FAILURES: int = 15

# Exponential back-off: delay = min(2**attempt, _MAX_BACKOFF_S)
_INITIAL_BACKOFF_S: float = 2.0
_MAX_BACKOFF_S: float = 30.0

# Warn if no fresh frame arrives for this many seconds
_STALE_WARN_S: float = 3.0

# MJPEG encode quality (1-100)
_JPEG_QUALITY: int = 75

# Thread join timeout — must be shorter than the connection open timeout so
# that stop() does not block forever when the reader is stuck waiting on TCP.
_JOIN_TIMEOUT_S: float = 4.0


# ── Protocol detection ──────────────────────────────────────────────────────

def _detect_protocol(url: str) -> str:
    """
    Return the lowercase URL scheme for the given stream URL.

    Examples:
        'http://192.168.10.3:8080/video' → 'http'
        'rtsp://157.245.111.63:8554/cam2' → 'rtsp'
    """
    parsed = urlparse(url)
    return parsed.scheme.lower()


def _is_rtsp(url: str) -> bool:
    return _detect_protocol(url) in ("rtsp", "rtsps")


def _is_http(url: str) -> bool:
    return _detect_protocol(url) in ("http", "https")


# ── Backoff helper ──────────────────────────────────────────────────────────

def _backoff(attempt: int) -> float:
    """Exponential backoff capped at _MAX_BACKOFF_S."""
    return min(_INITIAL_BACKOFF_S ** attempt, _MAX_BACKOFF_S)


# ── Per-camera stream object ────────────────────────────────────────────────

class CameraStream:
    """
    ONE persistent video stream connection for a single camera.

    • The URL stored in the database is used AS-IS — never mutated.
    • Protocol (RTSP vs HTTP) is detected dynamically from the URL scheme.
    • A single daemon thread calls cap.read() in a tight loop.
    • Exponential back-off prevents reconnect storms.
    • All public methods are thread-safe.
    """

    def __init__(self, camera_id: str, stream_url: str) -> None:
        self.camera_id = camera_id
        self.stream_url = stream_url           # raw DB value, never changed
        self._protocol = _detect_protocol(stream_url)

        # Shared frame state — guarded by _lock
        self._lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._frame_timestamp: float = 0.0

        # Lifecycle
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Diagnostics (read from any thread; minor races are acceptable)
        self._total_frames: int = 0
        self._reconnect_count: int = 0
        self._consecutive_failures: int = 0
        self._stream_open: bool = False

    # ── Public API ──────────────────────────────────────────────────────────

    def start(self) -> bool:
        """Start the background reader thread. Idempotent."""
        if self._running:
            logger.warning(
                "[CameraStream] Already running for camera %s", self.camera_id
            )
            return True

        self._running = True
        self._thread = threading.Thread(
            target=self._reader_loop,
            daemon=True,
            name=f"cam-reader-{self.camera_id[:8]}",
        )
        self._thread.start()
        logger.info(
            "[CameraStream] Started camera %s | protocol=%s | url=%s",
            self.camera_id, self._protocol, self.stream_url,
        )
        return True

    def stop(self) -> None:
        """Signal the reader thread to stop and wait briefly for it."""
        self._running = False
        if self._thread and self._thread.is_alive():
            # Use a short join so atexit / shutdown does not hang.
            self._thread.join(timeout=_JOIN_TIMEOUT_S)
            if self._thread.is_alive():
                logger.warning(
                    "[CameraStream] Reader thread for camera %s still alive after "
                    "%.1fs — proceeding with shutdown",
                    self.camera_id, _JOIN_TIMEOUT_S,
                )
        logger.info("[CameraStream] Stopped camera %s", self.camera_id)

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Return a copy of the most recently decoded frame, or None."""
        with self._lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None

    def get_frame_snapshot(self) -> Tuple[Optional[np.ndarray], float]:
        """
        Return (frame_copy, timestamp) atomically.

        Used by ContinuousMonitor to detect new frames without opening a
        second connection to the camera source.  Returns (None, 0.0) if no
        frame has been captured yet.
        """
        with self._lock:
            if self._latest_frame is None:
                return None, 0.0
            return self._latest_frame.copy(), self._frame_timestamp

    def get_latest_frame_age(self) -> float:
        """How many seconds ago the latest frame was captured (∞ if none)."""
        with self._lock:
            if self._frame_timestamp == 0.0:
                return float("inf")
            return time.time() - self._frame_timestamp

    def is_alive(self) -> bool:
        """True if the reader thread exists and is still running."""
        return (
            self._running
            and self._thread is not None
            and self._thread.is_alive()
        )

    def get_stats(self) -> Dict:
        with self._lock:
            age = (
                round(time.time() - self._frame_timestamp, 2)
                if self._frame_timestamp
                else None
            )
        return {
            "camera_id": self.camera_id,
            "protocol": self._protocol,
            "stream_url": self.stream_url,
            "is_running": self._running,
            "stream_open": self._stream_open,
            "total_frames": self._total_frames,
            "reconnect_count": self._reconnect_count,
            "latest_frame_age_s": age,
        }

    # ── VideoCapture factory ────────────────────────────────────────────────

    def _open_capture(self) -> Optional[cv2.VideoCapture]:
        """
        Open a VideoCapture appropriate for the URL scheme.

        RTSP  → cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                 OPENCV_FFMPEG_CAPTURE_OPTIONS (set in ai_engine/apps.py) applies.

        HTTP  → cv2.VideoCapture(url)
                 Plain OpenCV auto-select; FFmpeg RTSP options are NOT applied
                 (they would break HTTP streams).

        ALWAYS checks isOpened() before getBackendName().
        Returns ready VideoCapture on success, None on failure.
        """
        url = self.stream_url

        if _is_rtsp(url):
            logger.info(
                "[CameraStream] Opening RTSP stream for camera %s → %s",
                self.camera_id, url,
            )
            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)

        elif _is_http(url):
            logger.info(
                "[CameraStream] Opening HTTP stream for camera %s → %s",
                self.camera_id, url,
            )
            # Use MJPEGCapture instead of cv2.VideoCapture for HTTP streams.
            # DroidCam requires User-Agent: DroidCam/1.0 (sent by MJPEGCapture).
            # cv2.VideoCapture cannot set custom headers and receives DroidCam's
            # HTML web-player page instead of the MJPEG stream.
            # MJPEGCapture exposes the same read()/release()/isOpened() interface
            # so the rest of _reader_loop works unchanged.
            cap = MJPEGCapture(url)

        else:
            logger.error(
                "[CameraStream] Unsupported protocol '%s' for camera %s: %s",
                self._protocol, self.camera_id, url,
            )
            return None

        # ── CRITICAL: isOpened() BEFORE getBackendName() ──────────────────
        # getBackendName() internally asserts `api != 0`.  On a failed open
        # that assertion fires and crashes the process with:
        #   cv2.error: (-215:Assertion failed) api != 0 in getBackendName
        if not cap.isOpened():
            logger.error(
                "[CameraStream] Failed to open %s stream for camera %s: %s",
                self._protocol.upper(), self.camera_id, url,
            )
            cap.release()
            return None

        # Safe to query backend only after isOpened() returned True
        backend = cap.getBackendName()
        logger.info(
            "[CameraStream] Stream open for camera %s | backend=%s | protocol=%s",
            self.camera_id, backend, self._protocol,
        )

        if _is_rtsp(url) and backend != "FFMPEG":
            logger.warning(
                "[CameraStream] Non-FFmpeg backend '%s' for RTSP camera %s — "
                "OPENCV_FFMPEG_CAPTURE_OPTIONS may not apply (TCP may be used)",
                backend, self.camera_id,
            )

        # Minimise decode buffer to reduce latency for both protocols
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self._stream_open = True
        return cap

    # ── Reader loop ─────────────────────────────────────────────────────────

    def _reader_loop(self) -> None:
        """
        Main daemon thread loop.

        • Opens the stream once per connection lifetime.
        • On read failure: increments consecutive_failures counter.
        • After _MAX_CONSECUTIVE_FAILURES: releases cap, waits with
          exponential back-off, then reopens.
        • Stores only the latest frame — no queue accumulation.
        • Exits cleanly when self._running is set to False.
        """
        cap: Optional[cv2.VideoCapture] = None
        reconnect_attempt: int = 0      # resets to 0 after a successful connection
        last_stale_log: float = 0.0

        while self._running:

            # ── Open / reopen connection ────────────────────────────────────
            if cap is None:
                delay = _backoff(reconnect_attempt)
                if reconnect_attempt > 0:
                    self._reconnect_count += 1
                    logger.warning(
                        "[CameraStream] Reconnect #%d for camera %s in %.1fs "
                        "(backoff attempt %d)",
                        self._reconnect_count, self.camera_id,
                        delay, reconnect_attempt,
                    )
                    time.sleep(delay)

                cap = self._open_capture()

                if cap is None:
                    # Connection failed → increment attempt, stay in backoff loop
                    self._stream_open = False
                    reconnect_attempt += 1
                    continue

                # Connected successfully → reset backoff counter
                reconnect_attempt = 0
                self._consecutive_failures = 0
                logger.info(
                    "[CameraStream] Connected to camera %s (protocol=%s)",
                    self.camera_id, self._protocol,
                )

            # ── Read one frame ──────────────────────────────────────────────
            try:
                ret, raw_frame = cap.read()
            except Exception as exc:
                logger.error(
                    "[CameraStream] Exception in cap.read() for camera %s: %s",
                    self.camera_id, exc, exc_info=True,
                )
                # Release and trigger reconnect
                cap.release()
                cap = None
                self._stream_open = False
                reconnect_attempt += 1
                continue

            if not ret or raw_frame is None or raw_frame.size == 0:
                self._consecutive_failures += 1

                now = time.time()
                if now - last_stale_log >= _STALE_WARN_S:
                    logger.warning(
                        "[CameraStream] Stale/empty frame for camera %s "
                        "(consecutive_failures=%d)",
                        self.camera_id, self._consecutive_failures,
                    )
                    last_stale_log = now

                if self._consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                    logger.warning(
                        "[CameraStream] Triggering reconnect for camera %s "
                        "after %d consecutive read failures",
                        self.camera_id, self._consecutive_failures,
                    )
                    # ── Release old capture BEFORE creating a new one ───────
                    cap.release()
                    cap = None
                    self._stream_open = False
                    self._consecutive_failures = 0
                    reconnect_attempt += 1
                    # Back-off sleep happens at the top of the loop

                continue

            # ── Successful frame ────────────────────────────────────────────
            self._consecutive_failures = 0
            reconnect_attempt = 0   # keep reset so backoff stays at minimum
            self._total_frames += 1

            # Downscale to 640×480 for consistent memory footprint
            frame = cv2.resize(raw_frame, (640, 480))
            del raw_frame  # free the potentially large original immediately

            with self._lock:
                self._latest_frame = frame
                self._frame_timestamp = time.time()

        # ── Clean up on exit ────────────────────────────────────────────────
        if cap is not None:
            cap.release()
            cap = None
            self._stream_open = False
            logger.info(
                "[CameraStream] Released capture for camera %s", self.camera_id
            )


# ── Singleton manager ───────────────────────────────────────────────────────

class CameraStreamManager:
    """
    Singleton registry of CameraStream objects.

    Guarantees ONE persistent connection per camera regardless of how many
    frontend clients request the same feed simultaneously.

    Usage:
        from apps.cameras.stream_manager import stream_manager
        frame = stream_manager.get_or_create(camera_id, url).get_latest_frame()
    """

    _instance: Optional["CameraStreamManager"] = None
    _instance_lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        self._streams: Dict[str, CameraStream] = {}
        self._lock = threading.Lock()
        logger.info("[StreamManager] CameraStreamManager initialized")

    @classmethod
    def get_instance(cls) -> "CameraStreamManager":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ── Stream lifecycle ────────────────────────────────────────────────────

    def get_or_create(self, camera_id: str, stream_url: str) -> CameraStream:
        """
        Return the existing live CameraStream for *camera_id*, or create and
        start a new one.  Thread-safe — safe to call from concurrent requests.

        The *stream_url* is used AS-IS from the database; this method never
        mutates or converts it.
        """
        with self._lock:
            stream = self._streams.get(camera_id)

            if stream is not None and stream.is_alive():
                return stream

            # Dead or missing stream — (re)create
            if stream is not None:
                logger.warning(
                    "[StreamManager] Dead stream for camera %s — recreating",
                    camera_id,
                )
                stream.stop()

            stream = CameraStream(camera_id, stream_url)
            stream.start()
            self._streams[camera_id] = stream
            logger.info(
                "[StreamManager] Created stream for camera %s | protocol=%s",
                camera_id, _detect_protocol(stream_url),
            )
            return stream

    def get_stream(self, camera_id: str) -> Optional[CameraStream]:
        """Return the stream for *camera_id* if it exists, else None."""
        with self._lock:
            return self._streams.get(camera_id)

    def stop_stream(self, camera_id: str) -> bool:
        """Stop and remove the stream for *camera_id*."""
        with self._lock:
            stream = self._streams.pop(camera_id, None)
        if stream is None:
            return False
        stream.stop()
        logger.info("[StreamManager] Stream stopped for camera %s", camera_id)
        return True

    def stop_all(self) -> None:
        """Stop all managed streams (called on server shutdown via atexit)."""
        with self._lock:
            ids = list(self._streams.keys())
        for camera_id in ids:
            self.stop_stream(camera_id)
        logger.info("[StreamManager] All streams stopped")

    def get_all_stats(self) -> Dict[str, Dict]:
        """Return diagnostic stats for every managed stream."""
        with self._lock:
            streams = dict(self._streams)
        return {cid: s.get_stats() for cid, s in streams.items()}

    # ── MJPEG frame generator ───────────────────────────────────────────────

    def mjpeg_frame_generator(
        self,
        camera_id: str,
        stream_url: str,
        target_fps: float = 25.0,
    ):
        """
        Generator yielding multipart MJPEG boundary frames for
        StreamingHttpResponse.

        Uses the shared CameraStream — no new VideoCapture is opened per
        HTTP client.  Throttles to *target_fps* to avoid flooding slow clients.
        """
        stream = self.get_or_create(camera_id, stream_url)
        frame_interval = 1.0 / max(target_fps, 1.0)
        last_yield = 0.0
        no_frame_warned = False

        while True:
            now = time.time()

            # Throttle to target FPS
            wait = frame_interval - (now - last_yield)
            if wait > 0:
                time.sleep(wait)
                continue

            frame = stream.get_latest_frame()

            if frame is None:
                if not no_frame_warned:
                    logger.warning(
                        "[StreamManager] No frame yet for camera %s — waiting",
                        camera_id,
                    )
                    no_frame_warned = True
                time.sleep(0.05)
                continue

            no_frame_warned = False

            ret, buf = cv2.imencode(
                ".jpg",
                frame,
                [cv2.IMWRITE_JPEG_QUALITY, _JPEG_QUALITY, cv2.IMWRITE_JPEG_OPTIMIZE, 1],
            )
            if not ret:
                continue

            last_yield = time.time()
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
            )


# Module-level singleton
stream_manager = CameraStreamManager.get_instance()
