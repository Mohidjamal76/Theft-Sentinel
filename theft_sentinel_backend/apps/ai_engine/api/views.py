"""
AI Engine API Views
Provides endpoints for AI processing without modifying existing code
"""
from rest_framework import status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission


class IsAdminOrSecurityIncharge(BasePermission):
    """
    Allow ADMIN and SECURITY_INCHARGE roles to control AI monitoring.
    SECURITY_GUARD may view monitoring status but cannot start or stop it.
    Returns a clear 403 with a human-readable message on rejection.
    """
    message = (
        'You do not have permission to control AI monitoring. '
        'Required role: ADMIN or SECURITY_INCHARGE.'
    )
    ALLOWED_ROLES = {'ADMIN', 'SECURITY_INCHARGE'}

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return getattr(request.user, 'role', None) in self.ALLOWED_ROLES
from django.http import StreamingHttpResponse
from django.utils import timezone
import json
import logging
import queue
import time

from apps.ai_engine.services.ai_service import ai_service
from apps.ai_engine.services.inference_runner import InferenceRunner
from apps.ai_engine.utils.frame_utils import (
    decode_base64_frame,
    capture_frame_from_rtsp,
    validate_frame,
)
from apps.ai_engine.models import AIInference, DetectionTrack
from apps.cameras.models import Camera

# Import existing alert/incident logic (DO NOT MODIFY THEM)
from apps.alerts.models import Alert
from apps.alerts.serializers import AlertCreateSerializer
from apps.alerts.services import dispatch_theft_alert_notifications
from apps.incidents.models import Incident

from .serializers import (
    FrameAnalysisRequestSerializer,
    CameraProcessRequestSerializer,
    AnalysisResponseSerializer,
    ModelInfoSerializer,
    AIInferenceSerializer,
)

logger = logging.getLogger(__name__)


class AnalyzeFrameView(views.APIView):
    """
    POST /api/ai/analyze-frame/
    
    Analyze a single frame for theft detection
    Accepts base64 encoded image
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Validate request
        serializer = FrameAnalysisRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid request', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        
        # Check AI service ready
        if not ai_service.is_ready():
            return Response(
                {'error': 'AI service not initialized. Models may still be loading.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        # Decode frame
        frame = decode_base64_frame(data['frame'])
        if frame is None:
            return Response(
                {'error': 'Failed to decode frame from base64'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate frame
        is_valid, error_msg = validate_frame(frame)
        if not is_valid:
            return Response(
                {'error': f'Invalid frame: {error_msg}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get camera if provided
        camera = None
        camera_id = data.get('camera_id')
        if camera_id:
            try:
                camera = Camera.objects.get(pk=camera_id)
            except Camera.DoesNotExist:
                return Response(
                    {'error': f'Camera not found: {camera_id}'},
                    status=status.HTTP_404_NOT_FOUND
                )
            user_branch = getattr(request.user, "branch", None)
            if getattr(request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
                cam_branch = getattr(camera, "branch", None)
                if cam_branch is not None and cam_branch != user_branch:
                    return Response(
                        {'error': f'Camera not found: {camera_id}'},
                        status=status.HTTP_404_NOT_FOUND
                    )
        
        # Run inference
        try:
            runner = InferenceRunner()
            result = runner.process_frame(frame, camera_id=camera_id)
            
            # Handle theft detection
            alert_created = False
            alert_id = None
            inference_id = None
            
            if result['classification'] == 'theft' and data.get('create_alert_on_theft', True):
                if camera:
                    # Call existing alert creation logic (DO NOT MODIFY IT)
                    alert = self._create_alert_for_theft(camera, result, request.user)
                    if alert:
                        alert_created = True
                        alert_id = str(alert.id)
                        logger.info(f"🚨 Theft alert created: {alert_id}")
            
            # Save to database if requested
            if data.get('save_to_db', True):
                inference = self._save_inference(camera, result, alert_id)
                if inference:
                    inference_id = str(inference.id)
            
            # Build response with flattened metadata for frontend
            response_data = {
                # AI Results
                'classification': result['classification'],
                'confidence': result['confidence'],
                
                # Counts (flattened from frame_metadata)
                'persons': result['frame_metadata'].get('num_persons', 0),
                'objects': result['frame_metadata'].get('num_detections', 0),
                'tracks': result['frame_metadata'].get('num_tracks', 0),
                
                # Performance
                'processing_time_ms': result.get('processing_time_ms', 0),
                
                # Camera Info (if available)
                'camera_name': camera.name if camera else None,
                'camera_location': camera.location if camera else None,
                'camera_id': str(camera.id) if camera else camera_id,
                
                # Alert Status
                'alert_created': alert_created,
                'alert_id': alert_id,
                'inference_id': inference_id,
                
                # Detailed Data (optional)
                'detections': result.get('detections', []),
                'poses': result.get('poses', []),
                'tracks_data': result.get('tracks', []),
                'suspicious_tracks': result.get('suspicious_tracks', []),
                'frame_metadata': result.get('frame_metadata', {}),
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error processing frame: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Error processing frame: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _create_alert_for_theft(self, camera, result, user):
        """
        Create alert using EXISTING alert creation logic
        DO NOT MODIFY - only call existing code
        """
        try:
            # Prepare metadata
            metadata = {
                'confidence': result['confidence'],
                'suspicious_tracks': result.get('suspicious_tracks', []),
                'num_detections': result['frame_metadata'].get('num_detections', 0),
                'num_persons': result['frame_metadata'].get('num_persons', 0),
                'detected_by': 'AI_ENGINE',
                'detection_timestamp': timezone.now().isoformat(),
            }
            
            # Use existing AlertCreateSerializer (DO NOT MODIFY)
            alert_data = {
                'camera_id': camera.id,
                'alert_type': 'THEFT_DETECTED',
                'severity': 'HIGH' if result['confidence'] > 0.7 else 'MEDIUM',
                'metadata': metadata,
            }
            
            alert_serializer = AlertCreateSerializer(data=alert_data)
            if alert_serializer.is_valid():
                alert = alert_serializer.save()
                try:
                    dispatch_theft_alert_notifications(alert, async_send=True)
                except Exception:
                    logger.exception("Failed to dispatch alert notifications for alert %s", alert.id)
                
                # Optionally create incident (using existing logic)
                # Incident.objects.create(alert_id=alert, status='CREATED')
                
                return alert
            else:
                logger.error(f"Failed to create alert: {alert_serializer.errors}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating alert: {str(e)}", exc_info=True)
            return None
    
    def _save_inference(self, camera, result, alert_id=None):
        """Save inference result to database"""
        try:
            alert = None
            if alert_id:
                try:
                    alert = Alert.objects.get(pk=alert_id)
                except Alert.DoesNotExist:
                    pass
            
            inference = AIInference.objects.create(
                camera_id=camera,
                detections=result['detections'],
                poses=result['poses'],
                tracks=result['tracks'],
                classification=result['classification'],
                confidence=result['confidence'],
                frame_metadata=result['frame_metadata'],
                processing_time_ms=result['processing_time_ms'],
                alert=alert,
            )
            
            return inference
            
        except Exception as e:
            logger.error(f"Error saving inference: {str(e)}", exc_info=True)
            return None


class ProcessCameraView(views.APIView):
    """
    POST /api/ai/process-camera/
    
    Capture frame from camera RTSP stream and analyze it
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Validate request
        serializer = CameraProcessRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid request', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        
        # Check AI service ready
        if not ai_service.is_ready():
            return Response(
                {'error': 'AI service not initialized'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        # Get camera
        camera_id = data['camera_id']
        try:
            camera = Camera.objects.get(pk=camera_id)
        except Camera.DoesNotExist:
            return Response(
                {'error': f'Camera not found: {camera_id}'},
                status=status.HTTP_404_NOT_FOUND
            )

        user_branch = getattr(request.user, "branch", None)
        if getattr(request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            cam_branch = getattr(camera, "branch", None)
            if cam_branch is not None and cam_branch != user_branch:
                return Response(
                    {'error': f'Camera not found: {camera_id}'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Capture frame from RTSP
        logger.info(f"Capturing frame from camera {camera.name} (ID: {camera_id})")
        frame = capture_frame_from_rtsp(camera.rtsp_url)
        if frame is None:
            logger.error(f"Failed to capture frame from camera {camera.name}")
            return Response(
                {
                    'error': 'Failed to capture frame from camera',
                    'details': {
                        'camera_name': camera.name,
                        'camera_id': str(camera_id),
                        'possible_causes': [
                            'Camera is offline or unreachable',
                            'RTSP URL is invalid or incorrect',
                            'Network connectivity issue',
                            'Camera credentials are wrong',
                            'Camera is not streaming',
                        ],
                        'rtsp_url_preview': camera.rtsp_url[:30] + '...' if len(camera.rtsp_url) > 30 else camera.rtsp_url
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Validate frame
        is_valid, error_msg = validate_frame(frame)
        if not is_valid:
            return Response(
                {'error': f'Invalid frame: {error_msg}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Run inference
        try:
            runner = InferenceRunner()
            result = runner.process_frame(frame, camera_id=str(camera.id))
            
            # Handle theft detection
            alert_created = False
            alert_id = None
            inference_id = None
            
            if result['classification'] == 'theft' and data.get('create_alert_on_theft', True):
                alert = self._create_alert_for_theft(camera, result, request.user)
                if alert:
                    alert_created = True
                    alert_id = str(alert.id)
                    logger.info(f"🚨 Theft alert created for camera {camera.name}: {alert_id}")
            
            # Save to database if requested
            if data.get('save_to_db', True):
                inference = self._save_inference(camera, result, alert_id)
                if inference:
                    inference_id = str(inference.id)
            
            # Build response with flattened metadata for frontend
            response_data = {
                # AI Results
                'classification': result['classification'],
                'confidence': result['confidence'],
                
                # Counts (flattened from frame_metadata)
                'persons': result['frame_metadata'].get('num_persons', 0),
                'objects': result['frame_metadata'].get('num_detections', 0),
                'tracks': result['frame_metadata'].get('num_tracks', 0),
                
                # Performance
                'processing_time_ms': result.get('processing_time_ms', 0),
                
                # Camera Info
                'camera_name': camera.name,
                'camera_location': camera.location,
                'camera_id': str(camera.id),
                
                # Alert Status
                'alert_created': alert_created,
                'alert_id': alert_id,
                'inference_id': inference_id,
                
                # Detailed Data (optional)
                'detections': result.get('detections', []),
                'poses': result.get('poses', []),
                'tracks_data': result.get('tracks', []),
                'suspicious_tracks': result.get('suspicious_tracks', []),
                'frame_metadata': result.get('frame_metadata', {}),
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error processing camera: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Error processing camera: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _create_alert_for_theft(self, camera, result, user):
        """Same as AnalyzeFrameView"""
        try:
            metadata = {
                'confidence': result['confidence'],
                'suspicious_tracks': result.get('suspicious_tracks', []),
                'num_detections': result['frame_metadata'].get('num_detections', 0),
                'num_persons': result['frame_metadata'].get('num_persons', 0),
                'detected_by': 'AI_ENGINE',
                'detection_timestamp': timezone.now().isoformat(),
            }
            
            alert_data = {
                'camera_id': camera.id,
                'alert_type': 'THEFT_DETECTED',
                'severity': 'HIGH' if result['confidence'] > 0.7 else 'MEDIUM',
                'metadata': metadata,
            }
            
            alert_serializer = AlertCreateSerializer(data=alert_data)
            if alert_serializer.is_valid():
                alert = alert_serializer.save()
                try:
                    dispatch_theft_alert_notifications(alert, async_send=True)
                except Exception:
                    logger.exception("Failed to dispatch alert notifications for alert %s", alert.id)
                return alert
            else:
                logger.error(f"Failed to create alert: {alert_serializer.errors}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating alert: {str(e)}", exc_info=True)
            return None
    
    def _save_inference(self, camera, result, alert_id=None):
        """Same as AnalyzeFrameView"""
        try:
            alert = None
            if alert_id:
                try:
                    alert = Alert.objects.get(pk=alert_id)
                except Alert.DoesNotExist:
                    pass
            
            inference = AIInference.objects.create(
                camera_id=camera,
                detections=result['detections'],
                poses=result['poses'],
                tracks=result['tracks'],
                classification=result['classification'],
                confidence=result['confidence'],
                frame_metadata=result['frame_metadata'],
                processing_time_ms=result['processing_time_ms'],
                alert=alert,
            )
            
            return inference
            
        except Exception as e:
            logger.error(f"Error saving inference: {str(e)}", exc_info=True)
            return None


class FullPipelineView(views.APIView):
    """
    POST /api/ai/full-pipeline/
    
    Run full pipeline analysis (convenience endpoint that combines both options)
    Can accept either frame data or camera_id
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Check if frame or camera_id provided
        has_frame = 'frame' in request.data
        has_camera_id = 'camera_id' in request.data
        
        if not has_frame and not has_camera_id:
            return Response(
                {'error': 'Either "frame" or "camera_id" must be provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Route to appropriate view
        if has_frame:
            view = AnalyzeFrameView()
            view.request = request
            view.format_kwarg = None
            return view.post(request)
        else:
            view = ProcessCameraView()
            view.request = request
            view.format_kwarg = None
            return view.post(request)


class ModelInfoView(views.APIView):
    """
    GET /api/ai/model-info/
    
    Get information about loaded AI models
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        model_info = ai_service.get_model_info()
        serializer = ModelInfoSerializer(data=model_info)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(model_info, status=status.HTTP_200_OK)

class HealthCheckView(views.APIView):
    """
    GET /api/ai/health/
    
    Check AI service health
    """
    permission_classes = []  # Public endpoint
    
    def get(self, request):
        return Response({
            'status': 'healthy' if ai_service.is_ready() else 'initializing',
            'models_loaded': ai_service.is_ready(),
            'device': ai_service.device,
        }, status=status.HTTP_200_OK)


class StartContinuousMonitorView(views.APIView):
    """
    POST /api/ai/monitor/start/

    Start continuous monitoring on a camera (processes live feed at full FPS).
    Requires ADMIN or SECURITY_INCHARGE role; returns 403 otherwise.
    """
    permission_classes = [IsAuthenticated, IsAdminOrSecurityIncharge]
    
    def post(self, request):
        from ..services.continuous_monitor import monitor_manager
        
        camera_id = request.data.get('camera_id')
        restart = request.data.get('restart', False)  # Allow restart option
        
        if not camera_id:
            return Response(
                {'error': 'camera_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get camera
        try:
            camera = Camera.objects.get(pk=camera_id)
        except Camera.DoesNotExist:
            return Response(
                {'error': f'Camera not found: {camera_id}'},
                status=status.HTTP_404_NOT_FOUND
            )

        user_branch = getattr(request.user, "branch", None)
        if getattr(request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            cam_branch = getattr(camera, "branch", None)
            if cam_branch is not None and cam_branch != user_branch:
                return Response(
                    {'error': f'Camera not found: {camera_id}'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Check if AI is ready
        if not ai_service.is_ready():
            return Response(
                {'error': 'AI service not ready. Models still loading.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        try:
            from apps.cameras.services import test_camera_feed

            if not test_camera_feed(camera):
                return Response(
                    {'error': 'Camera feed is not available. Cannot turn on this camera.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as exc:
            logger.exception("Feed validation failed for camera %s", camera.id)
            return Response(
                {'error': f'Camera feed validation failed: {str(exc)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
        # Check if already running
        existing_stats = monitor_manager.get_monitor_stats(str(camera.id))
        if existing_stats and existing_stats['is_running']:
            if restart:
                # Stop and restart
                logger.info(f"Restarting monitor for camera {camera.id}")
                monitor_manager.stop_monitor(str(camera.id))
                time.sleep(1)  # Give it time to clean up
            else:
                # Already running, return success with current stats
                return Response({
                    'success': True,
                    'message': 'Monitor already running',
                    'already_running': True,
                    'camera_id': str(camera.id),
                    'camera_name': camera.name,
                    'stats': existing_stats,
                }, status=status.HTTP_200_OK)
        elif existing_stats:
            monitor_manager.stop_monitor(str(camera.id))
        
        # Start monitoring
        success = monitor_manager.start_monitor(str(camera.id), camera.rtsp_url)

        if success:
            # ── Persist to MongoDB so the toggle survives server restarts ──
            camera.ai_monitoring_enabled = True
            camera.save(update_fields=['ai_monitoring_enabled'])

            return Response({
                'success': True,
                'message': 'Started continuous monitoring',
                'already_running': False,
                'camera_id': str(camera.id),
                'camera_name': camera.name,
                'ai_monitoring_enabled': True,
                'rtsp_url_preview': camera.rtsp_url[:50] + '...' if len(camera.rtsp_url) > 50 else camera.rtsp_url,
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': 'Failed to start monitoring',
                'camera_id': str(camera.id),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StopContinuousMonitorView(views.APIView):
    """
    POST /api/ai/monitor/stop/

    Stop continuous monitoring on a camera.
    Requires ADMIN or SECURITY_INCHARGE role; returns 403 otherwise.
    Always returns 200 — "monitor not found" means it is already stopped,
    which is the desired outcome, so it is treated as a success.
    """
    permission_classes = [IsAuthenticated, IsAdminOrSecurityIncharge]
    
    def post(self, request):
        from ..services.continuous_monitor import monitor_manager
        
        camera_id = request.data.get('camera_id')
        if not camera_id:
            return Response(
                {'error': 'camera_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        success = monitor_manager.stop_monitor(camera_id)

        # ── Persist the OFF state to MongoDB regardless of whether a monitor
        # was actually running (handles double-stop gracefully) ─────────────
        try:
            cam = Camera.objects.get(pk=camera_id)
            user_branch = getattr(request.user, "branch", None)
            if getattr(request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
                cam_branch = getattr(cam, "branch", None)
                if cam_branch is not None and cam_branch != user_branch:
                    cam = None
                    raise Camera.DoesNotExist()
            cam.ai_monitoring_enabled = False
            cam.save(update_fields=['ai_monitoring_enabled'])
        except Camera.DoesNotExist:
            pass

        # Both success=True (process killed) and success=False (process was already
        # gone) result in HTTP 200.  From the frontend's perspective the desired
        # outcome — monitoring is stopped — is achieved either way.  Returning 404
        # would cause axios to throw, leaving the toggle stuck in the ON position.
        return Response({
            'success': True,
            'message': 'Stopped monitoring' if success else 'Monitoring was not running (already stopped)',
            'was_running': success,
            'camera_id': camera_id,
            'ai_monitoring_enabled': False,
        }, status=status.HTTP_200_OK)


class MonitorStatusView(views.APIView):
    """
    GET /api/ai/monitor/status/
    
    Get status of all continuous monitors or a specific one
    
    Query params:
    - camera_id (optional): Get status for specific camera
    
    Response:
    {
        "monitors": {
            "abc123": {
                "camera_id": "abc123",
                "is_running": true,
                "frames_processed": 1523,
                "fps": 28.5,
                "elapsed_seconds": 53.4,
                "error_count": 0,
                "last_result": {...}
            }
        },
        "total_monitors": 1
    }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from ..services.continuous_monitor import monitor_manager
        
        camera_id = request.query_params.get('camera_id')
        
        if camera_id:
            # Always return HTTP 200 so the frontend can read ai_monitoring_enabled
            # even when no in-process monitor is running (e.g. after a server restart).
            stats = monitor_manager.get_monitor_stats(camera_id)

            # Read the persisted DB flag — this is the source of truth across restarts
            ai_monitoring_enabled = False
            try:
                cam = Camera.objects.get(pk=camera_id)
                user_branch = getattr(request.user, "branch", None)
                if getattr(request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
                    cam_branch = getattr(cam, "branch", None)
                    if cam_branch is not None and cam_branch != user_branch:
                        raise Camera.DoesNotExist()
                ai_monitoring_enabled = bool(cam.ai_monitoring_enabled)
            except Camera.DoesNotExist:
                return Response(
                    {'error': f'Camera {camera_id} not found'},
                    status=status.HTTP_404_NOT_FOUND,
                )

            return Response({
                'camera_id':             camera_id,
                'monitor':               stats,          # None if no process running
                'ai_monitoring_enabled': ai_monitoring_enabled,
            }, status=status.HTTP_200_OK)
        else:
            # Get all monitors
            all_stats = monitor_manager.get_all_stats()
            return Response({
                'monitors': all_stats,
                'total_monitors': len(all_stats)
            }, status=status.HTTP_200_OK)


def realtime_tracking_sse_view(request, pk):
    """
    GET /api/ai/cameras/<pk>/realtime-tracking/

    Plain Django view (NOT a DRF APIView) so that DRF content negotiation is
    never involved.  Using APIView caused a 406 Not Acceptable because DRF
    found no renderer for the browser's "Accept: text/event-stream" header.

    Server-Sent Events stream that pushes lightweight JSON tracking payloads
    to the frontend in real time.  The frontend overlays bounding boxes on
    the raw MJPEG stream using an HTML5 <canvas> element — no server-side
    drawing required.

    Each SSE event payload:
      {
        "camera_id":       "...",
        "timestamp":       "2026-04-22T10:00:00.123Z",
        "frame_width":     1280,
        "frame_height":    720,
        "tracks":          [{"track_id":1,"global_id":5,"bbox":[x1,y1,x2,y2],
                             "x3d_score":0.85,"confidence":0.92}],
        "suspicious_ids":  [1],
        "alert_triggered": true,
        "classification":  "theft",
        "confidence":      0.85
      }

    Authentication: open (no token required) — same policy as CameraFeedView.
    The stream sends ": keepalive" comments every 25 s to keep proxies happy.
    """
    from django.http import JsonResponse as _JsonResponse

    camera_id = str(pk)

    # Verify the camera exists before opening a long-lived connection
    try:
        Camera.objects.get(pk=pk)
    except Camera.DoesNotExist:
        return _JsonResponse({'error': f'Camera {pk} not found'}, status=404)

    from ..services.sse_registry import sse_registry

    _QUEUE_TIMEOUT_S = 25.0

    def event_stream():
        q = sse_registry.subscribe(camera_id)
        logger.info("SSE stream opened  camera=%s  remote=%s",
                    camera_id, request.META.get('REMOTE_ADDR'))
        try:
            # Initial handshake — lets the client know the connection is live
            yield f"data: {json.dumps({'type': 'connected', 'camera_id': camera_id})}\n\n"

            while True:
                try:
                    # Block until a tracking result arrives or timeout
                    line = q.get(timeout=_QUEUE_TIMEOUT_S)
                    if line is None:
                        break
                    yield line          # already formatted as "data: {...}\n\n"
                except queue.Empty:
                    # SSE comment — keeps the TCP connection alive through
                    # proxies / load balancers that time out idle streams
                    yield ": keepalive\n\n"
        except GeneratorExit:
            pass
        finally:
            sse_registry.unsubscribe(camera_id, q)
            logger.info("SSE stream closed  camera=%s  remote=%s",
                        camera_id, request.META.get('REMOTE_ADDR'))

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream; charset=utf-8',
    )
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    # Prevent nginx / gunicorn / proxies from buffering the stream
    response['X-Accel-Buffering'] = 'no'
    return response


class StopTrackingView(views.APIView):
    """
    POST /api/ai/suspects/<global_id>/stop-tracking/

    Clear the given global_id from the active_thief_global_ids registry,
    stopping network-wide alerts and bounding boxes.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, global_id):
        try:
            global_id_int = int(global_id)
        except ValueError:
            return Response(
                {'error': 'Invalid global_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        from apps.ai_engine.services.ai_service import ai_service
        
        if ai_service.is_active_thief(global_id_int):
            ai_service.remove_active_thief(global_id_int)
            return Response({
                'success': True,
                'message': f'Stopped tracking suspect {global_id_int}'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': True,
                'message': f'Suspect {global_id_int} was not actively tracked'
            }, status=status.HTTP_200_OK)
