"""
Theft detection package — X3D-S per-global-ID state machine.
Imported as ai_pipeline.theft_detection.x3d_detector
"""
from ai_pipeline.theft_detection.x3d_detector import (
    GlobalTheftDetector,
    TheftState,
    load_x3d_model,
)

__all__ = ["GlobalTheftDetector", "TheftState", "load_x3d_model"]
