import logging
import threading

from django.conf import settings
from django.contrib.auth import get_user_model

from apps.accounts.validation import normalize_pakistani_phone
from apps.mobile.services import NotificationService

logger = logging.getLogger(__name__)


def is_theft_alert(alert) -> bool:
    alert_type = (getattr(alert, "alert_type", "") or "").lower()
    return "theft" in alert_type


def _get_branch_admin(alert):
    camera = getattr(alert, "camera_id", None)
    branch = getattr(camera, "branch", None)
    if not branch:
        return None, None, camera

    User = get_user_model()
    branch_admin = User.objects.filter(role="ADMIN", branch=branch, is_active=True).first()
    return branch, branch_admin, camera


def _merge_alert_metadata(alert, updates: dict) -> None:
    from apps.alerts.models import Alert

    fresh = Alert.objects.get(pk=alert.pk)
    metadata = dict(fresh.metadata or {})
    metadata.update(updates)
    fresh.metadata = metadata
    fresh.save(update_fields=["metadata"])
    alert.metadata = metadata


def _incident_link(alert) -> str:
    try:
        incident = alert.incidents.order_by("-created_at").first()
        if not incident:
            return ""
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
        return f"{frontend_url}/incidents/{incident.id}"
    except Exception:
        return ""


def dispatch_theft_alert_sms(alert, async_send=True) -> bool:
    """
    Send the branch-admin SMS for a theft alert exactly once.

    The idempotency marker lives in alert.metadata so manual API alerts,
    surveillance events, and the continuous monitor all share the same guard.
    """
    if not alert or not is_theft_alert(alert):
        return False

    metadata = dict(getattr(alert, "metadata", None) or {})
    if metadata.get("twilio_sms_attempted"):
        logger.info("Skipping duplicate Twilio SMS for alert %s", alert.id)
        return False

    branch, branch_admin, camera = _get_branch_admin(alert)
    raw_phone = getattr(branch, "admin_phone", "") if branch else ""

    try:
        phone = normalize_pakistani_phone(raw_phone, required=True)
    except Exception as exc:
        _merge_alert_metadata(alert, {
            "twilio_sms_attempted": True,
            "twilio_sms_status": "FAILED",
            "twilio_sms_error": str(exc),
        })
        logger.error("Twilio SMS skipped for alert %s: invalid branch admin phone %r", alert.id, raw_phone)
        return False

    if not branch_admin:
        _merge_alert_metadata(alert, {
            "twilio_sms_attempted": True,
            "twilio_sms_status": "FAILED",
            "twilio_sms_error": "Active branch admin not found",
        })
        logger.error("Twilio SMS skipped for alert %s: active branch admin not found", alert.id)
        return False

    _merge_alert_metadata(alert, {
        "twilio_sms_attempted": True,
        "twilio_sms_status": "PENDING",
        "twilio_sms_phone": phone,
    })
    logger.info("Twilio theft SMS target for alert %s: %s", alert.id, phone)

    incident_link = _incident_link(alert)
    message = (
        "Theft Sentinel Alert:\n"
        f"Branch: {getattr(branch, 'branch_name', 'Unknown branch')}\n"
        f"Camera: {getattr(camera, 'name', 'Unknown camera')}\n"
        f"Severity: {alert.severity}\n"
        f"Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    if incident_link:
        message += f"\nIncident: {incident_link}"

    def _send():
        try:
            success = NotificationService.send_sms(branch_admin, phone, message)
            from apps.alerts.models import Alert

            fresh = Alert.objects.get(pk=alert.pk)
            fresh_metadata = dict(fresh.metadata or {})
            fresh_metadata["twilio_sms_status"] = "SENT" if success else "FAILED"
            fresh.metadata = fresh_metadata
            fresh.save(update_fields=["metadata"])
            if success:
                logger.info("Twilio theft SMS sent for alert %s to %s", alert.id, phone)
            else:
                logger.error("Twilio theft SMS failed for alert %s to %s", alert.id, phone)
        except Exception as exc:
            logger.error("Twilio theft SMS failed for alert %s to %s: %s", alert.id, phone, exc, exc_info=True)
            try:
                from apps.alerts.models import Alert

                fresh = Alert.objects.get(pk=alert.pk)
                fresh_metadata = dict(fresh.metadata or {})
                fresh_metadata["twilio_sms_status"] = "FAILED"
                fresh_metadata["twilio_sms_error"] = str(exc)
                fresh.metadata = fresh_metadata
                fresh.save(update_fields=["metadata"])
            except Exception:
                logger.exception("Failed to persist Twilio failure metadata for alert %s", alert.id)

    if async_send:
        threading.Thread(target=_send, daemon=True, name=f"twilio-alert-{alert.id}").start()
    else:
        _send()
    return True


def dispatch_theft_alert_email(alert, async_send=True) -> bool:
    """Send the branch-admin email for a theft alert exactly once."""
    if not alert or not is_theft_alert(alert):
        return False

    metadata = dict(getattr(alert, "metadata", None) or {})
    if metadata.get("alert_email_attempted"):
        logger.info("Skipping duplicate alert email for alert %s", alert.id)
        return False

    branch, branch_admin, camera = _get_branch_admin(alert)
    email = (getattr(branch, "admin_email", "") if branch else "") or getattr(branch_admin, "email", "")
    if not branch_admin:
        _merge_alert_metadata(alert, {
            "alert_email_attempted": True,
            "alert_email_status": "FAILED",
            "alert_email_error": "Active branch admin not found",
        })
        logger.error("Alert email skipped for alert %s: active branch admin not found", alert.id)
        return False
    if not email:
        _merge_alert_metadata(alert, {
            "alert_email_attempted": True,
            "alert_email_status": "FAILED",
            "alert_email_error": "Branch admin email missing",
        })
        logger.error("Alert email skipped for alert %s: branch admin email missing", alert.id)
        return False

    _merge_alert_metadata(alert, {
        "alert_email_attempted": True,
        "alert_email_status": "PENDING",
        "alert_email_recipient": email,
    })

    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
    clip_url = getattr(alert, "video_url", None) or ""
    incident_link = _incident_link(alert)
    alert_link = f"{frontend_url}/alerts/{alert.id}"
    subject = "Theft Sentinel Alert - Suspicious Activity Detected"
    message = (
        "A theft alert was generated in Theft Sentinel.\n\n"
        f"Branch name: {getattr(branch, 'branch_name', 'Unknown branch')}\n"
        f"Camera name: {getattr(camera, 'name', 'Unknown camera')}\n"
        f"Severity: {alert.severity}\n"
        f"Timestamp: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Detection clip: {clip_url or 'Not available yet'}\n"
        f"Alert link: {alert_link}\n"
        f"Incident link: {incident_link or 'Not assigned yet'}\n"
        f"Dashboard login: {frontend_url}/login\n"
    )

    def _send():
        try:
            success = NotificationService.send_email(branch_admin, email, subject, message)
            _merge_alert_metadata(alert, {"alert_email_status": "SENT" if success else "FAILED"})
            if success:
                logger.info("Alert email sent for alert %s to %s", alert.id, email)
            else:
                logger.error("Alert email failed for alert %s to %s", alert.id, email)
        except Exception as exc:
            logger.error("Alert email failed for alert %s to %s: %s", alert.id, email, exc, exc_info=True)
            try:
                _merge_alert_metadata(alert, {
                    "alert_email_status": "FAILED",
                    "alert_email_error": str(exc),
                })
            except Exception:
                logger.exception("Failed to persist email failure metadata for alert %s", alert.id)

    if async_send:
        threading.Thread(target=_send, daemon=True, name=f"email-alert-{alert.id}").start()
    else:
        _send()
    return True


def dispatch_theft_alert_notifications(alert, async_send=True) -> dict:
    """
    Attempt SMS and email independently for a theft alert.

    Failures are logged and stored in alert.metadata by each channel and never
    prevent alert creation.
    """
    return {
        "sms_attempted": dispatch_theft_alert_sms(alert, async_send=async_send),
        "email_attempted": dispatch_theft_alert_email(alert, async_send=async_send),
    }
