"""
Visualization Module — Multi-Camera + Theft Detection Overlays.

Source: Updated_AI_Engine (best visualization with theft overlays) + minor
stats additions from New_MCMT (per-identity detail in draw_stats_overlay).

Features:
  - Color-coded bounding boxes by global ID (normal) or red on theft/suspicion
  - Soft red flash overlay inside the bounding box on theft confirmation
  - THEFT! / Suspicious label with live score
  - Top theft-status banner (red alert / green monitoring)
  - Tiled multi-camera grid layout (auto-computed for 1–N cameras)
  - Bottom-left stats panel including cumulative theft alerts
"""

import cv2
import numpy as np
from config.config import Config


# 20 distinct BGR colors for global IDs
COLORS = [
    (0, 255, 0),      # Green
    (255, 0, 0),      # Blue
    (0, 0, 255),      # Red
    (255, 255, 0),    # Cyan
    (0, 255, 255),    # Yellow
    (255, 0, 255),    # Magenta
    (128, 255, 0),    # Spring Green
    (255, 128, 0),    # Light Blue
    (0, 128, 255),    # Orange
    (128, 0, 255),    # Purple
    (255, 255, 128),  # Light Cyan
    (128, 255, 255),  # Light Yellow
    (255, 128, 255),  # Pale Magenta
    (0, 200, 100),    # Teal
    (200, 100, 0),    # Steel Blue
    (100, 0, 200),    # Violet
    (200, 200, 0),    # Dark Cyan
    (0, 200, 200),    # Dark Yellow
    (200, 0, 200),    # Dark Magenta
    (100, 200, 100),  # Medium Green
]

COLOR_NORMAL     = (50, 200, 50)    # green — normal status
COLOR_THEFT      = (0, 0, 220)      # red   — theft confirmed / cooldown
COLOR_SUSPICIOUS = (0, 200, 255)    # yellow — building suspicion


def get_color(global_id: int) -> tuple:
    """Return a consistent BGR color for a given global identity ID."""
    return COLORS[global_id % len(COLORS)]


class Visualizer:
    """Multi-camera visualization with theft detection overlays."""

    def __init__(self):
        self.font       = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = Config.VIS_FONT_SCALE
        self.thickness  = Config.VIS_BBOX_THICKNESS
        self.window_w   = Config.VIS_WINDOW_WIDTH
        self.window_h   = Config.VIS_WINDOW_HEIGHT

    def draw_detections(
        self,
        frame: np.ndarray,
        detections: list,
        camera_id: int,
    ) -> np.ndarray:
        """
        Draw bounding boxes and ID labels on a single camera frame.

        Each detection dict may carry:
            'bbox', 'track_id', 'global_id', 'match_score',
            'is_theft', 'in_cooldown', 'consecutive_theft',
            'theft_score', 'theft_label'
        """
        annotated = frame.copy()

        cv2.putText(
            annotated, f"Camera {camera_id}", (10, 30),
            self.font, 0.8, (255, 255, 255), 2, cv2.LINE_AA,
        )

        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            track_id    = det.get("track_id", -1)
            global_id   = det.get("global_id", -1)
            is_theft    = det.get("is_theft", False)
            in_cooldown = det.get("in_cooldown", False)
            consecutive = det.get("consecutive_theft", 0)
            theft_score = det.get("theft_score", 0.0)

            # Box color: theft > suspicious > global-ID color
            if is_theft or in_cooldown:
                box_color = COLOR_THEFT
            elif consecutive > 0:
                box_color = COLOR_SUSPICIOUS
            elif global_id > 0:
                box_color = get_color(global_id)
            else:
                box_color = (200, 200, 200)

            box_thick = self.thickness + (2 if (is_theft or in_cooldown) else 0)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, box_thick)

            # Soft red flash inside box on theft confirmation
            if is_theft or in_cooldown:
                overlay = annotated.copy()
                cv2.rectangle(overlay, (x1, y1), (x2, y2), COLOR_THEFT, -1)
                cv2.addWeighted(overlay, 0.15, annotated, 0.85, 0, annotated)

            # Build label text
            label_parts = []
            if Config.VIS_SHOW_GLOBAL_ID and global_id > 0:
                label_parts.append(f"G:{global_id}")
            if Config.VIS_SHOW_LOCAL_ID:
                label_parts.append(f"L:{track_id}")
            if is_theft or in_cooldown:
                label_parts.append("THEFT!")
            elif consecutive > 0:
                label_parts.append(f"Sus({consecutive})")
            if theft_score > 0:
                label_parts.append(f"s:{theft_score:.2f}")

            label = " | ".join(label_parts)

            if label:
                (tw, th), bl = cv2.getTextSize(label, self.font, self.font_scale, 1)
                cv2.rectangle(
                    annotated,
                    (x1, y1 - th - bl - 6), (x1 + tw + 4, y1),
                    box_color, -1,
                )
                cv2.putText(
                    annotated, label, (x1 + 2, y1 - bl - 4),
                    self.font, self.font_scale, (0, 0, 0), 1, cv2.LINE_AA,
                )

        return annotated

    def draw_theft_banner(
        self,
        frame: np.ndarray,
        any_theft: bool,
        theft_summary: dict,
    ) -> np.ndarray:
        """
        Draw a top banner showing the overall system theft status.

        Red + flashing when any identity has an active alert;
        dark green when all is normal.
        """
        h, w     = frame.shape[:2]
        banner_h = 44

        if any_theft:
            cv2.rectangle(frame, (0, 0), (w, banner_h), (0, 0, 160), -1)
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (w, banner_h), COLOR_THEFT, -1)
            cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
            theft_ids = [gid for gid, (alert, _, _) in theft_summary.items() if alert]
            ids_str   = ", ".join(f"G:{g}" for g in theft_ids)
            text      = f"!! THEFT ALERT — Person(s): {ids_str} !!"
            color     = (255, 255, 255)
        else:
            cv2.rectangle(frame, (0, 0), (w, banner_h), (20, 20, 20), -1)
            text  = "Theft Sentinel MCMT v2 — Monitoring Active — No Theft Detected"
            color = COLOR_NORMAL

        cv2.putText(frame, text, (12, 30), self.font, 0.75, color, 2, cv2.LINE_AA)
        return frame

    def create_tiled_display(self, frames: dict) -> np.ndarray:
        """
        Arrange all camera frames into a tiled grid.

        Grid layout is computed automatically for 1–N cameras.

        Args:
            frames: Dict camera_id → annotated BGR frame.

        Returns:
            Single combined BGR image.
        """
        if not frames:
            return np.zeros((self.window_h, self.window_w, 3), dtype=np.uint8)

        n = len(frames)
        if n <= 1:    cols, rows = 1, 1
        elif n <= 2:  cols, rows = 2, 1
        elif n <= 4:  cols, rows = 2, 2
        elif n <= 6:  cols, rows = 3, 2
        elif n <= 9:  cols, rows = 3, 3
        else:
            cols = int(np.ceil(np.sqrt(n)))
            rows = int(np.ceil(n / cols))

        tile_w = self.window_w // cols
        tile_h = self.window_h // rows
        canvas = np.zeros((rows * tile_h, cols * tile_w, 3), dtype=np.uint8)

        for idx, cam_id in enumerate(sorted(frames.keys())):
            row = idx // cols
            col = idx % cols
            resized = cv2.resize(frames[cam_id], (tile_w, tile_h))
            canvas[row * tile_h:(row + 1) * tile_h,
                   col * tile_w:(col + 1) * tile_w] = resized

        return canvas

    def draw_stats_overlay(self, frame: np.ndarray, stats: dict) -> np.ndarray:
        """
        Draw a stats panel at the bottom-left of the combined frame.

        Args:
            stats: Dict with keys: 'total_identities', 'active_tracks',
                   'faiss_size', 'fps', 'theft_alerts'.
        """
        annotated = frame.copy()
        h, _      = annotated.shape[:2]
        y         = h - 20

        lines = [
            f"Global IDs: {stats.get('total_identities', 0)}",
            f"Active Tracks: {stats.get('active_tracks', 0)}",
            f"FAISS Index: {stats.get('faiss_size', 0)}",
            f"FPS: {stats.get('fps', 0.0):.1f}",
            f"Theft Alerts: {stats.get('theft_alerts', 0)}",
        ]
        for line in reversed(lines):
            cv2.putText(annotated, line, (10, y), self.font, 0.5,
                        (0, 255, 255), 1, cv2.LINE_AA)
            y -= 22

        return annotated
