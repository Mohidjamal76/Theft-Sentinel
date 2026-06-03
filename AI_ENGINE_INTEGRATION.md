# Theft Sentinel — AI Engine Integration Guide
> **Architecture Snapshot — Stable Milestone.**
> This document describes the exact pipeline, optimizations, and architectural
> decisions that are active in the current production codebase.

---

## 1. Overview

The AI Engine is a self-contained Django application (`apps/ai_engine/`) that
runs a multi-stage computer vision pipeline on live RTSP camera streams. It
detects theft behavior in real time and streams annotated tracking data to
the frontend via Server-Sent Events (SSE).

The pipeline is **decoupled from the Django request cycle**. It runs in
background daemon threads managed by a singleton `MonitorManager`.

---

## 2. Complete AI Pipeline Flow

```
RTSP Camera Stream
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│  _capture_loop  (Thread 1 — dedicated capture)               │
│                                                              │
│  cv2.VideoCapture → raw_frame (1080p or native resolution)   │
│  cv2.resize(raw_frame, (640, 480))  ← IMMEDIATE DOWNSCALE    │
│  del raw_frame                      ← FREE native array      │
│  self.latest_frame = frame          ← rolling frame buffer   │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│  _monitor_loop  (Thread 2 — AI inference)                    │
│                                                              │
│  frame = self.latest_frame   ← read shared pointer          │
│                                                              │
│  Step 1 — YOLOv8  (GPU, inference_lock)                     │
│    Detect all persons in the 640×480 frame                   │
│    Output: raw_dets  [{bbox, confidence, class_id}]          │
│                                                              │
│  Step 2 — DeepSORT  (CPU, per-instance tracker)             │
│    Associate detections across frames → track_id             │
│    Output: tracks  [{track_id, bbox}]                        │
│                                                              │
│  Step 3 — OSNet (GPU, inference_lock) + FAISS (state_lock)  │
│    Extract 512-d Re-ID embedding for each person crop        │
│    Query FAISS index + DB for nearest neighbor match         │
│    Assign or register cross-camera global_id                 │
│    Update FAISS index with new/updated embedding             │
│                                                              │
│  Step 4 — X3D (GPU, inference_lock)                         │
│    Runs every Config.X3D_INFERENCE_EVERY frames per global_id│
│    Needs ≥ X3D_CLIP_FRAMES frames in ClipBuffer              │
│    Output: theft_score  float 0–1                            │
│      ≥ 0.80 → classification="theft" → alert eligible       │
│      ≥ 0.50 → suspicious (flag only, no alert)              │
│                                                              │
│  Step 5 — Build result dict (see SSE payload schema)        │
│    is_suspicious = True if score ≥ 0.50 OR in registry      │
│                                                              │
│  Step 6 — SSE Callback  (throttled to 10 FPS)              │
│    sse_registry.publish(camera_id, result)                   │
│    → All subscribed EventSource clients receive the event    │
│                                                              │
│  Step 7 — DB Write  (every ~2 s or immediately on theft)    │
│    AIInference.objects.create(...)                           │
│    If theft: Alert.objects.create(...) + clip upload         │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
SSE Stream → CameraFeedWithOverlay.jsx (canvas bounding boxes)
           → LiveTrackingNodeGraph.jsx (suspect node graph)
```

### Threshold Summary

| Score Range | `classification` | `alert_triggered` | `is_suspicious` |
|-------------|-----------------|-------------------|-----------------|
| `< 0.50` | `"normal"` | `false` | `false` |
| `≥ 0.50, < 0.80` | `"normal"` | `false` | `true` |
| `≥ 0.80` | `"theft"` | `true` | `true` |

---

## 3. Module Responsibilities

### `continuous_monitor.py` — Capture Loop & Video Saving

**`ContinuousMonitor`** (per camera instance)

- **`_capture_loop` (Thread 1):** Opens the RTSP stream with
  `cv2.VideoCapture`, reads raw frames at full camera FPS (15–30 FPS), and
  immediately downscales to 640×480 before storing them in a rolling
  `deque(maxlen=150)` frame buffer (≈ 5 seconds of footage at 30 FPS).

- **`_monitor_loop` (Thread 2):** Reads `self.latest_frame` from the shared
  pointer and calls `runner.run_inference()`. After inference, the result is
  immediately published to SSE clients (callback fires first, before any DB
  write), then saved to the database every ~2 seconds or immediately on theft.

- **Clip encoding / upload:** On every theft classification, the rolling
  frame buffer is snapshot (thread-safe copy), clipped to ≈ 5 seconds, encoded
  to MP4 with OpenCV VideoWriter, uploaded to Cloudinary, and the resulting
  URL is saved on the `Alert` document — all in a separate daemon thread
  (`clip-upload-<alert_id>`).

- **`MonitorManager`** is a process-level singleton. It owns all per-camera
  `ContinuousMonitor` instances and wires the `SSERegistry` as the primary
  callback automatically.

---

### `inference_runner.py` — AI Orchestration

**`InferenceRunner`** (per-camera, per-thread, stateful)

Each instance owns an isolated `MultiObjectTracker` (DeepSORT) and embedding
smoothing buffers. No state is shared between camera threads, preventing
cross-contamination.

All GPU forward passes use `ai_service.inference_lock` (mutual exclusion).
All shared FAISS/identity state uses `ai_service.state_lock`.

Key method: `run_inference(frame_bgr, camera_id) → dict`
(also aliased as `process_frame` for backward compatibility with on-demand views).

---

## 4. Critical Architecture Decisions & Gotchas

### 4.1 Hardware RAM — Immediate 640×480 Downscale

**Problem:** Full-resolution 1080p frames (≈ 6.2 MB each) accumulated in the
rolling frame buffer (150 frames) consumed ≈ 930 MB of RAM, causing
`cv::OutOfMemoryError` crashes in OpenCV when the VideoWriter tried to
allocate additional space for clip encoding.

**Fix (in `_capture_loop`):**
```python
frame = cv2.resize(raw_frame, (640, 480))  # 0.9 MB per frame
del raw_frame                              # free the native 1080p array immediately
```

A 640×480 frame is ≈ 0.9 MB. The full 150-frame buffer now uses only ≈ 135 MB,
keeping peak RAM well within safe limits. This resolution is also sufficient for
X3D inference and for producing acceptable quality alert clips.

---

### 4.2 RAM — `gc.collect()` Before and After Clip Encoding

**Problem:** Even after frame downscaling, the clip encoding process
(`write_frames_to_mp4` + `upload_video_to_cloudinary`) temporarily held
references to the frame list, preventing garbage collection and causing
further memory spikes at upload time.

**Fix (in `_upload_worker`):**
```python
import gc
gc.collect()                    # Flush RAM before VideoWriter allocation
write_frames_to_mp4(clip_frames, tmp_path, fps=fps)
del clip_frames                 # Release list immediately after encoding
del frames                      # Release the snapshot copy
gc.collect()                    # Flush RAM after VideoWriter releases
```

The inference loop itself also calls `gc.collect()` every 50 frames as a
periodic housekeeping measure.

---

### 4.3 VRAM — Aggressive `torch.cuda.empty_cache()` Scheduling

**Problem:** PyTorch reserves freed VRAM in its memory pool and does not return
it to the CUDA allocator, causing fragmentation. On a 6 GB GPU running YOLO +
OSNet + X3D simultaneously, this caused `CUDA out of memory` errors.

**Fixes:**

1. **Inference loop** — cache flush every 15 frames, or immediately on any
   theft detection:
   ```python
   if self.frames_processed % 15 == 0 or result.get('classification') == 'theft':
       torch.cuda.empty_cache()
   ```

2. **Before X3D inference** (inside `InferenceRunner`):
   ```python
   if torch.cuda.is_available():
       torch.cuda.empty_cache()  # Force VRAM defrag before X3D tensor allocation
   score = ai_service.x3d.predict(clip)
   ```

3. **X3D calls use `torch.inference_mode()`** (inside the X3D classifier)
   to prevent gradient tracking overhead, saving both VRAM and compute.

4. **Environment variable** set at server startup:
   ```python
   # Allows PyTorch to split large memory blocks to reduce fragmentation
   os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
   ```

---

### 4.4 FAISS Permanent Memory — Suspects Are Never Forgotten

**Design Decision:** FAISS embedding purges triggered by DeepSORT track
deletions are **explicitly disabled**.

**Rationale:** When a suspect walks out of frame and DeepSORT drops their
track, the default behavior would remove their embedding from the FAISS index,
causing them to be assigned a brand-new `global_id` when they re-enter the
frame. This defeats cross-camera Re-ID entirely.

**Current behavior:**
- Embeddings are **only added or updated** in the FAISS index, never deleted.
- The `active_thief_global_ids` in-memory registry persists a suspect's
  `global_id` until `StopTrackingView` explicitly calls `remove_active_thief()`.
- FAISS's nearest-neighbor search will re-recognize a suspect from any camera
  zone as long as their embedding remains in the index.

**DeepSORT distance thresholds** were intentionally **relaxed** (higher `max_dist`)
so that returning suspects — who may have slightly different poses or partial
occlusions — are still correctly re-associated with their existing `global_id`
rather than spawning ghost identities.

---

### 4.5 Identity Hijacking Prevention

**Problem:** When two people are in the same frame, FAISS could theoretically
assign the same `global_id` to both, causing one person's bounding box to
"teleport" to another person's position.

**Fix (in `inference_runner.py`):** A pre-pass collects all `global_id` values
already active in the current frame before processing new tracks:

```python
used_global_ids = set()
# Pre-pass: claim all existing global IDs first
for track_info in valid_tracks:
    existing_gid = ai_service.db.get_global_id_for_track(...)
    if existing_gid is not None:
        used_global_ids.add(existing_gid)

# Main pass: reject FAISS matches that are already in-frame
if best_match_gid is not None and best_match_gid in used_global_ids:
    global_id = None  # reject — assign new identity
```

---

### 4.6 Alert Cooldown Gatekeeper

**Problem:** At 28 FPS, the pipeline would trigger ≈ 28 theft alerts per
second the moment the X3D threshold was crossed, flooding the database.

**Fix (in `_monitor_loop`):** A 5-second cooldown enforced with a timestamp
comparison:
```python
if is_theft_detected and (current_time - self.last_alert_time) >= 5.0:
    self.last_alert_time = current_time
    # Proceed: save DB alert, trigger VideoWriter
else:
    # COOLDOWN ACTIVE: suppress alert, keep is_suspicious=True in SSE payload
    is_theft_detected = False
    result['classification'] = 'normal'
    result['alert_triggered'] = False
    # NOTE: suspicious_ids and is_suspicious are NOT cleared here,
    # so the canvas overlay and Node Graph remain active during cooldown.
```

---

### 4.7 Global OpenCV Configuration (`apps.py`)

**Problem:** Setting `OPENCV_FFMPEG_CAPTURE_OPTIONS` at the point of stream capture was too late if `cv2` had already been initialized elsewhere in the project, causing FFmpeg transport and buffer configurations to be silently ignored.

**Fix:** The FFmpeg capture options (e.g. `rtsp_transport`, `stimeout`, `buffer_size`) are injected directly into `os.environ` during Django's `apps.py` initialization. This ensures they are applied globally before the first `cv2.VideoCapture()` call is made by the health checker or any API endpoint, forcing the intended network negotiation for RTSP streams.

---

### 4.8 SSE Throttled to 10 FPS

The monitoring loop processes frames at full camera FPS (up to 30). The SSE
callback is rate-limited to `_SSE_MAX_FPS = 10.0` to prevent unnecessary
bandwidth consumption on cloud deployments while still providing smooth
bounding box animations:

```python
min_interval = 1.0 / self._SSE_MAX_FPS   # 0.1 s
if (now - self._last_callback_time) >= min_interval:
    self.callback(self.camera_id, result)
```

---

## 5. Frontend Rendering — `CameraFeedWithOverlay.jsx`

### 5.1 Architecture (Z-Index Layers)

```
┌─────────────────────────────────────────┐
│  <img>   z-index: 1  — raw MJPEG feed   │
│  <canvas> z-index: 10 — bounding boxes   │
│           pointer-events: none (click-   │
│           through so video is still      │
│           interactive)                   │
│  Alert badge / LIVE badge  z-index: 20   │
└─────────────────────────────────────────┘
```

### 5.2 `knownThievesRef` — Frontend Permanent Memory

The `knownThievesRef` is a `useRef(new Set())` that acts as a permanent
in-memory thief registry on the frontend, mirroring the backend's
`active_thief_global_ids` registry.

**Behaviour:**
1. When a new SSE event arrives with `is_suspicious: true` for a `global_id`
   not yet in `knownThievesRef`, the ID is immediately added to the Set.
2. Every future SSE event is checked against `knownThievesRef`. If the
   `global_id` is already in the Set, the track is treated as suspicious
   **regardless** of the current frame's `x3d_score`.
3. This ensures the bounding box remains visible even when the X3D score
   dips below the threshold between inference windows, or when DeepSORT
   temporarily loses and re-acquires the track.

**"Normal" tracks are completely ignored** — the canvas draws **only** tracks
that are either newly flagged by `is_suspicious` or already present in
`knownThievesRef`.

---

### 5.3 LERP Animation & 3.5-Second TTL Grace Period

**Problem:** HTTP polling and SSE network jitter can cause frames to arrive
irregularly. If the canvas cleared on every "missing" frame, bounding boxes
would flicker at 5–10 Hz.

**Fix:** The `requestAnimationFrame` loop (running at 60 Hz) uses LERP
(Linear Interpolation) to smoothly animate bounding boxes toward their
target positions, and a **3.5-second TTL (grace period)** to keep boxes
on screen even when no new SSE event has arrived:

```javascript
const LERP_FACTOR = 0.2;  // applied every rAF tick (~60 Hz)

// TTL check — 3500 ms without an update → person left the frame
if (now - timestamp > 3500) {
    latchedSuspectsRef.current.delete(trackId);
    delete targetBoxRef.current[trackId];
    delete visualBoxRef.current[trackId];
    continue;
}

// LERP step — smooth movement toward target bbox
visual[0] += (target.bbox[0] - visual[0]) * LERP_FACTOR;
// ... (all 4 coordinates)
```

The 3.5 s window is deliberately longer than the SSE throttle interval (100 ms)
and HTTP polling latency, ensuring boxes survive typical network hiccups without
flickering.

---

### 5.4 NaN Poisoning Guard

DeepSORT occasionally produces `NaN` or `undefined` bbox values during track
initialization. The canvas loop guards against this at two points:

```javascript
// Guard 1: Before LERP calculation
if (target && target.bbox && target.bbox.length === 4 && !target.bbox.some(isNaN)) {
    // safe to LERP
}

// Guard 2: Before strokeRect
if (visual && visual.length === 4 && !visual.some(isNaN)) {
    // safe to draw
} else {
    delete visualBoxRef.current[trackId]; // force reset on next frame
}
```

---

## 6. `LiveTrackingNodeGraph.jsx` — React Portal Architecture

### 6.1 The CSS Containment Problem

The Control Room page uses a CSS grid with `overflow: hidden` on the camera
grid container. This causes any absolutely-positioned child (like a footer
panel) to be clipped to the grid cell bounds, making the Node Graph invisible
or partially hidden.

### 6.2 The Fix: `ReactDOM.createPortal`

`LiveTrackingNodeGraph.jsx` uses `ReactDOM.createPortal` to teleport its
rendered DOM nodes **directly into `document.body`**, completely bypassing
the Control Room's CSS containment:

```jsx
import { createPortal } from 'react-dom';

// Rendered outside the ControlRoom grid — appended to <body>
return createPortal(
  <div className="fixed bottom-0 left-0 right-0 z-50 ...">
    {/* suspect node graph */}
  </div>,
  document.body
);
```

This gives the Node Graph a clean `z-index: 50` stacking context with no
parent overflow constraints.

---

## 7. Stop Tracking — Dual Synchronization Protocol

Clearing a suspect requires **two simultaneous actions** to be fully
effective:

### 7.1 Step A — Backend API Call (JWT Authenticated)

```javascript
// LiveTrackingNodeGraph.jsx
await axios.post(
  `${API_BASE_URL}/api/ai/suspects/${globalId}/stop-tracking/`,
  {},
  { headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` } }
);
```

This calls `StopTrackingView`, which:
1. Calls `ai_service.remove_active_thief(global_id_int)`
2. Removes the ID from the backend `active_thief_global_ids` Set
3. Future SSE events from the pipeline will no longer carry `is_suspicious: true`
   for that `global_id`

### 7.2 Step B — Frontend Global Event (`ai-suspect-cleared`)

```javascript
// Immediately after the API call succeeds:
window.dispatchEvent(new CustomEvent('ai-suspect-cleared', { detail: { globalId } }));
```

`CameraFeedWithOverlay.jsx` listens for this event on **every active camera
feed instance**:

```javascript
const handleSuspectCleared = (e) => {
  const globalId = String(e.detail.globalId);
  knownThievesRef.current.delete(globalId);      // remove from permanent memory
  latchedSuspectsRef.current.delete(globalId);   // stop drawing
  delete targetBoxRef.current[globalId];
  delete visualBoxRef.current[globalId];
  // Fallback scan: clear any track-ID-keyed entry whose label matches
  for (const [key, target] of Object.entries(targetBoxRef.current)) {
    if (target.label === `THIEF G:${globalId}`) { /* ... clear ... */ }
  }
};
```

**Why both steps are necessary:**
- The API call stops *future* SSE events from re-flagging the suspect.
- The frontend event *instantly* wipes the bounding box on all open camera
  overlays without waiting for the next SSE poll cycle (100 ms latency).

Without Step B, the bounding box remains on screen for up to 3.5 seconds
(the TTL grace period) after the API call returns.

---

## 8. SSE Registry — `sse_registry.py`

The `SSERegistry` is a thread-safe publish/subscribe broker that decouples
the AI inference threads from the SSE HTTP connections:

```
InferenceThread → sse_registry.publish(camera_id, result)
                        │
                   Queue.put() for each subscriber
                        │
SSE HTTP handler ← Queue.get(timeout=25)  → yield "data: {...}\n\n"
```

Each SSE client (`EventSource` in the browser) gets its own `queue.Queue`.
The registry manages subscription and cleanup automatically when the client
disconnects (`GeneratorExit` in the streaming generator).

---

## 9. Database Models Involved in the AI Pipeline

| Model | App | Purpose |
|-------|-----|---------|
| `Camera` | `cameras` | Source of RTSP URL; `ai_monitoring_enabled` flag persists monitor state |
| `AIInference` | `ai_engine` | Stores every inference result (classification, confidence, tracks JSON) |
| `Alert` | `alerts` | Created on theft detection; stores `video_url` (Cloudinary clip) |
| `TrackingRecord` | `tracking` | Per-camera sighting record written by `TrackingService.save_tracks()` |
| `DetectionTrack` | `ai_engine` | Stores behavioural feature counts per track (hand-in-bag, etc.) |

---

## 10. Key Configuration Constants

```python
# ai_pipeline/ai_config/config.py
X3D_THEFT_THRESHOLD      = 0.80   # Triggers "theft" + alert
X3D_SUSPICIOUS_THRESHOLD = 0.50   # Flags track as suspicious (no alert)
X3D_INFERENCE_EVERY      = 5      # Run X3D every N frames per global_id
X3D_CLIP_FRAMES          = 8      # Min frames in ClipBuffer to run X3D

EMBEDDING_UPDATE_INTERVAL = 10    # Update FAISS embedding every N frames

# continuous_monitor.py
_SSE_MAX_FPS     = 10.0           # Cap SSE callback at 10 events/second
ALERT_COOLDOWN_S = 5.0            # Min seconds between consecutive alerts
FRAME_BUFFER_LEN = 150            # Rolling buffer depth (≈5 s at 30 FPS)
CAPTURE_RESOLUTION = (640, 480)   # Immediate downscale target
```
