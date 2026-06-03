# TheftSentinel MCMT — Module Documentation

> **What this module is:**
> A standalone, pure-Python multi-camera multi-target tracking and theft
> detection system. It has no Django dependency. It is designed to be
> **transplanted** into the Django project's `ai_pipeline/` layer,
> replacing or upgrading specific components there.

---

## 1. Module Overview

TheftSentinel MCMT combines two systems:

1. **MCMT (Multi-Camera Multi-Target Tracking)** — tracks each person
   across multiple cameras under a single persistent `global_id` using
   YOLOv8 → DeepSORT → OSNet ReID → FAISS nearest-neighbor matching.

2. **X3D-S Theft Detection** — classifies behavior as normal or theft
   using a per-person rolling frame buffer fed into a fine-tuned X3D-S
   video model. The detection logic uses smoothed scoring, consecutive
   confirmation, and cooldown — identical to `Deployment_v3_final.py`.

---

## 2. Directory Structure

```
TheftSentinel_MCMT/
├── main.py                         ← Standalone entry point (NOT for Django)
├── config/
│   └── config.py                   ← All parameters: MCMT + X3D (edit here)
├── theft_detection/
│   └── x3d_detector.py             ← THE KEY FILE: X3D model + TheftState machine
├── detection/
│   └── detector.py                 ← YOLOv8 person detection wrapper
├── tracking/
│   └── tracker.py                  ← DeepSORT per-camera tracker wrapper
├── reid/
│   └── extractor.py                ← OSNet ReID feature extractor
├── matching/
│   └── matcher.py                  ← FAISS cross-camera matcher
├── database/
│   └── identity_db.py              ← Global identity database (thread-safe)
├── camera/
│   └── stream.py                   ← Threaded camera stream reader
└── visualization/
    └── display.py                  ← CV2 drawing + tiled display
```

---

## 3. The X3D Detection Engine — `theft_detection/x3d_detector.py`

This is the most important file. It contains **everything that makes the
theft detection work correctly** and must be integrated into the Django
project's `ai_pipeline/x3d/` layer.

### 3.1 `TheftState` — Per-Identity State Machine

One `TheftState` instance is created per `global_id`. It tracks:

| Attribute | Type | Purpose |
|---|---|---|
| `frame_buffer` | `deque(maxlen=64)` | Rolling buffer of full RGB frames |
| `box_buffer` | `deque(maxlen=64)` | Rolling buffer of padded bboxes per frame |
| `score_history` | `deque(maxlen=5)` | Last 5 raw X3D scores for smoothing |
| `consecutive_theft` | `int` | Count of consecutive above-threshold inferences |
| `frames_without_person` | `int` | Frames since person last detected (for state reset) |
| `in_cooldown` | `bool` | Whether alert cooldown is active |
| `cooldown_until` | `float` | `time.time()` timestamp when cooldown expires |
| `last_score` | `float` | Current smoothed score (for display) |
| `is_theft` | `bool` | Whether theft is currently confirmed |

**Detection flow (must not be changed):**
```
push_frame(frame_rgb, padded_bbox)   ← called every camera frame
         │
         ▼
should_infer() → True when:
  len(frame_buffer) >= 64   AND
  frames_since_infer >= 16
         │
         ▼
run_inference(x3d_model, device)
  1. Build median_box from box_buffer (smooths box jitter)
  2. _frames_to_tensor():
       - crop each frame using median_box
       - resize crop to 224×224
       - linspace(0,63,64) sample indices (no subsampling since 64=64)
       - normalize: mean=[0.45,0.45,0.45], std=[0.225,0.225,0.225]
       - return tensor shape (1, 3, 64, 224, 224)
  3. X3D forward pass → softmax → theft_score = probs[1]
  4. score_history.append(theft_score)
     smooth_score = mean(score_history)   ← rolling average of 5
  5. if smooth_score >= 0.70:
         consecutive_theft += 1
     else:
         consecutive_theft = 0
  6. if consecutive_theft >= 3:
         is_theft = True
         in_cooldown = True
         cooldown_until = now + 8.0 seconds
```

### 3.2 `_frames_to_tensor()` — Critical Preprocessing

**This function must not be changed.** It replicates exactly how
`step1_preprocess_yolo_crop.py` built training clips. Any deviation
breaks the train/deploy match.

```python
def _frames_to_tensor(frames_rgb: list, crop_box: list) -> torch.Tensor:
    x1, y1, x2, y2 = crop_box
    processed = []
    for frame_rgb in frames_rgb:
        crop = frame_rgb[y1:y2, x1:x2]
        if crop.size == 0:
            crop = frame_rgb
        resized = cv2.resize(crop, (224, 224))
        processed.append(resized)

    indices = np.linspace(0, len(processed)-1, 64).astype(int)
    clip    = np.array([processed[i] for i in indices], dtype=np.uint8)

    NORM_MEAN = torch.tensor([0.45, 0.45, 0.45]).view(3,1,1,1)
    NORM_STD  = torch.tensor([0.225, 0.225, 0.225]).view(3,1,1,1)

    tensor = torch.from_numpy(clip).permute(3,0,1,2).float() / 255.0
    tensor = (tensor - NORM_MEAN) / NORM_STD
    return tensor.unsqueeze(0)   # shape: (1, 3, 64, 224, 224)
```

### 3.3 `_apply_padding()` — 40% Padding (Matches Training)

```python
def _apply_padding(box, frame_h, frame_w):
    x1, y1, x2, y2 = box
    bw, bh = x2-x1, y2-y1
    x1 = max(0,       int(x1 - 0.40*bw))
    y1 = max(0,       int(y1 - 0.40*bh))
    x2 = min(frame_w, int(x2 + 0.40*bw))
    y2 = min(frame_h, int(y2 + 0.40*bh))
    return [x1, y1, x2, y2]
```

This is called inside `GlobalTheftDetector.push_frame()` on the **raw
YOLO bbox** (not the DeepSORT Kalman-filtered position).

### 3.4 `load_x3d_model()` — Model Loading

Loads the X3D-S model with a 2-class head (Normal / Theft):
- Replaces default 400-class projection: `Linear(2048, 400)` → `Linear(2048, 2)`
- Sets `dropout.p = 0.5` (matches training architecture exactly)
- Loads checkpoint with `strict=True`, falls back to `strict=False`
- Strips `module.` prefix if checkpoint was saved from `DataParallel`
- Calls `model.eval()` to disable dropout at inference time

### 3.5 `GlobalTheftDetector` — Manager Class

Owns the X3D model (loaded once) and a dict of `global_id → TheftState`.

Key methods:

| Method | Purpose |
|---|---|
| `push_frame(global_id, frame_rgb, bbox, frame_shape)` | Add frame to buffer; applies 40% padding to bbox |
| `maybe_infer(global_id)` | Run inference if interval elapsed; return TheftState |
| `get_state(global_id)` | Return current TheftState (creates one if new) |
| `get_active_global_ids()` | List all global IDs with active states |
| `get_theft_summary()` | Dict of `global_id → (is_alert, score, label)` |
| `any_theft_active()` | True if any identity is confirmed theft or in cooldown |
| `prune_states(active_ids)` | Remove states for expired/pruned global IDs |

---

## 4. Critical Parameters — Must Match Training

These values come from the training pipeline
(`step1_preprocess_yolo_crop.py` + `step2_train_v7_yolo_crop.py`)
and **cannot be changed without retraining the model**.

```python
# X3D Clip Parameters — TRAINING MATCH REQUIRED
X3D_CLIP_LENGTH     = 64      # frames fed to X3D per inference
X3D_BUFFER_FRAMES   = 64      # rolling buffer size (= CLIP_LENGTH)
X3D_SPATIAL_SIZE    = 224     # crop resize resolution
X3D_INFER_INTERVAL  = 16      # run inference every 16 new frames (sliding window stride)
X3D_PAD_RATIO       = 0.40    # bounding box padding ratio

# Kinetics-400 Normalization — TRAINING MATCH REQUIRED
X3D_NORM_MEAN       = [0.45, 0.45, 0.45]
X3D_NORM_STD        = [0.225, 0.225, 0.225]

# Detection Logic — tunable post-training
X3D_SMOOTH_WINDOW        = 5     # rolling average over N inferences
X3D_THEFT_THRESH         = 0.70  # smoothed score threshold
X3D_CONSECUTIVE_REQUIRED = 3     # consecutive hits to confirm theft
X3D_COOLDOWN_SECONDS     = 8.0   # seconds before new alert allowed
X3D_RESET_AFTER_ABSENT   = 150   # frames without person → state reset
```

---

## 5. Integration Points — What Changes in the Django Project

Only **two files** need significant changes. Everything else in the Django
project (`ai_engine`, `continuous_monitor`, `sse_registry`, alert
handling, clip upload, VRAM/RAM optimizations) stays exactly as-is.

### 5.1 `ai_pipeline/x3d/` — Replace X3D Logic

The current `ai_pipeline/x3d/` has a simple threshold classifier with
`X3D_CLIP_FRAMES=8` and `X3D_INFERENCE_EVERY=5`. This must be replaced
with the full `TheftState` state machine from `theft_detection/x3d_detector.py`.

**What to copy:**
- `TheftState` class (complete)
- `GlobalTheftDetector` class (complete)
- `_frames_to_tensor()` function (exact copy)
- `_apply_padding()` function (exact copy)
- `load_x3d_model()` function (exact copy)

### 5.2 `ai_pipeline/ai_config/config.py` — Update Parameters

Old values that must be replaced:

```python
# OLD (WRONG — does not match training)
X3D_INFERENCE_EVERY      = 5
X3D_CLIP_FRAMES          = 8
X3D_THEFT_THRESHOLD      = 0.80
X3D_SUSPICIOUS_THRESHOLD = 0.50

# NEW (CORRECT — matches Deployment_v3_final.py and training)
X3D_CLIP_LENGTH          = 64
X3D_BUFFER_FRAMES        = 64
X3D_SPATIAL_SIZE         = 224
X3D_INFER_INTERVAL       = 16
X3D_PAD_RATIO            = 0.40
X3D_NORM_MEAN            = [0.45, 0.45, 0.45]
X3D_NORM_STD             = [0.225, 0.225, 0.225]
X3D_SMOOTH_WINDOW        = 5
X3D_THEFT_THRESH         = 0.70
X3D_CONSECUTIVE_REQUIRED = 3
X3D_COOLDOWN_SECONDS     = 8.0
X3D_RESET_AFTER_ABSENT   = 150
```

### 5.3 `ai_pipeline/inference_runner.py` — Upgrade per-frame logic

The `InferenceRunner.run_inference()` method needs these additions:

1. **track_id normalization** — `str(track.track_id)` everywhere
2. **IoU-based YOLO→track bbox matching** — for X3D, use raw YOLO bbox
3. **Separate X3D push loop** — push frames to `GlobalTheftDetector`
   for every confirmed track, not just tracks with valid ReID embeddings
4. **`GlobalTheftDetector.maybe_infer(global_id)`** — called per global ID per frame
5. **Threshold mapping** — map TheftState results to Django's
   `classification` / `alert_triggered` / `is_suspicious` fields

---

## 6. What to Keep Unchanged in the Django Project

The following Django optimizations and architectural decisions must be
**fully preserved** — do not modify them:

| Feature | Location | Reason to preserve |
|---|---|---|
| `cv2.resize(raw_frame, (640,480))` + `del raw_frame` | `_capture_loop` | RAM: 930 MB → 135 MB, prevents OOM |
| `gc.collect()` before/after clip encoding | `_upload_worker` | RAM: prevents memory spikes at upload |
| `gc.collect()` every 50 frames | `_monitor_loop` | RAM: periodic housekeeping |
| `torch.cuda.empty_cache()` every 15 frames | `_monitor_loop` | VRAM: prevents fragmentation |
| `torch.cuda.empty_cache()` before X3D | `run_inference` | VRAM: defrag before large tensor alloc |
| `torch.inference_mode()` on X3D | X3D classifier | VRAM+speed: no gradient tracking |
| `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` | startup | VRAM: reduces fragmentation |
| `inference_lock` (threading.Lock) | `ai_service.py` | GPU mutual exclusion: YOLO/OSNet/X3D |
| `state_lock` (threading.Lock) | `ai_service.py` | FAISS/identity state thread safety |
| FAISS permanent memory (never delete embeddings) | `inference_runner` | Suspects re-identified after leaving frame |
| `active_thief_global_ids` registry | `ai_service` | Suspect persistence across X3D inference gaps |
| Identity hijacking prevention (`used_global_ids` pre-pass) | `inference_runner` | Two people in frame → no ID collision |
| Alert cooldown 5.0 seconds | `_monitor_loop` | Prevents DB flooding at camera FPS |
| SSE throttle `_SSE_MAX_FPS = 10.0` | `_monitor_loop` | Bandwidth management |
| `deque(maxlen=150)` rolling frame buffer | `_capture_loop` | 5-second clip history for alert video |
| Per-camera `InferenceRunner` isolation | `inference_runner` | No cross-camera state contamination |
| `MonitorManager` process-level singleton | `continuous_monitor` | Single owner of all camera threads |

---

## 7. Modules NOT Needed from TheftSentinel MCMT

These TheftSentinel MCMT files are **redundant** because the Django project
already has superior, Django-integrated equivalents:

| TheftSentinel MCMT file | Django equivalent | Reason |
|---|---|---|
| `camera/stream.py` | `continuous_monitor.py` `_capture_loop` | Django version adds rolling buffer + clip support |
| `detection/detector.py` | `ai_pipeline/detection/` | Same YOLOv8 wrapper already exists |
| `tracking/tracker.py` | `ai_pipeline/tracking/` | Same DeepSORT wrapper already exists |
| `reid/extractor.py` | `ai_pipeline/reid/` | Same OSNet wrapper already exists |
| `matching/matcher.py` | `ai_pipeline/matching/` | Same FAISS matcher already exists |
| `database/identity_db.py` | `ai_pipeline/matching/` | Same identity DB already exists |
| `visualization/display.py` | Frontend `CameraFeedWithOverlay.jsx` | Canvas-based rendering is better |
| `main.py` | `continuous_monitor.py` + `inference_runner.py` | Django orchestrates the pipeline |
| `config/config.py` | `ai_pipeline/ai_config/config.py` | Django config already exists |

**Only copy:** `theft_detection/x3d_detector.py` → adapted into `ai_pipeline/x3d/`

---

## 8. X3D Theft State → Django Field Mapping

After `TheftState` runs inference, map its output to Django's SSE payload:

```python
theft_state = global_theft_detector.get_state(global_id)

# Map TheftState → Django pipeline fields
x3d_score     = theft_state.last_score           # smoothed score (0–1)
is_theft      = theft_state.is_theft             # True = confirmed theft
in_cooldown   = theft_state.in_cooldown          # True = within 8s cooldown window
consecutive   = theft_state.consecutive_theft    # consecutive above-threshold count

# Django classification (mapped to existing thresholds)
if is_theft or in_cooldown:
    classification   = "theft"
    alert_triggered  = True     # gated by Django's 5s alert cooldown in _monitor_loop
    is_suspicious    = True
elif consecutive > 0 or x3d_score >= 0.50:
    classification   = "normal"
    alert_triggered  = False
    is_suspicious    = True     # yellow flag — show in frontend, no DB alert
else:
    classification   = "normal"
    alert_triggered  = False
    is_suspicious    = False
```

Note: `alert_triggered=True` is still gated by Django's existing 5-second
alert cooldown in `_monitor_loop`. The X3D 8-second cooldown operates at
the score level; Django's cooldown gates actual DB writes and clip uploads.
Both are necessary and complementary.

---

## 9. Per-Frame Integration Pattern for `inference_runner.py`

```python
# At module level in inference_runner.py (or ai_service.py):
# global_theft_detector = GlobalTheftDetector(checkpoint_path, device)

def run_inference(self, frame_bgr, camera_id):
    h, w = frame_bgr.shape[:2]
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

    # Step 1: YOLO
    raw_detections = ai_service.yolo.detect(frame_bgr)

    # Step 2: DeepSORT
    tracks = self.tracker.update(raw_detections, frame_bgr)

    # Step 3: IoU-match tracks → raw YOLO boxes (for X3D bbox accuracy)
    track_to_yolo_bbox = {}
    for track in tracks:
        tid = str(track["track_id"])        # ← always normalize to str
        best_iou, best_box = 0.0, track["bbox"]
        for det in raw_detections:
            iou = compute_iou(track["bbox"], det["bbox"])
            if iou > best_iou:
                best_iou, best_box = iou, det["bbox"]
        track_to_yolo_bbox[tid] = best_box

    # Step 4: OSNet ReID + FAISS global ID assignment
    # (existing logic, with str(track_id) normalization)
    # ... [existing code] ...

    # Step 5: Push frames to X3D buffer for every confirmed track
    for track in tracks:
        tid       = str(track["track_id"])
        global_id = track_to_global_id.get(tid)
        if global_id is None:
            continue
        yolo_bbox = track_to_yolo_bbox.get(tid, track["bbox"])
        # push_frame applies 40% padding internally
        global_theft_detector.push_frame(global_id, frame_rgb, yolo_bbox, (h, w))

    # Step 6: Run X3D inference for all active identities
    for gid in global_theft_detector.get_active_global_ids():
        global_theft_detector.maybe_infer(gid)

    # Step 7: Build result dict with theft fields
    # ... map TheftState → classification/is_suspicious/alert_triggered ...
```

---

## 10. Checkpoint File Requirement

The trained X3D-S checkpoint (`best_model.pth`) must be placed at the
path specified in config:

```
Final_FYP_Project/
└── theft_sentinel_backend/
    └── best_model.pth   ← or configure path in ai_config/config.py
```

The checkpoint contains:
- `model_state_dict` — X3D-S weights fine-tuned for theft/normal (2 classes)
- `epoch`, `val_acc`, `val_f1` — training metadata (logged on load)

Without this file, the system will fail at startup.
