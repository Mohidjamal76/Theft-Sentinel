from django.utils import timezone
from rest_framework import status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsSuperAdmin
from .models import SupportQuery
from .serializers import (
    SupportQueryCreateSerializer,
    SupportQuerySerializer,
    BranchAdminQueryActionSerializer,
    SuperAdminQueryAnswerSerializer,
)


class MyQueriesView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = SupportQuery.objects.select_related("sender", "branch", "branch__tenant").filter(sender=request.user)
        return Response(SupportQuerySerializer(qs, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SupportQueryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        branch = getattr(request.user, "branch", None)
        if not branch:
            return Response({"error": "User is not linked to a branch."}, status=status.HTTP_400_BAD_REQUEST)

        # Branch Admin goes directly to Super Admin; others go to Branch Admin first
        if request.user.role == "ADMIN":
            q = SupportQuery.objects.create(
                sender=request.user,
                branch=branch,
                status=SupportQuery.STATUS_PENDING_SUPER_ADMIN,
                message=serializer.validated_data["message"],
            )
        else:
            q = SupportQuery.objects.create(
                sender=request.user,
                branch=branch,
                status=SupportQuery.STATUS_PENDING_BRANCH_ADMIN,
                message=serializer.validated_data["message"],
            )

        return Response(SupportQuerySerializer(q).data, status=status.HTTP_201_CREATED)


class BranchAdminPendingQueriesView(views.APIView):
    """
    Branch Admin reviews guard/incharge queries (approve/escalate or delete).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "ADMIN":
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        branch = getattr(request.user, "branch", None)
        qs = SupportQuery.objects.select_related("sender", "branch", "branch__tenant").filter(
            branch=branch, status=SupportQuery.STATUS_PENDING_BRANCH_ADMIN
        )
        return Response(SupportQuerySerializer(qs, many=True).data, status=status.HTTP_200_OK)


class BranchAdminAnsweredQueriesView(views.APIView):
    """
    Branch Admin can review answered staff queries in their branch.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "ADMIN":
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        branch = getattr(request.user, "branch", None)
        qs = SupportQuery.objects.select_related("sender", "branch", "branch__tenant").filter(
            branch=branch,
            status=SupportQuery.STATUS_ANSWERED,
            sender__role__in=["SECURITY_INCHARGE", "SECURITY_GUARD"],
        )
        return Response(SupportQuerySerializer(qs, many=True).data, status=status.HTTP_200_OK)

    def delete(self, request, query_id: str):
        if request.user.role != "ADMIN":
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        branch = getattr(request.user, "branch", None)

        try:
            q = SupportQuery.objects.get(
                pk=query_id,
                branch=branch,
                status=SupportQuery.STATUS_ANSWERED,
                sender__role__in=["SECURITY_INCHARGE", "SECURITY_GUARD"],
            )
        except SupportQuery.DoesNotExist:
            return Response({"error": "Answered query not found."}, status=status.HTTP_404_NOT_FOUND)

        q.delete()
        return Response({"message": "Deleted."}, status=status.HTTP_200_OK)


class BranchAdminQueryActionView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, query_id: str):
        if request.user.role != "ADMIN":
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        branch = getattr(request.user, "branch", None)

        serializer = BranchAdminQueryActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]

        try:
            q = SupportQuery.objects.get(pk=query_id, branch=branch)
        except SupportQuery.DoesNotExist:
            return Response({"error": "Query not found."}, status=status.HTTP_404_NOT_FOUND)

        if action == "delete":
            # Branch Admin can delete any query in branch that is not answered yet
            if q.status == SupportQuery.STATUS_ANSWERED:
                return Response({"error": "Cannot delete answered queries here."}, status=status.HTTP_400_BAD_REQUEST)
            q.delete()
            return Response({"message": "Deleted."}, status=status.HTTP_200_OK)

        if q.status != SupportQuery.STATUS_PENDING_BRANCH_ADMIN:
            return Response({"error": "Query is not pending Branch Admin review."}, status=status.HTTP_400_BAD_REQUEST)

        q.status = SupportQuery.STATUS_PENDING_SUPER_ADMIN
        q.save(update_fields=["status"])
        return Response({"message": "Escalated to Super Admin."}, status=status.HTTP_200_OK)


class SuperAdminQueriesView(views.APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        qs = SupportQuery.objects.select_related("sender", "branch", "branch__tenant").filter(
            status=SupportQuery.STATUS_PENDING_SUPER_ADMIN
        )
        return Response(SupportQuerySerializer(qs, many=True).data, status=status.HTTP_200_OK)


class SuperAdminQueryAnswerView(views.APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request, query_id: str):
        serializer = SuperAdminQueryAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            q = SupportQuery.objects.get(pk=query_id)
        except SupportQuery.DoesNotExist:
            return Response({"error": "Query not found."}, status=status.HTTP_404_NOT_FOUND)

        if q.status != SupportQuery.STATUS_PENDING_SUPER_ADMIN:
            return Response({"error": "Query is not pending Super Admin."}, status=status.HTTP_400_BAD_REQUEST)

        q.answer = serializer.validated_data["answer"]
        q.status = SupportQuery.STATUS_ANSWERED
        q.answered_at = timezone.now()
        q.answered_by = request.user
        q.save(update_fields=["answer", "status", "answered_at", "answered_by"])

        return Response({"message": "Answered."}, status=status.HTTP_200_OK)

    def delete(self, request, query_id: str):
        try:
            q = SupportQuery.objects.get(pk=query_id)
        except SupportQuery.DoesNotExist:
            return Response({"error": "Query not found."}, status=status.HTTP_404_NOT_FOUND)

        if q.status != SupportQuery.STATUS_ANSWERED:
            return Response({"error": "Query can be deleted only after answered."}, status=status.HTTP_400_BAD_REQUEST)

        q.delete()
        return Response({"message": "Deleted."}, status=status.HTTP_200_OK)


class DeleteAnsweredMyQueryView(views.APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, query_id: str):
        try:
            q = SupportQuery.objects.get(pk=query_id, sender=request.user)
        except SupportQuery.DoesNotExist:
            return Response({"error": "Query not found."}, status=status.HTTP_404_NOT_FOUND)

        if q.status != SupportQuery.STATUS_ANSWERED:
            return Response({"error": "You can delete only answered queries."}, status=status.HTTP_400_BAD_REQUEST)

        q.delete()
        return Response({"message": "Deleted."}, status=status.HTTP_200_OK)

