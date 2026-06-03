"""
Person Detection Module — YOLOv8 (Ultralytics).

Source: Updated_AI_Engine_v2 (identical logic kept with full docstrings).

Detects persons in a frame and returns bounding boxes + confidence scores.
Only the 'person' class (COCO class 0) is returned.
Supports single-frame and batch inference.
"""

import numpy as np
from ultralytics import YOLO
from ai_pipeline.ai_config.config import Config


class PersonDetector:
    """YOLOv8-based person detector optimised for real-time inference."""

    def __init__(self):
        """
        Initialize YOLOv8.
        Weights are downloaded automatically on first run if not found.
        """
        self.model            = YOLO(Config.YOLO_MODEL)
        self.model.to(Config.DEVICE)
        self.conf_threshold   = Config.YOLO_CONFIDENCE
        self.iou_threshold    = Config.YOLO_IOU_THRESHOLD
        self.person_class_id  = Config.YOLO_PERSON_CLASS_ID
        self.img_size         = Config.YOLO_IMG_SIZE

        print(f"[Detector] YOLOv8 loaded: {Config.YOLO_MODEL} on {Config.DEVICE}  "
              f"conf={self.conf_threshold}")

    def detect(self, frame: np.ndarray) -> list:
        """
        Run person detection on a single frame.

        Args:
            frame: BGR image (H, W, 3).

        Returns:
            List of dicts: {'bbox': [x1,y1,x2,y2], 'confidence': float, 'class_id': int}
        """
        results = self.model(
            frame,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            imgsz=self.img_size,
            classes=[self.person_class_id],
            verbose=False,
        )

        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is None or len(boxes) == 0:
                continue
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                conf   = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                detections.append({
                    "bbox":       [int(x1), int(y1), int(x2), int(y2)],
                    "confidence": conf,
                    "class_id":   cls_id,
                })
        return detections

    def detect_batch(self, frames: list) -> list:
        """
        Run person detection on a batch of frames.

        Args:
            frames: List of BGR images.

        Returns:
            List of detection lists, one per frame.
        """
        results = self.model(
            frames,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            imgsz=self.img_size,
            classes=[self.person_class_id],
            verbose=False,
        )

        all_detections = []
        for result in results:
            frame_dets = []
            boxes = result.boxes
            if boxes is not None and len(boxes) > 0:
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                    conf   = float(box.conf[0].cpu().numpy())
                    cls_id = int(box.cls[0].cpu().numpy())
                    frame_dets.append({
                        "bbox":       [int(x1), int(y1), int(x2), int(y2)],
                        "confidence": conf,
                        "class_id":   cls_id,
                    })
            all_detections.append(frame_dets)
        return all_detections
