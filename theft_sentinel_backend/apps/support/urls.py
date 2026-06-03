from django.urls import path

from .views import (
    MyQueriesView,
    BranchAdminPendingQueriesView,
    BranchAdminAnsweredQueriesView,
    BranchAdminQueryActionView,
    SuperAdminQueriesView,
    SuperAdminQueryAnswerView,
    DeleteAnsweredMyQueryView,
)


urlpatterns = [
    # Tenant side
    path("me/", MyQueriesView.as_view(), name="my_queries"),
    path("me/<str:query_id>/", DeleteAnsweredMyQueryView.as_view(), name="delete_answered_my_query"),

    # Branch Admin review
    path("branch-admin/pending/", BranchAdminPendingQueriesView.as_view(), name="branch_admin_pending_queries"),
    path("branch-admin/answered/", BranchAdminAnsweredQueriesView.as_view(), name="branch_admin_answered_queries"),
    path(
        "branch-admin/answered/<str:query_id>/",
        BranchAdminAnsweredQueriesView.as_view(),
        name="branch_admin_delete_answered_query",
    ),
    path("branch-admin/<str:query_id>/action/", BranchAdminQueryActionView.as_view(), name="branch_admin_query_action"),

    # Super Admin
    path("super-admin/pending/", SuperAdminQueriesView.as_view(), name="super_admin_pending_queries"),
    path("super-admin/<str:query_id>/", SuperAdminQueryAnswerView.as_view(), name="super_admin_answer_query"),
]

