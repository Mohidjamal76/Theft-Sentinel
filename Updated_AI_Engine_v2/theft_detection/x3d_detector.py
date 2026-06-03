"""
X3D-S Theft Detection Module — Per-Person State Machine.

Source: Updated_AI_Engine (best theft detection logic — complete, unmodified).

This module wraps the exact same X3D-S inference logic from
Deployment_v3_final.py, adapted to work per global identity
instead of per single camera.

Key design:
  - One TheftState instance per global_id tracks that person's
    frame buffer, score history, consecutive count, and cooldown.
  - The X3D model is loaded once by GlobalTheftDetector and shared
    across all identities — no duplicate model loading.
  - Inference is triggered every X3D_INFER_INTERVAL new frames once
    the buffer is full (BUFFER_FRAMES = CLIP_LENGTH = 64).
  - Detection logic is IDENTICAL to Deployment_v3_final.py:
      smoothed score → consecutive check → cooldown.

Three critical fixes applied in main.py (not here):
  FIX 1  track_id type normalisation (str()) — avoids dict-key mismatches.
  FIX 2  Dense frame pushing — every confirmed track every frame, so the
         64-frame buffer fills at camera FPS (not sparsely on reid success).
  FIX 3  Raw YOLO bbox (IoU-matched) used for X3D, not DeepSORT Kalman box —
         matches step1_preprocess_yolo_crop.py training crop exactly.
"""

import time
import collections
import numpy as np
import torch
import torch.nn as nn
import cv2

from config.config import Config


# ── Preprocessing tensors (built once, reused every inference) ────────────────

_NORM_MEAN = torch.tensor(Config.X3D_NORM_MEAN).view(3, 1, 1, 1)
_NORM_STD  = torch.tensor(Config.X3D_NORM_STD).view(3, 1, 1, 1)


def _frames_to_tensor(frames_rgb: list, crop_box: list) -> torch.Tensor:
    """
    Preprocess a list of RGB frames into the X3D input tensor.

    Exactly matches Deployment_v3_final.py frames_to_tensor():
      - Crop using crop_box
      - Resize to SPATIAL_SIZE x SPATIAL_SIZE
      - Sample CLIP_LENGTH frames via linspace (no subsampling when
        BUFFER_FRAMES == CLIP_LENGTH == 64)
      - Convert to float [0, 1], normalise with Kinetics-400 stats
      - Return shape: (1, 3, T, H, W)
    """
    x1, y1, x2, y2 = crop_box
    SPATIAL  = Config.X3D_SPATIAL_SIZE
    processed = []

    for frame_rgb in frames_rgb:
        crop = frame_rgb[y1:y2, x1:x2]
        if crop.size == 0:
            crop = frame_rgb
        resized = cv2.resize(crop, (SPATIAL, SPATIAL))
        processed.append(resized)

    total   = len(processed)
    indices = np.linspace(0, total - 1, Config.X3D_CLIP_LENGTH).astype(int)
    clip    = np.array([processed[i] for i in indices], dtype=np.uint8)

    tensor  = torch.from_numpy(clip).permute(3, 0, 1, 2).float() / 255.0
    tensor  = (tensor - _NORM_MEAN) / _NORM_STD
    return tensor.unsqueeze(0)   # (1, 3, T, H, W)


def _apply_padding(box: list, frame_h: int, frame_w: int) -> list:
    """Apply PAD_RATIO padding around a bounding box, clamped to frame bounds."""
    x1, y1, x2, y2 = box
    bw  = x2 - x1
    bh  = y2 - y1
    pad = Config.X3D_PAD_RATIO
    x1  = max(0,       int(x1 - pad * bw))
    y1  = max(0,       int(y1 - pad * bh))
    x2  = min(frame_w, int(x2 + pad * bw))
    y2  = min(frame_h, int(y2 + pad * bh))
    return [x1, y1, x2, y2]


# ── Per-person theft state machine ────────────────────────────────────────────

class TheftState:
    """
    Per-global-ID theft detection state machine.

    Mirrors the TheftDetector class from Deployment_v3_final.py
    operating on a per-identity basis: each tracked person has
    independent frame buffer, score history, and cooldown.

    Detection flow (identical to Deployment_v3_final.py):
      1. Buffer BUFFER_FRAMES consecutive RGB frames + bounding boxes.
      2. Every INFER_INTERVAL new frames → run X3D inference.
      3. Rolling average of last SMOOTH_WINDOW raw scores.
      4. If smoothed score >= THEFT_THRESH for CONSECUTIVE_REQUIRED
         consecutive inferences → THEFT CONFIRMED.
      5. After confirmation → cooldown for COOLDOWN_SECONDS.
      6. No person for RESET_AFTER_ABSENT frames → reset score state
         (cooldown preserved if still active).
    """

    def __init__(self, global_id: int):
        self.global_id = global_id

        self.frame_buffer  = collections.deque(maxlen=Config.X3D_BUFFER_FRAMES)
        self.box_buffer    = collections.deque(maxlen=Config.X3D_BUFFER_FRAMES)
        self.score_history = collections.deque(maxlen=Config.X3D_SMOOTH_WINDOW)

        self.last_score      = 0.0
        self.raw_score       = 0.0
        self.is_theft        = False
        self.inference_count = 0
        self.label           = "Buffering..."

        self.consecutive_theft     = 0
        self.frames_without_person = 0

        self.cooldown_until = 0.0
        self.in_cooldown    = False

        self.frames_since_infer = 0

    def push_frame(self, frame_rgb: np.ndarray, padded_box):
        """
        Add a new frame to the buffer.

        Args:
            frame_rgb:   RGB frame (H, W, 3).
            padded_box:  Padded bounding box [x1,y1,x2,y2] or None if absent.
        """
        if padded_box is not None:
            self.frames_without_person = 0
        else:
            self.frames_without_person += 1

        # Conservative state reset — only after ~6 seconds with no person
        if self.frames_without_person >= Config.X3D_RESET_AFTER_ABSENT:
            if len(self.score_history) > 0:
                self.score_history.clear()
                self.consecutive_theft = 0
                self.raw_score  = 0.0
                self.last_score = 0.0
                self.is_theft   = False
                # Preserve cooldown if still active

        self.frame_buffer.append(frame_rgb)
        self.box_buffer.append(padded_box)
        self.frames_since_infer += 1

    def should_infer(self) -> bool:
        """Return True when the buffer is full and the stride interval has elapsed."""
        return (
            len(self.frame_buffer) >= Config.X3D_CLIP_LENGTH
            and self.frames_since_infer >= Config.X3D_INFER_INTERVAL
        )

    def run_inference(self, x3d_model: nn.Module, device: str) -> bool:
        """
        Run X3D inference on the buffered frames.

        Detection logic is identical to Deployment_v3_final.py run_inference().

        Args:
            x3d_model: Loaded X3D-S model in eval mode.
            device:    torch device string.

        Returns:
            True if theft is currently confirmed or in cooldown.
        """
        now = time.time()

        # ── Cooldown check ────────────────────────────────────────────────────
        if self.in_cooldown:
            if now < self.cooldown_until:
                remaining = self.cooldown_until - now
                self.frames_since_infer = 0
                self.inference_count   += 1
                self.label = f"ALERT ACTIVE — cooldown {remaining:.1f}s"
                return True
            else:
                # Cooldown expired — reset for fresh monitoring
                self.in_cooldown       = False
                self.is_theft          = False
                self.consecutive_theft = 0
                self.score_history.clear()

        # ── Median box across buffer (stabilises jitter) ──────────────────────
        frames = list(self.frame_buffer)
        boxes  = list(self.box_buffer)

        valid = [b for b in boxes if b is not None]
        if valid:
            median_box = np.median(valid, axis=0).astype(int).tolist()
        else:
            h, w = frames[0].shape[:2]
            median_box = [0, 0, w, h]

        x1, y1, x2, y2 = median_box
        h, w = frames[0].shape[:2]
        if x2 <= x1 or y2 <= y1:
            median_box = [0, 0, w, h]

        # ── X3D forward pass ──────────────────────────────────────────────────
        t0     = time.time()
        tensor = _frames_to_tensor(frames, median_box).to(device)

        with torch.no_grad():
            logits      = x3d_model(tensor)
            probs       = torch.softmax(logits, dim=1)[0]
            theft_score = probs[1].item()

        infer_ms = (time.time() - t0) * 1000

        # ── Rolling average smoothing ─────────────────────────────────────────
        self.score_history.append(theft_score)
        smooth_score = float(np.mean(self.score_history))

        self.last_score      = smooth_score
        self.raw_score       = theft_score
        self.inference_count += 1
        self.frames_since_infer = 0

        # ── Consecutive detection (on smoothed score) ─────────────────────────
        if smooth_score >= Config.X3D_THEFT_THRESH:
            self.consecutive_theft += 1
        else:
            self.consecutive_theft = 0

        # ── Theft confirmation + cooldown trigger ─────────────────────────────
        if self.consecutive_theft >= Config.X3D_CONSECUTIVE_REQUIRED:
            self.is_theft    = True
            self.in_cooldown = True
            self.cooldown_until = time.time() + Config.X3D_COOLDOWN_SECONDS
            self.label = (
                f"!! THEFT CONFIRMED !! ({self.consecutive_theft} consecutive)"
            )
        elif self.consecutive_theft > 0:
            self.is_theft = False
            self.label = (
                f"Suspicious ({self.consecutive_theft}/{Config.X3D_CONSECUTIVE_REQUIRED})"
            )
        else:
            self.is_theft = False
            self.label    = "Normal"

        self.label += f"  [s:{smooth_score:.3f} r:{theft_score:.3f} {infer_ms:.0f}ms]"

        return self.is_theft or self.in_cooldown


# ── X3D model loader ──────────────────────────────────────────────────────────

def load_x3d_model(checkpoint_path: str, device: str) -> nn.Module:
    """
    Load the X3D-S model with a 2-class head.

    Identical to Deployment_v3_final.py load_x3d_model() — same architecture
    replacement, same dropout handling, same strict/fallback loading.

    Args:
        checkpoint_path: Path to best_model.pth produced by step2_train.py.
        device:          torch device string.

    Returns:
        X3D-S model in eval mode, moved to device.
    """
    print(f"\n[TheftDetector] Loading X3D-S ...")
    print(f"  Checkpoint: {checkpoint_path}")

    try:
        model = torch.hub.load(
            'facebookresearch/pytorchvideo', 'x3d_s',
            pretrained=False, verbose=False,
        )
    except Exception as e:
        print(f"  Hub failed ({e}), trying pytorchvideo library ...")
        from pytorchvideo.models.hub import x3d_s as x3d_s_fn
        model = x3d_s_fn(pretrained=False)

    # Step 1: Replace 400-class head with 2-class head
    if hasattr(model, 'blocks'):
        in_features = model.blocks[5].proj.in_features
        model.blocks[5].proj = nn.Linear(in_features, 2)
    elif hasattr(model, 'head'):
        attr = model.head.proj if hasattr(model.head, 'proj') else model.head
        in_features = attr.in_features
        if hasattr(model.head, 'proj'):
            model.head.proj = nn.Linear(in_features, 2)
        else:
            model.head = nn.Linear(in_features, 2)

    # Step 2: Set dropout to match training architecture exactly
    dropout_set = False
    if hasattr(model, 'blocks'):
        if hasattr(model.blocks[5], 'dropout'):
            model.blocks[5].dropout.p = 0.5
            dropout_set = True
        else:
            for module in model.blocks[5].modules():
                if isinstance(module, nn.Dropout):
                    module.p = 0.5
                    dropout_set = True
                    break
    if not dropout_set:
        print("  Wrapping proj with Dropout (matching training architecture)")
        if hasattr(model, 'blocks'):
            original_proj = model.blocks[5].proj
            model.blocks[5].proj = nn.Sequential(nn.Dropout(p=0.5), original_proj)

    # Step 3: Load checkpoint
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)

    if 'model_state_dict' in ckpt:
        state_dict = ckpt['model_state_dict']
        print(f"  Epoch: {ckpt.get('epoch', '?')}  "
              f"Val Acc: {ckpt.get('val_acc', 0.0):.4f}  "
              f"Val F1: {ckpt.get('val_f1', 0.0):.4f}")
    else:
        state_dict = ckpt

    # Strip DataParallel 'module.' prefix if present
    new_state = {k.replace('module.', ''): v for k, v in state_dict.items()}

    try:
        model.load_state_dict(new_state, strict=True)
        print("  Checkpoint loaded (strict=True)")
    except RuntimeError as e:
        print(f"  strict=True failed: {e}")
        print("  Retrying with strict=False ...")
        model.load_state_dict(new_state, strict=False)
        print("  Checkpoint loaded (strict=False)")

    model = model.to(device)
    model.eval()

    total = sum(p.numel() for p in model.parameters())
    print(f"  Parameters: {total:,}  |  Device: {device}")
    print("  X3D-S ready.\n")
    return model


# ── Manager that holds all per-person states ──────────────────────────────────

class GlobalTheftDetector:
    """
    Manages one TheftState per global identity and runs X3D inference.

    The MCMT pipeline calls:
        push_frame(global_id, frame_rgb, bbox, frame_shape)
        maybe_infer(global_id)

    The X3D model is loaded once and shared across all identities.
    """

    def __init__(self, checkpoint_path: str, device: str):
        self.device = device
        self.x3d    = load_x3d_model(checkpoint_path, device)
        self._states: dict = {}   # global_id → TheftState

    def _get_state(self, global_id: int) -> TheftState:
        if global_id not in self._states:
            self._states[global_id] = TheftState(global_id)
        return self._states[global_id]

    def push_frame(
        self,
        global_id: int,
        frame_rgb: np.ndarray,
        bbox: list,
        frame_shape: tuple,
    ):
        """
        Add a frame to the buffer for this global identity.

        Args:
            global_id:   Cross-camera global ID.
            frame_rgb:   Full-frame RGB image (H, W, 3).
            bbox:        Raw detection bounding box [x1,y1,x2,y2] or None.
            frame_shape: (height, width) of the frame.
        """
        h, w  = frame_shape
        state = self._get_state(global_id)

        padded = _apply_padding(bbox, h, w) if bbox is not None else None
        state.push_frame(frame_rgb, padded)

    def maybe_infer(self, global_id: int) -> TheftState:
        """
        Run X3D inference for this identity if the interval has elapsed.

        Returns:
            The TheftState (with updated label, scores, is_theft).
        """
        state = self._get_state(global_id)
        if state.should_infer():
            state.run_inference(self.x3d, self.device)
        return state

    def get_state(self, global_id: int) -> TheftState:
        """Return the TheftState for a global ID (creates one if missing)."""
        return self._get_state(global_id)

    def prune_states(self, active_global_ids: set):
        """
        Remove states for identities that are no longer tracked.
        Called periodically to free memory.
        """
        dead = [gid for gid in self._states if gid not in active_global_ids]
        for gid in dead:
            del self._states[gid]
        if dead:
            print(f"[TheftDetector] Pruned {len(dead)} inactive identity states")

    def any_theft_active(self) -> bool:
        """Return True if any tracked identity currently has a theft alert."""
        return any(
            s.is_theft or s.in_cooldown
            for s in self._states.values()
        )

    def get_theft_summary(self) -> dict:
        """Return {global_id: (is_alert, smoothed_score, label)} for all states."""
        return {
            gid: (s.is_theft or s.in_cooldown, s.last_score, s.label)
            for gid, s in self._states.items()
        }

    def get_active_global_ids(self) -> list:
        """Return list of all global IDs that have an active TheftState."""
        return list(self._states.keys())
