"""
AI Service — pipeline lifecycle manager (singleton).

Updated to v2 stack (Updated_AI_Engine_v2 logic at highest priority):
  • PersonDetector        (YOLOv8m — YOLO_CONFIDENCE=0.35)
  • ReIDExtractor         (osnet_ain_x1_0 — mean-centred L2 norm)
  • GlobalTheftDetector   (X3D-S per-global-ID state machine — replaces
                           TheftClassifier + ClipBuffer pair)
  • CrossCameraMatcher    (FAISS — corrected 0.555/0.70 thresholds)
  • GlobalIdentityDatabase (thread-safe, best-match-in-buffer)

Thread-safety contract
----------------------
inference_lock  — must be held around every GPU forward pass
                  (YOLO detect, OSNet extract_batch, X3D state.run_inference).
                  Prevents CUDA context contention when multiple
                  ContinuousMonitor threads run simultaneously.

state_lock      — must be held around every mutation of:
                    matcher (FAISS index), theft_detector states,
                    theft_scores, x3d_frame_counters.
                  GlobalIdentityDatabase manages its own internal lock;
                  callers do NOT need state_lock for db calls.

Both locks are exposed as attributes so InferenceRunner (and any
future consumer) share the exact same lock objects.

Public interface (unchanged from old service):
  AIService.get_instance()  → AIService singleton
  .initialize()             → bool
  .is_ready()               → bool
  .get_model_info()         → dict  (JSON-serialisable)
  .device                   → str
"""

import os
import threading
import torch
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

# ── model path constants ───────────────────────────────────────────────────────
_BACKEND_DIR     = Path(__file__).resolve().parent.parent.parent.parent
_AI_PIPELINE_DIR = _BACKEND_DIR / "ai_pipeline"

# ── pipeline imports ───────────────────────────────────────────────────────────
from ai_pipeline.detection.detector            import PersonDetector
from ai_pipeline.reid.extractor                import ReIDExtractor
from ai_pipeline.theft_detection.x3d_detector  import GlobalTheftDetector
from ai_pipeline.matching.matcher              import CrossCameraMatcher
from ai_pipeline.database.identity_db          import GlobalIdentityDatabase
from ai_pipeline.ai_config.config              import Config


class AIService:
    """
    Singleton service for the v2 AI pipeline.

    Usage
    -----
    service = AIService.get_instance()   # or AIService()
    service.initialize()                 # called once in apps.py ready()
    runner  = InferenceRunner()          # one per camera, shares service locks
    """

    _instance: Optional["AIService"] = None
    _class_lock = threading.Lock()
    _initialized: bool = False

    # ── singleton machinery ───────────────────────────────────────────────────

    def __new__(cls) -> "AIService":
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AIService":
        return cls()

    def __init__(self) -> None:
        if self._initialized:
            return

        # ── pipeline models (populated by initialize()) ───────────────────
        self.detector:        Optional[PersonDetector]        = None
        self.reid:            Optional[ReIDExtractor]         = None
        self.theft_detector:  Optional[GlobalTheftDetector]   = None
        self.matcher:         Optional[CrossCameraMatcher]    = None
        self.db:              Optional[GlobalIdentityDatabase] = None

        # ── legacy alias kept for backward compatibility ──────────────────
        # inference_runner.py may reference ai_service.x3d and
        # ai_service.clip_buffer from the old API. Point them at
        # the new unified object so no AttributeError is raised.
        self.x3d:         Optional[GlobalTheftDetector] = None   # alias
        self.clip_buffer: None = None                             # no-op sentinel

        # ── shared per-global-id state (guarded by state_lock) ───────────
        # global_id → latest X3D theft probability (None = not yet scored)
        self.theft_scores:       Dict[int, Optional[float]] = {}
        # global_id → frame counter used to throttle X3D calls
        self.x3d_frame_counters: Dict[int, int] = {}

        # ── thread-safety locks ───────────────────────────────────────────
        self.inference_lock = threading.RLock()  # GPU forward passes (RLock: re-entrant so YOLO + X3D can both acquire in same thread)
        self.state_lock     = threading.Lock()   # FAISS / theft_detector / counters

        self.device: str = "cpu"

        # ── model paths from ai_pipeline config (single source of truth) ──
        self._yolo_weights = Config.YOLO_MODEL
        self._x3d_weights  = Config.X3D_CHECKPOINT

        AIService._initialized = True

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self) -> bool:
        """
        Load all pipeline models.  Called once by apps.AiEngineConfig.ready().
        """
        try:
            logger.info("🚀 Initialising AI Service v2 (YOLOv8 + OSNet-AIN + X3D State Machine) …")

            # ── Device ────────────────────────────────────────────────────
            if torch.cuda.is_available():
                self.device = "cuda:0"
                torch.backends.cudnn.benchmark = True
                # Cap VRAM to 85 % — leaves headroom for CUDA kernel buffers.
                torch.cuda.set_per_process_memory_fraction(0.85, device=0)
                logger.info(f"✅ CUDA: {torch.cuda.get_device_name(0)} | VRAM cap: 85 %")
            else:
                self.device = "cpu"
                logger.warning("⚠️  CUDA not available — using CPU (slower)")

            # Override Config class-attributes so every pipeline module
            # sees the same device and model paths.
            Config.DEVICE         = self.device.split(":")[0]   # "cuda" | "cpu"
            Config.YOLO_MODEL     = self._yolo_weights
            Config.X3D_CHECKPOINT = self._x3d_weights
            # Keep legacy alias in sync
            Config.X3D_MODEL_PATH = self._x3d_weights

            # ── YOLOv8 detector ───────────────────────────────────────────
            logger.info(f"📦 Loading YOLOv8 detector: {self._yolo_weights}")
            self.detector = PersonDetector()
            logger.info("✅ Detector loaded")

            # ── OSNet-AIN ReID extractor ──────────────────────────────────
            logger.info(f"📦 Loading OSNet-AIN ReID extractor ({Config.REID_MODEL_NAME}) …")
            self.reid = ReIDExtractor()
            logger.info("✅ ReID extractor loaded")

            # ── X3D-S GlobalTheftDetector (v2 state machine) ──────────────
            logger.info(f"📦 Loading X3D-S GlobalTheftDetector: {self._x3d_weights}")
            self.theft_detector = GlobalTheftDetector(
                checkpoint_path=self._x3d_weights,
                device=Config.DEVICE,
            )
            # Keep legacy .x3d alias pointing at the same object
            self.x3d = self.theft_detector
            logger.info(
                f"✅ GlobalTheftDetector loaded  "
                f"(clip={Config.X3D_CLIP_LENGTH}, stride={Config.X3D_INFER_INTERVAL}, "
                f"smooth={Config.X3D_SMOOTH_WINDOW}, "
                f"consecutive={Config.X3D_CONSECUTIVE_REQUIRED}, "
                f"cooldown={Config.X3D_COOLDOWN_SECONDS}s)"
            )

            # ── FAISS cross-camera matcher ────────────────────────────────
            logger.info("📦 Initialising FAISS cross-camera matcher …")
            self.matcher = CrossCameraMatcher()
            logger.info("✅ Matcher initialised")

            # ── Global identity DB (pure in-memory) ───────────────────────
            logger.info("📦 Initialising GlobalIdentityDatabase …")
            self.db = GlobalIdentityDatabase()
            logger.info("✅ Identity DB initialised")

            # ── YOLO warmup ───────────────────────────────────────────────
            logger.info("🔥 Warming up YOLO …")
            dummy = np.zeros((640, 640, 3), dtype=np.uint8)
            self.detector.detect(dummy)
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            logger.info("✅ Warmup complete")

            logger.info("✅ AI Service v2 ready")
            return True

        except Exception as exc:
            logger.error(f"❌ AI Service init failed: {exc}", exc_info=True)
            raise

    # ── public API ─────────────────────────────────────────────────────────────

    def is_ready(self) -> bool:
        """Return True when all pipeline components are loaded."""
        return (
            self.detector       is not None
            and self.reid       is not None
            and self.theft_detector is not None
            and self.matcher    is not None
            and self.db         is not None
        )

    def get_model_info(self) -> Dict[str, Any]:
        """Return a JSON-serialisable dict describing loaded models."""
        return {
            "detection_model":          self._yolo_weights,
            "reid_model":               f"OSNet-AIN ({Config.REID_MODEL_NAME})",
            "x3d_model":                self._x3d_weights,
            "x3d_clip_length":          Config.X3D_CLIP_LENGTH,
            "x3d_infer_interval":       Config.X3D_INFER_INTERVAL,
            "x3d_smooth_window":        Config.X3D_SMOOTH_WINDOW,
            "x3d_theft_threshold":      Config.X3D_THEFT_THRESH,
            "x3d_suspicious_threshold": Config.X3D_SUSPICIOUS_THRESHOLD,
            "x3d_consecutive_required": Config.X3D_CONSECUTIVE_REQUIRED,
            "x3d_cooldown_seconds":     Config.X3D_COOLDOWN_SECONDS,
            "reid_threshold_same_cam":  Config.MATCH_THRESHOLD_SAME_CAM,
            "reid_threshold_diff_cam":  Config.MATCH_THRESHOLD_DIFF_CAM,
            "device":                   self.device,
            "cuda_available":           torch.cuda.is_available(),
            "models_loaded":            self.is_ready(),
        }

    # ── maintenance helpers (called from InferenceRunner) ─────────────────────

    def prune_expired_identities(self) -> None:
        """Prune expired global IDs from DB and TheftDetector states."""
        pruned = self.db.prune_expired()
        if pruned > 0:
            active = set(self.db.get_all_identities().keys())
            with self.state_lock:
                self.theft_detector.prune_states(active)
                # Clean up counter dicts
                for gid in list(self.theft_scores.keys()):
                    if gid not in active:
                        self.theft_scores.pop(gid, None)
                        self.x3d_frame_counters.pop(gid, None)

    def rebuild_matcher_index(self) -> None:
        """Rebuild the FAISS index from current identity DB embeddings."""
        identities    = self.db.get_all_identities()
        identity_data = {
            gid: {"embedding_buffer": list(rec.embedding_buffer)}
            for gid, rec in identities.items()
        }
        with self.state_lock:
            self.matcher.rebuild_index(identity_data)


# ── global suspect registry methods ───────────────────────────────────────────

    def add_active_thief(self, global_id: int) -> None:
        with self.state_lock:
            gid_str = str(global_id)
            thieves = cache.get('active_thief_global_ids', [])
            thieves = [str(x) for x in thieves]
            if gid_str not in thieves:
                thieves.append(gid_str)
                cache.set('active_thief_global_ids', thieves, timeout=None)

    def remove_active_thief(self, global_id: int) -> None:
        with self.state_lock:
            gid_str = str(global_id)
            thieves = cache.get('active_thief_global_ids', [])
            thieves = [str(x) for x in thieves]
            if gid_str in thieves:
                thieves.remove(gid_str)
                cache.set('active_thief_global_ids', thieves, timeout=None)

    def is_active_thief(self, global_id: int) -> bool:
        if global_id is None: return False
        gid_str = str(global_id)
        thieves = cache.get('active_thief_global_ids', [])
        return gid_str in [str(x) for x in thieves]


# ── module-level singleton ────────────────────────────────────────────────────
ai_service = AIService()
