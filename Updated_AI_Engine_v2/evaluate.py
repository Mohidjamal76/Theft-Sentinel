"""
Evaluation & Metrics Module.

Provides tools to evaluate MCMT-ReID system performance including:
    - IDF1 (ID F1-score): Primary metric for multi-camera tracking
    - MOTA (Multiple Object Tracking Accuracy)
    - ID Switches count
    - Precision / Recall

Also includes utilities for:
    - Threshold tuning via sweep
    - Common failure case analysis
    - Suggestions for accuracy improvement

Usage:
    python evaluate.py --gt ground_truth.txt --pred predictions.txt
    python evaluate.py --sweep --gt ground_truth.txt --pred predictions.txt
"""

import os
import sys
import json
import argparse
import numpy as np
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ═══════════════════════════════════════════════════
# METRICS COMPUTATION
# ═══════════════════════════════════════════════════

def compute_iou(box_a: list, box_b: list) -> float:
    """
    Compute Intersection over Union (IoU) between two boxes.

    Args:
        box_a: [x1, y1, x2, y2]
        box_b: [x1, y1, x2, y2]

    Returns:
        IoU value (0.0 to 1.0).
    """
    x1 = max(box_a[0], box_b[0])
    y1 = max(box_a[1], box_b[1])
    x2 = min(box_a[2], box_b[2])
    y2 = min(box_a[3], box_b[3])

    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    union = area_a + area_b - intersection

    return intersection / union if union > 0 else 0.0


def compute_mot_metrics(
    ground_truth: list[dict],
    predictions: list[dict],
    iou_threshold: float = 0.5,
) -> dict:
    """
    Compute MOT metrics: MOTA, IDF1, ID switches, precision, recall.

    Args:
        ground_truth: List of dicts with keys:
            - 'frame': frame number
            - 'id': ground truth identity
            - 'bbox': [x1, y1, x2, y2]
            - 'camera_id': camera identifier
        predictions: List of dicts with keys:
            - 'frame': frame number
            - 'global_id': predicted global identity
            - 'bbox': [x1, y1, x2, y2]
            - 'camera_id': camera identifier
        iou_threshold: IoU threshold for matching.

    Returns:
        Dict with all computed metrics.
    """
    # Group by frame
    gt_by_frame = defaultdict(list)
    pred_by_frame = defaultdict(list)

    for gt in ground_truth:
        key = (gt["camera_id"], gt["frame"])
        gt_by_frame[key].append(gt)

    for pred in predictions:
        key = (pred["camera_id"], pred["frame"])
        pred_by_frame[key].append(pred)

    all_frames = sorted(set(list(gt_by_frame.keys()) + list(pred_by_frame.keys())))

    # Counters
    total_gt = 0
    total_pred = 0
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    id_switches = 0

    # Track ID mapping: gt_id → last assigned pred_id
    id_mapping = {}

    # For IDF1 calculation
    id_tp = defaultdict(int)   # Per GT-ID true positive count
    id_fn = defaultdict(int)   # Per GT-ID false negative count
    id_fp = defaultdict(int)   # Per Pred-ID false positive count

    for frame_key in all_frames:
        gt_dets = gt_by_frame.get(frame_key, [])
        pred_dets = pred_by_frame.get(frame_key, [])

        total_gt += len(gt_dets)
        total_pred += len(pred_dets)

        # Compute IoU matrix
        n_gt = len(gt_dets)
        n_pred = len(pred_dets)

        if n_gt == 0:
            false_positives += n_pred
            for pd in pred_dets:
                id_fp[pd["global_id"]] += 1
            continue

        if n_pred == 0:
            false_negatives += n_gt
            for gd in gt_dets:
                id_fn[gd["id"]] += 1
            continue

        iou_matrix = np.zeros((n_gt, n_pred))
        for i, gd in enumerate(gt_dets):
            for j, pd in enumerate(pred_dets):
                iou_matrix[i, j] = compute_iou(gd["bbox"], pd["bbox"])

        # Greedy matching (highest IoU first)
        matched_gt = set()
        matched_pred = set()

        while True:
            max_iou = iou_matrix.max()
            if max_iou < iou_threshold:
                break

            max_idx = np.unravel_index(iou_matrix.argmax(), iou_matrix.shape)
            gt_idx, pred_idx = max_idx

            matched_gt.add(gt_idx)
            matched_pred.add(pred_idx)

            gt_id = gt_dets[gt_idx]["id"]
            pred_id = pred_dets[pred_idx]["global_id"]

            true_positives += 1
            id_tp[gt_id] += 1

            # Check for ID switch
            if gt_id in id_mapping:
                if id_mapping[gt_id] != pred_id:
                    id_switches += 1
            id_mapping[gt_id] = pred_id

            # Zero out matched rows/cols
            iou_matrix[gt_idx, :] = 0
            iou_matrix[:, pred_idx] = 0

        # Count unmatched
        for i in range(n_gt):
            if i not in matched_gt:
                false_negatives += 1
                id_fn[gt_dets[i]["id"]] += 1

        for j in range(n_pred):
            if j not in matched_pred:
                false_positives += 1
                id_fp[pred_dets[j]["global_id"]] += 1

    # ─── Compute MOTA ─────────────────────────────
    mota = 1 - (false_negatives + false_positives + id_switches) / max(total_gt, 1)

    # ─── Compute IDF1 ─────────────────────────────
    # IDF1 = 2 * IDTP / (2 * IDTP + IDFP + IDFN)
    total_id_tp = sum(id_tp.values())
    total_id_fp = sum(id_fp.values())
    total_id_fn = sum(id_fn.values())
    idf1 = (2 * total_id_tp) / max(2 * total_id_tp + total_id_fp + total_id_fn, 1)

    # ─── Precision / Recall ────────────────────────
    precision = true_positives / max(true_positives + false_positives, 1)
    recall = true_positives / max(true_positives + false_negatives, 1)

    metrics = {
        "MOTA": round(mota, 4),
        "IDF1": round(idf1, 4),
        "Precision": round(precision, 4),
        "Recall": round(recall, 4),
        "ID_Switches": id_switches,
        "True_Positives": true_positives,
        "False_Positives": false_positives,
        "False_Negatives": false_negatives,
        "Total_GT": total_gt,
        "Total_Predictions": total_pred,
    }

    return metrics


# ═══════════════════════════════════════════════════
# THRESHOLD TUNING
# ═══════════════════════════════════════════════════

def sweep_threshold(
    ground_truth: list[dict],
    predictions_by_threshold: dict[float, list[dict]],
) -> dict:
    """
    Sweep across threshold values and compute metrics for each.

    Args:
        ground_truth: Ground truth detections.
        predictions_by_threshold: Dict mapping threshold → predictions list.

    Returns:
        Dict mapping threshold → metrics dict.
    """
    results = {}
    for threshold, preds in sorted(predictions_by_threshold.items()):
        metrics = compute_mot_metrics(ground_truth, preds)
        metrics["threshold"] = threshold
        results[threshold] = metrics
        print(f"  Threshold {threshold:.2f}: MOTA={metrics['MOTA']:.4f}, "
              f"IDF1={metrics['IDF1']:.4f}, IDSw={metrics['ID_Switches']}")

    # Find best threshold
    best_idf1 = max(results.items(), key=lambda x: x[1]["IDF1"])
    best_mota = max(results.items(), key=lambda x: x[1]["MOTA"])

    print(f"\n  Best IDF1: threshold={best_idf1[0]:.2f} → IDF1={best_idf1[1]['IDF1']:.4f}")
    print(f"  Best MOTA: threshold={best_mota[0]:.2f} → MOTA={best_mota[1]['MOTA']:.4f}")

    return results


# ═══════════════════════════════════════════════════
# FAILURE ANALYSIS & SUGGESTIONS
# ═══════════════════════════════════════════════════

def print_failure_analysis():
    """Print common failure cases and fixes for MCMT-ReID systems."""

    analysis = """
╔══════════════════════════════════════════════════════════════════╗
║                  COMMON FAILURE CASES & FIXES                   ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║ 1. ID SWITCHES (Frequent)                                       ║
║    Cause: Poor ReID embeddings, similar-looking people.          ║
║    Fix:   ▸ Increase MATCH_THRESHOLD (0.80+)                    ║
║           ▸ Use larger ReID model (osnet_x1_0 or osnet_ain)     ║
║           ▸ Increase MAX_EMBEDDINGS_PER_IDENTITY buffer         ║
║                                                                  ║
║ 2. IDENTITY FRAGMENTATION (Too Many Global IDs)                 ║
║    Cause: Threshold too high, embeddings differ across cameras.  ║
║    Fix:   ▸ Lower MATCH_THRESHOLD (0.65–0.70)                   ║
║           ▸ Add data augmentation (horizontal flip) to ReID      ║
║           ▸ Use average embedding matching instead of best       ║
║                                                                  ║
║ 3. WRONG CROSS-CAMERA MATCHES                                   ║
║    Cause: People wearing similar clothes, low resolution.        ║
║    Fix:   ▸ Enable temporal constraints (MATCH_TEMPORAL_WINDOW)  ║
║           ▸ Add camera transition priors                         ║
║           ▸ Use spatio-temporal constraints                      ║
║                                                                  ║
║ 4. LOST TRACKS DURING OCCLUSION                                 ║
║    Cause: DeepSORT loses track, person reappears as 'new'.      ║
║    Fix:   ▸ Increase DEEPSORT_MAX_AGE (100+)                    ║
║           ▸ Lower DEEPSORT_N_INIT (2)                            ║
║           ▸ The ReID global matching will re-associate anyway    ║
║                                                                  ║
║ 5. LOW FPS / PERFORMANCE                                        ║
║    Cause: Large model, no GPU, too many cameras.                 ║
║    Fix:   ▸ Use yolov8n (nano) instead of larger variants        ║
║           ▸ Reduce YOLO_IMG_SIZE (416 or 320)                    ║
║           ▸ Increase EMBEDDING_UPDATE_INTERVAL (10+)             ║
║           ▸ Process cameras on separate GPU streams               ║
║                                                                  ║
║ 6. LIGHTING VARIATION ACROSS CAMERAS                             ║
║    Cause: Indoor/outdoor, day/night transitions.                 ║
║    Fix:   ▸ Fine-tune ReID model on target domain                ║
║           ▸ Apply histogram equalization as preprocessing        ║
║           ▸ Use domain-adapted models (e.g., OSNet-AIN)          ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║                   ACCURACY IMPROVEMENT TIPS                      ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║ ▸ Fine-tune OSNet on your specific camera setup                  ║
║ ▸ Use camera transition matrix (which cameras can see each       ║
║   other's exits/entrances)                                       ║
║ ▸ Implement zone-based matching (e.g., only match people near    ║
║   door regions)                                                  ║
║ ▸ Use temporal smoothing (weighted average of recent embeddings) ║
║ ▸ Add pose estimation as auxiliary feature                       ║
║ ▸ Use re-ranking (k-reciprocal encoding) for better matching     ║
║ ▸ Ensemble multiple ReID models                                  ║
║ ▸ Track head/shoulder crop in addition to full body              ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""
    print(analysis)


# ═══════════════════════════════════════════════════
# FILE I/O
# ═══════════════════════════════════════════════════

def load_detections_from_file(filepath: str) -> list[dict]:
    """
    Load detections from a JSON lines file.

    Expected format (one JSON object per line):
        {"frame": 1, "camera_id": 1, "id": 3, "bbox": [x1, y1, x2, y2]}

    Args:
        filepath: Path to the detections file.

    Returns:
        List of detection dicts.
    """
    detections = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                detections.append(json.loads(line))
    return detections


def save_detections_to_file(detections: list[dict], filepath: str):
    """Save detections to a JSON lines file."""
    with open(filepath, "w") as f:
        for det in detections:
            # Convert numpy types to Python types
            clean_det = {}
            for k, v in det.items():
                if isinstance(v, np.integer):
                    clean_det[k] = int(v)
                elif isinstance(v, np.floating):
                    clean_det[k] = float(v)
                elif isinstance(v, np.ndarray):
                    clean_det[k] = v.tolist()
                else:
                    clean_det[k] = v
            f.write(json.dumps(clean_det) + "\n")


# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="MCMT-ReID Evaluation")
    parser.add_argument("--gt", type=str, help="Ground truth file (JSON lines)")
    parser.add_argument("--pred", type=str, help="Predictions file (JSON lines)")
    parser.add_argument("--sweep", action="store_true", help="Run threshold sweep")
    parser.add_argument("--analysis", action="store_true", help="Print failure analysis")

    args = parser.parse_args()

    if args.analysis:
        print_failure_analysis()
        return

    if args.gt and args.pred:
        print("Loading ground truth and predictions...")
        gt = load_detections_from_file(args.gt)
        pred = load_detections_from_file(args.pred)

        print(f"Ground truth: {len(gt)} entries")
        print(f"Predictions:  {len(pred)} entries")

        metrics = compute_mot_metrics(gt, pred)

        print("\n" + "=" * 50)
        print(" Evaluation Results")
        print("=" * 50)
        for key, value in metrics.items():
            print(f"  {key:20s}: {value}")
        print("=" * 50)
    else:
        print("No input files provided. Printing failure analysis...\n")
        print_failure_analysis()


if __name__ == "__main__":
    main()
