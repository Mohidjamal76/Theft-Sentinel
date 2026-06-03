"""Encode in-memory frames to a temporary H.264-friendly MP4 via OpenCV.

On first call, _probe_working_fourcc() tests every candidate codec by
actually opening a VideoWriter on a throwaway temp file.  The winning codec
is cached for the process lifetime so subsequent clip saves pay no overhead.

Windows DLL note
----------------
OpenCV ships openh264-1.8.0-win64.dll alongside the cv2 .pyd.  If a
different version is on PATH the codec raises:
  "Incorrect library version loaded" / "Failed to initialize VideoWriter"
The probe detects this automatically and falls back to mp4v, while logging
a clear path to the missing DLL so the developer can fix it.
"""
import logging
import os
import platform
import tempfile
from typing import Any, Sequence

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Maximum width for uploaded clips (keeps Cloudinary storage small)
_MAX_WIDTH = 1280

# Codecs tried in preference order.  avc1/H264/X264 all need openh264;
# mp4v is the universal fallback (slightly larger files, still plays in browser).
_CODECS_TO_TRY = ("avc1", "H264", "X264", "mp4v")

# Module-level cache — None until first probe
_cached_fourcc: "int | None" = None


# ── Windows DLL pre-flight ────────────────────────────────────────────────────

def _check_openh264_dll() -> None:
    """
    Warn early on Windows when the expected openh264 DLL is missing or
    mismatched so the developer gets a clear fix path in the log.
    """
    if platform.system() != "Windows":
        return

    expected_dll = "openh264-1.8.0-win64.dll"

    # Search cv2 package dir first (where pip places it), then CWD, then PATH
    search_dirs = [
        os.path.dirname(cv2.__file__),
        os.getcwd(),
    ] + os.environ.get("PATH", "").split(os.pathsep)

    for d in search_dirs:
        if d and os.path.isfile(os.path.join(d, expected_dll)):
            logger.info("✅ OpenH264 DLL found: %s", os.path.join(d, expected_dll))
            return

    logger.warning(
        "⚠️  %s NOT found in cv2 package dir or system PATH.  "
        "H.264 clip encoding will fall back to MPEG-4 (mp4v).  "
        "Fix: copy %s into %s",
        expected_dll,
        expected_dll,
        os.path.dirname(cv2.__file__),
    )


# ── Codec probe ───────────────────────────────────────────────────────────────

def _probe_working_fourcc() -> int:
    """
    Return the first fourcc whose VideoWriter can actually open *and write*
    to a real file.  Result is cached so the probe runs only once per process.

    This replaces the old _best_fourcc() which only checked fourcc != -1 and
    never exercised the actual encoder — causing silent failures when the
    openh264 DLL version was wrong.
    """
    global _cached_fourcc
    if _cached_fourcc is not None:
        return _cached_fourcc

    _check_openh264_dll()

    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp.close()

    try:
        for name in _CODECS_TO_TRY:
            cc = cv2.VideoWriter_fourcc(*name)
            if cc == -1:
                logger.debug("Codec '%s': fourcc returned -1 — skipping", name)
                continue

            writer = cv2.VideoWriter(tmp.name, cc, 25.0, (16, 16))
            if not writer.isOpened():
                logger.debug("Codec '%s': VideoWriter would not open — skipping", name)
                writer.release()
                continue

            try:
                writer.write(np.zeros((16, 16, 3), dtype=np.uint8))
            except Exception as exc:  # noqa: BLE001
                logger.debug("Codec '%s': write() raised %s — skipping", name, exc)
                writer.release()
                continue

            writer.release()
            logger.info(
                "🎬 VideoWriter codec probe: '%s' works — using for all clips", name
            )
            _cached_fourcc = cc
            return cc

    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    # No codec passed the probe — log clearly and use mp4v as last resort.
    logger.error(
        "❌ All VideoWriter codec probes failed (including mp4v).  "
        "Clip saving may not work.  "
        "On Windows: ensure openh264-1.8.0-win64.dll is next to cv2.__file__ (%s).  "
        "Falling back to mp4v fourcc anyway.",
        cv2.__file__,
    )
    _cached_fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    return _cached_fourcc


# ── Public API ────────────────────────────────────────────────────────────────

def write_frames_to_mp4(frames: Sequence[Any], out_path: str, fps: float) -> bool:
    """
    Encode *frames* (BGR numpy arrays) to an MP4 at *out_path*.

    Returns True on success, False on any failure (VideoWriter refused to open,
    bad frames, etc.).  Errors are logged but never raised so the caller's
    monitoring loop is not interrupted.
    """
    if not frames:
        return False

    fps = max(8.0, min(float(fps), 60.0))
    h, w = frames[0].shape[:2]

    # Downscale wide frames to keep file size manageable
    if w > _MAX_WIDTH:
        scale = _MAX_WIDTH / w
        w     = _MAX_WIDTH
        h     = int(h * scale)

    fourcc = _probe_working_fourcc()

    try:
        writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))
    except cv2.error as exc:
        logger.error("VideoWriter constructor raised cv2.error: %s", exc)
        return False

    if not writer.isOpened():
        logger.error(
            "VideoWriter failed to open '%s' (fourcc=0x%08X, fps=%.1f, size=%dx%d).  "
            "If you see 'Incorrect library version' above, the openh264 DLL is "
            "mismatched — place openh264-1.8.0-win64.dll next to %s.",
            out_path, fourcc, fps, w, h, cv2.__file__,
        )
        # Invalidate the cache so the next call re-probes with fallback
        global _cached_fourcc
        _cached_fourcc = None
        return False

    try:
        for frame in frames:
            f = frame
            if f.shape[0] != h or f.shape[1] != w:
                f = cv2.resize(f, (w, h))
            if f.ndim == 2:
                f = cv2.cvtColor(f, cv2.COLOR_GRAY2BGR)
            elif f.shape[2] == 4:
                f = cv2.cvtColor(f, cv2.COLOR_BGRA2BGR)
            writer.write(f)
    except cv2.error as exc:
        logger.error("VideoWriter.write() raised cv2.error: %s", exc)
        return False
    finally:
        writer.release()

    return True
