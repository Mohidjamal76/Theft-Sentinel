"""
MJPEGCapture — Pure-Python MJPEG-over-HTTP reader
===================================================
Shared by CameraStreamManager and any other component needing MJPEG frames
without going through OpenCV/FFmpeg backends.

DroidCam note:
  DroidCam's HTTP server returns text/html to generic HTTP clients and
  multipart/x-mixed-replace ONLY to requests carrying 'User-Agent: DroidCam/1.0'.
  This header is included in all requests.  IP Webcam ignores the UA header
  and always serves multipart, so the header is safe for both apps.
"""

import logging
import numpy as np
import cv2

logger = logging.getLogger(__name__)


class MJPEGCapture:
    """
    Drop-in cv2.VideoCapture replacement for MJPEG-over-HTTP streams.

    Reads a multipart/x-mixed-replace MJPEG stream from a URL using
    requests streaming — completely bypasses all OpenCV video backends
    and the OPENCV_FFMPEG_CAPTURE_OPTIONS env-var that breaks FFmpeg
    for HTTP connections on this system.

    Exposes the minimal interface used by CameraStream and ContinuousMonitor:
        isOpened()       -> bool
        read()           -> (bool, np.ndarray | None)
        release()
        set()            -> (no-op, accepted for compat)
        getBackendName() -> str
    """

    _CONNECT_TIMEOUT = 5.0       # seconds to establish TCP connection
    _READ_TIMEOUT    = 10.0      # seconds between received bytes
    _CHUNK_SIZE      = 4096      # bytes per requests.iter_content chunk
    _MAX_FRAME_BYTES = 4 * 1024 * 1024  # 4 MB safety cap per JPEG

    # Sent with every request.
    # DroidCam serves text/html without this UA; multipart/x-mixed-replace with it.
    _REQUEST_HEADERS = {
        "Connection": "keep-alive",
        "User-Agent": "DroidCam/1.0",
    }

    def __init__(self, url: str):
        self._url      = url
        self._response = None
        self._iter     = None
        self._buf      = b""
        self._opened   = False
        self._open()

    def _open(self) -> None:
        """Establish the streaming HTTP connection with content-type validation."""
        try:
            import requests
            self._response = requests.get(
                self._url,
                stream=True,
                timeout=(self._CONNECT_TIMEOUT, self._READ_TIMEOUT),
                headers=self._REQUEST_HEADERS,
            )
            content_type = self._response.headers.get("Content-Type", "")
            if self._response.status_code == 200:
                if any(t in content_type for t in ("multipart", "image", "video")):
                    self._iter   = self._response.iter_content(chunk_size=self._CHUNK_SIZE)
                    self._opened = True
                    logger.info(
                        "[MJPEGCapture] Connected to %s  content-type=%s",
                        self._url, content_type,
                    )
                else:
                    logger.error(
                        "[MJPEGCapture] Unexpected content-type '%s' for %s "
                        "— non-media response (HTML web page?). "
                        "Check camera URL and User-Agent handling.",
                        content_type, self._url,
                    )
                    self._response.close()
            else:
                logger.error(
                    "[MJPEGCapture] HTTP %d for %s",
                    self._response.status_code, self._url,
                )
                self._response.close()
        except Exception as exc:
            logger.error("[MJPEGCapture] Connection failed for %s: %s", self._url, exc)

    def isOpened(self) -> bool:       # noqa: N802
        return self._opened

    def getBackendName(self) -> str:  # noqa: N802
        return "MJPEG-requests"

    def set(self, *args, **kwargs):   # accepted for compat — no-op
        return True

    def read(self):
        """
        Read the next JPEG frame from the MJPEG stream.

        Scans the raw byte stream for JPEG SOI (\\xff\\xd8) and EOI (\\xff\\xd9)
        markers and decodes the enclosed JPEG.

        Returns:
            (True, frame_bgr)  on success
            (False, None)      on end-of-stream or error
        """
        if not self._opened or self._iter is None:
            return False, None

        try:
            while True:
                try:
                    chunk = next(self._iter)
                    self._buf += chunk
                except StopIteration:
                    self._opened = False
                    return False, None

                if len(self._buf) > self._MAX_FRAME_BYTES:
                    logger.warning(
                        "[MJPEGCapture] Buffer exceeded %d B — discarding",
                        self._MAX_FRAME_BYTES,
                    )
                    self._buf = b""
                    continue

                start = self._buf.find(b"\xff\xd8")
                if start == -1:
                    self._buf = b""
                    continue

                end = self._buf.find(b"\xff\xd9", start + 2)
                if end == -1:
                    continue

                jpeg_bytes = self._buf[start : end + 2]
                self._buf   = self._buf[end + 2:]

                jpg_array = np.frombuffer(jpeg_bytes, dtype=np.uint8)
                frame     = cv2.imdecode(jpg_array, cv2.IMREAD_COLOR)
                if frame is not None:
                    return True, frame

        except Exception as exc:
            logger.warning("[MJPEGCapture] read() error: %s", exc)
            self._opened = False
            return False, None

    def release(self) -> None:
        self._opened = False
        self._iter   = None
        self._buf    = b""
        if self._response is not None:
            try:
                self._response.close()
            except Exception:
                pass
            self._response = None
        logger.debug("[MJPEGCapture] Released %s", self._url)
