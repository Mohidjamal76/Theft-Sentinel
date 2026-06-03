"""
Inference Runner — per-camera frame processor (Updated_AI_Engine_v2).

Each ContinuousMonitor owns one InferenceRunner instance.
The instance holds its own DeepSORT tracker and embedding-smoothing buffer
so that per-camera state is completely isolated between threads.

Root-cause fix (v2 parity):
  The previous version auto-assigned a module-level integer _int_cam_id
  (1, 2, 3 …) to each InferenceRunner.  Embeddings were stored under that
  integer; FAISS queries used that same integer for adaptive-threshold
  selection.  On server restart or a new InferenceRunner creation the
  integer changed, every track looked like a new cross-camera identity,
  and with MATCH_THRESHOLD_DIFF_CAM = 0.50 everything collapsed into
  GID=1 — exactly the bug reported.

  Fix: use the real MongoDB camera_id STRING passed to run_inference()
  as the camera key throughout.  This is stable across restarts and
  exactly matches the v2 main.py behavior (camera_id = integer index
  there, string here — but used consistently either way).

v2 Changes (Updated_AI_Engine_v2 priority):
  - X3D inference is delegated to ai_service.theft_detector (GlobalTheftDetector)
    which owns the per-global-ID TheftState state machine.
  - push_frame() is called for EVERY confirmed track every frame (FIX 2).
  - IoU-matched raw YOLO bbox passed to push_frame() (FIX 3).
  - track_id is always normalised via str() (FIX 1).
  - is_theft / in_cooldown / consecutive_theft / theft_label propagated.

All GPU calls go through ai_service.inference_lock.
All shared-state mutations go through ai_service.state_lock.
"""

import collections
import threading
import time
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

from .ai_service import ai_service

from ai_pipeline.ai_config.config import Config
from ai_pipeline.tracking.tracker import MultiObjectTracker


def _bbox_iou(b1: List[float], b2: List[float]) -> float:
    """Intersection-over-Union for two [x1,y1,x2,y2] boxes."""
    x1 = max(b1[0], b2[0]);  y1 = max(b1[1], b2[1])
    x2 = min(b1[2], b2[2]);  y2 = min(b1[3], b2[3])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
    a2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
    union = a1 + a2 - inter
    return inter / union if union > 0 else 0.0


class InferenceRunner:
    """
    Stateful per-camera pipeline runner — v2 (Updated_AI_Engine_v2).

    Maintains:
      • A DeepSORT tracker (thread-isolated — never shared between cameras)
      • Per-(camera_id_str, track_id_str) embedding smoothing deque (maxlen=10)
      • Per-(camera_id_str, track_id_str) embedding update counters
      • A local frame counter for periodic maintenance scheduling

    The camera_id is stored as None until the first run_inference() call,
    at which point it is fixed to the MongoDB camera_id string.  All
    subsequent FAISS / DB calls use this stable string key.
    """

    _PRUNE_EVERY   = 300   # frames between expired-ID pruning
    _REBUILD_EVERY = 500   # frames between FAISS index rebuild

    def __init__(self) -> None:
        # Set on first call to run_inference() — the actual MongoDB camera_id string.
        # Using None until then avoids premature tracker construction.
        self._camera_id_str: Optional[str] = None

        # Lazy-initialised DeepSORT tracker
        self._tracker: Optional[MultiObjectTracker] = None

        # Per-(camera_id_str, track_id_str) embedding smoothing
        self._embed_buf:        Dict[tuple, collections.deque] = {}
        # Per-(camera_id_str, track_id_str) embedding update throttle counter
        self._embed_update_cnt: Dict[tuple, int]               = {}

        self._frame_idx: int = 0

    def _ensure_tracker(self, camera_id_str: str) -> None:
        """Lazily create the DeepSORT tracker on first use."""
        if self._tracker is None:
            self._tracker = MultiObjectTracker(camera_id_str)

    def _match_det_to_track(
        self,
        track_bbox: List[float],
        raw_dets:   List[Dict],
    ) -> Optional[Dict]:
        """
        Return the raw YOLO detection best-matching a track by IoU.
        Used for FIX 3: X3D gets training-aligned YOLO crop, not Kalman box.
        """
        best_det = None
        best_iou = 0.3   # minimum overlap threshold
        for det in raw_dets:
            iou = _bbox_iou(track_bbox, [float(v) for v in det["bbox"]])
            if iou > best_iou:
                best_iou = iou
                best_det = det
        return best_det

    # ── public API ────────────────────────────────────────────────────────────

    def run_inference(
        self,
        frame_bgr: np.ndarray,
        camera_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process one BGR frame through the full v2 pipeline.

        Args:
            frame_bgr:  BGR image as numpy array (any resolution).
            camera_id:  String MongoDB camera ID — used for metadata only.

        Returns:
            Dict with keys: classification, confidence, detections, poses,
            tracks, suspicious_tracks, frame_metadata, processing_time_ms.
        """
        if not ai_service.is_ready():
            raise RuntimeError("AI Service not initialized")

        # ── Pin camera_id on first call ──────────────────────────────────────
        # Use the stable MongoDB camera_id string as the camera key throughout
        # FAISS / DB / state_machine.  Previously an auto-incrementing integer
        # was used, which changed on every InferenceRunner construction causing
        # every track to look like a new cross-camera identity.
        if self._camera_id_str is None:
            self._camera_id_str = str(camera_id) if camera_id is not None else "default"
            logger.info(
                "[InferenceRunner] Camera ID pinned as '%s'", self._camera_id_str
            )

        self._ensure_tracker(self._camera_id_str)
        start = time.time()
        self._frame_idx += 1

        h, w      = frame_bgr.shape[:2]
        # FIX 4: always convert to RGB here so frame_rgb is never None.
        # v2 converts unconditionally at the top of process_camera().
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)


        # ── 1. Detect persons (GPU — inference_lock) ──────────────────────
        with ai_service.inference_lock:
            raw_dets = ai_service.detector.detect(frame_bgr)

        # ── 2. Track locally (per-instance, no shared state) ──────────────
        tracks = self._tracker.update(raw_dets, frame_bgr)

        # ── 3. IoU-match tracks → raw YOLO bboxes (FIX 3) ─────────────────
        # track_id normalised to str (FIX 1)
        track_to_yolo_bbox: Dict[str, list] = {}
        for t in tracks:
            tid   = str(t["track_id"])
            t_box = [float(v) for v in t["bbox"]]
            matched = self._match_det_to_track(t_box, raw_dets)
            track_to_yolo_bbox[tid] = matched["bbox"] if matched else t_box

        # ── 4. Crop person regions for ReID ───────────────────────────────
        crops:        List[np.ndarray] = []
        valid_tracks: List[Dict]       = []

        for t in tracks:
            crop = ai_service.reid.crop_person(frame_bgr, t["bbox"])
            if crop is not None:
                crops.append(crop)
                valid_tracks.append(t)

        # ── 5. Extract ReID embeddings (GPU — inference_lock) ─────────────
        embeddings: List[Optional[np.ndarray]] = []
        if crops:
            with ai_service.inference_lock:
                embeddings = ai_service.reid.extract_batch(crops)
        else:
            embeddings = []

        # ── 6. Match each track to a global ID ────────────────────────────
        results: List[Dict] = []

        # Hijack prevention pre-pass: claim already-known global IDs first.
        used_global_ids = set()
        with ai_service.state_lock:
            for track_info in valid_tracks:
                existing_gid = ai_service.db.get_global_id_for_track(
                    self._camera_id_str, str(track_info["track_id"])
                )
                if existing_gid is not None:
                    used_global_ids.add(existing_gid)

        for i, (track_info, embedding) in enumerate(zip(valid_tracks, embeddings)):
            if embedding is None:
                continue

            track_id = str(track_info["track_id"])   # FIX 1
            bbox     = [float(v) for v in track_info["bbox"]]
            key      = (self._camera_id_str, track_id)

            # 10-frame embedding smoothing (per-instance, no lock)
            if key not in self._embed_buf:
                self._embed_buf[key] = collections.deque(maxlen=10)
            self._embed_buf[key].append(embedding)

            smoothed = np.mean(list(self._embed_buf[key]), axis=0)
            norm     = np.linalg.norm(smoothed)
            smoothed = smoothed / norm if norm > 1e-6 else embedding

            # Assign global ID (state_lock guards matcher + shared dicts)
            with ai_service.state_lock:
                existing_gid = ai_service.db.get_global_id_for_track(
                    self._camera_id_str, track_id
                )

                if existing_gid is not None:
                    # Known track — update embedding periodically
                    cnt = self._embed_update_cnt.get(key, 0)
                    if cnt % Config.EMBEDDING_UPDATE_INTERVAL == 0:
                        ai_service.db.update_identity(
                            existing_gid, smoothed,
                            self._camera_id_str, track_id,
                        )
                        ai_service.matcher.add_embedding(
                            smoothed, existing_gid, self._camera_id_str
                        )
                    self._embed_update_cnt[key] = cnt + 1
                    global_id = existing_gid

                else:
                    # New track — dual-strategy match (FAISS + DB)
                    faiss_gid, faiss_score = ai_service.matcher.query(
                        smoothed, self._camera_id_str
                    )
                    db_gid, db_score = ai_service.db.find_match(
                        smoothed, self._camera_id_str
                    )

                    best_match_gid = None
                    if faiss_score >= db_score and faiss_gid is not None:
                        best_match_gid = faiss_gid
                    elif db_gid is not None:
                        best_match_gid = db_gid

                    # HIJACK PREVENTION
                    if best_match_gid is not None and best_match_gid in used_global_ids:
                        logger.debug(
                            "[FAISS] Track %s matched GID %s already in frame - rejected",
                            track_id, best_match_gid,
                        )
                        global_id = None
                    else:
                        global_id = best_match_gid

                    logger.debug(
                        "[FAISS] Track %s -> GID %s | FAISS %.3f | DB %.3f",
                        track_id, global_id, faiss_score, db_score,
                    )

                    if global_id is not None:
                        ai_service.db.update_identity(
                            global_id, smoothed, self._camera_id_str, track_id
                        )
                        ai_service.matcher.add_embedding(
                            smoothed, global_id, self._camera_id_str
                        )
                    else:
                        global_id = ai_service.db.register_new_identity(
                            smoothed, self._camera_id_str, track_id
                        )
                        ai_service.matcher.add_embedding(
                            smoothed, global_id, self._camera_id_str
                        )

                    used_global_ids.add(global_id)

                    # Ensure legacy per-global-id score tracking slots exist
                    ai_service.theft_scores.setdefault(global_id, None)
                    ai_service.x3d_frame_counters.setdefault(global_id, 0)


            yolo_bbox = track_to_yolo_bbox.get(track_id, bbox)
            matched_det = self._match_det_to_track(bbox, raw_dets)
            det_conf    = matched_det["confidence"] if matched_det else 0.0

            results.append({
                "track_id":  track_id,
                "global_id": global_id,
                "bbox":      bbox,
                "yolo_bbox": yolo_bbox,
                "det_conf":  det_conf,
            })

        # ── 7. Push frames to GlobalTheftDetector (FIX 2 + FIX 4 — dense fill) ────
        # frame_rgb was converted unconditionally at the top of run_inference().
        # Push for ALL DeepSORT-confirmed tracks with a known global_id, not
        # just those with successful ReID this frame.  This keeps the 64-frame
        # X3D buffer filling at camera FPS even when ReID temporarily fails.
        with ai_service.state_lock:
            pushed_gids: set = set()

            # Pass 1: tracks that completed full ReID pipeline this frame
            for res in results:
                gid = res["global_id"]
                if gid is None:
                    continue
                ai_service.theft_detector.push_frame(
                    global_id   = gid,
                    frame_rgb   = frame_rgb,
                    bbox        = res["yolo_bbox"],   # FIX 3: YOLO bbox
                    frame_shape = (h, w),
                )
                pushed_gids.add(gid)

            # Pass 2: DeepSORT tracks with a known GID that were excluded from
            # results this frame (crop/embedding failed).  Look up their GID
            # from the DB and push the frame to keep the buffer dense.
            result_track_ids = {res["track_id"] for res in results}
            for t in tracks:
                tid = str(t["track_id"])
                if tid in result_track_ids:
                    continue
                existing_gid = ai_service.db.get_global_id_for_track(
                    self._camera_id_str, tid
                )
                if existing_gid is not None and existing_gid not in pushed_gids:
                    t_box   = [float(v) for v in t["bbox"]]
                    matched = self._match_det_to_track(t_box, raw_dets)
                    yolo_b  = matched["bbox"] if matched else t_box
                    ai_service.theft_detector.push_frame(
                        global_id   = existing_gid,
                        frame_rgb   = frame_rgb,
                        bbox        = yolo_b,
                        frame_shape = (h, w),
                    )
                    pushed_gids.add(existing_gid)

        # ── 8. X3D inference via GlobalTheftDetector ──────────────────────
        # maybe_infer() checks should_infer() internally; no wasted GPU calls.
        for res in results:
            gid = res["global_id"]
            if gid is None:
                continue

            # Run under inference_lock (GPU forward pass)
            with ai_service.inference_lock:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                # maybe_infer acquires no external lock — state is per-identity
                theft_state = ai_service.theft_detector.maybe_infer(gid)

            # Update legacy score dict under state_lock
            with ai_service.state_lock:
                ai_service.theft_scores[gid] = theft_state.last_score
                ai_service.x3d_frame_counters[gid] = (
                    ai_service.x3d_frame_counters.get(gid, 0) + 1
                )

            res["theft_state"] = theft_state
            res["x3d_score"]   = theft_state.last_score

        # ── 9. Build classification result ────────────────────────────────
        highest_score = max(
            (r.get("x3d_score", 0.0) for r in results), default=0.0
        )

        classification = "normal"
        confidence     = highest_score

        # Theft confirmed when TheftState.is_theft or in_cooldown
        any_theft_confirmed = any(
            r.get("theft_state") and (
                r["theft_state"].is_theft or r["theft_state"].in_cooldown
            )
            for r in results
        )

        if any_theft_confirmed:
            # Any X3D-confirmed theft → classify as theft immediately.
            # The monitor-level cooldown gate (continuous_monitor._allow_db_alert)
            # ensures only ONE DB Alert is created per theft event.
            # classification='theft' is kept on every cooldown frame so the
            # SSE/frontend shows real-time THEFT overlays throughout.
            classification = "theft"
            for res in results:
                ts = res.get("theft_state")
                if ts and (ts.is_theft or ts.in_cooldown):
                    gid = res["global_id"]
                    if gid is not None and not ai_service.is_active_thief(gid):
                        ai_service.add_active_thief(gid)

        # ── 10. Build suspicious_tracks ────────────────────────────────────
        suspicious_tracks = []
        for res in results:
            gid = res["global_id"]
            ts  = res.get("theft_state")

            # Determine suspicion from TheftState or x3d_score threshold
            is_susp = False
            if ts and (ts.is_theft or ts.in_cooldown or ts.consecutive_theft > 0):
                is_susp = True
            elif res.get("x3d_score", 0.0) >= Config.X3D_SUSPICIOUS_THRESHOLD:
                is_susp = True

            # Override: known thief in registry → always suspicious
            if gid is not None:
                if ai_service.is_active_thief(str(gid)) or ai_service.is_active_thief(gid):
                    is_susp = True

            res["is_suspicious"] = is_susp

            if is_susp:
                suspicious_tracks.append({
                    "track_id":  res["track_id"],
                    "global_id": gid,
                    "x3d_score": res.get("x3d_score", 0.0),
                })

        # ── 11. Periodic maintenance ──────────────────────────────────────
        if self._frame_idx % self._PRUNE_EVERY == 0:
            ai_service.prune_expired_identities()
        if self._frame_idx % self._REBUILD_EVERY == 0:
            ai_service.rebuild_matcher_index()

        # ── 12. Assemble return dict (API contract preserved) ─────────────
        processing_time = (time.time() - start) * 1000.0

        tracks_out = []
        for res in results:
            gid = res["global_id"]
            ts  = res.get("theft_state")

            is_susp = res.get("is_suspicious", False)
            if gid is not None:
                if ai_service.is_active_thief(str(gid)) or ai_service.is_active_thief(gid):
                    is_susp = True

            track_dict = {
                "track_id":          res["track_id"],
                "global_id":         gid,
                "bbox":              res["bbox"],
                "class":             "person",
                "confidence":        res["det_conf"],
                "x3d_score":         res.get("x3d_score", 0.0),
                "is_suspicious":     bool(is_susp),
                # v2 extra fields from TheftState
                "is_theft":          bool(ts.is_theft)     if ts else False,
                "in_cooldown":       bool(ts.in_cooldown)  if ts else False,
                "consecutive_theft": (ts.consecutive_theft if ts else 0),
                "theft_label":       (ts.label             if ts else "Buffering..."),
            }

            if track_dict.get("global_id") is not None and track_dict["is_suspicious"]:
                logger.debug(
                    "📡 [PAYLOAD] GID %s is_suspicious=True  theft=%s",
                    track_dict["global_id"], track_dict["is_theft"],
                )

            tracks_out.append(track_dict)

        frame_metadata: Dict[str, Any] = {
            "frame_index":    self._frame_idx,
            "camera_id":      camera_id,
            "num_detections": len(raw_dets),
            "num_tracks":     len(tracks),
            "num_persons":    len(results),
            "raw_x3d_score":  highest_score,
        }
        if highest_score >= Config.X3D_SUSPICIOUS_THRESHOLD:
            frame_metadata["suspicious"] = True

        return {
            "classification":     classification,
            "confidence":         confidence,
            "detections": [
                {
                    "bbox":       [float(v) for v in d["bbox"]],
                    "confidence": d["confidence"],
                    "class":      "person",
                    "class_id":   d["class_id"],
                }
                for d in raw_dets
            ],
            "poses":              [],
            "tracks":             tracks_out,
            "suspicious_tracks":  suspicious_tracks,
            "frame_metadata":     frame_metadata,
            "processing_time_ms": processing_time,
        }

    # Backward-compatible alias
    process_frame = run_inference

    def reset(self) -> None:
        """Reset per-instance state (tracker + embedding buffers)."""
        self._tracker = None
        self._embed_buf.clear()
        self._embed_update_cnt.clear()
        self._frame_idx = 0
