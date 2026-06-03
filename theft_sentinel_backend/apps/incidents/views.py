"""
Incident Views

RBAC Rules (Incidents are part of alert management):
-----------------------------------------------------
- Admin: Full access to incidents (view, create, update, delete, assign)
- Security In-Charge: Can view, create, update, and assign incidents
- Security Guard: Can view incidents assigned to them only
"""
from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model

from .models import Incident
from .serializers import (
    IncidentSerializer,
    IncidentCreateSerializer,
    IncidentStatusUpdateSerializer,
    IncidentAssignSerializer
)
from apps.accounts.permissions import IsAdminOrIncharge

User = get_user_model()


class IncidentListCreateView(generics.ListCreateAPIView):
    """
    List all incidents or create new
    
    Permissions:
    - Admin & Security In-Charge: Can view all incidents and create new
    - Security Guard: Can only view incidents assigned to them
    """
    queryset = Incident.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return IncidentCreateSerializer
        return IncidentSerializer
    
    def get_queryset(self):
        queryset = Incident.objects.select_related('alert_id', 'assigned_to', 'assigned_by').all()

        # Branch scoping (via incident -> alert -> camera)
        user_branch = getattr(self.request.user, "branch", None)
        if getattr(self.request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            queryset = queryset.filter(alert_id__camera_id__branch=user_branch)
        
        # Security Guard: Only view incidents assigned to them
        if self.request.user.role == 'SECURITY_GUARD':
            queryset = queryset.filter(assigned_to=self.request.user)
        
        # Admin & Security In-Charge: Can view all incidents
        # No filtering needed
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by assigned user (Admin & Security In-Charge only)
        assigned_to = self.request.query_params.get('assigned_to', None)
        if assigned_to and self.request.user.role in ['ADMIN', 'SECURITY_INCHARGE']:
            queryset = queryset.filter(assigned_to_id=assigned_to)
        
        # Filter by current user's assignments
        my_incidents = self.request.query_params.get('my_incidents', None)
        if my_incidents == 'true':
            queryset = queryset.filter(assigned_to=self.request.user)
        
        return queryset.order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """
        Only Admin & Security In-Charge can create incidents
        """
        if request.user.role == 'SECURITY_GUARD':
            return Response(
                {'error': 'You do not have permission to create incidents.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)


class IncidentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete incident
    
    Permissions:
    - Admin: Full access (view, update, delete)
    - Security In-Charge: View and update only
    - Security Guard: View only (their assigned incidents)
    """
    queryset = Incident.objects.all()
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Incident.objects.select_related('alert_id', 'assigned_to', 'assigned_by').all()

        # Branch scoping
        user_branch = getattr(self.request.user, "branch", None)
        if getattr(self.request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            queryset = queryset.filter(alert_id__camera_id__branch=user_branch)
        
        # Security Guard: Only view incidents assigned to them
        if self.request.user.role == 'SECURITY_GUARD':
            queryset = queryset.filter(assigned_to=self.request.user)
        
        return queryset
    
    def update(self, request, *args, **kwargs):
        """
        Security Guard cannot update incidents
        """
        if request.user.role == 'SECURITY_GUARD':
            return Response(
                {'error': 'You do not have permission to update incidents.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """
        Security Guard cannot update incidents
        """
        if request.user.role == 'SECURITY_GUARD':
            return Response(
                {'error': 'You do not have permission to update incidents.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().partial_update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """
        Admin and Security In-Charge can delete incidents, but only RESOLVED incidents can be deleted
        """
        if request.user.role not in ['ADMIN', 'SECURITY_INCHARGE']:
            return Response(
                {'error': 'You do not have permission to delete incidents. Only Admin and Security In-Charge can delete incidents.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get the incident instance
        instance = self.get_object()
        
        # Only allow deletion of RESOLVED incidents
        if instance.status != 'RESOLVED':
            return Response(
                {'error': 'Only resolved incidents can be deleted. Please resolve the incident first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().destroy(request, *args, **kwargs)


class IncidentStatusUpdateView(views.APIView):
    """
    Update incident status
    
    Permissions:
    - Admin & Security In-Charge: Can update incident status
    - Security Guard: Can update status of incidents assigned to them
    """
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, pk):
        try:
            incident = Incident.objects.get(pk=pk)
        except Incident.DoesNotExist:
            return Response(
                {'error': 'Incident not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        user_branch = getattr(request.user, "branch", None)
        if getattr(request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            cam_branch = getattr(getattr(getattr(incident, "alert_id", None), "camera_id", None), "branch", None)
            if cam_branch is not None and cam_branch != user_branch:
                return Response({'error': 'Incident not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Security Guard can only update incidents assigned to them
        if request.user.role == 'SECURITY_GUARD':
            if incident.assigned_to != request.user:
                return Response(
                    {'error': 'You can only update incidents assigned to you.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = IncidentStatusUpdateSerializer(data=request.data)
        if serializer.is_valid():
            incident.status = serializer.validated_data['status']
            if 'notes' in serializer.validated_data:
                incident.notes = serializer.validated_data['notes']
            incident.save()
            return Response(IncidentSerializer(incident).data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IncidentAssignView(views.APIView):
    """
    Assign incident to a user
    
    Permissions:
    - Admin & Security In-Charge: Can assign incidents
    - Security Guard: Cannot assign incidents
    """
    permission_classes = [IsAuthenticated, IsAdminOrIncharge]
    
    def patch(self, request, pk):
        try:
            incident = Incident.objects.get(pk=pk)
        except Incident.DoesNotExist:
            return Response(
                {'error': 'Incident not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        user_branch = getattr(request.user, "branch", None)
        if getattr(request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            cam_branch = getattr(getattr(getattr(incident, "alert_id", None), "camera_id", None), "branch", None)
            if cam_branch is not None and cam_branch != user_branch:
                return Response({'error': 'Incident not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = IncidentAssignSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = User.objects.get(pk=serializer.validated_data['assigned_to'])
            except User.DoesNotExist:
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            if user.role != 'SECURITY_GUARD':
                return Response(
                    {'error': 'Incidents can only be assigned to Security Guards.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if user_branch is not None and getattr(user, "branch", None) != user_branch:
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            incident.assigned_to = user
            incident.assigned_by = request.user  # Track who assigned the incident
            incident.status = 'ASSIGNED'
            if 'notes' in serializer.validated_data:
                incident.notes = serializer.validated_data['notes']
            incident.save()
            
            return Response(IncidentSerializer(incident).data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyIncidentsView(generics.ListAPIView):
    """
    Get incidents assigned to current user
    
    Permissions:
    - All authenticated users can view their assigned incidents
    """
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        qs = Incident.objects.select_related('alert_id', 'assigned_to', 'assigned_by').filter(
            assigned_to=self.request.user
        )
        user_branch = getattr(self.request.user, "branch", None)
        if getattr(self.request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            qs = qs.filter(alert_id__camera_id__branch=user_branch)
        return qs.order_by('-created_at')


class UnassignedIncidentsView(generics.ListAPIView):
    """
    Get unassigned incidents
    
    Permissions:
    - Admin & Security In-Charge: Can view unassigned incidents
    - Security Guard: Cannot view unassigned incidents
    """
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrIncharge]
    
    def get_queryset(self):
        qs = Incident.objects.select_related('alert_id', 'assigned_by').filter(
            assigned_to__isnull=True
        )
        user_branch = getattr(self.request.user, "branch", None)
        if getattr(self.request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            qs = qs.filter(alert_id__camera_id__branch=user_branch)
        return qs.order_by('-created_at')
