"""
Central Configuration — Updated_AI_Engine_v2.

Merges the best settings from:
  - New_MCMT          → Multi-Camera Tracking (osnet_ain_x1_0, better thresholds,
                         EMA FPS, dual FAISS+DB matching strategy)
  - Updated_AI_Engine → Theft Detection (X3D-S params, YOLO conf 0.35,
                         wider display window for theft banner)

All tunable parameters live here; no other file hard-codes constants.
"""

import torch


class Config:
    """Master configuration for the Theft Sentinel MCMT v2 system."""

    # ──────────────────────────────────────────────
    # Device
    # ──────────────────────────────────────────────
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

    # ──────────────────────────────────────────────
    # Camera / Input
    # ──────────────────────────────────────────────
    # Add your sources: file paths, RTSP/HTTP URLs, or integer device indices.
    CAMERA_SOURCES = [
        # ── Live / network cameras ──
        "http://192.168.10.28:8080/video",      # phone cam (New_MCMT style)
        "http://192.168.10.28:8080/video",      # phone cam (New_MCMT style)
        # "rtsp://user:pass@192.168.1.100/stream1",
        # 0,                                       # USB webcam

        # ── Pre-recorded theft test clips ──
        # "test_videos/theft/A001_04271805_F781_fast_flip.mp4",
        # "test_videos/Theft/WhatsApp-Video_2026-05-09_at_00.13.57.mp4",
        # "test_videos/Theft/WhatsApp-Video_2026-05-09_at_00.13.57.mp4",
        # "test_videos/Theft/A001_04280729_G171.mp4",

        # ── General multi-camera test clips ──
        # "test_videos/cam1.mp4",
        # "test_videos/cam2.mp4",
    ]
    CAMERA_IDS  = [1, 2, 3, 4, 5, 6]   # sliced to match CAMERA_SOURCES length
    TARGET_FPS  = 25                     # Max processing FPS per camera
    FRAME_WIDTH  = 640
    FRAME_HEIGHT = 480

    # ──────────────────────────────────────────────
    # Detection (YOLOv8)
    # ──────────────────────────────────────────────
    YOLO_MODEL           = "yolov8n.pt"
    YOLO_CONFIDENCE      = 0.35   # 0.35 from Updated_AI_Engine (better recall for theft)
    YOLO_IOU_THRESHOLD   = 0.5
    YOLO_PERSON_CLASS_ID = 0
    YOLO_IMG_SIZE        = 640

    # ──────────────────────────────────────────────
    # Tracking (DeepSORT)
    # ──────────────────────────────────────────────
    DEEPSORT_MAX_AGE            = 50
    DEEPSORT_N_INIT             = 3
    DEEPSORT_MAX_IOU_DISTANCE   = 0.7
    DEEPSORT_MAX_COSINE_DISTANCE= 0.3
    DEEPSORT_NN_BUDGET          = 100

    # ──────────────────────────────────────────────
    # ReID (OSNet) — osnet_ain_x1_0 from New_MCMT
    # (Attentive Instance Normalization handles cross-camera lighting shifts better)
    # ──────────────────────────────────────────────
    REID_MODEL_NAME  = "osnet_ain_x1_0"   # New_MCMT: better cross-domain robustness
    REID_MODEL_WEIGHTS = "imagenet"
    REID_EMBEDDING_DIM = 512
    REID_INPUT_SIZE    = (256, 128)        # (H, W)
    REID_BATCH_SIZE    = 32

    # ──────────────────────────────────────────────
    # Cross-Camera Matching — thresholds from New_MCMT
    # (stricter same-cam 0.6, tighter cross-cam 0.7 reduce false merges)
    # ──────────────────────────────────────────────
    MATCH_THRESHOLD_SAME_CAM = 0.6   # New_MCMT value
    MATCH_THRESHOLD_DIFF_CAM = 0.50   # New_MCMT value
    MATCH_TEMPORAL_WINDOW    = 30.0   # seconds
    MATCH_MIN_EMBEDDINGS     = 3

    # ──────────────────────────────────────────────
    # Global Identity Database
    # ──────────────────────────────────────────────
    MAX_EMBEDDINGS_PER_IDENTITY = 50
    EMBEDDING_UPDATE_INTERVAL   = 5    # frames between embedding updates
    IDENTITY_EXPIRY_TIME        = 300.0  # seconds before an unseen ID is pruned

    # ──────────────────────────────────────────────
    # FAISS
    # ──────────────────────────────────────────────
    FAISS_USE_GPU = torch.cuda.is_available()
    FAISS_NPROBE  = 10   # unused with IndexFlatIP but kept for IVF experiments

    # ──────────────────────────────────────────────
    # X3D-S Theft Detection — MUST MATCH TRAINING
    # (complete module from Updated_AI_Engine)
    # ──────────────────────────────────────────────

    # Checkpoint produced by step2_train.py
    X3D_CHECKPOINT = "best_model.pth"

    # Temporal clip settings (must match training step2_train config)
    X3D_CLIP_LENGTH   = 64    # frames fed to X3D (= BUFFER_FRAMES)
    X3D_SPATIAL_SIZE  = 224   # crop resize resolution
    X3D_BUFFER_FRAMES = 64    # rolling frame buffer per identity
    X3D_INFER_INTERVAL= 16    # run inference every N new frames (sliding stride)
    X3D_PAD_RATIO     = 0.40  # bbox padding (must match step1_preprocess)

    # Kinetics-400 normalization (must match training _to_tensor)
    X3D_NORM_MEAN = [0.45, 0.45, 0.45]
    X3D_NORM_STD  = [0.225, 0.225, 0.225]

    # Detection state machine
    X3D_SMOOTH_WINDOW         = 3     # rolling average over N inferences
    X3D_THEFT_THRESH          = 0.380  # smoothed score threshold for suspicion
    X3D_CONSECUTIVE_REQUIRED  = 1     # consecutive above-threshold to confirm
    X3D_COOLDOWN_SECONDS      = 8.0   # seconds before a new alert can fire
    X3D_RESET_AFTER_ABSENT    = 150   # frames without person before state reset (~6 s at 25 fps)

    # ──────────────────────────────────────────────
    # Visualization — wider window from Updated_AI_Engine for theft banner
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
