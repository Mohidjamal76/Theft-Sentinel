from datetime import timedelta
from collections import Counter

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework import status, views
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import PasswordResetToken
from apps.accounts.permissions import IsSuperAdmin

from .models import Tenant, Branch, SuperAdminProfile, BranchPasswordResetRequest
from .serializers import (
    SuperAdminExistsSerializer,
    SuperAdminCreateSerializer,
    TenantBranchRegistrationSerializer,
    BranchSerializer,
    BranchStatusUpdateSerializer,
    SuperAdminProfileSerializer,
    SuperAdminProfileUpdateSerializer,
    BranchAdminProfileSerializer,
    BranchAdminProfileUpdateSerializer,
    SuperAdminForgotPasswordSerializer,
    BranchAdminResetRequestCreateSerializer,
    BranchPasswordResetRequestSerializer,
)
from .cnic_registry import (
    sync_branch_admin_cnic,
    sync_super_admin_partner_cnics,
    unregister_branch_admin_cnic,
)

User = get_user_model()


class SuperAdminExistsView(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        exists = User.objects.filter(role="SUPER_ADMIN", is_active=True).exists()
        return Response(SuperAdminExistsSerializer({"exists": exists}).data, status=status.HTTP_200_OK)


class CreateSuperAdminView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if User.objects.filter(role="SUPER_ADMIN", is_active=True).exists():
            return Response(
                {"error": "Super Admin already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SuperAdminCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            user = User.objects.filter(
                email__iexact=data["email"],
                role="SUPER_ADMIN",
                is_active=False,
            ).first()
            if user is not None:
                user.username = data["username"]
                user.email = data["email"]
                user.role = "SUPER_ADMIN"
                user.branch = None
                user.is_active = True
                user.is_staff = True
                user.is_superuser = True
                user.set_password(data["password"])
                user.save(
                    update_fields=[
                        "username",
                        "email",
                        "role",
                        "branch",
                        "is_active",
                        "is_staff",
                        "is_superuser",
                        "password",
                    ]
                )
            else:
                user = User.objects.create_user(
                    username=data["username"],
                    email=data["email"],
                    password=data["password"],
                    role="SUPER_ADMIN",
                    is_active=True,
                    is_staff=True,
                    is_superuser=True,
                )

            partners = []
            for name, cnic in zip(data.get("partner_names", []), data.get("partner_cnics", [])):
                partners.append({"name": name, "cnic": cnic})

            profile, _ = SuperAdminProfile.objects.get_or_create(
                user=user,
                defaults={
                    "full_name": data["full_name"],
                    "phone_number": data.get("phone_number") or "",
                    "partners_count": data["partners_count"],
                    "partners": partners,
                },
            )
            profile.full_name = data["full_name"]
            profile.phone_number = data.get("phone_number") or ""
            profile.partners_count = data["partners_count"]
            profile.partners = partners
            profile.save(
                update_fields=[
                    "full_name",
                    "phone_number",
                    "partners_count",
                    "partners",
                ]
            )
            sync_super_admin_partner_cnics(profile)

        return Response(
            {
                "message": "Super Admin created successfully.",
                "user": {"id": str(user.id), "email": user.email, "username": user.username, "role": user.role},
            },
            status=status.HTTP_201_CREATED,
        )


class BranchRegistrationView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TenantBranchRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            tenant = Tenant.objects.create(
                company_name=data["company_name"],
                company_address=data["company_address"],
            )
            branch = Branch.objects.create(
                tenant=tenant,
                branch_name=data["branch_name"],
                admin_name=data["admin_name"],
                admin_cnic=data["cnic"],
                admin_email=data["email"],
                admin_phone=data["phone_number"],
                status=Branch.STATUS_PENDING,
            )

            admin_user = User.objects.create_user(
                username=data["username"],
                email=data["email"],
                password=data["password"],
                role="ADMIN",
                is_active=True,
                branch=branch,
            )
            sync_branch_admin_cnic(branch)

        return Response(
            {
                "message": "Branch registered successfully and is pending approval.",
                "branch": BranchSerializer(branch).data,
                "admin_user": {"id": str(admin_user.id), "email": admin_user.email, "username": admin_user.username},
            },
            status=status.HTTP_201_CREATED,
        )


class SuperAdminBranchListView(views.APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        branches = Branch.objects.select_related("tenant").all().order_by("-created_at")

        total = branches.count()
        approved = branches.filter(status=Branch.STATUS_APPROVED).count()
        suspended = branches.filter(status=Branch.STATUS_SUSPENDED).count()
        pending = branches.filter(status=Branch.STATUS_PENDING).count()

        try:
            from apps.support.models import SupportQuery
            query_count = SupportQuery.objects.filter(status=SupportQuery.STATUS_PENDING_SUPER_ADMIN).count()
            query_status_counts = {
                "pending_branch_admin": SupportQuery.objects.filter(
                    status=SupportQuery.STATUS_PENDING_BRANCH_ADMIN
                ).count(),
                "pending_super_admin": query_count,
                "answered": SupportQuery.objects.filter(status=SupportQuery.STATUS_ANSWERED).count(),
            }
        except Exception:
            query_count = 0
            query_status_counts = {
                "pending_branch_admin": 0,
                "pending_super_admin": 0,
                "answered": 0,
            }

        reset_status_counts = {
            "total": BranchPasswordResetRequest.objects.count(),
            "pending": BranchPasswordResetRequest.objects.filter(
                status=BranchPasswordResetRequest.STATUS_PENDING
            ).count(),
            "approved": BranchPasswordResetRequest.objects.filter(
                status=BranchPasswordResetRequest.STATUS_APPROVED
            ).count(),
            "rejected": BranchPasswordResetRequest.objects.filter(
                status=BranchPasswordResetRequest.STATUS_REJECTED
            ).count(),
        }

        trend_counter = Counter()
        for branch in branches:
            if branch.created_at:
                trend_counter[branch.created_at.date().isoformat()] += 1
        registration_trend = [
            {"date": date, "count": count}
            for date, count in sorted(trend_counter.items())
        ]

        return Response(
            {
                "counts": {
                    "total_branches": total,
                    "approved_branches": approved,
                    "suspended_branches": suspended,
                    "pending_branches": pending,
                    "query_count": query_count,
                },
                "analytics": {
                    "approved_vs_suspended": [
                        {"name": "Approved", "value": approved},
                        {"name": "Suspended", "value": suspended},
                    ],
                    "branch_status_distribution": [
                        {"name": "Pending", "value": pending},
                        {"name": "Approved", "value": approved},
                        {"name": "Suspended", "value": suspended},
                    ],
                    "registration_trend": registration_trend,
                    "password_reset_requests": reset_status_counts,
                    "query_status_counts": query_status_counts,
                },
                "branches": BranchSerializer(branches, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class SuperAdminBranchActionView(views.APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def patch(self, request, branch_id: str):
        serializer = BranchStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]

        try:
            branch = Branch.objects.select_related("tenant").get(pk=branch_id)
        except Branch.DoesNotExist:
            return Response({"error": "Branch not found."}, status=status.HTTP_404_NOT_FOUND)

        old_status = branch.status

        if action == "approve":
            branch.status = Branch.STATUS_APPROVED
        elif action == "suspend":
            branch.status = Branch.STATUS_SUSPENDED
        elif action == "reapprove":
            branch.status = Branch.STATUS_APPROVED

        branch.save(update_fields=["status"])

        self._notify_branch_status_change(branch=branch, old_status=old_status, new_status=branch.status)

        return Response({"message": "Branch status updated.", "branch": BranchSerializer(branch).data})

    def _notify_branch_status_change(self, branch: Branch, old_status: str, new_status: str) -> None:
        subject = "Theft Sentinel - Branch Status Update"
        company = branch.tenant.company_name if branch.tenant else "Your Company"
        msg = (
            f"Hello {branch.admin_name},\n\n"
            f"Your branch registration has been updated.\n\n"
            f"Company: {company}\n"
            f"Branch: {branch.branch_name}\n"
            f"Previous status: {old_status}\n"
            f"New status: {new_status}\n\n"
            f"Regards,\nTheft Sentinel Team"
        )
        try:
            send_mail(
                subject=subject,
                message=msg,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", settings.EMAIL_HOST_USER),
                recipient_list=[branch.admin_email],
                fail_silently=False,
            )
        except Exception:
            # Never break status transitions if email fails
            pass


class SuperAdminBranchDeleteView(views.APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def delete(self, request, branch_id: str):
        try:
            branch = Branch.objects.select_related("tenant").get(pk=branch_id)
        except Branch.DoesNotExist:
            return Response({"error": "Branch not found."}, status=status.HTTP_404_NOT_FOUND)

        # Email before delete (best-effort)
        try:
            send_mail(
                subject="Theft Sentinel - Branch Deletion",
                message=(
                    f"Hello {branch.admin_name},\n\n"
                    f"Your branch has been deleted from Theft Sentinel.\n"
                    f"Company: {branch.tenant.company_name if branch.tenant else ''}\n"
                    f"Branch: {branch.branch_name}\n\n"
                    f"If you believe this is a mistake, contact support."
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", settings.EMAIL_HOST_USER),
                recipient_list=[branch.admin_email],
                fail_silently=False,
            )
        except Exception:
            pass

        with transaction.atomic():
            # Delete all branch-associated users first so SET_NULL on User.branch never
            # leaves deactivated/orphaned accounts behind.
            User.objects.filter(branch=branch).exclude(role="SUPER_ADMIN").delete()

            # Camera deletion cascades camera-owned alerts, incidents, tracking,
            # surveillance events, and AI inference records.
            from apps.cameras.models import Camera
            from apps.cameras.services import cleanup_camera_runtime

            for camera in Camera.objects.filter(branch=branch):
                cleanup_camera_runtime(camera)
                camera.delete()

            tenant = branch.tenant
            unregister_branch_admin_cnic(branch)
            branch.delete()

            if tenant and not tenant.branches.exists():
                tenant.delete()

        return Response({"message": "Branch deleted."}, status=status.HTTP_200_OK)


class SuperAdminProfileView(views.APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def _get_profile(self, user):
        profile, _ = SuperAdminProfile.objects.get_or_create(
            user=user,
            defaults={
                "full_name": user.username or user.email or "Super Admin",
                "phone_number": "",
                "partners_count": 0,
                "partners": [],
            },
        )
        return profile

    def get(self, request):
        profile = self._get_profile(request.user)
        return Response(SuperAdminProfileSerializer(profile).data, status=status.HTTP_200_OK)

    def put(self, request):
        profile = self._get_profile(request.user)

        serializer = SuperAdminProfileUpdateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if "full_name" in data:
            profile.full_name = data["full_name"]
        if "phone_number" in data:
            profile.phone_number = data["phone_number"]
        if "partners_count" in data:
            profile.partners_count = data["partners_count"]
            partners = []
            for name, cnic in zip(data.get("partner_names", []), data.get("partner_cnics", [])):
                partners.append({"name": name, "cnic": cnic})
            profile.partners = partners

        profile.save()
        sync_super_admin_partner_cnics(profile)
        return Response(SuperAdminProfileSerializer(profile).data, status=status.HTTP_200_OK)

    def delete(self, request):
        # Super Admin can be deleted only if all branches are deleted
        if Branch.objects.exists():
            return Response(
                {"error": "Delete all branches before deleting Super Admin account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.is_active = False
        request.user.save(update_fields=["is_active"])
        return Response({"message": "Super Admin account deleted."}, status=status.HTTP_200_OK)


class BranchAdminProfileView(views.APIView):
    permission_classes = [IsAuthenticated]

    def _get_branch(self, request):
        if getattr(request.user, "role", None) != "ADMIN":
            return None
        return getattr(request.user, "branch", None)

    def get(self, request):
        branch = self._get_branch(request)
        if not branch:
            return Response({"error": "Branch Admin profile not found."}, status=status.HTTP_404_NOT_FOUND)

        branch = Branch.objects.select_related("tenant").get(pk=branch.pk)
        return Response(BranchAdminProfileSerializer(branch).data, status=status.HTTP_200_OK)

    def put(self, request):
        branch = self._get_branch(request)
        if not branch:
            return Response({"error": "Branch Admin profile not found."}, status=status.HTTP_404_NOT_FOUND)

        branch = Branch.objects.select_related("tenant").get(pk=branch.pk)
        serializer = BranchAdminProfileUpdateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        old_email = request.user.email
        new_email = data["email"]

        if request.user.username == old_email:
            request.user.username = new_email
        request.user.email = new_email
        request.user.save(update_fields=["email", "username"])

        branch.admin_name = data["full_name"]
        branch.admin_cnic = data["cnic"]
        branch.admin_email = new_email
        branch.admin_phone = data.get("phone_number") or ""
        branch.branch_name = data["branch_name"]

        if branch.tenant:
            branch.tenant.company_name = data["company_name"]
            branch.tenant.company_address = data.get("address") or ""
            branch.tenant.save(update_fields=["company_name", "company_address"])

        branch.save(update_fields=["admin_name", "admin_cnic", "admin_email", "admin_phone", "branch_name"])
        sync_branch_admin_cnic(branch)
        return Response(BranchAdminProfileSerializer(branch).data, status=status.HTTP_200_OK)


class SuperAdminForgotPasswordView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SuperAdminForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email__iexact=email, role="SUPER_ADMIN", is_active=True)
        except User.DoesNotExist:
            return Response({"error": "Invalid Super Admin email."}, status=status.HTTP_400_BAD_REQUEST)

        token = PasswordResetToken.generate_token()
        expires_at = timezone.now() + timedelta(minutes=30)
        PasswordResetToken.objects.filter(user=user, used=False).update(used=True)
        reset_token = PasswordResetToken.objects.create(user=user, token=token, expires_at=expires_at)

        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
        reset_link = f"{frontend_url}/reset-password?token={token}"

        try:
            send_mail(
                subject="Theft Sentinel - Super Admin Password Reset",
                message=f"Hello,\n\nReset your password using this link:\n{reset_link}\n\nThis link expires in 30 minutes.",
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", settings.EMAIL_HOST_USER),
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception:
            try:
                reset_token.delete()
            except Exception:
                pass
            return Response(
                {"error": "Email service is currently unavailable. Please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({"message": "Reset link sent."}, status=status.HTTP_200_OK)


class BranchAdminResetRequestCreateView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = BranchAdminResetRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        reason = serializer.validated_data["reason"]

        try:
            user = User.objects.select_related("branch").get(email__iexact=email, role="ADMIN", is_active=True)
        except User.DoesNotExist:
            return Response({"error": "Email must belong to a Branch Admin."}, status=status.HTTP_400_BAD_REQUEST)

        branch = getattr(user, "branch", None)
        if not branch:
            return Response({"error": "Branch Admin is not linked to a branch."}, status=status.HTTP_400_BAD_REQUEST)

        req_obj = BranchPasswordResetRequest.objects.create(user=user, branch=branch, reason=reason)
        return Response(
            {"message": "Password reset request submitted for Super Admin review.", "id": str(req_obj.id)},
            status=status.HTTP_201_CREATED,
        )


class SuperAdminResetRequestListView(views.APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        qs = BranchPasswordResetRequest.objects.select_related("user", "branch", "branch__tenant").all()
        return Response(BranchPasswordResetRequestSerializer(qs, many=True).data, status=status.HTTP_200_OK)


class SuperAdminResetRequestActionView(views.APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request, request_id: str):
        action = request.data.get("action")
        if action not in {"approve", "reject", "delete"}:
            return Response({"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            req_obj = BranchPasswordResetRequest.objects.select_related("user", "branch").get(pk=request_id)
        except BranchPasswordResetRequest.DoesNotExist:
            return Response({"error": "Request not found."}, status=status.HTTP_404_NOT_FOUND)

        if action == "delete":
            if req_obj.status == BranchPasswordResetRequest.STATUS_PENDING:
                return Response({"error": "Cannot delete a pending request."}, status=status.HTTP_400_BAD_REQUEST)
            req_obj.delete()
            return Response({"message": "Request deleted."}, status=status.HTTP_200_OK)

        if req_obj.status != BranchPasswordResetRequest.STATUS_PENDING:
            return Response({"error": "Request already processed."}, status=status.HTTP_400_BAD_REQUEST)

        if action == "reject":
            req_obj.status = BranchPasswordResetRequest.STATUS_REJECTED
            req_obj.reviewed_at = timezone.now()
            req_obj.reviewed_by = request.user
            req_obj.save(update_fields=["status", "reviewed_at", "reviewed_by"])
            return Response({"message": "Request rejected."}, status=status.HTTP_200_OK)

        # approve
        user = req_obj.user
        token = PasswordResetToken.generate_token()
        expires_at = timezone.now() + timedelta(minutes=30)
        PasswordResetToken.objects.filter(user=user, used=False).update(used=True)
        reset_token = PasswordResetToken.objects.create(user=user, token=token, expires_at=expires_at)

        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
        reset_link = f"{frontend_url}/reset-password?token={token}"

        try:
            send_mail(
                subject="Theft Sentinel - Password Reset Approved",
                message=f"Hello {user.username},\n\nYour password reset request was approved.\n\nReset link:\n{reset_link}\n\nThis link expires in 30 minutes.",
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", settings.EMAIL_HOST_USER),
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception:
            try:
                reset_token.delete()
            except Exception:
                pass
            return Response(
                {"error": "Email service is currently unavailable. Please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        req_obj.status = BranchPasswordResetRequest.STATUS_APPROVED
        req_obj.reviewed_at = timezone.now()
        req_obj.reviewed_by = request.user
        req_obj.save(update_fields=["status", "reviewed_at", "reviewed_by"])

        return Response({"message": "Approved and reset link sent."}, status=status.HTTP_200_OK)

