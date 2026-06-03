"""
Camera Feed Health Services

Observes feed availability WITHOUT modifying camera activation state.
Camera ONLINE/OFFLINE is controlled only by explicit user actions.

Dual-protocol:
  HTTP/HTTPS  → tested via requests.get()          (no OpenCV)
  RTSP/RTSPS  → tested via cv2.VideoCapture + read (CAP_FFMPEG)

URL is NEVER mutated — used exactly as stored in the database.

HARD 5-SECOND SLA: All cameras must be checked within 5 seconds total.
Uses parallel execution to ensure no single camera blocks others.
"""
import logging
import os
import cv2
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
from django.utils import timezone
from .models import Camera

logger = logging.getLogger(__name__)

# Hard 5-second SLA for the whole batch
MAX_TOTAL_CHECK_TIME_SECONDS = 5.0

# Per-camera timeout — must be well under the batch SLA
PER_CAMERA_TIMEOUT_SECONDS = 2.0


# ── Protocol helpers ────────────────────────────────────────────────────────

def _scheme(url: str) -> str:
    return urlparse(url).scheme.lower()


def _is_rtsp(url: str) -> bool:
    return _scheme(url) in ("rtsp", "rtsps")


def _is_http(url: str) -> bool:
    return _scheme(url) in ("http", "https")


# ── Per-protocol testers ────────────────────────────────────────────────────

def _test_http_feed(stream_url: str, timeout_s: float) -> bool:
    """
    Test an HTTP/HTTPS stream by sending a HEAD/GET request.
    Returns True if a 200 response with a media content-type is received.
    URL is used AS-IS — no endpoint suffix is added automatically.
    """
    try:
        # Try the stored URL first, then common video endpoint suffixes
        candidates = [stream_url]
        # Only append /video if the URL has no path segment beyond the port
        parsed = urlparse(stream_url)
        if not parsed.path or parsed.path == "/":
            candidates.append(stream_url.rstrip("/"))

        for url in candidates:
            try:
                resp = requests.get(url, stream=True, timeout=timeout_s)
                if resp.status_code == 200:
                    ct = resp.headers.get("Content-Type", "")
                    if any(t in ct for t in ("multipart", "image", "video")):
                        logger.debug(
                            "[health] HTTP feed LIVE: camera url=%s ct=%s", url, ct
                        )
                        return True
            except requests.exceptions.RequestException:
                continue
    except Exception as exc:
        logger.debug("[health] HTTP feed test error: %s", exc)
    return False


def _test_rtsp_feed(stream_url: str, timeout_s: float) -> bool:
    """
    Test an RTSP stream by opening it with CAP_FFMPEG and reading one frame.
    URL is used AS-IS — never converted or extended.

    isOpened() is ALWAYS checked before getBackendName().
    """
    timeout_ms = int(timeout_s * 1000)
    cap = None
    try:
        cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_ms)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout_ms)

        # ── CRITICAL: isOpened() BEFORE getBackendName() ───────────────────
        if not cap.isOpened():
            logger.debug("[health] RTSP feed DEAD (could not open): %s", stream_url)
            return False

        # Safe to call getBackendName() only after isOpened()
        backend = cap.getBackendName()
        if backend != "FFMPEG":
            logger.warning(
                "[health] Non-FFmpeg backend '%s' for RTSP health probe: %s",
                backend, stream_url,
            )

        ret, frame = cap.read()
        if ret and frame is not None and frame.size > 0:
            logger.debug("[health] RTSP feed LIVE: %s", stream_url)
            return True
        logger.debug("[health] RTSP feed DEAD (no frame): %s", stream_url)
        return False

    except Exception as exc:
        logger.debug("[health] RTSP feed test exception for %s: %s", stream_url, exc)
        return False
    finally:
        if cap is not None:
            cap.release()


# ── Public interface ────────────────────────────────────────────────────────

def test_camera_feed(camera) -> bool:
    """
    Test whether a camera's feed is reachable and returning data.

    Routes to the correct protocol tester based on the URL scheme.
    The URL is used exactly as stored — NEVER mutated.
    """
    stream_url = camera.rtsp_url  # field name is legacy; may hold any URL
    timeout = PER_CAMERA_TIMEOUT_SECONDS

    if _is_http(stream_url):
        return _test_http_feed(stream_url, timeout)

    if _is_rtsp(stream_url):
        return _test_rtsp_feed(stream_url, timeout)

    logger.warning(
        "[health] Unknown protocol for camera %s: %s", camera.name, stream_url
    )
    return False


def update_camera_status_from_feed(camera) -> bool:
    """
    Read-only feed health probe.

    Returns True when the feed is reachable. This never changes camera.status;
    it may refresh last_feed_timestamp so dashboards can show recent health.
    """
    feed_live = test_camera_feed(camera)
    now = timezone.now()

    if feed_live:
        if hasattr(camera, "last_feed_timestamp"):
            camera.last_feed_timestamp = now
            camera.save(update_fields=["last_feed_timestamp"])
        return True

    logger.debug("[health] Camera %s feed unavailable; status unchanged", camera.name)
    return False


def check_all_camera_feeds() -> dict:
    """
    Check all cameras in parallel without changing camera status.
    Hard 5-second SLA for the entire batch.
    """
    start_time = time.time()
    now = timezone.now()

    cameras = list(Camera.objects.all())
    total = len(cameras)

    if total == 0:
        return {
            "checked": 0,
            "feeds_live": 0,
            "updated": 0,
            "timestamp": now,
            "elapsed_seconds": 0.0,
        }

    max_workers = min(total, 10)
    cameras_checked = 0
    feeds_live = 0

    def _check(cam):
        try:
            return update_camera_status_from_feed(cam)
        except Exception as exc:
            logger.error(
                "[health] Error checking camera %s: %s", cam.name, exc, exc_info=True
            )
            return False

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_check, cam): cam for cam in cameras}
        for future in as_completed(futures, timeout=MAX_TOTAL_CHECK_TIME_SECONDS):
            cam = futures[future]
            cameras_checked += 1
            try:
                if future.result(timeout=0.1):
                    feeds_live += 1
            except Exception as exc:
                logger.error(
                    "[health] Result error for camera %s: %s", cam.name, exc
                )

    elapsed = time.time() - start_time

    if cameras_checked < total:
        logger.warning(
            "[health] SLA exceeded: only %d/%d cameras checked in %.2fs",
            cameras_checked, total, elapsed,
        )

    stats = {
        "checked": cameras_checked,
        "feeds_live": feeds_live,
        "updated": 0,
        "timestamp": now,
        "elapsed_seconds": round(elapsed, 2),
    }

    if elapsed > MAX_TOTAL_CHECK_TIME_SECONDS:
        logger.warning(
            "[health] Batch check exceeded 5s SLA: %.2fs (%d/%d cameras)",
            elapsed, cameras_checked, total,
        )
    else:
        logger.debug(
            "[health] Batch check OK: %.2fs | %d cameras | %d feeds live",
            elapsed, cameras_checked, feeds_live,
        )

    return stats


def cleanup_camera_runtime(camera) -> dict:
    """
    Stop all in-process runtime state associated with a camera.

    Used before turning a camera off and before deleting it so no monitor or
    shared stream remains orphaned after the database row changes.
    """
    camera_id = str(getattr(camera, "id", camera))
    cleanup = {
        "camera_id": camera_id,
        "monitor_stopped": False,
        "stream_stopped": False,
        "sse_closed": False,
    }

    try:
        from apps.ai_engine.services.continuous_monitor import monitor_manager

        cleanup["monitor_stopped"] = bool(monitor_manager.stop_monitor(camera_id))
    except Exception:
        logger.exception("[cleanup] Failed to stop AI monitor for camera %s", camera_id)

    try:
        from .stream_manager import stream_manager

        cleanup["stream_stopped"] = bool(stream_manager.stop_stream(camera_id))
    except Exception:
        logger.exception("[cleanup] Failed to stop stream for camera %s", camera_id)

    try:
        from apps.ai_engine.services.sse_registry import sse_registry

        cleanup["sse_closed"] = bool(sse_registry.close_camera(camera_id))
    except Exception:
        logger.exception("[cleanup] Failed to close SSE subscribers for camera %s", camera_id)

    return cleanup
