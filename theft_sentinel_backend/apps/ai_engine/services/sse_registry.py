"""
SSE (Server-Sent Events) Registry

Thread-safe publish/subscribe broker for real-time tracking data.

The ContinuousMonitor callback calls publish(); SSE view handlers call
subscribe() to register a per-request queue and unsubscribe() when the
client disconnects.
"""
import json
import queue
import threading
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class SSERegistry:
    """
    Per-camera fan-out queue for SSE clients.

    Designed to be called from multiple threads simultaneously:
      - publish()      — called from the ContinuousMonitor background thread
      - subscribe()    — called from Django HTTP worker threads
      - unsubscribe()  — called from Django HTTP worker threads (on disconnect)
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # camera_id (str) → list of per-client queues
        self._subscribers: Dict[str, List[queue.Queue]] = {}

    # ── public API ────────────────────────────────────────────────────────────

    def subscribe(self, camera_id: str) -> queue.Queue:
        """
        Register a new SSE client for camera_id.

        Returns a Queue that will receive serialised JSON strings (already
        formatted as SSE data lines).  maxsize=10 keeps memory bounded; slow
        clients simply lose frames (same as MJPEG streams).
        """
        q: queue.Queue = queue.Queue(maxsize=10)
        with self._lock:
            self._subscribers.setdefault(str(camera_id), []).append(q)
        logger.debug("SSE: client subscribed  camera=%s  total=%d",
                     camera_id, self.subscriber_count(camera_id))
        return q

    def unsubscribe(self, camera_id: str, q: queue.Queue) -> None:
        """Remove a client queue from the registry (called on disconnect)."""
        with self._lock:
            bucket = self._subscribers.get(str(camera_id), [])
            try:
                bucket.remove(q)
            except ValueError:
                pass
        logger.debug("SSE: client unsubscribed camera=%s  total=%d",
                     camera_id, self.subscriber_count(camera_id))

    def publish(self, camera_id: str, result: dict) -> None:
        """
        Push a tracking result to every subscriber of camera_id.

        Called from the ContinuousMonitor background thread at up to 10 FPS.
        The payload is stripped down to the minimum the frontend needs so we
        keep JSON packets small (typically < 2 KB even with 10 tracks).
        """
        with self._lock:
            bucket = list(self._subscribers.get(str(camera_id), []))

        if not bucket:
            return  # no clients connected — exit fast

        payload = _build_payload(camera_id, result)
        line = f"data: {json.dumps(payload)}\n\n"

        dead: List[queue.Queue] = []
        for q in bucket:
            try:
                q.put_nowait(line)
            except queue.Full:
                # Slow / disconnected client — mark for eviction
                dead.append(q)

        if dead:
            with self._lock:
                bucket2 = self._subscribers.get(str(camera_id), [])
                for q in dead:
                    try:
                        bucket2.remove(q)
                    except ValueError:
                        pass

    def subscriber_count(self, camera_id: str) -> int:
        """Return the number of active SSE clients for a camera."""
        with self._lock:
            return len(self._subscribers.get(str(camera_id), []))

    def has_subscribers(self, camera_id: str) -> bool:
        return self.subscriber_count(camera_id) > 0

    def close_camera(self, camera_id: str) -> bool:
        """Close and remove every SSE subscriber for a deleted/stopped camera."""
        with self._lock:
            bucket = self._subscribers.pop(str(camera_id), [])

        for q in bucket:
            try:
                q.put_nowait(None)
            except queue.Full:
                pass

        if bucket:
            logger.info("SSE: closed %d subscriber(s) for camera=%s", len(bucket), camera_id)
        return bool(bucket)


# ── helpers ───────────────────────────────────────────────────────────────────

def _build_payload(camera_id: str, result: dict) -> dict:
    """
    Extract only the fields the frontend canvas overlay needs.

    Keeping the payload small is important: at 10 FPS with 5 tracks, this
    is ~1–2 KB/s per connected client — negligible on DigitalOcean bandwidth.
    """
    tracks_out = []
    for t in result.get("tracks", []):
        tracks_out.append({
            "track_id":  t.get("track_id"),
            "global_id": t.get("global_id"),
            "bbox":      t.get("bbox", [0, 0, 0, 0]),
            "x3d_score": round(float(t.get("x3d_score", 0.0)), 4),
            "confidence": round(float(t.get("confidence", 0.0)), 4),
            "is_suspicious": t.get("is_suspicious", False),
        })

    suspicious_ids = {
        t.get("track_id")
        for t in result.get("suspicious_tracks", [])
    }

    return {
        "camera_id":         str(camera_id),
        "timestamp":         result.get("timestamp"),
        "frame_width":       result.get("frame_width", 640),
        "frame_height":      result.get("frame_height", 480),
        "tracks":            tracks_out,
        "suspicious_ids":    list(suspicious_ids),
        "alert_triggered":   result.get("classification") == "theft",
        "classification":    result.get("classification", "normal"),
        "confidence":        round(float(result.get("confidence", 0.0)), 4),
    }


# Global singleton — imported by continuous_monitor and SSE views
sse_registry = SSERegistry()
