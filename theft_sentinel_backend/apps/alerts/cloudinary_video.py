"""
Cloudinary upload/delete for alert video clips.

Credentials: CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
(or configure via Django settings at startup in config.settings).
"""
import logging
import os
from typing import Optional, Tuple

import cloudinary
import cloudinary.uploader

logger = logging.getLogger(__name__)

_config_attempted = False
_config_ok = False


def _ensure_config() -> bool:
    """Ensure Cloudinary SDK is configured (Django settings first, then env)."""
    global _config_attempted, _config_ok
    if _config_attempted:
        return _config_ok
    _config_attempted = True

    cloud_name = api_key = api_secret = None
    try:
        from django.conf import settings as dj_settings

        cloud_name = getattr(dj_settings, "CLOUDINARY_CLOUD_NAME", None) or ""
        api_key = getattr(dj_settings, "CLOUDINARY_API_KEY", None) or ""
        api_secret = getattr(dj_settings, "CLOUDINARY_API_SECRET", None) or ""
    except Exception:
        pass

    if not (cloud_name and api_key and api_secret):
        cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME") or ""
        api_key = os.environ.get("CLOUDINARY_API_KEY") or ""
        api_secret = os.environ.get("CLOUDINARY_API_SECRET") or ""

    if not all([cloud_name, api_key, api_secret]):
        logger.warning("Cloudinary credentials missing; clip upload/delete disabled")
        _config_ok = False
        return False

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )
    _config_ok = True
    return True


def upload_video_to_cloudinary(file_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Upload a local video file to Cloudinary.

    Returns:
        (secure_url, public_id) or (None, None) on skip/failure.
    """
    if not _ensure_config():
        return None, None
    try:
        response = cloudinary.uploader.upload(file_path, resource_type="video")
        return response.get("secure_url"), response.get("public_id")
    except Exception:
        logger.exception("Cloudinary video upload failed")
        return None, None


def upload_video_file(file_path: str) -> Optional[str]:
    """Backward-compatible helper: returns secure_url only."""
    url, _ = upload_video_to_cloudinary(file_path)
    return url


def public_id_from_video_url(url: str) -> Optional[str]:
    """Extract Cloudinary public_id (no extension) from a video secure_url (legacy rows)."""
    if not url:
        return None
    marker = "/video/upload/"
    idx = url.find(marker)
    if idx == -1:
        return None
    path = url[idx + len(marker) :].split("?")[0]
    parts = [p for p in path.split("/") if p]
    if not parts:
        return None
    if parts[0].startswith("v") and len(parts[0]) > 1 and parts[0][1:].isdigit():
        parts = parts[1:]
    if not parts:
        return None
    rest = "/".join(parts)
    lower = rest.lower()
    for ext in (".mp4", ".webm", ".mov", ".mkv"):
        if lower.endswith(ext):
            rest = rest[: -len(ext)]
            break
    return rest or None


def delete_cloudinary_video(public_id: str) -> None:
    if not public_id:
        return
    if not _ensure_config():
        return
    try:
        cloudinary.uploader.destroy(public_id, resource_type="video")
    except Exception:
        logger.exception("Cloudinary destroy failed for public_id=%s", public_id)


def delete_cloudinary_video_from_url(url: str) -> None:
    """Legacy: derive public_id from stored URL when video_public_id is absent."""
    if not url:
        return
    public_id = public_id_from_video_url(url)
    if not public_id:
        logger.warning("Could not derive Cloudinary public_id from URL; skip destroy")
        return
    delete_cloudinary_video(public_id)
