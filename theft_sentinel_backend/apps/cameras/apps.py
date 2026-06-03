from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class CamerasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.cameras'

    def ready(self):
        """
        Register a clean shutdown handler for the CameraStreamManager so all
        persistent RTSP VideoCapture objects are released when Django stops.
        This prevents zombie RTSP sessions lingering in MediaMTX.
        """
        import atexit
        from .stream_manager import stream_manager

        def _shutdown():
            logger.info("[CamerasConfig] Server shutting down — stopping all camera streams …")
            stream_manager.stop_all()
            logger.info("[CamerasConfig] All camera streams stopped.")

        atexit.register(_shutdown)
        logger.info("[CamerasConfig] CameraStreamManager shutdown handler registered")

