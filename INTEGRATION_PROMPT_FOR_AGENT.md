# Integration Task — TheftSentinel MCMT → Django AI Pipeline

## Your Mission

You are integrating the `TheftSentinel_MCMT` module's X3D theft detection
engine into the existing Django project's AI pipeline. The goal is to
replace the current simple X3D threshold classifier with the full
`TheftState` state machine that was trained and validated in
`Deployment_v3_final.py`.

---

## Project Layout

```
Final_FYP_Project/
├── theft_sentinel_backend/          ← Django project (DO NOT break this)
│   ├── ai_pipeline/
│   │   ├── ai_config/config.py      ← MODIFY: update X3D parameters
│   │   ├── detection/               ← DO NOT TOUCH
│   │   ├── tracking/                ← DO NOT TOUCH
│   │   ├── reid/                    ← DO NOT TOUCH
│   │   ├── matching/                ← DO NOT TOUCH
│   │   └── x3d/                     ← REPLACE/UPGRADE: X3D logic
│   └── apps/ai_engine/services/
│       └── inference_runner.py      ← MODIFY: integrate TheftState
│
└── TheftSentinel_MCMT/              ← Source module (read-only reference)
    └── theft_detection/
        └── x3d_detector.py          ← THE SOURCE: copy logic from here
```

---

## Step 1 — Read Everything First

Before writing a single line of code, read these files completely:

1. `TheftSentinel_MCMT/theft_detection/x3d_detector.py` — full file
2. `TheftSentinel_MCMT/config/config.py` — X3D section only
3. `theft_sentinel_backend/ai_pipeline/ai_config/config.py` — full file
4. `theft_sentinel_backend/apps/ai_engine/services/inference_runner.py` — full file
5. `theft_sentinel_backend/apps/ai_engine/services/ai_service.py` — full file
6. `theft_sentinel_backend/apps/ai_engine/services/continuous_monitor.py` — full file

Do NOT skip any of these. The integration has subtle state management
that you will break if you do not understand the existing architecture.

---

## Step 2 — Create `ai_pipeline/x3d/x3d_detector.py`

Create the file `theft_sentinel_backend/ai_pipeline/x3d/x3d_detector.py`
by adapting `TheftSentinel_MCMT/theft_detection/x3d_detector.py`.

### 2.1 Import changes

Replace:
```python
from config.config import Config
```
With:
```python
from ai_pipeline.ai_config.config import Config
```

### 2.2 Classes to copy EXACTLY (no logic changes allowed)

Copy these items with zero modification to their internal logic:

- `_frames_to_tensor(frames_rgb, crop_box)` — exact copy
- `_apply_padding(box, frame_h, frame_w)` — exact copy
- `TheftState.__init__()` — exact copy
- `TheftState.push_frame()` — exact copy
- `TheftState.should_infer()` — exact copy
- `TheftState.run_inference()` — exact copy, but add these two lines
  at the top of the method, BEFORE the cooldown check:
  ```python
  # VRAM optimization: defrag before large X3D tensor allocation
  if torch.cuda.is_available():
      torch.cuda.empty_cache()
  ```
  And wrap the X3D forward pass with `torch.inference_mode()`:
  ```python
  with torch.inference_mode():
      logits = x3d_model(tensor)
      probs  = torch.softmax(logits, dim=1)[0]
      theft_score = probs[1].item()
  ```
  (replace the existing `torch.no_grad()` block with `torch.inference_mode()`)

- `load_x3d_model(checkpoint_path, device)` — exact copy
- `GlobalTheftDetector.__init__()` — exact copy
- `GlobalTheftDetector.push_frame()` — exact copy
- `GlobalTheftDetector.maybe_infer()` — exact copy
- `GlobalTheftDetector.get_state()` — exact copy
- `GlobalTheftDetector.get_active_global_ids()` — exact copy
- `GlobalTheftDetector.get_theft_summary()` — exact copy
- `GlobalTheftDetector.any_theft_active()` — exact copy
- `GlobalTheftDetector.prune_states()` — exact copy

### 2.3 DO NOT change these values — they match training

```python
# These come from the training pipeline — changing them breaks the model
CLIP_LENGTH     = 64
BUFFER_FRAMES   = 64
SPATIAL_SIZE    = 224
INFER_INTERVAL  = 16
PAD_RATIO       = 0.40
NORM_MEAN       = [0.45, 0.45, 0.45]
NORM_STD        = [0.225, 0.225, 0.225]
```

---

## Step 3 — Update `ai_pipeline/ai_config/config.py`

Find the existing X3D configuration section and replace it entirely.

Remove these old parameters:
```python
X3D_INFERENCE_EVERY      = 5
X3D_CLIP_FRAMES          = 8
X3D_THEFT_THRESHOLD      = 0.80
X3D_SUSPICIOUS_THRESHOLD = 0.50
```

Add these new parameters:
```python
# ── X3D-S Theft Detection — MUST MATCH TRAINING ────────────────────
# DO NOT change CLIP_LENGTH, BUFFER_FRAMES, SPATIAL_SIZE, INFER_INTERVAL,
# PAD_RATIO, NORM_MEAN, NORM_STD — these are locked to training config.

X3D_CHECKPOINT           = "best_model.pth"    # path to trained checkpoint
X3D_CLIP_LENGTH          = 64     # frames fed to X3D per inference
X3D_BUFFER_FRAMES        = 64     # rolling frame buffer (= CLIP_LENGTH)
X3D_SPATIAL_SIZE         = 224    # crop resize resolution
X3D_INFER_INTERVAL       = 16     # run inference every 16 new frames
X3D_PAD_RATIO            = 0.40   # bbox padding (matches step1_preprocess)
X3D_NORM_MEAN            = [0.45, 0.45, 0.45]
X3D_NORM_STD             = [0.225, 0.225, 0.225]

# Tunable detection logic
X3D_SMOOTH_WINDOW        = 5      # rolling average over N raw scores
X3D_THEFT_THRESH         = 0.70   # smoothed score threshold for theft
X3D_SUSPICIOUS_THRESH    = 0.50   # score threshold for suspicious flag
X3D_CONSECUTIVE_REQUIRED = 3      # consecutive hits to confirm theft
X3D_COOLDOWN_SECONDS     = 8.0    # seconds of X3D-level cooldown after alert
X3D_RESET_AFTER_ABSENT   = 150    # frames without person → state reset
```

Keep all other existing config values (YOLO, ReID, FAISS, DeepSORT,
SSE, alert cooldown, etc.) exactly as they are.

---

## Step 4 — Update `ai_service.py`

Find where the X3D model is loaded in `ai_service.py` and replace it
with `GlobalTheftDetector`.

Add this import at the top of the file:
```python
from ai_pipeline.x3d.x3d_detector import GlobalTheftDetector
```

Find the existing X3D model loading code (it likely loads a simple
classifier). Replace it with:
```python
self.global_theft_detector = GlobalTheftDetector(
    checkpoint_path=Config.X3D_CHECKPOINT,
    device=self.device,
)
```

Remove any old `self.x3d` or `self.x3d_classifier` attribute that
held the previous simple classifier. Make sure `inference_lock` and
`state_lock` are still defined — do not remove them.

---

## Step 5 — Update `inference_runner.py`

This is the most important change. Modify `InferenceRunner.run_inference()`
(also called `process_frame()` in some versions).

### 5.1 Add IoU helper function at module level

Add this function at the top of `inference_runner.py`, outside any class:

```python
def _compute_iou(boxA: list, boxB: list) -> float:
    """Intersection over Union of two [x1,y1,x2,y2] boxes."""
    xA = max(boxA[0], boxB[0]);  yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2]);  yB = min(boxA[3], boxB[3])
    inter = max(0, xB-xA) * max(0, yB-yA)
    if inter == 0: return 0.0
    areaA = (boxA[2]-boxA[0]) * (boxA[3]-boxA[1])
    areaB = (boxB[2]-boxB[0]) * (boxB[3]-boxB[1])
    union = areaA + areaB - inter
    return inter / union if union > 0 else 0.0
```

### 5.2 Add BGR→RGB conversion at the start of `run_inference`

Add immediately after reading `frame_bgr`:
```python
h, w   = frame_bgr.shape[:2]
frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
```

### 5.3 Normalize ALL track_id usage to `str()`

Find every place in `run_inference` where `track_id` is used as a dict
key or passed to `ai_service.db` methods. Wrap every occurrence with
`str()`. Specifically:

```python
# In tracker output extraction:
track_id = str(track.track_id)    # ← add str() here

# In db lookups:
existing_gid = ai_service.db.get_global_id_for_track(camera_id, str(track_id))
ai_service.db.update_identity(global_id, smoothed, camera_id, str(track_id))
ai_service.db.register_new_identity(smoothed, camera_id, str(track_id))
```

This is critical. `deep_sort_realtime` returns `track_id` as either `int`
or `str` depending on version. Without normalization, the same person gets
a new `global_id` every frame, the X3D buffer never fills, and no theft
is ever detected.

### 5.4 Add IoU-based YOLO→track bbox matching

After the DeepSORT `update()` call, before the ReID loop, add:

```python
# Match each DeepSORT track back to its raw YOLO detection by IoU.
# X3D needs the raw YOLO bbox, not the Kalman-extrapolated DeepSORT position.
track_to_yolo_bbox = {}
for track in tracks:
    tid      = str(track["track_id"])
    t_box    = track["bbox"]
    best_iou, best_box = 0.0, t_box
    for det in raw_detections:
        iou = _compute_iou(t_box, det["bbox"])
        if iou > best_iou:
            best_iou, best_box = iou, det["bbox"]
    track_to_yolo_bbox[tid] = best_box
```

### 5.5 Build `track_to_global_id` mapping during the ReID loop

During the existing ReID + FAISS loop, collect the mapping of
`track_id → global_id` into a dict. After all global IDs are assigned:

```python
track_to_global_id = {}
# (during the existing loop, after assigning global_id):
track_to_global_id[str(track_id)] = global_id
```

### 5.6 Push frames to X3D buffer (SEPARATE loop, after ReID)

Add this block AFTER the entire ReID + global ID assignment loop is done,
and BEFORE building the result dict:

```python
# Push frames to GlobalTheftDetector for every confirmed track.
# This loop is SEPARATE from the ReID loop — frames are pushed even if
# ReID failed for a given frame. This ensures the 64-frame buffer fills
# at camera FPS without gaps (sparse buffer = X3D never fires).
for track in tracks:
    tid       = str(track["track_id"])
    global_id = track_to_global_id.get(tid)
    if global_id is None:
        continue
    yolo_bbox = track_to_yolo_bbox.get(tid, track["bbox"])
    # push_frame applies 40% padding internally and stores full RGB frame
    with ai_service.state_lock:
        ai_service.global_theft_detector.push_frame(
            global_id   = global_id,
            frame_rgb   = frame_rgb,
            bbox        = yolo_bbox,
            frame_shape = (h, w),
        )

# Run X3D inference for all active identities
with ai_service.state_lock:
    for gid in ai_service.global_theft_detector.get_active_global_ids():
        with ai_service.inference_lock:
            ai_service.global_theft_detector.maybe_infer(gid)
```

### 5.7 Map TheftState output to Django result fields

When building the result dict for each track, replace the old X3D score
lookup with:

```python
with ai_service.state_lock:
    theft_state = ai_service.global_theft_detector.get_state(global_id)

x3d_score    = theft_state.last_score         # smoothed (0–1)
is_confirmed = theft_state.is_theft or theft_state.in_cooldown
consecutive  = theft_state.consecutive_theft

# Map to Django's classification schema
if is_confirmed:
    classification  = "theft"
    alert_triggered = True   # still gated by 5s cooldown in _monitor_loop
    is_suspicious   = True
elif consecutive > 0 or x3d_score >= Config.X3D_SUSPICIOUS_THRESH:
    classification  = "normal"
    alert_triggered = False
    is_suspicious   = True
else:
    classification  = "normal"
    alert_triggered = False
    is_suspicious   = False
```

Remove any old `clip`, `ClipBuffer`, or simple `x3d.predict()` calls
that the old classifier used.

### 5.8 Prune theft states periodically

In the periodic maintenance section of `inference_runner` or
`_monitor_loop` (wherever `db.prune_expired()` is called), add:

```python
active_ids = set(ai_service.db.get_all_identities().keys())
with ai_service.state_lock:
    ai_service.global_theft_detector.prune_states(active_ids)
```

---

## Step 6 — Preserve ALL Existing Optimizations

After making the above changes, verify that every one of these still exists
and is unchanged:

### RAM optimizations (in `_capture_loop`):
```python
frame = cv2.resize(raw_frame, (640, 480))
del raw_frame
```

### RAM optimizations (in `_upload_worker`):
```python
import gc
gc.collect()
write_frames_to_mp4(clip_frames, tmp_path, fps=fps)
del clip_frames
del frames
gc.collect()
```

### RAM optimization (in `_monitor_loop`):
```python
if self.frames_processed % 50 == 0:
    gc.collect()
```

### VRAM optimizations (in `_monitor_loop`):
```python
if self.frames_processed % 15 == 0 or result.get('classification') == 'theft':
    torch.cuda.empty_cache()
```

### VRAM optimization at startup (in `settings.py` or `asgi.py`):
```python
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
```

### Threading (in `inference_runner.py`):
- All GPU calls: `with ai_service.inference_lock:`
- All FAISS/identity state: `with ai_service.state_lock:`

### SSE throttle (in `_monitor_loop`):
```python
if (now - self._last_callback_time) >= (1.0 / self._SSE_MAX_FPS):
    self.callback(self.camera_id, result)
```

### Alert cooldown (in `_monitor_loop`):
```python
if is_theft_detected and (current_time - self.last_alert_time) >= 5.0:
    self.last_alert_time = current_time
    # proceed with DB write and clip upload
else:
    is_theft_detected = False
    result['classification'] = 'normal'
    result['alert_triggered'] = False
```

### FAISS permanent memory:
Do NOT add any code that deletes embeddings from the FAISS index when a
DeepSORT track is dropped. Embeddings are only ever added or updated.

### Identity hijacking prevention (`used_global_ids` pre-pass):
```python
used_global_ids = set()
# Pre-pass: claim existing global IDs first
for track_info in valid_tracks:
    existing_gid = ai_service.db.get_global_id_for_track(...)
    if existing_gid is not None:
        used_global_ids.add(existing_gid)
# Main pass: reject FAISS matches already in-frame
if best_match_gid in used_global_ids:
    global_id = None  # force new identity
```

---

## Step 7 — Do NOT Touch These Files

- `continuous_monitor.py` — only the `inference_runner` call inside
  `_monitor_loop` changes (which happens automatically when
  `inference_runner.run_inference()` is updated)
- `sse_registry.py` — no changes
- `ai_engine/api/views.py` — no changes
- `ai_engine/models.py` — no changes
- `apps/cameras/`, `apps/alerts/`, `apps/accounts/` — no changes
- Any frontend `.jsx` files — no changes
- `apps/ai_engine/services/clip_encoding.py` — no changes

---

## Step 8 — Verify Your Changes

After making all changes, verify these specific behaviors:

1. **No import errors:** Start Django with `python manage.py runserver`
   and confirm no `ImportError` or `ModuleNotFoundError` at startup.

2. **Checkpoint loads:** Check logs for:
   ```
   [TheftDetector] Loading X3D-S ...
     Checkpoint loaded (strict=True)
     X3D-S ready.
   ```

3. **track_id is str:** Add a temporary `print(type(track_id))` in
   `run_inference` and confirm it prints `<class 'str'>`, not `<class 'int'>`.

4. **Buffer fills:** Add a temporary `print(len(state.frame_buffer))`
   inside `maybe_infer` and confirm it reaches 64 within 3–4 seconds
   of a person appearing on camera.

5. **Inference fires:** Confirm `state.inference_count` increments every
   ~16 frames (~0.6 seconds at 25 FPS) once the buffer is full.

6. **Existing optimizations intact:** Search for `empty_cache`,
   `gc.collect`, `inference_lock`, `state_lock`, `_SSE_MAX_FPS`,
   `last_alert_time`, `used_global_ids` in the codebase and confirm
   all still exist in their original locations.

---

## What You Must NOT Do

- Do not change `_frames_to_tensor()` logic — any change breaks train/deploy match
- Do not change `_apply_padding()` ratio from 0.40
- Do not change `X3D_CLIP_LENGTH=64`, `X3D_BUFFER_FRAMES=64`, `X3D_SPATIAL_SIZE=224`
- Do not change `X3D_NORM_MEAN` or `X3D_NORM_STD` values
- Do not remove `torch.cuda.empty_cache()` calls
- Do not remove `gc.collect()` calls
- Do not remove `inference_lock` or `state_lock` from any GPU/FAISS call
- Do not delete embeddings from FAISS (permanent memory design)
- Do not copy `main.py`, `camera/stream.py`, `visualization/display.py`,
  `detection/detector.py`, `tracking/tracker.py`, `reid/extractor.py`,
  `matching/matcher.py`, or `database/identity_db.py` from TheftSentinel MCMT
  into the Django project — the Django versions are better
- Do not modify any frontend `.jsx` files
- Do not modify `continuous_monitor.py`'s capture or clip logic

---

## Summary of Files to Create/Modify

| Action | File |
|---|---|
| **CREATE** | `theft_sentinel_backend/ai_pipeline/x3d/x3d_detector.py` |
| **MODIFY** | `theft_sentinel_backend/ai_pipeline/ai_config/config.py` |
| **MODIFY** | `theft_sentinel_backend/apps/ai_engine/services/ai_service.py` |
| **MODIFY** | `theft_sentinel_backend/apps/ai_engine/services/inference_runner.py` |
| **DO NOT TOUCH** | Everything else |
