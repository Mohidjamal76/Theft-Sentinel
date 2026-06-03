import numpy as np
from typing import Optional

class MLFeatureBuilder:
    """Converts raw pose features + rule-based counters into ML-ready vectors."""

    @staticmethod
    def build_feature_vector(track) -> Optional[np.ndarray]:
        # Must have pose and features
        if not track.has_pose() or not track.latest_features():
            return None

        f = track.latest_features()
        pbox = track.get_smoothed_bbox()
        if pbox is None:
            return None

        # Geometry from bbox
        px1, py1, px2, py2 = pbox
        person_w = px2 - px1
        person_h = py2 - py1
        aspect = person_w / max(person_h, 1)

        # --------------- Core pose features (8) ---------------
        torso_angle = f["torso_angle"]
        head_angle = f["head_angle"]
        left_elbow = f["left_elbow_angle"]
        right_elbow = f["right_elbow_angle"]
        lw_hip = f["left_wrist_to_hip"]
        rw_hip = f["right_wrist_to_hip"]
        lw_speed = f["left_wrist_speed"]
        rw_speed = f["right_wrist_speed"]

        # --------------- Behavioral counters (5) ---------------
        # These fields MUST exist in TrackInfo (and you already added them)
        in_bag = track.hand_in_bag_frames
        in_torso = track.hand_in_torso_frames
        fast = track.fast_wrist_frames
        near_obj = track.near_object_frames
        conceal = track.recent_concealment_events

        # --------------- Timing / confidence (2) ---------------
        dwell = track.get_dwell_time()
        conf = track.get_avg_conf()

        # ---------- Final ML input vector (18 floats) ----------
        vec = np.array([
            torso_angle,
            head_angle,
            left_elbow,
            right_elbow,
            lw_hip,
            rw_hip,
            lw_speed,
            rw_speed,
            in_bag,
            in_torso,
            fast,
            near_obj,
            conceal,
            dwell,
            conf,
            aspect,
            person_w,
            person_h,
        ], dtype=np.float32)

        return vec
