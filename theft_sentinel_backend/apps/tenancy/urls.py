from django.urls import path

from .views import (
    SuperAdminExistsView,
    CreateSuperAdminView,
    BranchRegistrationView,
    SuperAdminBranchListView,
    SuperAdminBranchActionView,
    SuperAdminBranchDeleteView,
    SuperAdminProfileView,
    BranchAdminProfileView,
    SuperAdminForgotPasswordView,
    BranchAdminResetRequestCreateView,
    SuperAdminResetRequestListView,
    SuperAdminResetRequestActionView,
)


urlpatterns = [
    # Landing helpers
    path("super-admin/exists/", SuperAdminExistsView.as_view(), name="super_admin_exists"),
    path("super-admin/create/", CreateSuperAdminView.as_view(), name="super_admin_create"),

    # Public branch registration
    path("branches/register/", BranchRegistrationView.as_view(), name="branch_register"),

    # Super Admin dashboard (branch management)
    path("super-admin/branches/", SuperAdminBranchListView.as_view(), name="super_admin_branches"),
    path(
        "super-admin/branches/<str:branch_id>/status/",
        SuperAdminBranchActionView.as_view(),
        name="super_admin_branch_status",
    ),
    path(
        "super-admin/branches/<str:branch_id>/",
        SuperAdminBranchDeleteView.as_view(),
        name="super_admin_branch_delete",
    ),

    # Super Admin profile
    path("super-admin/profile/", SuperAdminProfileView.as_view(), name="super_admin_profile"),
    path("branch-admin/profile/", BranchAdminProfileView.as_view(), name="branch_admin_profile"),

    # Password reset flows
    path(
        "super-admin/forgot-password/",
        SuperAdminForgotPasswordView.as_view(),
        name="super_admin_forgot_password",
    ),
    path(
        "branch-admin/reset-request/",
        BranchAdminResetRequestCreateView.as_view(),
        name="branch_admin_reset_request",
    ),
    path(
        "super-admin/reset-requests/",
        SuperAdminResetRequestListView.as_view(),
        name="super_admin_reset_requests",
    ),
    path(
        "super-admin/reset-requests/<str:request_id>/action/",
        SuperAdminResetRequestActionView.as_view(),
        name="super_admin_reset_request_action",
    ),
]

