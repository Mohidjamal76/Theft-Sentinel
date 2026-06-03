"""
Central Configuration — Theft Sentinel Backend AI Pipeline.

Merged from Updated_AI_Engine_v2:
  - osnet_ain_x1_0 ReID model (Attentive Instance Normalization)
  - Corrected cross-camera thresholds (0.555 same-cam, 0.70 diff-cam)
  - Full X3D-S state machine parameters (clip=64, stride=16, smooth=5,
    consecutive=3, cooldown=8s, reset_after_absent=150)
  - Kinetics-400 normalisation constants for X3D
  - IoU YOLO-bbox alignment, dense frame buffer fill (FIX 2 & 3)
  - EMA FPS, rising-edge alert counting

All tunable parameters live here; no other file hard-codes constants.
"""

import torch
import os

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Config:
    """Master configuration for the Theft Sentinel MCMT v2 system."""

    # ──────────────────────────────────────────────
    # Device
    # ──────────────────────────────────────────────
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

    # ──────────────────────────────────────────────
    # Camera / Input
    # ──────────────────────────────────────────────
    CAMERA_SOURCES = [
        "test_videos/cam1.mp4",
        "test_videos/cam2.mp4",
    ]
    CAMERA_IDS   = [1, 2, 3, 4, 5, 6]   # sliced to match CAMERA_SOURCES length
    TARGET_FPS   = 25                     # Max processing FPS per camera (EMA seed)
    FRAME_WIDTH  = 640
    FRAME_HEIGHT = 480

    # ──────────────────────────────────────────────
    # Detection (YOLOv8)
    # Updated_AI_Engine_v2: conf=0.35 (better theft recall), model=yolov8n.pt
    # ──────────────────────────────────────────────
    YOLO_MODEL           = os.path.join(_BASE, "yolov8n.pt")
    YOLO_CONFIDENCE      = 0.35   # 0.35 from Updated_AI_Engine (better recall for theft)
    YOLO_IOU_THRESHOLD   = 0.5
    YOLO_PERSON_CLASS_ID = 0
    YOLO_IMG_SIZE        = 640

    # ──────────────────────────────────────────────
    # Tracking (DeepSORT)
    # ──────────────────────────────────────────────
    DEEPSORT_MAX_AGE             = 50
    DEEPSORT_N_INIT              = 3
    DEEPSORT_MAX_IOU_DISTANCE    = 0.7
    DEEPSORT_MAX_COSINE_DISTANCE = 0.3
    DEEPSORT_NN_BUDGET           = 100

    # ──────────────────────────────────────────────
    # ReID (OSNet-AIN) — Updated_AI_Engine_v2: osnet_ain_x1_0
    # Attentive Instance Normalization handles cross-camera lighting shifts better.
    # ──────────────────────────────────────────────
    REID_MODEL_NAME    = "osnet_ain_x1_0"   # upgraded from osnet_x1_0
    REID_MODEL_WEIGHTS = "imagenet"
    REID_EMBEDDING_DIM = 512
    REID_INPUT_SIZE    = (256, 128)          # (H, W)
    REID_BATCH_SIZE    = 32

    # ──────────────────────────────────────────────
    # Cross-Camera Matching — thresholds from Updated_AI_Engine_v2
    # (stricter same-cam 0.555, tighter cross-cam 0.70 reduce false merges)
    # ──────────────────────────────────────────────
    MATCH_THRESHOLD_SAME_CAM = 0.6  # v2 exact — strict same-cam to prevent false merges
    MATCH_THRESHOLD_DIFF_CAM = 0.50   # v2 exact — high bar for cross-camera identity merge
    MATCH_TEMPORAL_WINDOW    = 30.0    # seconds
    MATCH_MIN_EMBEDDINGS     = 3

    # ──────────────────────────────────────────────
    # Global Identity Database
    # ──────────────────────────────────────────────
    MAX_EMBEDDINGS_PER_IDENTITY = 50
    EMBEDDING_UPDATE_INTERVAL   = 5       # frames between embedding updates
    IDENTITY_EXPIRY_TIME        = 300.0   # seconds before unseen ID is pruned

    # ──────────────────────────────────────────────
    # FAISS
    # ──────────────────────────────────────────────
    FAISS_USE_GPU = torch.cuda.is_available()
    FAISS_NPROBE  = 10   # unused with IndexFlatIP but kept for IVF experiments

    # ──────────────────────────────────────────────
    # X3D-S Theft Detection — Updated_AI_Engine_v2 state machine
    # MUST MATCH TRAINING (step2_train.py / Deployment_v3_final.py)
    # ──────────────────────────────────────────────

    # Checkpoint produced by step2_train.py
    X3D_CHECKPOINT  = os.path.join(_BASE, "best_model.pth")

    # Temporal clip settings (must match training step2_train config)
    X3D_CLIP_LENGTH   = 64    # frames fed to X3D (= BUFFER_FRAMES)
    X3D_SPATIAL_SIZE  = 224   # crop resize resolution
    X3D_BUFFER_FRAMES = 64    # rolling frame buffer per identity
    X3D_INFER_INTERVAL= 16    # run inference every N new frames (sliding stride)
    X3D_PAD_RATIO     = 0.40  # bbox padding (must match step1_preprocess)

    # Kinetics-400 normalisation (must match training _to_tensor)
    X3D_NORM_MEAN = [0.45, 0.45, 0.45]
    X3D_NORM_STD  = [0.225, 0.225, 0.225]

    # Detection state machine
    X3D_SMOOTH_WINDOW         = 3     # rolling average over N inferences
    X3D_THEFT_THRESH          = 0.380  # smoothed score threshold for suspicion (v2 calibrated)
    X3D_CONSECUTIVE_REQUIRED  = 1     # consecutive above-threshold to confirm theft
    X3D_COOLDOWN_SECONDS      = 8.0   # seconds before a new alert can fire
    X3D_RESET_AFTER_ABSENT    = 150   # frames without person before state reset (~6 s at 25 fps)

    # ── Legacy aliases kept for backward compat with inference_runner ─────────
    # (inference_runner.py uses X3D_INFERENCE_EVERY / X3D_CLIP_FRAMES /
    #  X3D_THEFT_THRESHOLD / X3D_SUSPICIOUS_THRESHOLD)
    X3D_INFERENCE_EVERY      = X3D_INFER_INTERVAL       # = 16
    X3D_CLIP_FRAMES          = X3D_CLIP_LENGTH           # = 64
    X3D_THEFT_THRESHOLD      = X3D_THEFT_THRESH          # = 0.380
    X3D_SUSPICIOUS_THRESHOLD = 0.50  # score range [0.50, 0.70) → "suspicious" label

    # Old path alias (still referenced by ai_service.py on initial load)
    X3D_MODEL_PATH = X3D_CHECKPOINT

    # ──────────────────────────────────────────────
    # Visualization — wider window from Updated_AI_Engine_v2 for theft banner
    # ──────────────────────────────────────────────
    VIS_SHOW_LOCAL_ID  = True
    VIS_SHOW_GLOBAL_ID = True
    VIS_BBOX_THICKNESS = 2
    VIS_FONT_SCALE     = 0.6
    VIS_WINDOW_WIDTH   = 1280   # wider to accommodate multi-cam grid + theft banner
    VIS_WINDOW_HEIGHT  = 720

    # ──────────────────────────────────────────────
    # Logging
    # ──────────────────────────────────────────────
    LOG_LEVEL      = "INFO"
    LOG_DETECTIONS = False   # toggle with 'd' key at runtime
