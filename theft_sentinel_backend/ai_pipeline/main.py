"""
Theft Sentinel MCMT v2 — Multi-Camera Tracking + X3D-S Theft Detection
=======================================================================

MERGED from:
  New_MCMT          → Best multi-camera tracking logic:
                        osnet_ain_x1_0 ReID, dual FAISS+DB match strategy,
                        EMA FPS, per-identity _print_stats, evaluate.py module.
  Updated_AI_Engine → Best theft detection logic:
                        X3D-S per-global-ID state machine, IoU YOLO-bbox
                        alignment (FIX 3), dense frame pushing (FIX 2),
                        str() track-id normalisation (FIX 1), rising-edge
                        alert counting, theft banner visualization.

Full pipeline (per frame, per camera):
  1. YOLOv8 detects all persons → raw YOLO bboxes
  2. DeepSORT tracks per-camera (stable local track IDs, str-normalised)
  3. IoU-match each DeepSORT track back to its raw YOLO detection bbox
     (FIX 3: X3D gets training-matched crop, not Kalman-extrapolated position)
  4. OSNet-AIN extracts ReID embeddings (batched, mean-centered)
  5. 10-frame rolling average smoothing per track before matching
  6. Dual matching: FAISS (fast) + DB best-match-in-buffer (robust)
     → assigns / updates global IDs
  7. EVERY confirmed track that has a global_id → push full RGB frame +
     raw YOLO bbox to that identity's X3D buffer (FIX 2: dense filling)
  8. Every X3D_INFER_INTERVAL frames per identity → X3D-S inference →
     smoothed score → consecutive check → theft alert + cooldown
  9. Draw per-box theft overlay, theft banner, stats

Usage:
  python main.py
  python main.py --sources cam1.mp4 cam2.mp4
  python main.py --sources rtsp://cam1/stream rtsp://cam2/stream
  python main.py --checkpoint best_model.pth --threshold 0.70
  python main.py --sources 0 --match-threshold 0.65

Keys:  q / ESC → quit   s → stats   d → toggle detection logging
"""

import sys
import os
import time
import argparse
import numpy as np
import cv2
import collections
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_pipeline.ai_config.config            import Config
from ai_pipeline.detection.detector          import PersonDetector
from ai_pipeline.tracking.tracker            import MultiObjectTracker
from ai_pipeline.reid.extractor              import ReIDExtractor
from ai_pipeline.matching.matcher            import CrossCameraMatcher
from ai_pipeline.database.identity_db        import GlobalIdentityDatabase
from ai_pipeline.camera.stream               import MultiCameraManager
from ai_pipeline.visualization.display       import Visualizer
from ai_pipeline.theft_detection.x3d_detector import GlobalTheftDetector


# ── IoU helper (FIX 3 — YOLO-bbox alignment) ──────────────────────────────────

def _compute_iou(boxA: list, boxB: list) -> float:
    """Compute Intersection over Union of two [x1,y1,x2,y2] boxes."""
    xA = max(boxA[0], boxB[0]);  yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2]);  yB = min(boxA[3], boxB[3])
    inter = max(0, xB - xA) * max(0, yB - yA)
    if inter == 0:
        return 0.0
    areaA = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    areaB = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    union = areaA + areaB - inter
    return inter / union if union > 0 else 0.0


# ── Main pipeline class ────────────────────────────────────────────────────────

class TheftSentinelMCMT:
    """
    Unified Multi-Camera Multi-Target Tracking + X3D-S Theft Detection pipeline.

    Incorporates the best logic from New_MCMT (tracking) and
    Updated_AI_Engine (theft detection) into a single coherent system.
    """

    def __init__(self, sources: list = None, camera_ids: list = None):
        self.sources    = sources    or Config.CAMERA_SOURCES
        self.camera_ids = camera_ids or Config.CAMERA_IDS[:len(self.sources)]

        print("=" * 68)
        print("  THEFT SENTINEL MCMT v2")
        print("  Multi-Camera Tracking  +  X3D-S Behavioral Theft Detection")
        print("=" * 68)
        print(f"  Device:              {Config.DEVICE}")
        print(f"  Cameras:             {len(self.sources)}")
        print(f"  ReID model:          {Config.REID_MODEL_NAME}")
        print(f"  ReID threshold:      {Config.MATCH_THRESHOLD_DIFF_CAM} (cross-cam) / "
              f"{Config.MATCH_THRESHOLD_SAME_CAM} (same-cam)")
        print(f"  X3D checkpoint:      {Config.X3D_CHECKPOINT}")
        print(f"  X3D theft threshold: {Config.X3D_THEFT_THRESH}")
        print(f"  X3D clip length:     {Config.X3D_CLIP_LENGTH} frames")
        print(f"  X3D infer interval:  every {Config.X3D_INFER_INTERVAL} frames")
        print(f"  X3D consecutive req: {Config.X3D_CONSECUTIVE_REQUIRED}")
        print("=" * 68)

        print("\n[Init] Loading modules...")

        # MCMT modules
        self.detector       = PersonDetector()
        self.reid           = ReIDExtractor()
        self.matcher        = CrossCameraMatcher()
        self.db             = GlobalIdentityDatabase()
        self.camera_manager = MultiCameraManager()
        self.visualizer     = Visualizer()

        # One DeepSORT tracker per camera
        self.trackers: dict = {
            cam_id: MultiObjectTracker(cam_id) for cam_id in self.camera_ids
        }

        # X3D theft detector (model loaded once, shared across all identities)
        self.theft_detector = GlobalTheftDetector(
            checkpoint_path=Config.X3D_CHECKPOINT,
            device=Config.DEVICE,
        )

        # Bookkeeping
        self._frame_counter    = 0
        self._prune_interval   = 300   # frames between DB prunes
        self._rebuild_interval = 500   # frames between FAISS rebuilds
        self._start_time       = time.time()
        self._fps              = float(Config.TARGET_FPS)   # EMA seed
        self._running          = False
        self._total_alerts     = 0
        self._alerted_last     = False   # rising-edge tracker

        # ReID embedding smoothing: (camera_id, track_id_str) → deque(maxlen=10)
        self._embedding_update_counters: dict = {}
        self._track_embeddings_buffer:   dict = {}

        print("[Init] All modules loaded.\n")

    # ── Camera startup ─────────────────────────────────────────────────────────

    def start_cameras(self) -> bool:
        print("[Pipeline] Starting camera streams...")
        ok = 0
        for source, cam_id in zip(self.sources, self.camera_ids):
            if self.camera_manager.add_camera(source, cam_id):
                ok += 1
            else:
                print(f"  WARNING: Could not open Camera {cam_id}: {source}")
        if ok == 0:
            print("[Pipeline] ERROR: No cameras started!")
            return False
        time.sleep(1.0)
        print(f"[Pipeline] {ok}/{len(self.sources)} cameras active\n")
        return True

    # ── Global match helper (dual-strategy) ────────────────────────────────────

    def _match_globally(self, embedding: np.ndarray, camera_id: int) -> tuple:
        """
        Dual-strategy global identity matching.

        Strategy 1 — FAISS fast approximate search.
        Strategy 2 — Direct DB best-match-in-buffer (robust fallback).

        Returns the winner with the higher cosine similarity score.
        """
        faiss_gid, faiss_score = self.matcher.query(embedding, camera_id)
        db_gid,    db_score    = self.db.find_match(embedding, camera_id)

        if faiss_score >= db_score and faiss_gid is not None:
            return faiss_gid, faiss_score
        elif db_gid is not None:
            return db_gid, db_score

        return None, max(faiss_score, db_score)

    # ── Per-camera frame processing ────────────────────────────────────────────

    def process_camera(self, camera_id: int, frame_bgr: np.ndarray) -> tuple:
        """
        Full pipeline for one camera frame.

        Incorporates three critical fixes from Updated_AI_Engine_v2:

        FIX 1 (track_id type): DeepSORT may return track_id as int or str.
          str() normalisation throughout avoids dict-key mismatches.

        FIX 2 (sparse frame buffer): X3D push_frame is called for EVERY
          confirmed track every frame — ensures the 64-frame buffer fills
          at camera FPS, exactly like Deployment_v3_final.py behavior.

        FIX 3 (bbox source): Each DeepSORT track is IoU-matched back to
          its raw YOLO detection bbox so X3D receives training-aligned crops.
          The 40% padding is applied inside push_frame() in x3d_detector.py.
        """
        h, w      = frame_bgr.shape[:2]
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        # ─── Step 1: YOLOv8 person detection ────────────────────────────────
        raw_detections = self.detector.detect(frame_bgr)

        # ─── Step 2: DeepSORT tracking ───────────────────────────────────────
        tracker = self.trackers[camera_id]
        tracks  = tracker.update(raw_detections, frame_bgr)

        # ─── Step 3: IoU-match tracks → raw YOLO bboxes (FIX 3) ─────────────
        track_to_yolo_bbox: dict = {}
        for track in tracks:
            tid   = str(track["track_id"])   # FIX 1
            t_box = track["bbox"]
            best_iou = 0.0
            best_box = t_box   # fallback: use DeepSORT Kalman box
            for det in raw_detections:
                iou = _compute_iou(t_box, det["bbox"])
                if iou > best_iou:
                    best_iou = iou
                    best_box = det["bbox"]
            track_to_yolo_bbox[tid] = best_box

        # ─── Step 4: OSNet-AIN ReID embeddings ───────────────────────────────
        crops      = []
        track_list = []
        for track in tracks:
            crop = self.reid.crop_person(frame_bgr, track["bbox"])
            if crop is not None:
                crops.append(crop)
                track_list.append(track)

        embeddings = self.reid.extract_batch(crops) if crops else []

        # ─── Step 5: 10-frame smoothing + global ID assignment ───────────────
        track_to_global_id: dict = {}

        for track_info, embedding in zip(track_list, embeddings):
            if embedding is None:
                continue

            track_id = str(track_info["track_id"])   # FIX 1
            key      = (camera_id, track_id)

            # Rolling 10-frame embedding average for stable representation
            if key not in self._track_embeddings_buffer:
                self._track_embeddings_buffer[key] = collections.deque(maxlen=10)
            self._track_embeddings_buffer[key].append(embedding)

            smoothed = np.mean(list(self._track_embeddings_buffer[key]), axis=0)
            norm = np.linalg.norm(smoothed)
            smoothed = smoothed / norm if norm > 0 else embedding

            existing_gid = self.db.get_global_id_for_track(camera_id, track_id)

            if existing_gid is not None:
                # Already assigned — update embedding at configured interval
                counter = self._embedding_update_counters.get(key, 0)
                if counter % Config.EMBEDDING_UPDATE_INTERVAL == 0:
                    self.db.update_identity(existing_gid, smoothed, camera_id, track_id)
                    self.matcher.add_embedding(smoothed, existing_gid, camera_id)
                self._embedding_update_counters[key] = counter + 1
                global_id   = existing_gid
                match_score = 1.0
            else:
                # New track — dual-strategy global matching
                global_id, match_score = self._match_globally(smoothed, camera_id)

                if global_id is not None:
                    print(f"[Match] Cam {camera_id} Track {track_id} "
                          f"→ Global {global_id} (score: {match_score:.3f})")
                    self.db.update_identity(global_id, smoothed, camera_id, track_id)
                    self.matcher.add_embedding(smoothed, global_id, camera_id)
                else:
                    global_id = self.db.register_new_identity(
                        smoothed, camera_id, track_id
                    )
                    print(f"[New ID] Cam {camera_id} Track {track_id} "
                          f"→ Global {global_id}")
                    self.matcher.add_embedding(smoothed, global_id, camera_id)
                    match_score = 0.0

            track_to_global_id[track_id] = global_id

        # ─── Step 6: Push frames to X3D buffer (FIX 2 — dense, every track) ──
        # Iterate ALL confirmed tracks (not just those with reid embeddings).
        # Only skip a track if it has no global_id yet (reid failed this frame).
        # This fills the 64-frame buffer at camera FPS — identical to
        # Deployment_v3_final.py behavior and training preprocessing.
        for track in tracks:
            track_id  = str(track["track_id"])
            global_id = track_to_global_id.get(track_id)
            if global_id is None:
                continue

            yolo_bbox = track_to_yolo_bbox.get(track_id, track["bbox"])
            self.theft_detector.push_frame(
                global_id   = global_id,
                frame_rgb   = frame_rgb,
                bbox        = yolo_bbox,
                frame_shape = (h, w),
            )

        # ─── Step 7: X3D inference for every known identity ──────────────────
        # Run for ALL identities with states, not just ones visible this frame
        # (a person may be off-screen but their buffer can still fire)
        for gid in list(self.theft_detector.get_active_global_ids()):
            self.theft_detector.maybe_infer(gid)

        # ─── Step 8: Build result list for visualization ─────────────────────
        results = []
        for track_info, embedding in zip(track_list, embeddings):
            track_id  = str(track_info["track_id"])
            global_id = track_to_global_id.get(track_id)
            if global_id is None:
                continue

            theft_state = self.theft_detector.get_state(global_id)

            results.append({
                "camera_id":         camera_id,
                "track_id":          track_id,
                "global_id":         global_id,
                "bbox":              track_info["bbox"],
                "match_score":       1.0 if self.db.get_global_id_for_track(
                                         camera_id, track_id) else 0.0,
                "is_theft":          theft_state.is_theft,
                "in_cooldown":       theft_state.in_cooldown,
                "consecutive_theft": theft_state.consecutive_theft,
                "theft_score":       theft_state.last_score,
                "theft_label":       theft_state.label,
            })

        # ─── Step 9: Annotate frame ───────────────────────────────────────────
        annotated = self.visualizer.draw_detections(frame_bgr, results, camera_id)
        return annotated, results

    # ── Periodic maintenance ───────────────────────────────────────────────────

    def _periodic_maintenance(self):
        """Prune expired identities and rebuild the FAISS index periodically."""
        self._frame_counter += 1

        if self._frame_counter % self._prune_interval == 0:
            self.db.prune_expired()
            active = set(self.db.get_all_identities().keys())
            self.theft_detector.prune_states(active)

        if self._frame_counter % self._rebuild_interval == 0:
            identities    = self.db.get_all_identities()
            identity_data = {
                gid: {"embedding_buffer": list(rec.embedding_buffer)}
                for gid, rec in identities.items()
            }
            self.matcher.rebuild_index(identity_data)

    # ── Main loop ──────────────────────────────────────────────────────────────

    def run(self):
        """
        Main processing loop.

        Frame pacing uses EMA FPS — smooth readout instead of jumpy per-second
        resets. Theft alerts use rising-edge counting — one console alert per
        event, not one per frame.
        """
        if not self.start_cameras():
            return

        self._running = True
        print("[Pipeline] Running.  Press q to quit, s for stats, d to toggle logging.\n")

        target_interval = 1.0 / Config.TARGET_FPS if Config.TARGET_FPS > 0 else 0

        try:
            while self._running:
                loop_start = time.time()

                frames = self.camera_manager.get_all_frames()
                if not frames:
                    time.sleep(0.01)
                    continue

                annotated_frames = {}
                all_detections   = []

                for cam_id, frame in frames.items():
                    ann, dets = self.process_camera(cam_id, frame)
                    annotated_frames[cam_id] = ann
                    all_detections.extend(dets)

                self._periodic_maintenance()

                # Theft summary
                theft_summary = self.theft_detector.get_theft_summary()
                any_theft     = self.theft_detector.any_theft_active()

                # Rising-edge alert counting (Updated_AI_Engine)
                if any_theft and not self._alerted_last:
                    self._total_alerts += 1
                    for gid, (alert, score, lbl) in theft_summary.items():
                        if alert:
                            ts = datetime.now().strftime("%H:%M:%S")
                            print(f"  [{ts}] !! THEFT ALERT — GlobalID:{gid}  {lbl}")
                self._alerted_last = any_theft

                # EMA FPS (smooth, stable readout)
                processing_time = time.time() - loop_start
                sleep_time      = target_interval - processing_time
                if sleep_time > 0:
                    time.sleep(sleep_time)
                frame_time   = time.time() - loop_start
                instant_fps  = 1.0 / max(frame_time, 0.001)
                self._fps    = 0.9 * self._fps + 0.1 * instant_fps

                # Display
                tiled = self.visualizer.create_tiled_display(annotated_frames)
                tiled = self.visualizer.draw_theft_banner(tiled, any_theft, theft_summary)

                db_stats = self.db.get_stats()
                db_stats.update({
                    "fps":          self._fps,
                    "faiss_size":   self.matcher.get_index_size(),
                    "theft_alerts": self._total_alerts,
                })
                tiled = self.visualizer.draw_stats_overlay(tiled, db_stats)

                cv2.imshow("Theft Sentinel MCMT v2", tiled)

                if Config.LOG_DETECTIONS and all_detections:
                    for det in all_detections:
                        print(f"  Cam:{det['camera_id']}  "
                              f"Track:{det['track_id']}  "
                              f"Global:{det['global_id']}  "
                              f"Theft:{det['is_theft']}  "
                              f"Score:{det['theft_score']:.3f}")

                key = cv2.waitKey(1) & 0xFF
                if key in (ord('q'), 27):
                    print("\n[Pipeline] Quit signal received.")
                    break
                elif key == ord('s'):
                    self._print_stats()
                elif key == ord('d'):
                    Config.LOG_DETECTIONS = not Config.LOG_DETECTIONS
                    print(f"[Pipeline] Detection logging: "
                          f"{'ON' if Config.LOG_DETECTIONS else 'OFF'}")

        except KeyboardInterrupt:
            print("\n[Pipeline] Interrupted by user.")
        finally:
            self.shutdown()

    # ── Detailed stats ─────────────────────────────────────────────────────────

    def _print_stats(self):
        """Print detailed system statistics including per-identity theft state."""
        db_stats = self.db.get_stats()
        runtime  = time.time() - self._start_time

        print("\n" + "=" * 60)
        print("  Theft Sentinel MCMT v2 — System Statistics")
        print("=" * 60)
        print(f"  Runtime:            {runtime:.1f}s")
        print(f"  Pipeline FPS:       {self._fps:.1f}")
        print(f"  Total Global IDs:   {db_stats['total_identities']}")
        print(f"  Active Tracks:      {db_stats['active_tracks']}")
        print(f"  FAISS Index Size:   {self.matcher.get_index_size()}")
        print(f"  Total Alerts:       {self._total_alerts}")
        print(f"  Frames Processed:   {self._frame_counter}")
        print(f"  Match Threshold:    {Config.MATCH_THRESHOLD_DIFF_CAM} (cross) / "
              f"{Config.MATCH_THRESHOLD_SAME_CAM} (same)")
        print(f"  X3D Theft Thresh:   {Config.X3D_THEFT_THRESH}")

        print("\n  Per-identity status:")
        identities = self.db.get_all_identities()
        for gid, record in identities.items():
            info        = record.to_dict()
            theft_state = self.theft_detector.get_state(gid)
            print(f"    GlobalID {gid:3d}:  cams={info['cameras_seen']}  "
                  f"sightings={info['total_sightings']}  "
                  f"embs={info['embedding_count']}  "
                  f"theft={'ALERT' if theft_state.is_theft else 'ok'}  "
                  f"score={theft_state.last_score:.3f}")

        print("\n  X3D Theft summary:")
        for gid, (alert, score, lbl) in self.theft_detector.get_theft_summary().items():
            status = "ALERT" if alert else "ok"
            print(f"    GlobalID {gid:3d}:  {status}  score={score:.3f}  {lbl}")

        print("=" * 60 + "\n")

    # ── Shutdown ───────────────────────────────────────────────────────────────

    def shutdown(self):
        """Clean shutdown of all cameras and display windows."""
        self._running = False
        self.camera_manager.stop_all()
        cv2.destroyAllWindows()

        print("\n" + "=" * 55)
        print("  Session Summary")
        print("=" * 55)
        print(f"  Frames processed : {self._frame_counter}")
        print(f"  Average FPS      : {self._fps:.1f}")
        print(f"  Total alerts     : {self._total_alerts}")
        print("=" * 55)
        print("[Pipeline] Shutdown complete.")


# Backward-compat alias for any callers that import MCMTTheftPipeline
MCMTTheftPipeline = TheftSentinelMCMT


# ── CLI ────────────────────────────────────────────────────────────────────────

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Theft Sentinel MCMT v2 — Multi-Camera Tracking + X3D-S Theft Detection"
    )

    # Camera / input
    parser.add_argument("--sources", nargs="+", default=None,
        help="Video sources (file paths, RTSP/HTTP URLs, or device indices)")
    parser.add_argument("--camera-ids", nargs="+", type=int, default=None,
        help="Camera IDs (must match number of sources)")

    # X3D theft detection
    parser.add_argument("--checkpoint", type=str, default=None,
        help=f"Path to X3D best_model.pth (default: {Config.X3D_CHECKPOINT})")
    parser.add_argument("--threshold", type=float, default=None,
        help=f"X3D theft score threshold (default: {Config.X3D_THEFT_THRESH})")
    parser.add_argument("--consecutive", type=int, default=None,
        help=f"Consecutive inferences to confirm theft (default: {Config.X3D_CONSECUTIVE_REQUIRED})")
    parser.add_argument("--cooldown", type=float, default=None,
        help=f"Cooldown seconds after alert (default: {Config.X3D_COOLDOWN_SECONDS})")

    # Cross-camera matching
    parser.add_argument("--match-threshold", type=float, default=None,
        help=f"Cross-camera ReID threshold (default: {Config.MATCH_THRESHOLD_DIFF_CAM})")
    parser.add_argument("--temporal-window", type=float, default=None,
        help=f"Temporal match window in seconds (default: {Config.MATCH_TEMPORAL_WINDOW})")

    # Detection / tracking
    parser.add_argument("--yolo-model", type=str, default=None,
        help=f"YOLO model path (default: {Config.YOLO_MODEL})")
    parser.add_argument("--yolo-conf", type=float, default=None,
        help=f"YOLO confidence threshold (default: {Config.YOLO_CONFIDENCE})")
    parser.add_argument("--max-age", type=int, default=None,
        help=f"DeepSORT max age (default: {Config.DEEPSORT_MAX_AGE})")

    # Display
    parser.add_argument("--log-detections", action="store_true",
        help="Log every detection to console")
    parser.add_argument("--width", type=int, default=None,
        help=f"Display window width (default: {Config.VIS_WINDOW_WIDTH})")
    parser.add_argument("--height", type=int, default=None,
        help=f"Display window height (default: {Config.VIS_WINDOW_HEIGHT})")

    return parser.parse_args()


def main():
    args = parse_args()

    # Apply CLI overrides to Config
    if args.checkpoint:      Config.X3D_CHECKPOINT          = args.checkpoint
    if args.threshold:       Config.X3D_THEFT_THRESH         = args.threshold
    if args.consecutive:     Config.X3D_CONSECUTIVE_REQUIRED = args.consecutive
    if args.cooldown:        Config.X3D_COOLDOWN_SECONDS      = args.cooldown
    if args.match_threshold: Config.MATCH_THRESHOLD_DIFF_CAM = args.match_threshold
    if args.temporal_window: Config.MATCH_TEMPORAL_WINDOW    = args.temporal_window
    if args.yolo_model:      Config.YOLO_MODEL               = args.yolo_model
    if args.yolo_conf:       Config.YOLO_CONFIDENCE          = args.yolo_conf
    if args.max_age:         Config.DEEPSORT_MAX_AGE         = args.max_age
    if args.log_detections:  Config.LOG_DETECTIONS           = True
    if args.width:           Config.VIS_WINDOW_WIDTH         = args.width
    if args.height:          Config.VIS_WINDOW_HEIGHT        = args.height

    sources    = args.sources
    camera_ids = args.camera_ids

    # Convert numeric strings to device-index integers
    if sources is not None:
        processed = []
        for s in sources:
            try:    processed.append(int(s))
            except: processed.append(s)
        sources = processed

    TheftSentinelMCMT(sources=sources, camera_ids=camera_ids).run()


if __name__ == "__main__":
    main()
