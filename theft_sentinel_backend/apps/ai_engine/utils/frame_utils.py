"""
Frame Utilities
Handle frame decoding, encoding, and preprocessing
"""
import cv2
import base64
import numpy as np
from typing import Optional, Tuple
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def decode_base64_frame(base64_string: str) -> Optional[np.ndarray]:
    """
    Decode base64 string to OpenCV frame
    """
    try:
        # Remove data URL prefix if present
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        # Decode base64
        img_data = base64.b64decode(base64_string)
        
        # Convert to numpy array
        nparr = np.frombuffer(img_data, np.uint8)
        
        # Decode image
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            logger.error("Failed to decode frame from base64")
            return None
        
        return frame
        
    except Exception as e:
        logger.error(f"Error decoding base64 frame: {str(e)}")
        return None


def encode_frame_to_base64(frame: np.ndarray, format: str = '.jpg', quality: int = 90) -> Optional[str]:
    """
    Encode OpenCV frame to base64 string
    """
    try:
        if format == '.jpg':
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        else:
            encode_param = []
        
        _, buffer = cv2.imencode(format, frame, encode_param)
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        
        return jpg_as_text
        
    except Exception as e:
        logger.error(f"Error encoding frame to base64: {str(e)}")
        return None


def capture_frame_from_rtsp(stream_url: str, timeout: int = 5) -> Optional[np.ndarray]:
    """
    Capture a single frame from any camera stream URL.

    Protocol is detected from the URL scheme:
      rtsp/rtsps  → cv2.VideoCapture(url, CAP_FFMPEG)
      http/https  → cv2.VideoCapture(url)   (no FFmpeg RTSP options)

    The URL is used AS-IS — never mutated or extended.
    isOpened() is ALWAYS checked before getBackendName().
    """
    cap = None
    try:
        scheme = urlparse(stream_url).scheme.lower()
        logger.info(
            "[frame_utils] Capturing from %s (scheme=%s)",
            stream_url[:60], scheme,
        )

        if scheme in ("rtsp", "rtsps"):
            cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
        elif scheme in ("http", "https"):
            cap = cv2.VideoCapture(stream_url)
        else:
            logger.error(
                "[frame_utils] Unsupported protocol '%s' for URL: %s",
                scheme, stream_url,
            )
            return None

        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout * 1000)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout * 1000)

        # ── CRITICAL: isOpened() BEFORE getBackendName() ──────────────────
        # getBackendName() asserts api != 0 internally — calling it on a
        # failed VideoCapture causes cv2.error (-215:Assertion failed).
        if not cap.isOpened():
            logger.error(
                "[frame_utils] Failed to open %s stream: %s",
                scheme.upper(), stream_url,
            )
            return None

        # Safe to call getBackendName() only after isOpened() returned True
        backend = cap.getBackendName()
        if scheme in ("rtsp", "rtsps") and backend != "FFMPEG":
            logger.warning(
                "[frame_utils] Non-FFmpeg backend '%s' for RTSP stream: %s",
                backend, stream_url,
            )
        else:
            logger.debug(
                "[frame_utils] Opened %s stream with backend=%s",
                scheme.upper(), backend,
            )

        ret, frame = cap.read()

        if not ret or frame is None:
            logger.error(
                "[frame_utils] No frame received from %s: %s",
                scheme.upper(), stream_url,
            )
            return None

        logger.info("[frame_utils] Captured frame %s from %s", frame.shape, stream_url[:40])
        return frame

    except Exception as exc:
        logger.error(
            "[frame_utils] Exception capturing from %s: %s",
            stream_url, exc, exc_info=True,
        )
        return None

    finally:
        if cap is not None:
            cap.release()


def resize_frame(frame: np.ndarray, max_width: int = 1280, max_height: int = 720) -> np.ndarray:
    """
    Resize frame while maintaining aspect ratio
    """
    h, w = frame.shape[:2]
    
    if w <= max_width and h <= max_height:
        return frame
    
    # Calculate scaling factor
    scale = min(max_width / w, max_height / h)
    
    new_w = int(w * scale)
    new_h = int(h * scale)
    
    resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    return resized


def validate_frame(frame: np.ndarray) -> Tuple[bool, Optional[str]]:
    """
    Validate frame is suitable for processing
    """
    if frame is None:
        return False, "Frame is None"
    
    if not isinstance(frame, np.ndarray):
        return False, "Frame is not a numpy array"
    
    if len(frame.shape) != 3:
        return False, "Frame must be a 3D array (H, W, C)"
    
    h, w, c = frame.shape
    
    if c != 3:
        return False, "Frame must have 3 channels (BGR)"
    
    if h < 100 or w < 100:
        return False, "Frame is too small (min 100x100)"
    
    if h > 4096 or w > 4096:
        return False, "Frame is too large (max 4096x4096)"
    
    return True, None


def draw_detections_on_frame(
    frame: np.ndarray,
    detections: list,
    tracks: list,
    poses: list
) -> np.ndarray:
    """
    Draw detection results on frame for visualization
    """
    vis_frame = frame.copy()
    
    # Draw tracks with bboxes
    for track in tracks:
        bbox = track['bbox']
        x1, y1, x2, y2 = map(int, bbox)
        
        # Color based on ML score
        ml_score = track.get('ml_score', 0.0)
        if ml_score > 0.7:
            color = (0, 0, 255)  # Red for suspicious
        elif ml_score > 0.4:
            color = (0, 165, 255)  # Orange for medium
        else:
            color = (0, 255, 0)  # Green for normal
        
        # Draw bbox
        cv2.rectangle(vis_frame, (x1, y1), (x2, y2), color, 2)
        
        # Draw label
        label = f"Track {track['track_id']} - {track['class']}"
        if ml_score > 0.3:
            label += f" [{int(ml_score*100)}%]"
        
        cv2.putText(vis_frame, label, (x1, max(15, y1 - 8)),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    # Draw pose keypoints
    skeleton_pairs = [
        (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
        (11, 12), (5, 11), (6, 12), (11, 13), (13, 15),
        (12, 14), (14, 16), (0, 5), (0, 6),
    ]
    
    for pose in poses:
        kps = np.array(pose['keypoints'])
        
        # Draw skeleton
        for (i, j) in skeleton_pairs:
            if i < len(kps) and j < len(kps):
                xi, yi, ci = kps[i]
                xj, yj, cj = kps[j]
                if ci > 0.3 and cj > 0.3:
                    cv2.line(vis_frame,
                            (int(xi), int(yi)),
                            (int(xj), int(yj)),
                            (0, 255, 255), 2)
        
        # Draw wrists
        if len(kps) > 10:
            rwx, rwy, rc = kps[10]
            lwx, lwy, lc = kps[9]
            if rc > 0.3:
                cv2.circle(vis_frame, (int(rwx), int(rwy)), 5, (0, 0, 255), -1)
            if lc > 0.3:
                cv2.circle(vis_frame, (int(lwx), int(lwy)), 5, (0, 255, 0), -1)
    
    return vis_frame

