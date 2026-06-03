"""
Feedback Views

RBAC Rules:
-----------
- Admin: View all feedback, Delete feedback
- Security In-Charge: Cannot view all feedback, Cannot delete feedback
- Security Guard: Submit feedback (correct/incorrect detection + notes), View own feedback only
"""
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Feedback
from .serializers import FeedbackSerializer, FeedbackCreateSerializer
from apps.accounts.permissions import IsAdmin, CanSubmitFeedback, CanDeleteFeedback


class FeedbackListCreateView(generics.ListCreateAPIView):
    """
    List all feedback or create new
    
    Permissions:
    - Admin: Can view all feedback
    - Security In-Charge & Security Guard: Can only view their own feedback
    - All: Can submit feedback
    """
    queryset = Feedback.objects.all()
    permission_classes = [IsAuthenticated, CanSubmitFeedback]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return FeedbackCreateSerializer
        return FeedbackSerializer
    
    def get_queryset(self):
        queryset = Feedback.objects.select_related('user_id').all()

        user_branch = getattr(self.request.user, "branch", None)
        scoped = getattr(self.request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None
        
        # Admin: Can view all feedback
        if self.request.user.role == 'ADMIN':
            if scoped:
                queryset = queryset.filter(user_id__branch=user_branch)
        else:
            # Security In-Charge & Security Guard: Only view their own feedback
            queryset = queryset.filter(user_id=self.request.user)
        
        # Filter by type
        feedback_type = self.request.query_params.get('type', None)
        if feedback_type:
            queryset = queryset.filter(type=feedback_type)
        
        # Filter by user (admin only)
        user_id = self.request.query_params.get('user_id', None)
        if user_id and self.request.user.role == 'ADMIN':
            queryset = queryset.filter(user_id=user_id)
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(user_id=self.request.user)


class FeedbackDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete feedback
    
    Permissions:
    - Admin: Can view all feedback and delete
    - Security In-Charge & Security Guard: Can only view/update their own feedback
    - Only Admin can delete feedback
    """
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated, CanSubmitFeedback]
    
    def get_queryset(self):
        queryset = Feedback.objects.select_related('user_id').all()

        user_branch = getattr(self.request.user, "branch", None)
        scoped = getattr(self.request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None
        
        # Admin: Can view all feedback
        if self.request.user.role == 'ADMIN':
            if scoped:
                queryset = queryset.filter(user_id__branch=user_branch)
        else:
            # Security In-Charge & Security Guard: Only access their own feedback
            queryset = queryset.filter(user_id=self.request.user)
        
        return queryset
    
    def destroy(self, request, *args, **kwargs):
        """
        Only Admin can delete feedback
        """
        if request.user.role != 'ADMIN':
            return Response(
                {'error': 'You do not have permission to delete feedback. Only Admin can delete feedback.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


class MyFeedbackView(generics.ListAPIView):
    """
    Get current user's feedback
    
    Permissions:
    - All authenticated users can view their own feedback
    """
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Feedback.objects.filter(
            user_id=self.request.user
        ).order_by('-created_at')


class FeedbackStatsView(generics.GenericAPIView):
    """
    Get feedback statistics
    
    Permissions:
    - Only Admin can view feedback statistics
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        """Get feedback statistics"""
        from django.db.models import Count
        
        total_feedback = Feedback.objects.count()
        
        # By type
        feedback_by_type = Feedback.objects.values('type').annotate(count=Count('id'))
        
        # Recent feedback (last 30 days)
        from django.utils import timezone
        from datetime import timedelta
        
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_feedback = Feedback.objects.filter(created_at__gte=thirty_days_ago).count()
        
        # False positive vs True positive
        false_positive_count = Feedback.objects.filter(type='FALSE_POSITIVE').count()
        true_positive_count = Feedback.objects.filter(type='TRUE_POSITIVE').count()
        
        data = {
            'total_feedback': total_feedback,
            'by_type': list(feedback_by_type),
            'recent_30_days': recent_feedback,
            'false_positive': false_positive_count,
            'true_positive': true_positive_count,
            'accuracy_feedback_ratio': round(
                (true_positive_count / (true_positive_count + false_positive_count) * 100)
                if (true_positive_count + false_positive_count) > 0 else 0,
                2
            )
        }
        
        return Response(data, status=status.HTTP_200_OK)


class FeedbackDeleteView(generics.DestroyAPIView):
    """
    Delete feedback
    
    Permissions:
    - Only Admin can delete feedback
    """
    queryset = Feedback.objects.all()
    permission_classes = [IsAuthenticated, CanDeleteFeedback]
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {'message': 'Feedback deleted successfully'},
            status=status.HTTP_200_OK
        )
