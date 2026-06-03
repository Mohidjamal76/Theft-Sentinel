"""
Tracking Service — writes TrackingRecords from InferenceRunner results.

Called by ContinuousMonitor._save_tracking_data() after every inference
that yields confirmed tracks.  Records are throttled to one per
(person_id, camera_id) per TRACKING_SAVE_INTERVAL seconds to keep the
database lean.
"""

import logging
import threading
import time
from typing import Dict, List, Optional

from django.utils import timezone

logger = logging.getLogger(__name__)


# Minimum seconds between DB writes for the same (person_id, camera_id).
TRACKING_SAVE_INTERVAL = 5


class TrackingService:
    """
    Service for persisting person tracking data from the AI pipeline.

    Thread-safe — multiple ContinuousMonitor threads may call
    save_tracks() concurrently.
    """

    _lock = threading.Lock()
    # Throttle map: (person_id, camera_id_str) → last-save timestamp
    _last_saved: Dict[tuple, float] = {}

    # ── public API ────────────────────────────────────────────────────────────

    @classmethod
    def save_tracks(
        cls,
        camera_id: str,
        tracks: List[Dict],
        inference_result: Dict,
    ) -> int:
        """
        Persist confirmed tracks from one inference frame.

        Args:
            camera_id:        MongoDB Camera PK (string ObjectId).
            tracks:           The ``tracks`` list from InferenceRunner output.
                              Each entry has: track_id, global_id, bbox,
                              confidence, x3d_score.
            inference_result: Full inference dict (used for metadata).

        Returns:
            Number of TrackingRecords actually created (after throttling).
        """
        if not tracks:
            return 0

        from .models import TrackingRecord
        from apps.cameras.models import Camera

        try:
            camera = Camera.objects.get(pk=camera_id)
        except Camera.DoesNotExist:
            logger.warning("TrackingService: Camera %s not found — skipping", camera_id)
            return 0

        now = time.time()
        created = 0

        for track in tracks:
            global_id = track.get("global_id")
            person_id = f"GID_{global_id}" if global_id is not None else f"TRK_{track.get('track_id', '?')}"

            key = (person_id, str(camera_id))

            # ── throttle: one write per person per camera every N seconds ──
            with cls._lock:
                last = cls._last_saved.get(key, 0)
                if now - last < TRACKING_SAVE_INTERVAL:
                    continue
                cls._last_saved[key] = now

            try:
                TrackingRecord.objects.create(
                    person_id=person_id,
                    camera_id=camera,
                    confidence=float(track.get("confidence", 0.0)),
                    location=camera.location or '',
                    global_id=global_id,
                    x3d_score=track.get("x3d_score"),
                    bbox=track.get("bbox", []),
                    vector={},  # embeddings are large; store as empty for now
                )
                created += 1
            except Exception as exc:
                logger.error(
                    "TrackingService: Failed to create record for %s on cam %s: %s",
                    person_id, camera_id, exc,
                )

        if created:
            logger.debug(
                "TrackingService: Saved %d tracking records for camera %s",
                created, camera_id,
            )

        return created

    @classmethod
    def cleanup_throttle_cache(cls) -> None:
        """Remove stale entries from the throttle map (older than 5 minutes)."""
        cutoff = time.time() - 300
        with cls._lock:
            expired = [k for k, v in cls._last_saved.items() if v < cutoff]
            for k in expired:
                del cls._last_saved[k]

    # ── query helpers (used by views) ─────────────────────────────────────────

    @staticmethod
    def generate_person_id(vector_data) -> str:
        """
        Generate a person ID from a feature vector.
        
        For MVP, this is a simple hash.  In production it would do
        vector-similarity lookup against known identities.
        """
        import hashlib
        import json

        vector_str = json.dumps(vector_data, sort_keys=True)
        person_hash = hashlib.md5(vector_str.encode()).hexdigest()[:12]
        return f"PERSON_{person_hash}"

    @staticmethod
    def track_person_across_cameras(person_id: str, time_window_minutes: int = 60) -> list:
        """
        Build a chronological movement path for a person across cameras.

        Returns a list of dicts with camera info and timestamps, ordered
        oldest → newest.
        """
        from .models import TrackingRecord
        from datetime import timedelta

        time_threshold = timezone.now() - timedelta(minutes=time_window_minutes)

        records = (
            TrackingRecord.objects
            .filter(person_id=person_id, timestamp__gte=time_threshold)
            .select_related('camera_id')
            .order_by('timestamp')
        )

        tracking_path = []
        for record in records:
            tracking_path.append({
                'camera_id': str(record.camera_id.id),
                'camera_name': record.camera_id.name,
                'location': record.camera_id.location,
                'timestamp': record.timestamp,
                'confidence': record.confidence,
                'x3d_score': record.x3d_score,
                'bbox': record.bbox,
            })

        return tracking_path
