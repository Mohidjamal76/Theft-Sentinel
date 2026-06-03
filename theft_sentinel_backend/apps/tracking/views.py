"""
Tracking Views
"""
from rest_framework import status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import TrackingRecord
from .serializers import TrackingRecordSerializer, TrackingRecordCreateSerializer
from .services import TrackingService


class TrackingIngestView(views.APIView):
    """
    Ingest tracking data from AI detection system.
    Used exclusively by the AI pipeline — not by any UI page.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Receive and process tracking data

        Expected payload:
        {
            "camera_id": 1,
            "vector": {...} or [...],
            "person_id": "optional - will be generated if not provided"
        }
        """
        data = request.data.copy()

        # Generate person_id if not provided
        if 'person_id' not in data or not data['person_id']:
            vector_data = data.get('vector', {})
            data['person_id'] = TrackingService.generate_person_id(vector_data)

        serializer = TrackingRecordCreateSerializer(data=data)

        if serializer.is_valid():
            tracking_record = serializer.save()

            return Response({
                'tracking_record': TrackingRecordSerializer(tracking_record).data,
                'message': 'Tracking data ingested successfully'
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

