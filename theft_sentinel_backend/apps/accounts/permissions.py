"""
Custom permissions for role-based access control

RBAC Model:
-----------
1. ADMIN (Administrator):
   - Full CRUD on users
   - Change any user's password
   - Add/edit/delete cameras
   - View real-time camera feeds
   - View all alerts & alert history
   - Delete alerts
   - View all feedback
   - Delete feedback
   - Generate manual reports
   - View automatic and old reports
   - Delete reports
   - Full system access

2. SECURITY_INCHARGE (Security In-Charge):
   - Can change only their own password
   - View real-time camera feeds
   - Receive alerts
   - View alert history
   - Generate manual reports
   - View reports
   - Cannot delete alerts
   - Cannot edit or delete reports
   - Cannot add/edit/delete cameras
   - Cannot modify users

3. SECURITY_GUARD (Security Guard):
   - Can change only their own password
   - View real-time camera feeds
   - Receive real-time alerts
   - Submit feedback (correct/incorrect detection + notes)
   - Cannot view alert history
   - Cannot delete or edit anything
   - Cannot access user management
"""
from rest_framework import permissions


class IsSuperAdmin(permissions.BasePermission):
    """Permission class for Super Admin users only"""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == "SUPER_ADMIN"


class IsAdmin(permissions.BasePermission):
    """Permission class for Admin users only"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'ADMIN'


class IsSecurityIncharge(permissions.BasePermission):
    """Permission class for Security In-Charge users only"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'SECURITY_INCHARGE'


class IsSecurityGuard(permissions.BasePermission):
    """Permission class for Security Guard users only"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'SECURITY_GUARD'


class IsAdminOrIncharge(permissions.BasePermission):
    """Permission class for Admin or Security In-Charge"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['ADMIN', 'SECURITY_INCHARGE']
        )


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Admin can modify, others can only read
    Used for: Cameras, Personnel
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated and request.user.role == 'ADMIN'


class CanViewCameraFeeds(permissions.BasePermission):
    """
    All authenticated users can view camera feeds
    (Admin, Security In-Charge, Security Guard)
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class CanManageCameras(permissions.BasePermission):
    """
    Only Admin can add/edit/delete cameras
    Others can only view
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated and request.user.role == 'ADMIN'


class CanViewAlerts(permissions.BasePermission):
    """
    Admin and Security In-Charge: View all alerts including history
    Security Guard: View real-time alerts only (no history)
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class CanDeleteAlerts(permissions.BasePermission):
    """
    Only Admin can delete alerts
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'ADMIN'


class CanSubmitFeedback(permissions.BasePermission):
    """
    All authenticated users can submit feedback
    Security Guard: Can only submit feedback
    Admin: Can view all feedback and delete
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class CanViewAllFeedback(permissions.BasePermission):
    """
    Only Admin can view all feedback
    Others can only view their own
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'ADMIN'


class CanDeleteFeedback(permissions.BasePermission):
    """
    Only Admin can delete feedback
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'ADMIN'


class CanGenerateReports(permissions.BasePermission):
    """
    Admin and Security In-Charge can generate manual reports
    Security Guard: Cannot generate reports
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['ADMIN', 'SECURITY_INCHARGE']
        )


class CanViewReports(permissions.BasePermission):
    """
    Admin and Security In-Charge can view all reports
    Security Guard: Cannot view reports
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['ADMIN', 'SECURITY_INCHARGE']
        )


class CanDeleteReports(permissions.BasePermission):
    """
    Only Admin can delete reports
    Security In-Charge: Cannot delete reports
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'ADMIN'


class CanManageUsers(permissions.BasePermission):
    """
    Only Admin can manage users (CRUD operations)
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'ADMIN'


class CanChangeOwnPassword(permissions.BasePermission):
    """
    All authenticated users can change their own password
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class CanChangeAnyPassword(permissions.BasePermission):
    """
    Only Admin can change any user's password
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'ADMIN'
