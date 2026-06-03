"""
Camera Views
"""
from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import StreamingHttpResponse, JsonResponse
import logging

from .stream_manager import stream_manager

logger = logging.getLogger(__name__)

from .models import Camera
from .serializers import CameraSerializer, CameraCreateSerializer, CameraStatusUpdateSerializer
from .services import cleanup_camera_runtime, test_camera_feed
from apps.accounts.permissions import CanManageCameras, CanViewCameraFeeds


class CameraListCreateView(generics.ListCreateAPIView):
    """
    List all cameras or create new
    All authenticated users can view cameras
    Only Admin can add/edit/delete cameras
    """
    queryset = Camera.objects.all()
    permission_classes = [IsAuthenticated, CanManageCameras]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CameraCreateSerializer
        return CameraSerializer
    
    def get_queryset(self):
        queryset = Camera.objects.all()

        # Branch scoping (single DB, tenant isolation)
        user_branch = getattr(self.request.user, "branch", None)
        if getattr(self.request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            queryset = queryset.filter(branch=user_branch)
        
        # Filter by zone
        zone = self.request.query_params.get('zone', None)
        if zone:
            queryset = queryset.filter(zone=zone)
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        # Cameras are created inactive. Activation is manual via the status
        # endpoint, which validates the feed and starts AI monitoring.
        # Ensure camera is linked to creator's branch (Super Admin may omit)
        user_branch = getattr(self.request.user, "branch", None)
        if getattr(self.request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            serializer.save(branch=user_branch, status="OFFLINE")
            return
        serializer.save(status="OFFLINE")


class CameraDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete camera
    All authenticated users can view camera details
    Only Admin can update/delete cameras
    """
    queryset = Camera.objects.all()
    serializer_class = CameraSerializer
    permission_classes = [IsAuthenticated, CanManageCameras]

    def get_queryset(self):
        qs = Camera.objects.all()
        user_branch = getattr(self.request.user, "branch", None)
        if getattr(self.request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            qs = qs.filter(branch=user_branch)
        return qs

    def perform_destroy(self, instance):
        cleanup_camera_runtime(instance)
        instance.delete()


class CameraStatusUpdateView(views.APIView):
    """
    Update camera status
    Only Admin can update camera status
    """
    permission_classes = [IsAuthenticated, CanManageCameras]
    
    def patch(self, request, pk):
        try:
            queryset = Camera.objects.all()
            user_branch = getattr(request.user, "branch", None)
            if getattr(request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
                queryset = queryset.filter(branch=user_branch)
            camera = queryset.get(pk=pk)
        except Camera.DoesNotExist:
            return Response(
                {'error': 'Camera not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CameraStatusUpdateSerializer(data=request.data)
        if serializer.is_valid():
            requested_status = serializer.validated_data['status']

            if requested_status == 'ONLINE':
                if not test_camera_feed(camera):
                    return Response(
                        {'error': 'Camera feed is not available. Cannot turn on this camera.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                camera.status = 'ONLINE'
                camera.save(update_fields=['status'])
                data = CameraSerializer(camera).data
                data['message'] = 'Camera turned on successfully.'
                return Response(data, status=status.HTTP_200_OK)

            camera.status = 'OFFLINE'
            camera.save(update_fields=['status'])
            data = CameraSerializer(camera).data
            data['message'] = 'Camera turned off successfully.'
            return Response(data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CamerasByZoneView(generics.ListAPIView):
    """
    Get all cameras in a specific zone
    All authenticated users can view cameras
    """
    serializer_class = CameraSerializer
    permission_classes = [IsAuthenticated, CanViewCameraFeeds]
    
    def get_queryset(self):
        zone = self.kwargs.get('zone')
        return Camera.objects.filter(zone=zone).order_by('name')


class CameraStreamURLView(views.APIView):
    """
    Get direct camera stream URL
    All authenticated users can view camera feeds
    (Admin, Security In-Charge, Security Guard)
    """
    permission_classes = [IsAuthenticated, CanViewCameraFeeds]
    
    def get(self, request, pk):
        try:
            camera = Camera.objects.get(pk=pk)
        except Camera.DoesNotExist:
            return JsonResponse(
                {'error': 'Camera not found'},
                status=404
            )
        
        # Use the raw URL exactly as stored in the database.
        # The correct endpoint (e.g. /video for IP Webcam, /mjpegfeed for DroidCam)
        # must be included in the camera's rtsp_url field — never auto-appended here.
        stream_url = camera.rtsp_url

        return JsonResponse({
            'camera_id': str(camera.id),
            'camera_name': camera.name,
            'stream_url': stream_url,
            'status': camera.status,
            'location': camera.location,
            'zone': camera.zone,
            'stream_type': 'http' if stream_url.startswith('http') else 'rtsp'
        })


class CameraFeedView(views.APIView):
    """
    Stream MJPEG camera feed using a SINGLE persistent RTSP connection.

    Architecture:
        RTSP Camera
            ↓
        CameraStreamManager (one VideoCapture per camera, daemon reader thread)
            ↓
        Shared latest-frame cache  (thread-safe)
            ↓
        Multiple MJPEG clients  ← this view

    No new cv2.VideoCapture is ever opened per HTTP request.  All clients
    for the same camera read from the same shared frame buffer.
    """
    permission_classes = []  # Allow unauthenticated for <img> tags; add JWT check if needed

    def get(self, request, pk):
        try:
            camera = Camera.objects.get(pk=pk)
        except Camera.DoesNotExist:
            return JsonResponse({'error': 'Camera not found'}, status=404)

        # Camera must be marked ONLINE before we attempt streaming
        if camera.status != 'ONLINE':
            logger.warning(
                "[CameraFeedView] Camera %s is %s — rejecting stream request",
                camera.name, camera.status,
            )
            return JsonResponse(
                {'error': 'Camera is offline', 'status': camera.status},
                status=503,
            )

        camera_id = str(camera.id)
        rtsp_url   = camera.rtsp_url

        logger.info(
            "[CameraFeedView] Client connected for camera %s (id=%s) url=%s",
            camera.name, camera_id, rtsp_url,
        )

        # All protocols (HTTP DroidCam/IP Webcam and RTSP) go through the shared
        # CameraStreamManager.  stream_manager owns the ONE connection to the
        # camera source; this view reads from its frame cache.
        # Opening a direct connection here would steal DroidCam's single-client
        # slot and prevent stream_manager (and the AI monitor) from connecting.
        return StreamingHttpResponse(
            stream_manager.mjpeg_frame_generator(camera_id, rtsp_url),
            content_type='multipart/x-mixed-replace; boundary=frame',
        )


