"""
Multi-Object Tracking Module — DeepSORT.

Source: Updated_AI_Engine_v2 / New_MCMT (identical logic; v2 version kept).

Wraps deep_sort_realtime to maintain per-camera local track IDs.
Each camera gets its own tracker instance for independent tracking.

Important: track_id values returned by DeepSORT may be integers or strings
depending on the library version.  All callers in main.py / inference_runner.py
normalise them with str() before using them as dict keys.
"""

import numpy as np
from deep_sort_realtime.deepsort_tracker import DeepSort
from ai_pipeline.ai_config.config import Config


class MultiObjectTracker:
    """
    DeepSORT-based multi-object tracker for a single camera.

    Maintains stable local track IDs, handles short occlusions,
    and returns tracked bounding boxes + IDs per frame.
    """

    def __init__(self, camera_id: int):
        """
        Initialize DeepSORT for one camera.

        Args:
            camera_id: Unique identifier for this camera.
        """
        self.camera_id = camera_id

        self.tracker = DeepSort(
            max_age=Config.DEEPSORT_MAX_AGE,
            n_init=Config.DEEPSORT_N_INIT,
            max_iou_distance=Config.DEEPSORT_MAX_IOU_DISTANCE,
            max_cosine_distance=Config.DEEPSORT_MAX_COSINE_DISTANCE,
            nn_budget=Config.DEEPSORT_NN_BUDGET,
            embedder="mobilenet",   # local appearance model for stable track IDs
        )

        print(f"[Tracker] DeepSORT initialised for Camera {camera_id}")

    def update(self, detections: list, frame: np.ndarray) -> list:
        """
        Update the tracker with new detections for the current frame.

        Args:
            detections: List of dicts with 'bbox' [x1,y1,x2,y2] and 'confidence'.
            frame: Current BGR frame (used by DeepSORT's local embedder).

        Returns:
            List of confirmed tracks, each a dict with:
                - 'track_id': local per-camera ID (str after normalisation in callers)
                - 'bbox':     [x1, y1, x2, y2]
                - 'confirmed': bool
        """
        if not detections:
            tracks = self.tracker.update_tracks([], frame=frame)
            return self._extract_tracks(tracks)

        # deep_sort_realtime expects: ([left, top, w, h], confidence, class_name)
        ds_detections = []
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            w    = x2 - x1
            h    = y2 - y1
            conf = det["confidence"]
            ds_detections.append(([x1, y1, w, h], conf, "person"))

        tracks = self.tracker.update_tracks(ds_detections, frame=frame)
        return self._extract_tracks(tracks)

    def _extract_tracks(self, tracks) -> list:
        """
        Filter and convert raw DeepSORT track objects.

        Returns only confirmed, recently-updated tracks in a clean dict format.
        """
        results = []
        for track in tracks:
            if not track.is_confirmed():
                continue
            if track.time_since_update > 1:
                continue   # skip stale (not updated this frame)

            ltrb = track.to_ltrb()
            bbox = [int(ltrb[0]), int(ltrb[1]), int(ltrb[2]), int(ltrb[3])]

            results.append({
                "track_id":  track.track_id,
                "bbox":      bbox,
                "confirmed": True,
            })
        return results

    def get_active_track_count(self) -> int:
        """Return the number of currently confirmed active tracks."""
        if hasattr(self.tracker, 'tracks'):
            return sum(1 for t in self.tracker.tracks if t.is_confirmed())
        return 0
