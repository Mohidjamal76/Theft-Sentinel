"""
X3D Theft Classifier Module — COMPATIBILITY SHIM.

THIS FILE IS DEPRECATED AND MUST NOT BE USED DIRECTLY.

The original classifier.py used SAMPLED_FRAMES=180, but the X3D-S model
was trained on 64-frame clips (step2_train.py).  Using 180 frames produces
garbage predictions due to the temporal dimension mismatch.

The authoritative, correctly-configured implementation lives in:
    ai_pipeline/theft_detection/x3d_detector.py  ← USE THIS

That module provides:
  - GlobalTheftDetector   — full per-identity state machine (model shared)
  - TheftState            — per-global-ID frame buffer, score history, cooldown
  - load_x3d_model()      — checkpoint loader matching step2_train architecture

The symbols below are re-exported only to avoid ImportError in any legacy
caller that was already referencing this module.  Do NOT write new code
that imports from here.
"""

import warnings

warnings.warn(
    "ai_pipeline.x3d.classifier is deprecated and superseded by "
    "ai_pipeline.theft_detection.x3d_detector (v2, 64-frame clips). "
    "Update your imports to use GlobalTheftDetector from x3d_detector.",
    DeprecationWarning,
    stacklevel=2,
)

# ── Re-export the correct v2 implementations ──────────────────────────────────
from ai_pipeline.theft_detection.x3d_detector import (   # noqa: F401, E402
    GlobalTheftDetector,
    TheftState,
    load_x3d_model,
)

# ── Legacy aliases so old callers don't immediately crash ─────────────────────
# TheftClassifier → GlobalTheftDetector
TheftClassifier = GlobalTheftDetector

__all__ = [
    "GlobalTheftDetector",
    "TheftClassifier",   # legacy alias
    "TheftState",
    "load_x3d_model",
]
