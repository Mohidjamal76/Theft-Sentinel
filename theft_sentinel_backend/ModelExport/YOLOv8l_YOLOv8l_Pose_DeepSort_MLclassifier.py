"""
Subtle-Theft Pose Foundation - Ultra-Optimized (Balanced, RTX 3050)

Features:
- YOLOv8-L detection (dynamic imgsz, CUDA)
- YOLOv8-Pose (per-person crops, batch inference)
- DeepSORT tracking (GPU embedder)
- Multi-threaded capture
- Dedicated detection+tracking thread
- Dedicated pose thread
- Async CUDA streams
- Warmup inference before realtime loop
- Detection skipping (every N frames)
- Dynamic resolution downscaling based on FPS
- GPU REQUIRED (exits if CUDA not available)
"""

import sys
import cv2
import time
import torch
import threading
import numpy as np
import os
import shutil

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
from ml_classifier.feature_builder import MLFeatureBuilder
from ml_classifier.sequence_collector import SequenceCollector
from ml_classifier.theft_classifier import TheftClassifier



# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class Config:
    det_model_name: str = "yolov8l.pt"
    pose_model_name: str = "yolov8l-pose.pt"
    device_str: str = "cuda:0"

    # Webcam
    webcam_index: int = 0
    window_width: int = 1280
    window_height: int = 720
    window_name: str = "Subtle Theft - High Accuracy (RTX 3050)"

    # Detection
    imgsz_init: int = 704
    imgsz_min: int = 576
    imgsz_max: int = 768
    det_every_n_frames: int = 1
    confidence: float = 0.45
    iou: float = 0.50
    min_detection_size: int = 450

    # Runtime thresholds (reserved for theft logic)
    person_overlap_threshold: float = 0.40
    concealment_threshold: float = 0.70
    size_shrink_ratio: float = 0.35
    bag_overlap_threshold: float = 0.40
    dwell_time_threshold: int = 180
    max_distance_norm: float = 0.15
    concealment_stable_frames: int = 10

    # Pose
    pose_confidence: float = 0.30
    pose_iou: float = 0.50
    pose_crop_pad: float = 0.25
    pose_imgsz: int = 320

    # Tracking
    max_track_age: int = 25
    min_track_hits: int = 3

    # FPS scaling thresholds
    fps_update_frames: int = 30
    fps_history_size: int = 10
    fps_target_low: float = 28.0
    fps_target_high: float = 45.0

    use_bbox_smoothing: bool = True

    # Classes
    person_class: int = 0
    bag_classes: set = field(default_factory=lambda: {24, 26, 28})
    suspicious_classes: set = field(default_factory=lambda: {67, 73})

    # Colors
    color_person: tuple = (200, 200, 0)
    color_bag: tuple = (0, 180, 255)
    color_object: tuple = (0, 255, 0)
    color_pose: tuple = (0, 255, 255)
    color_fps: tuple = (0, 255, 0)
    color_text: tuple = (255, 255, 255)
    color_debug: tuple = (255, 255, 0)


cfg = Config()


sequence_collector = SequenceCollector()
ml_classifier = TheftClassifier()

# ============================================================
# GLOBAL SHARED STATE
# ============================================================

latest_frame: Optional[np.ndarray] = None
latest_frame_idx: int = 0
frame_lock = threading.Lock()

tracks: Dict[int, "TrackInfo"] = {}
tracks_lock = threading.Lock()

running: bool = True
current_fps: float = 0.0
current_imgsz: int = cfg.imgsz_init


# ============================================================
# BASIC STRUCTURES
# ============================================================


def safe_append_dataset(x_path, y_path, X_new, y_new, label_name=""):
    """
    Appends new samples to an existing dataset with:
      - directory auto-creation
      - automatic backup of old files before overwrite
      - graceful handling of feature dimension mismatch
    """
    os.makedirs(os.path.dirname(x_path), exist_ok=True)

    # first time: just save
    if not os.path.exists(x_path):
        np.save(x_path, X_new)
        np.save(y_path, y_new)
        print(f"💾 Saved first {label_name} dataset with {len(X_new)} samples.")
        return len(X_new)

    # backup old files
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup_x = f"{x_path}.backup_{ts}"
    backup_y = f"{y_path}.backup_{ts}"
    try:
        shutil.copy2(x_path, backup_x)
        shutil.copy2(y_path, backup_y)
        print(f"🛡 Backup created for {label_name} dataset:")
        print(f"   {backup_x}")
        print(f"   {backup_y}")
    except Exception as e:
        print(f"⚠ Failed to backup {label_name} dataset:", e)

    # now load and append or reset
    try:
        X_old = np.load(x_path)
        y_old = np.load(y_path)

        if X_old.shape[1] != X_new.shape[1]:
            print("⚠ Feature dimension changed, starting a NEW", label_name, "dataset.")
            X_final = X_new
            y_final = y_new
        else:
            X_final = np.vstack([X_old, X_new])
            y_final = np.hstack([y_old, y_new])
    except Exception as e:
        print(f"⚠ Error reading old {label_name} dataset. Starting new. Error:", e)
        X_final = X_new
        y_final = y_new

    np.save(x_path, X_final)
    np.save(y_path, y_final)
    print(f"💾 Saved {len(X_new)} new {label_name} sequences. Total now: {len(X_final)}")
    return len(X_final)






class Detection:
    """Wrapper for YOLO detection output."""
    def __init__(self, bbox: List[float], conf: float, coco_class: int):
        self.bbox = bbox  # [x1, y1, x2, y2]
        self.conf = conf
        self.coco_class = coco_class
        self.logical_class = self._map_class()
        self.area = self._calculate_area()

    def _calculate_area(self) -> float:
        return max(0.0, self.bbox[2] - self.bbox[0]) * max(0.0, self.bbox[3] - self.bbox[1])

    def _map_class(self) -> str:
        if self.coco_class == cfg.person_class:
            return "person"
        elif self.coco_class in cfg.bag_classes:
            return "bag"
        elif self.coco_class in cfg.suspicious_classes:
            return "suspicious_object"
        else:
            return "object"

    def is_valid(self) -> bool:
        return self.conf >= cfg.confidence and self.area >= cfg.min_detection_size


class PoseDetection:
    """Pose estimation result for a single person (full-frame coords)."""
    def __init__(self, bbox: List[float], keypoints: np.ndarray, conf: float):
        self.bbox = bbox          # [x1,y1,x2,y2] in full-frame coords
        self.keypoints = keypoints  # (17,3) in full-frame coords
        self.conf = conf


class TrackInfo:
    """Per-track information including pose and behavior features."""
    def __init__(self, track_id: int, coco_class: int, logical_class: str):
        self.track_id = track_id
        self.coco_class = coco_class
        self.label = logical_class

        self.first_seen = 0
        self.last_seen = 0

        self.bbox_history = deque(maxlen=10)
        self.conf_history = deque(maxlen=10)

        self.pose_history: deque[PoseDetection] = deque(maxlen=30)
        self.feature_history: deque[dict] = deque(maxlen=30)

        self.hand_in_bag_frames = 0
        self.hand_in_torso_frames = 0
        self.fast_wrist_frames = 0
        self.near_object_frames = 0
        self.recent_concealment_events = 0
        
         # to detect “object → concealment”
        self.prev_wrist_region = "none"


    def update_bbox(self, frame_num: int, bbox: List[float], conf: float):
        self.last_seen = frame_num
        if not self.bbox_history:
            self.first_seen = frame_num
        self.bbox_history.append(bbox)
        self.conf_history.append(conf)

    def update_pose(self, pose_det: PoseDetection, features: dict):
        self.pose_history.append(pose_det)
        self.feature_history.append(features)

    def get_smoothed_bbox(self) -> Optional[List[float]]:
        if not self.bbox_history:
            return None
        if cfg.use_bbox_smoothing and len(self.bbox_history) >= 2:
            cur = self.bbox_history[-1]
            prev = self.bbox_history[-2]
            return [
                0.7 * cur[0] + 0.3 * prev[0],
                0.7 * cur[1] + 0.3 * prev[1],
                0.7 * cur[2] + 0.3 * prev[2],
                0.7 * cur[3] + 0.3 * prev[3],
            ]
        return list(self.bbox_history[-1])

    def get_avg_conf(self) -> float:
        if not self.conf_history:
            return 0.0
        return float(np.mean(self.conf_history))

    def get_dwell_time(self) -> int:
        return self.last_seen - self.first_seen if self.last_seen and self.first_seen else 0

    def has_pose(self) -> bool:
        return len(self.pose_history) > 0

    def latest_pose(self) -> Optional[PoseDetection]:
        return self.pose_history[-1] if self.pose_history else None

    def latest_features(self) -> Optional[dict]:
        return self.feature_history[-1] if self.feature_history else None


# ============================================================
# GEOMETRY HELPERS
# ============================================================

def bbox_area(bbox: List[float]) -> float:
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])


def bbox_overlap(b1: List[float], b2: List[float]) -> float:
    x1 = max(b1[0], b2[0])
    y1 = max(b1[1], b2[1])
    x2 = min(b1[2], b2[2])
    y2 = min(b1[3], b2[3])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    return float((x2 - x1) * (y2 - y1))


def bbox_iou(b1: List[float], b2: List[float]) -> float:
    inter = bbox_overlap(b1, b2)
    union = bbox_area(b1) + bbox_area(b2) - inter
    return inter / union if union > 0 else 0.0


def keypoint_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Returns angle at point b for triangle a-b-c in degrees."""
    v1 = a - b
    v2 = c - b
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 < 1e-6 or n2 < 1e-6:
        return 0.0
    cos_ang = np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_ang)))


def distance(p1: np.ndarray, p2: np.ndarray) -> float:
    return float(np.linalg.norm(p1 - p2))


# ============================================================
# POSE FEATURE ENGINE
# ============================================================

class PoseFeatureEngine:
    """Computes simple pose-based features useful for theft modeling."""

    @staticmethod
    def compute_features(pose: PoseDetection, prev_pose: Optional[PoseDetection]) -> dict:
        kps = pose.keypoints
        xy = kps[:, :2]

        NOSE = 0
        L_SH = 5
        R_SH = 6
        L_EL = 7
        R_EL = 8
        L_WR = 9
        R_WR = 10
        L_HIP = 11
        R_HIP = 12

        nose = xy[NOSE]
        l_sh = xy[L_SH]
        r_sh = xy[R_SH]
        l_el = xy[L_EL]
        r_el = xy[R_EL]
        l_wr = xy[L_WR]
        r_wr = xy[R_WR]
        l_hip = xy[L_HIP]
        r_hip = xy[R_HIP]

        mid_sh = (l_sh + r_sh) / 2.0
        mid_hip = (l_hip + r_hip) / 2.0

        torso_vec = mid_sh - mid_hip
        torso_angle = float(np.degrees(np.arctan2(torso_vec[0], torso_vec[1])))

        head_vec = nose - mid_sh
        head_angle = float(np.degrees(np.arctan2(head_vec[0], head_vec[1])))

        left_elbow_angle = keypoint_angle(l_sh, l_el, l_wr)
        right_elbow_angle = keypoint_angle(r_sh, r_el, r_wr)

        left_wrist_to_hip = distance(l_wr, mid_hip)
        right_wrist_to_hip = distance(r_wr, mid_hip)

        left_wrist_speed = 0.0
        right_wrist_speed = 0.0
        if prev_pose is not None:
            prev_xy = prev_pose.keypoints[:, :2]
            prev_l_wr = prev_xy[L_WR]
            prev_r_wr = prev_xy[R_WR]
            left_wrist_speed = distance(l_wr, prev_l_wr)
            right_wrist_speed = distance(r_wr, prev_r_wr)

        return {
            "torso_angle": torso_angle,
            "head_angle": head_angle,
            "left_elbow_angle": left_elbow_angle,
            "right_elbow_angle": right_elbow_angle,
            "left_wrist_to_hip": left_wrist_to_hip,
            "right_wrist_to_hip": right_wrist_to_hip,
            "left_wrist_speed": left_wrist_speed,
            "right_wrist_speed": right_wrist_speed,
        }


# ============================================================
# VISUALIZER
# ============================================================

class Visualizer:
    """Drawing of tracks, poses, and HUD overlay."""

    skeleton_pairs = [
        (5, 6),
        (5, 7), (7, 9),
        (6, 8), (8, 10),
        (11, 12),
        (5, 11), (6, 12),
        (11, 13), (13, 15),
        (12, 14), (14, 16),
        (0, 5), (0, 6),
    ]

    @staticmethod
    def draw_tracks_and_pose(frame: np.ndarray, tracks_dict: Dict[int, TrackInfo]) -> np.ndarray:
        vis = frame.copy()
        for tid, tinfo in tracks_dict.items():
            bbox = tinfo.get_smoothed_bbox()
            if bbox is None:
                continue

            x1, y1, x2, y2 = map(int, bbox)
            label = tinfo.label
            dwell = tinfo.get_dwell_time()
            conf = tinfo.get_avg_conf()

            if label == "person":
                color = cfg.color_person
            elif label == "bag":
                color = cfg.color_bag
            else:
                color = cfg.color_object

            thickness = 3 if dwell > cfg.dwell_time_threshold else 2
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, thickness)

            text = f"{label} {tid} {conf:.2f}"
            # ML score for theft (if exists)
            if hasattr(tinfo, "ml_score"):
                text += f" ML:{int(tinfo.ml_score * 100)}%"

            if dwell > 0:
                text += f" [{dwell}f]"
            cv2.putText(vis, text, (x1, max(15, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            if tinfo.has_pose():
                pose = tinfo.latest_pose()
                kps = pose.keypoints
                for (i, j) in Visualizer.skeleton_pairs:
                    xi, yi, ci = kps[i]
                    xj, yj, cj = kps[j]
                    if ci > 0.3 and cj > 0.3:
                        cv2.line(vis, (int(xi), int(yi)), (int(xj), int(yj)),
                                 cfg.color_pose, 2)

                rwx, rwy, rc = kps[10]
                lwx, lwy, lc = kps[9]
                if rc > 0.3:
                    cv2.circle(vis, (int(rwx), int(rwy)), 5, (0, 0, 255), -1)
                if lc > 0.3:
                    cv2.circle(vis, (int(lwx), int(lwy)), 5, (0, 255, 0), -1)

        return vis

    @staticmethod
    def draw_overlay(frame: np.ndarray,
                     tracks_dict: Dict[int, TrackInfo],
                     fps: float,
                     paused: bool) -> np.ndarray:
        h, w = frame.shape[:2]
        overlay = frame.copy()

        cv2.rectangle(overlay, (0, 0), (w, 180), (0, 0, 0), -1)
        frame = cv2.addWeighted(frame, 0.75, overlay, 0.25, 0)

        y = 25
        fps_color = cfg.color_fps if fps > 10 else (0, 0, 255)
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, fps_color, 2)

        if paused:
            cv2.putText(frame, "PAUSED", (150, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        y += 30

        persons = sum(1 for t in tracks_dict.values() if t.label == "person")
        bags = sum(1 for t in tracks_dict.values() if t.label == "bag")
        objects = sum(1 for t in tracks_dict.values() if t.label not in ("person", "bag"))
        cv2.putText(frame, f"Tracks - Persons: {persons} | Bags: {bags} | Obj: {objects}",
                    (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, cfg.color_text, 1)
        y += 20

        smooth_status = "ON (Light)" if cfg.use_bbox_smoothing else "OFF (Responsive)"
        cv2.putText(frame, f"Smoothing: {smooth_status}",
                    (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, cfg.color_debug, 1)
        y += 25

        cv2.putText(frame,
                    f"DetConf: {cfg.confidence:.2f} | PoseConf: {cfg.pose_confidence:.2f} | ImgSz: {current_imgsz}",
                    (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, cfg.color_text, 1)
        y += 20

        cv2.putText(frame,
                    f"Dwell: {cfg.dwell_time_threshold}f | DetEveryN: {cfg.det_every_n_frames}",
                    (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, cfg.color_text, 1)
        y += 30

        cv2.putText(frame, "CONTROLS:", (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, cfg.color_text, 2)
        y += 20

        controls = [
            "Q: Quit | SPACE: Pause | S: Screenshot | R: Reset",
            "M: Toggle Smoothing | +/-: DetConf",
        ]
        for c in controls:
            cv2.putText(frame, c, (10, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, cfg.color_text, 1)
            y += 18

        return frame


# ============================================================
# THREADS
# ============================================================

def capture_thread_func(cap: cv2.VideoCapture):
    """Continuously grab frames from the webcam."""
    global latest_frame, latest_frame_idx, running
    while running:
        ret, frame = cap.read()
        if not ret:
            running = False
            break
        with frame_lock:
            latest_frame = frame
            latest_frame_idx += 1
        time.sleep(0.001)


def detection_thread_func(det_model: YOLO,
                          deepsort: DeepSort,
                          det_stream: torch.cuda.Stream):
    """Detection + DeepSORT tracking thread."""
    global running, latest_frame, latest_frame_idx, current_imgsz, current_fps, tracks

    local_frame_idx = 0
    frame_counter = 0

    while running:
        frame_copy = None
        frame_idx = 0
        with frame_lock:
            if latest_frame is not None:
                frame_copy = latest_frame.copy()
                frame_idx = latest_frame_idx

        if frame_copy is None:
            time.sleep(0.002)
            continue

        if frame_idx == local_frame_idx:
            time.sleep(0.002)
            continue

        local_frame_idx = frame_idx
        frame_counter += 1

        # Skip detection on some frames (Balanced Mode)
        if frame_counter % cfg.det_every_n_frames != 0:
            time.sleep(0.001)
            continue

        # Dynamic resolution based on FPS snapshot
        fps_snapshot = current_fps
        if fps_snapshot < cfg.fps_target_low and current_imgsz > cfg.imgsz_min:
            current_imgsz = max(cfg.imgsz_min, current_imgsz - 64)
        elif fps_snapshot > cfg.fps_target_high and current_imgsz < cfg.imgsz_max:
            current_imgsz = min(cfg.imgsz_max, current_imgsz + 64)

        # Detection with async CUDA stream
        with torch.cuda.stream(det_stream):
            det_results = det_model(
                frame_copy,
                imgsz=current_imgsz,
                conf=cfg.confidence,
                iou=cfg.iou,
                verbose=False
            )
        torch.cuda.current_stream().wait_stream(det_stream)
        det_res = det_results[0]

        yolo_detections: List[Detection] = []
        if det_res.boxes is not None:
            for box in det_res.boxes:
                cls_id = int(box.cls.cpu().item())
                conf = float(box.conf.cpu().item())
                xyxy = box.xyxy.cpu().numpy()[0]
                bbox = [float(v) for v in xyxy]
                det_obj = Detection(bbox, conf, cls_id)
                if det_obj.is_valid():
                    yolo_detections.append(det_obj)

        # Prepare inputs for DeepSORT
        deepsort_input = []
        for det in yolo_detections:
            x1, y1, x2, y2 = det.bbox
            tlwh = [x1, y1, x2 - x1, y2 - y1]
            deepsort_input.append((tlwh, det.conf, det.logical_class))

        ds_tracks = deepsort.update_tracks(deepsort_input, frame=frame_copy)

        active_ids = set()
        with tracks_lock:
            for t in ds_tracks:
                if not t.is_confirmed():
                    continue
                tid = t.track_id
                active_ids.add(tid)
                bbox = [float(v) for v in t.to_ltrb()]

                best_det = None
                best_iou = 0.0
                for det in yolo_detections:
                    iou = bbox_iou(bbox, det.bbox)
                    if iou > best_iou:
                        best_iou = iou
                        best_det = det
                if best_det is None or best_iou < 0.3:
                    continue

                coco_class = best_det.coco_class
                logical_class = best_det.logical_class
                conf = best_det.conf

                if tid not in tracks:
                    tracks[tid] = TrackInfo(tid, coco_class, logical_class)
                else:
                    tracks[tid].coco_class = coco_class
                    tracks[tid].label = logical_class

                tracks[tid].update_bbox(frame_idx, bbox, conf)

            # Remove dead tracks
            for tid in list(tracks.keys()):
                if tid not in active_ids:
                    del tracks[tid]

        time.sleep(0.001)


def pose_thread_func(pose_model: YOLO, pose_stream: torch.cuda.Stream):
    """Per-person crop-based batch pose inference thread."""
    global running, latest_frame, latest_frame_idx, tracks

    local_last_frame_idx = 0

    while running:
        frame_copy = None
        frame_idx = 0
        with frame_lock:
            if latest_frame is not None:
                frame_copy = latest_frame.copy()
                frame_idx = latest_frame_idx

        if frame_copy is None:
            time.sleep(0.002)
            continue

        if frame_idx == local_last_frame_idx:
            time.sleep(0.002)
            continue
        local_last_frame_idx = frame_idx

        # Snapshot of person tracks
        with tracks_lock:
            person_items: List[Tuple[int, List[float], TrackInfo]] = [
                (tid, t.get_smoothed_bbox(), t)
                for tid, t in tracks.items()
                if t.label == "person" and t.get_smoothed_bbox() is not None
            ]

        if not person_items:
            time.sleep(0.002)
            continue

        H, W = frame_copy.shape[:2]
        crops: List[np.ndarray] = []
        crop_meta: List[Tuple[int, int, int]] = []  # (tid, x1, y1)

        # Build crop batch
        for tid, bbox, _t in person_items:
            x1, y1, x2, y2 = bbox
            w = x2 - x1
            h = y2 - y1
            pad_x = w * cfg.pose_crop_pad
            pad_y = h * cfg.pose_crop_pad
            cx1 = max(0, int(x1 - pad_x))
            cy1 = max(0, int(y1 - pad_y))
            cx2 = min(W - 1, int(x2 + pad_x))
            cy2 = min(H - 1, int(y2 + pad_y))
            if cx2 <= cx1 or cy2 <= cy1:
                continue

            crop = frame_copy[cy1:cy2, cx1:cx2]
            if crop.size == 0:
                continue

            crops.append(crop)
            crop_meta.append((tid, cx1, cy1))

        if not crops:
            time.sleep(0.002)
            continue

        # Batch pose inference on crops with async stream
        with torch.cuda.stream(pose_stream):
            pose_results = pose_model(
                crops,
                imgsz=cfg.pose_imgsz,
                conf=cfg.pose_confidence,
                iou=cfg.pose_iou,
                verbose=False
            )
        torch.cuda.current_stream().wait_stream(pose_stream)

        # Update tracks with pose data and features
        with tracks_lock:
            for idx, res in enumerate(pose_results):
                tid, base_x, base_y = crop_meta[idx]
                if tid not in tracks:
                    continue
                if res.boxes is None or res.keypoints is None or len(res.boxes) == 0:
                    continue

                boxes = res.boxes.xyxy.cpu().numpy()
                scores = res.boxes.conf.cpu().numpy()
                classes = res.boxes.cls.cpu().numpy().astype(int)
                kpts = res.keypoints.data.cpu().numpy()

                best_idx = -1
                best_score = 0.0
                for i in range(len(boxes)):
                    if classes[i] != cfg.person_class:
                        continue
                    if scores[i] > best_score:
                        best_score = scores[i]
                        best_idx = i

                if best_idx < 0:
                    continue

                bbox_crop = boxes[best_idx]
                kps_crop = kpts[best_idx]

                bbox_full = [
                    float(bbox_crop[0] + base_x),
                    float(bbox_crop[1] + base_y),
                    float(bbox_crop[2] + base_x),
                    float(bbox_crop[3] + base_y),
                ]
                kps_full = kps_crop.copy()
                kps_full[:, 0] += base_x
                kps_full[:, 1] += base_y

                pose_det = PoseDetection(bbox=bbox_full, keypoints=kps_full, conf=float(best_score))
                prev_pose = tracks[tid].latest_pose()
                features = PoseFeatureEngine.compute_features(pose_det, prev_pose)
                tracks[tid].update_pose(pose_det, features)
                
                # -----------------------------------------
                # RULE-BASED BEHAVIOR DETECTION
                # -----------------------------------------

                kps = kps_full  # 17x3 array
                rw = kps[10][:2]   # right wrist (x, y)
                lw = kps[9][:2]    # left wrist (x, y)
                mid_hip = (kps[11][:2] + kps[12][:2]) / 2.0
                mid_shoulder = (kps[5][:2] + kps[6][:2]) / 2.0
                torso_top = mid_shoulder[1]
                torso_bottom = mid_hip[1]

                # --------------------------
                # 1️⃣ HAND IN BAG
                # --------------------------
                for other_tid, other_tinfo in tracks.items():
                    if other_tid == tid:
                        continue
                    if other_tinfo.label == "bag":
                        bag_bbox = other_tinfo.get_smoothed_bbox()
                        if bag_bbox is None:
                            continue
                        bx1, by1, bx2, by2 = bag_bbox

                        # right wrist inside bag
                        if bx1 <= rw[0] <= bx2 and by1 <= rw[1] <= by2:
                            tracks[tid].hand_in_bag_frames += 1

                        # left wrist inside bag
                        if bx1 <= lw[0] <= bx2 and by1 <= lw[1] <= by2:
                            tracks[tid].hand_in_bag_frames += 1

                # --------------------------
                # 2️⃣ HAND IN TORSO REGION
                # --------------------------
                if torso_top <= rw[1] <= torso_bottom:
                    tracks[tid].hand_in_torso_frames += 1
                if torso_top <= lw[1] <= torso_bottom:
                    tracks[tid].hand_in_torso_frames += 1

                # --------------------------
                # 3️⃣ FAST WRIST MOTION
                # --------------------------
                wrist_speed_r = features["right_wrist_speed"]
                wrist_speed_l = features["left_wrist_speed"]

                # threshold depends on resolution
                if wrist_speed_r > 15 or wrist_speed_l > 15:
                    tracks[tid].fast_wrist_frames += 1

                # --------------------------
                # 4️⃣ NEAR OBJECT INTERACTION
                # --------------------------
                for other_tid, other_tinfo in tracks.items():
                    if other_tid == tid:
                        continue
                    if other_tinfo.label == "object":
                        ob = other_tinfo.get_smoothed_bbox()
                        if ob is None:
                            continue
                        ox1, oy1, ox2, oy2 = ob

                        # wrist near object (distance < 40px)
                        if ox1 - 40 <= rw[0] <= ox2 + 40 and oy1 - 40 <= rw[1] <= oy2 + 40:
                            tracks[tid].near_object_frames += 1
                        if ox1 - 40 <= lw[0] <= ox2 + 40 and oy1 - 40 <= lw[1] <= oy2 + 40:
                            tracks[tid].near_object_frames += 1

                # --------------------------
                # 5️⃣ DETECT CONCEALMENT EVENT:
                # interaction → concealment
                # --------------------------
                region_now = "none"

                if tracks[tid].near_object_frames > 0:
                    region_now = "object"
                if tracks[tid].hand_in_bag_frames > 0:
                    region_now = "bag"
                if tracks[tid].hand_in_torso_frames > 0:
                    region_now = "torso"

                # Detect event: object → torso OR object → bag
                if tracks[tid].prev_wrist_region == "object" and region_now in ("torso", "bag"):
                    tracks[tid].recent_concealment_events += 1

                tracks[tid].prev_wrist_region = region_now

                
                vec = MLFeatureBuilder.build_feature_vector(tracks[tid])
                if vec is not None:
                    # store per-frame features
                    sequence_collector.add(tid, vec)

                    # allow early prediction after a few frames, but
                    # get_sequence will still return a fixed-length vector
                    seq = sequence_collector.get_sequence(tid, min_frames=3)

                    if seq is not None and ml_classifier.model is not None:
                        try:
                            ml_score = ml_classifier.predict(seq)  # 0..1
                            tracks[tid].ml_score = float(ml_score)

                            # rule: high probability -> likely theft
                            if ml_score > 0.6:
                                print(f"🚨 Theft Likely Detected! Track {tid} | Score {ml_score:.2f}")
                        except Exception as e:
                            print("ML classifier error:", e)




        time.sleep(0.001)


# ============================================================
# MAIN
# ============================================================

def main():
    global running, current_fps, current_imgsz

    print("=" * 60)
    print("🚀 Subtle Theft - Pose Foundation (Ultra-Optimized, Balanced Mode)")
    print("=" * 60)

    # GPU requirement
    if not torch.cuda.is_available():
        print("❌ CUDA not available. GPU is required. Exiting.")
        sys.exit(1)

    torch.backends.cudnn.benchmark = True
    device_str = cfg.device_str
    print(f"✅ Using GPU: {device_str}")
    print(f"   Device name: {torch.cuda.get_device_name(0)}")

    # Load models (no manual .half()!)
    print(f"\nLoading detection model: {cfg.det_model_name}")
    det_model = YOLO(cfg.det_model_name)
    det_model.to(device_str)
    print("✅ Detection model loaded (FP32 fused → FP16 inference handled internally)")

    print(f"\nLoading pose model: {cfg.pose_model_name}")
    pose_model = YOLO(cfg.pose_model_name)
    pose_model.to(device_str)
    print("✅ Pose model loaded (FP32 fused → FP16 inference handled internally)")

    # Warmup
    dummy = np.zeros((cfg.window_height, cfg.window_height, 3), dtype=np.uint8)
    print("\n🔥 Warming up models...")
    det_model(dummy, imgsz=cfg.imgsz_init, conf=cfg.confidence, iou=cfg.iou, verbose=False)
    pose_model(dummy, imgsz=cfg.pose_imgsz, conf=cfg.pose_confidence, iou=cfg.pose_iou, verbose=False)
    torch.cuda.synchronize()
    print("✅ Warmup complete")

    # DeepSORT tracker
    print("\nInitializing DeepSORT...")
    deepsort = DeepSort(
        max_age=cfg.max_track_age,
        n_init=cfg.min_track_hits,
        max_iou_distance=0.7,
        max_cosine_distance=0.4,
        nn_budget=100,
        embedder="mobilenet",
        embedder_gpu=True,
    )
    print("✅ DeepSORT initialized (GPU embedder)")

    # Video capture
    print("\nOpening webcam...")
    cap = cv2.VideoCapture(cfg.webcam_index)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            print("❌ Cannot open webcam")
            sys.exit(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.window_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.window_height)
    print("✅ Webcam ready")

    # CUDA streams
    det_stream = torch.cuda.Stream()
    pose_stream = torch.cuda.Stream()

    # Threads
    cam_thread = threading.Thread(target=capture_thread_func, args=(cap,), daemon=True)
    det_thread = threading.Thread(target=detection_thread_func, args=(det_model, deepsort, det_stream), daemon=True)
    pose_thread = threading.Thread(target=pose_thread_func, args=(pose_model, pose_stream), daemon=True)

    cam_thread.start()
    det_thread.start()
    pose_thread.start()

    frame_display_count = 0
    fps_hist: List[float] = []
    fps_timer_start = time.time()
    paused = False
    screenshot_count = 0
    display_frame: Optional[np.ndarray] = None

    try:
        while True:
            if not paused:
                with frame_lock:
                    if latest_frame is not None:
                        display_frame = latest_frame.copy()

                if display_frame is not None:
                    with tracks_lock:
                        tracks_snapshot = dict(tracks)
                    vis = Visualizer.draw_tracks_and_pose(display_frame, tracks_snapshot)

                    frame_display_count += 1
                    if frame_display_count % cfg.fps_update_frames == 0:
                        now = time.time()
                        dt = now - fps_timer_start
                        if dt > 0:
                            curr_fps = cfg.fps_update_frames / dt
                            fps_hist.append(curr_fps)
                            if len(fps_hist) > cfg.fps_history_size:
                                fps_hist.pop(0)
                            current_fps = float(np.mean(fps_hist))
                        fps_timer_start = now

                    vis = Visualizer.draw_overlay(vis, tracks_snapshot, current_fps, paused)
                    

                    # - THEFT ALERT OVERLAY (main thread only) -
                    theft_alert = any(
                        hasattr(tinfo, "ml_score") and tinfo.ml_score > 0.8
                        for tinfo in tracks_snapshot.values()
                    )
                    if theft_alert:
                        cv2.putText(
                            vis,
                            "🚨 THEFT DETECTED",
                            (20, 80),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1.0,
                            (0, 0, 255),
                            3,
                        )

                    
                    
                    
                    
                    
                    
                    
                    display_frame = vis

            if display_frame is not None:
                cv2.imshow(cfg.window_name, display_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break
            elif key == ord(' '):
                paused = not paused
                print("PAUSED" if paused else "RESUMED")
            elif key == ord('s'):
                screenshot_count += 1
                fname = f"pose_realtime_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
                if display_frame is not None:
                    cv2.imwrite(fname, display_frame)
                    print(f"📸 Saved {fname}")
            elif key == ord('r'):
                with tracks_lock:
                    tracks.clear()
                frame_display_count = 0
                fps_hist.clear()
                current_fps = 0.0
                print("🔄 Reset tracks & FPS")
            elif key == ord('m') or key == ord('M'):
                cfg.use_bbox_smoothing = not cfg.use_bbox_smoothing
                print(f"📍 Smoothing: {'ON (Light)' if cfg.use_bbox_smoothing else 'OFF (Responsive)'}")
            elif key == ord('+'):
                cfg.confidence = min(0.85, cfg.confidence + 0.05)
                print(f"⬆️ DetConf: {cfg.confidence:.2f}")
            elif key == ord('-'):
                cfg.confidence = max(0.20, cfg.confidence - 0.05)
                print(f"⬇️ DetConf: {cfg.confidence:.2f}")
            elif key == ord('t'):
                print("📥 Collecting theft samples...")

                X_new, y_new = [], []

                # use latest snapshot of tracks
                with tracks_lock:
                    tracks_snapshot = dict(tracks)

                for tid in tracks_snapshot:
                    # require full window for dataset (no min_frames)
                    seq = sequence_collector.get_sequence(tid, min_frames=10)
                    if seq is not None:
                        X_new.append(seq)
                        y_new.append(1)

                if len(X_new) == 0:
                    print("⚠ No valid sequences to save.")
                    continue

                X_new = np.array(X_new, dtype=np.float32)
                y_new = np.array(y_new, dtype=np.int64)

                total = safe_append_dataset(
                    "datasets/X_theft.npy",
                    "datasets/y_theft.npy",
                    X_new,
                    y_new,
                    label_name="theft"
                )


            elif key == ord('n'):
                print("📥 Collecting normal samples...")

                X_new, y_new = [], []

                # thread-safe snapshot of tracks
                with tracks_lock:
                    tracks_snapshot = dict(tracks)

                # require full window for dataset saving
                for tid in tracks_snapshot:
                    seq = sequence_collector.get_sequence(tid)
                    if seq is not None:
                        X_new.append(seq)
                        y_new.append(0)

                if len(X_new) == 0:
                    print("⚠ No valid normal sequences to save.")
                    continue

                X_new = np.array(X_new, dtype=np.float32)
                y_new = np.array(y_new, dtype=np.int64)

                # ---- SAFE APPEND ----
                try:
                    os.makedirs("datasets", exist_ok=True)

                    # first time saving (no old dataset)
                    if not os.path.exists("datasets/X_normal.npy"):
                        np.save("datasets/X_normal.npy", X_new)
                        np.save("datasets/y_normal.npy", y_new)
                        print(f"💾 Saved first normal dataset with {len(X_new)} samples.")
                        continue

                    # backup old files
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    backup_X = f"datasets/X_normal.npy.backup_{timestamp}"
                    backup_y = f"datasets/y_normal.npy.backup_{timestamp}"
                    shutil.copy2("datasets/X_normal.npy", backup_X)
                    shutil.copy2("datasets/y_normal.npy", backup_y)
                    print(f"🛡 Backup created for normal dataset: {backup_X}")

                    # load old dataset
                    X_old = np.load("datasets/X_normal.npy")
                    y_old = np.load("datasets/y_normal.npy")

                    # check dimension mismatch
                    if X_old.shape[1] != X_new.shape[1]:
                        print("⚠ Feature dimension mismatch. Starting NEW normal dataset.")
                        X_final = X_new
                        y_final = y_new
                    else:
                        # append normally
                        X_final = np.vstack([X_old, X_new])
                        y_final = np.hstack([y_old, y_new])

                    np.save("datasets/X_normal.npy", X_final)
                    np.save("datasets/y_normal.npy", y_final)

                    print(f"💾 Saved {len(X_new)} normal sequences. Total now: {len(X_final)}")

                except Exception as e:
                    print("❌ Error saving normal dataset:", e)

    except KeyboardInterrupt:
        print("\n⚠️ Keyboard interrupt")
    finally:
        # Shutdown
        running = False
        time.sleep(0.2)
        cap.release()
        cv2.destroyAllWindows()

        print("\n" + "=" * 60)
        print("📊 SESSION SUMMARY")
        print("=" * 60)
        print(f"Approx FPS (last interval): {current_fps:.1f}")
        with tracks_lock:
            persons = sum(1 for t in tracks.values() if t.label == "person")
            bags = sum(1 for t in tracks.values() if t.label == "bag")
            objs = sum(1 for t in tracks.values() if t.label not in ("person", "bag"))
        print(f"Tracks at end: Persons={persons}, Bags={bags}, Objects={objs}")
        print("=" * 60)


if __name__ == "__main__":
    main()
