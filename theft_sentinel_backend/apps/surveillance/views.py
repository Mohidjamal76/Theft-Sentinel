"""
Surveillance Views
"""
from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import SurveillanceEvent
from .serializers import SurveillanceEventSerializer, SurveillanceEventCreateSerializer
from .services import SurveillanceService
from apps.alerts.serializers import AlertSerializer
from apps.incidents.serializers import IncidentSerializer
import logging

logger = logging.getLogger(__name__)


class SurveillanceEventListView(generics.ListAPIView):
    """List all surveillance events"""
    serializer_class = SurveillanceEventSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = SurveillanceEvent.objects.select_related('camera_id').all()

        user_branch = getattr(self.request.user, "branch", None)
        if getattr(self.request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            queryset = queryset.filter(camera_id__branch=user_branch)
        
        # Filter by camera
        camera_id = self.request.query_params.get('camera_id', None)
        if camera_id:
            queryset = queryset.filter(camera_id=camera_id)
        
        # Filter by event_type
        event_type = self.request.query_params.get('event_type', None)
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        
        end_date = self.request.query_params.get('end_date', None)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset.order_by('-created_at')


class SurveillanceEventDetailView(generics.RetrieveAPIView):
    """Retrieve a surveillance event"""
    queryset = SurveillanceEvent.objects.all()
    serializer_class = SurveillanceEventSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        qs = SurveillanceEvent.objects.select_related('camera_id').all()
        user_branch = getattr(self.request.user, "branch", None)
        if getattr(self.request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            qs = qs.filter(camera_id__branch=user_branch)
        return qs


class SurveillanceEventIngestView(views.APIView):
    """
    Ingest AI-detected surveillance events
    This endpoint receives events from AI detection systems
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Receive and process a surveillance event
        
        Expected payload:
        {
            "camera_id": 1,
            "event_type": "theft_detected",
            "frame_url": "http://...",
            "ai_data": {
                "confidence": 0.95,
                "bounding_boxes": [...],
                "detected_objects": [...]
            }
        }
        """
        serializer = SurveillanceEventCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            # Save surveillance event
            surveillance_event = serializer.save()
            
            # Process event (create alerts/incidents if needed)
            try:
                process_result = SurveillanceService.process_event(surveillance_event)
                
                response_data = {
                    'surveillance_event': SurveillanceEventSerializer(surveillance_event).data,
                    'alert_created': process_result['alert_created'],
                    'incident_created': process_result['incident_created']
                }
                
                if process_result['alert_created']:
                    response_data['alert'] = AlertSerializer(process_result['alert']).data
                
                if process_result['incident_created']:
                    response_data['incident'] = IncidentSerializer(process_result['incident']).data
                
                return Response(response_data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"Error processing surveillance event: {str(e)}")
                # Event is saved, but processing failed
                return Response({
                    'surveillance_event': SurveillanceEventSerializer(surveillance_event).data,
                    'alert_created': False,
                    'incident_created': False,
                    'error': 'Event saved but processing failed'
                }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

