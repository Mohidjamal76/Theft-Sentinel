"""
AI Engine App Configuration
"""
import os

# ═══════════════════════════════════════════════════════════════════════════
# OpenCV FFmpeg RTSP low-latency + UDP transport — GLOBAL STARTUP CONFIG
# ═══════════════════════════════════════════════════════════════════════════
# WHY HERE:
#   This module is imported by Django's app registry at startup (before any
#   request handler, background thread, or management command runs). Setting
#   the env-var here guarantees it exists in BOTH the autoreload parent process
#   and the child process (RUN_MAIN=true) before the first cv2.VideoCapture()
#   call is made anywhere in the codebase.
#
#   Previous location (continuous_monitor.py) was lazily imported only on the
#   first /api/ai/monitor/start/ call — too late for the health checker and
#   MJPEG feed endpoint which run at Django startup time.
#
# OPTIONS:
#   rtsp_transport;udp   → force UDP RTP media transport (no TCP interleaving)
#   fflags;nobuffer      → disable FFmpeg demuxer read buffer
#   flags;low_delay      → low-delay decode mode (skip B-frame reorder)
#   max_delay;0          → remove 0.5s FFmpeg jitter buffer
#   buffer_size;102400   → shrink socket recv buffer to 100 KB
#   analyzeduration;0    → skip stream analysis delay at open
#   probesize;32         → minimal probe to speed up stream open
#   loglevel;48          → AV_LOG_DEBUG — shows transport negotiation in stderr
# os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
#     "rtsp_transport;udp|"
#     "buffer_size;524288|"
#     "max_delay;200000|"
#     "reorder_queue_size;32|"
#     "stimeout;5000000"
# )

# os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = ( 
#     "rtsp_transport;tcp|" 
#     "buffer_size;1024000|" 
#     "max_delay;500000|"
#     "reorder_queue_size;32|" 
#     "stimeout;5000000" 
# )
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
    "rtsp_transport;tcp|"
    "buffer_size;1024000|"
    "max_delay;500000|"
    "reorder_queue_size;32|"
    "stimeout;5000000"
)
    # "stimeout;5000000|"
    # "fflags;nobuffer|"
    # "flags;low_delay"

# Enables OpenCV's own backend-selection debug log (prints to stderr)
os.environ["OPENCV_VIDEOIO_DEBUG"] = "1"

# PyTorch CUDA allocator — keeps existing behaviour
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
# ═══════════════════════════════════════════════════════════════════════════

from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

# Log immediately so ops can confirm the env-var was set in THIS process
import sys as _sys
logger.warning(
    f"[DJANGO PROCESS] PID={os.getpid()} | "
    f"argv={_sys.argv} | "
    f"OPENCV_FFMPEG_CAPTURE_OPTIONS="
    f"{os.environ.get('OPENCV_FFMPEG_CAPTURE_OPTIONS', 'NOT SET')}"
)


class AiEngineConfig(AppConfig):
    default_auto_field = 'django_mongodb_backend.fields.ObjectIdAutoField'
    name = 'apps.ai_engine'
    verbose_name = 'AI Engine'

    def ready(self):
        """
        Initialize AI service when Django starts.
        """
        import sys
        logger.warning(
            f"[DJANGO PROCESS ready()] PID={os.getpid()} | "
            f"OPENCV_FFMPEG_CAPTURE_OPTIONS="
            f"{os.environ.get('OPENCV_FFMPEG_CAPTURE_OPTIONS', 'NOT SET')}"
        )
        # Only initialize AI models in the HTTP-serving process
        if 'runserver' in sys.argv or 'gunicorn' in sys.argv[0]:
            try:
                logger.info("🚀 Initializing AI Engine...")
                from apps.ai_engine.services import ai_service
                ai_service.initialize()
                logger.info("✅ AI Engine initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize AI Engine: {str(e)}")
                # Don't crash the server, just log the error
                logger.warning("⚠️ Server will run without AI capabilities")

