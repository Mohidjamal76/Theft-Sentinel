"""
Personnel Views
"""
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Personnel
from .serializers import PersonnelSerializer, PersonnelCreateSerializer
from apps.accounts.permissions import IsAdmin, CanManageUsers


class PersonnelListCreateView(generics.ListCreateAPIView):
    """
    List all personnel or create new
    
    Permissions:
    - All authenticated users can view personnel
    - Only Admin can create personnel (part of user management)
    """
    queryset = Personnel.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PersonnelCreateSerializer
        return PersonnelSerializer
    
    def get_queryset(self):
        queryset = Personnel.objects.select_related('user').all()

        user_branch = getattr(self.request.user, "branch", None)
        if getattr(self.request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            queryset = queryset.filter(user__branch=user_branch)
        
        # Filter by zone if provided
        zone = self.request.query_params.get('zone', None)
        if zone:
            queryset = queryset.filter(assigned_zones__contains=zone)
        
        return queryset.order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """
        Only Admin can create personnel
        """
        if request.user.role != 'ADMIN':
            return Response(
                {'error': 'You do not have permission to create personnel. Only Admin can manage users.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)


class PersonnelDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete personnel
    
    Permissions:
    - All authenticated users can view personnel details
    - Only Admin can update/delete personnel (part of user management)
    """
    queryset = Personnel.objects.all()
    serializer_class = PersonnelSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        qs = Personnel.objects.select_related('user').all()
        user_branch = getattr(self.request.user, "branch", None)
        if getattr(self.request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            qs = qs.filter(user__branch=user_branch)
        return qs
    
    def update(self, request, *args, **kwargs):
        """
        Only Admin can update personnel
        """
        if request.user.role != 'ADMIN':
            return Response(
                {'error': 'You do not have permission to update personnel. Only Admin can manage users.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """
        Only Admin can update personnel
        """
        if request.user.role != 'ADMIN':
            return Response(
                {'error': 'You do not have permission to update personnel. Only Admin can manage users.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().partial_update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """
        Only Admin can delete personnel
        """
        if request.user.role != 'ADMIN':
            return Response(
                {'error': 'You do not have permission to delete personnel. Only Admin can manage users.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


class MyPersonnelProfileView(generics.RetrieveAPIView):
    """Get current user's personnel profile"""
    serializer_class = PersonnelSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        try:
            return Personnel.objects.select_related('user').get(user=self.request.user)
        except Personnel.DoesNotExist:
            return Response(
                {'error': 'Personnel profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

