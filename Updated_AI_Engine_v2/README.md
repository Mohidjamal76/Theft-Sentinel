# Theft Sentinel MCMT v2

**Merged from:**
- `New_MCMT` — best Multi-Camera Multi-Object Tracking (MCMT) logic
- `Updated_AI_Engine` — best X3D-S Theft Detection logic

---

## What was merged and why

| Component | Source | Reason |
|-----------|--------|--------|
| `config/config.py` | **Merged** | MCMT params from New_MCMT + all X3D params from Updated_AI_Engine |
| `camera/stream.py` | **New_MCMT** | Better network-stream handling: grab()/retrieve() drains buffer, reconnects on drop, handles HTTP/RTSP/HTTPS |
| `detection/detector.py` | Both (identical) | YOLOv8 person detector; `YOLO_CONFIDENCE=0.35` from Updated_AI_Engine (better recall for theft) |
| `tracking/tracker.py` | Both (identical) | DeepSORT per-camera tracker |
| `reid/extractor.py` | **New_MCMT** | `osnet_ain_x1_0` (Attentive Instance Normalization — more robust to cross-camera lighting shifts) + mean-centering before L2 normalize |
| `matching/matcher.py` | **New_MCMT** | FAISS IndexFlatIP with adaptive thresholds; cleaner dual-strategy usage |
| `database/identity_db.py` | **New_MCMT** | `get_best_match_score()` compares against every buffered embedding (not just average) — more robust matching |
| `theft_detection/x3d_detector.py` | **Updated_AI_Engine** | Complete X3D-S state machine (unchanged) |
| `theft_detection/__init__.py` | **New** | Was missing in Updated_AI_Engine |
| `visualization/display.py` | **Updated_AI_Engine** | Theft-specific overlays: red flash, THEFT! label, theft banner |
| `main.py` | **Merged** | TheftSentinelMCMT with all 3 FIXes from Updated_AI_Engine + `_match_globally()` dual strategy, EMA FPS, and extended `_print_stats()` from New_MCMT |
| `evaluate.py` | **New_MCMT** | MOTA, IDF1, ID-switches evaluation (unique to New_MCMT) |

---

## Key improvements in v2

### Multi-Camera Tracking (from New_MCMT)
- **`osnet_ain_x1_0`** ReID model — Attentive Instance Normalization handles cross-camera lighting/domain shifts, critical for accurate cross-camera identity matching.
- **Mean-centering** before L2-normalize reduces style bias in embeddings.
- **Dual matching strategy**: FAISS fast search + direct DB best-match-in-buffer (takes the higher score). Reduces false identity merges.
- **`get_best_match_score()`** in IdentityRecord — compares query against all buffered embeddings, not just the running average. A single clear sighting at a different angle still matches.
- **EMA FPS** — exponential moving average for smooth FPS display.
- **Stricter thresholds**: `MATCH_THRESHOLD_SAME_CAM=0.60`, `MATCH_THRESHOLD_DIFF_CAM=0.70`.
- **evaluate.py** — offline MOTA/IDF1/ID-switches evaluation with threshold sweep.

### Theft Detection (from Updated_AI_Engine)
- **X3D-S per-global-ID** behavioral classification (64-frame buffer per person).
- **FIX 1** — `str()` normalisation of `track_id` everywhere prevents dict-key mismatches.
- **FIX 2** — Dense frame pushing: every confirmed track every frame, so the X3D buffer fills at camera FPS (not sparsely on ReID success).
- **FIX 3** — IoU-based YOLO-bbox alignment: X3D gets the raw YOLO detection box (not DeepSORT's Kalman position), matching training crop preprocessing exactly.
- **Smoothed score + consecutive check + cooldown** state machine.
- **Rising-edge alert counting** — one console alert per theft event, not one per frame.
- **Red theft banner**, soft flash overlay, `THEFT!` box label.

---

## Quick start

```bash
pip install -r requirements.txt

# Place your trained X3D-S checkpoint:
cp /path/to/best_model.pth .

# Run with default sources from config.py
python main.py

# Run with custom video files
python main.py --sources test_videos/cam1.mp4 test_videos/cam2.mp4

# Run with live cameras (integer = device index)
python main.py --sources 0 1

# Run with RTSP streams
python main.py --sources rtsp://user:pass@192.168.1.100/stream1 rtsp://user:pass@192.168.1.101/stream2

# Override key parameters
python main.py --checkpoint best_model.pth --threshold 0.70 --match-threshold 0.65
```

### Runtime keys
| Key | Action |
|-----|--------|
| `q` / `ESC` | Quit |
| `s` | Print detailed stats |
| `d` | Toggle per-detection console logging |

---

## Configuration

All parameters are in `config/config.py`. Key sections:

**ReID matching** — adjust `MATCH_THRESHOLD_SAME_CAM` / `MATCH_THRESHOLD_DIFF_CAM` for your scene.

**Theft detection** — `X3D_THEFT_THRESH`, `X3D_CONSECUTIVE_REQUIRED`, `X3D_COOLDOWN_SECONDS`.

**Camera sources** — edit `CAMERA_SOURCES` list (or pass `--sources` on CLI).

---

## Evaluate tracking accuracy (offline)

```bash
# Compute MOTA, IDF1, ID-switches
python evaluate.py --gt ground_truth.txt --pred predictions.txt

# Print common failure cases and tuning tips
python evaluate.py --analysis
```

---

## Project structure

```
Updated_AI_Engine_v2/
├── main.py                  # Merged pipeline (TheftSentinelMCMT)
├── evaluate.py              # Offline MOTA/IDF1 evaluation (New_MCMT)
├── requirements.txt
├── README.md
├── config/
│   └── config.py            # All parameters (MCMT + X3D)
├── camera/
│   └── stream.py            # Threaded multi-camera capture
├── detection/
│   └── detector.py          # YOLOv8 person detector
├── tracking/
│   └── tracker.py           # DeepSORT per-camera tracker
├── reid/
│   └── extractor.py         # OSNet-AIN ReID feature extractor
├── matching/
│   └── matcher.py           # FAISS cross-camera matcher
├── database/
│   └── identity_db.py       # Global identity database
├── theft_detection/
│   └── x3d_detector.py      # X3D-S state machine (TheftState, GlobalTheftDetector)
├── visualization/
│   └── display.py           # Tiled display + theft overlays
└── test_videos/             # Place your test clips here
```
