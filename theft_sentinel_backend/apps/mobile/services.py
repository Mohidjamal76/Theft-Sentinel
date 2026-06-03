"""
Notification Service - SMS (Twilio) and Email
"""
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from .models import Notification
from apps.accounts.validation import normalize_pakistani_phone
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications via SMS and Email"""
    
    @staticmethod
    def send_sms(user, phone_number, message):
        """
        Send SMS notification using Twilio
        
        Args:
            user: User instance
            phone_number: Recipient phone number
            message: Message content
        
        Returns:
            bool: Success status
        """
        try:
            phone_number = normalize_pakistani_phone(phone_number, required=True)
        except Exception as exc:
            logger.error("Failed to send SMS: invalid phone number %r (%s)", phone_number, exc)
            return False

        notification = Notification.objects.create(
            user=user,
            notification_type='SMS',
            recipient=phone_number,
            message=message,
            status='PENDING'
        )
        
        try:
            # Check if Twilio is configured
            if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
                logger.warning("Twilio credentials not configured")
                notification.status = 'FAILED'
                notification.error_message = "Twilio credentials not configured"
                notification.save()
                return False
            
            # Import Twilio client
            from twilio.rest import Client
            
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            
            # Send SMS
            twilio_message = client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=phone_number
            )
            
            notification.status = 'SENT'
            notification.sent_at = timezone.now()
            notification.save()
            
            logger.info(f"SMS sent successfully to {phone_number}. Twilio SID: {twilio_message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send SMS to {phone_number}: {str(e)}")
            notification.status = 'FAILED'
            notification.error_message = str(e)
            notification.save()
            return False
    
    @staticmethod
    def send_email(user, email_address, subject, message):
        """
        Send Email notification
        
        Args:
            user: User instance
            email_address: Recipient email
            subject: Email subject
            message: Email message
        
        Returns:
            bool: Success status
        """
        notification = Notification.objects.create(
            user=user,
            notification_type='EMAIL',
            recipient=email_address,
            subject=subject,
            message=message,
            status='PENDING'
        )
        
        try:
            # Check if email is configured
            if not settings.EMAIL_HOST_USER:
                logger.warning("Email credentials not configured")
                notification.status = 'FAILED'
                notification.error_message = "Email credentials not configured"
                notification.save()
                return False
            
            # Send email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email_address],
                fail_silently=False,
            )
            
            notification.status = 'SENT'
            notification.sent_at = timezone.now()
            notification.save()
            
            logger.info(f"Email sent successfully to {email_address}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {email_address}: {str(e)}")
            notification.status = 'FAILED'
            notification.error_message = str(e)
            notification.save()
            return False
    
    @staticmethod
    def send_alert_notification(alert, users):
        """
        Send alert notifications to multiple users
        
        Args:
            alert: Alert instance
            users: List of User instances
        
        Returns:
            dict: Results summary
        """
        results = {
            'sms_sent': 0,
            'sms_failed': 0,
            'email_sent': 0,
            'email_failed': 0
        }
        
        message = f"ALERT: {alert.alert_type} detected at {alert.camera_id.location}. " \
                  f"Severity: {alert.severity}. Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        
        subject = f"Security Alert: {alert.alert_type}"
        
        for user in users:
            # Send email
            if user.email:
                success = NotificationService.send_email(
                    user=user,
                    email_address=user.email,
                    subject=subject,
                    message=message
                )
                if success:
                    results['email_sent'] += 1
                else:
                    results['email_failed'] += 1
            
            # Send SMS if personnel profile exists with phone
            try:
                personnel = user.personnel_profile
                if personnel.phone:
                    success = NotificationService.send_sms(
                        user=user,
                        phone_number=personnel.phone,
                        message=message
                    )
                    if success:
                        results['sms_sent'] += 1
                    else:
                        results['sms_failed'] += 1
            except:
                pass
        
        return results
    
    @staticmethod
    def send_incident_notification(incident, user):
        """
        Send notification about incident assignment
        
        Args:
            incident: Incident instance
            user: User instance (assigned user)
        
        Returns:
            dict: Results summary
        """
        message = f"You have been assigned to Incident #{incident.id}. " \
                  f"Alert Type: {incident.alert_id.alert_type}. " \
                  f"Location: {incident.alert_id.camera_id.location}. " \
                  f"Please review and take action."
        
        subject = f"Incident Assignment: #{incident.id}"
        
        results = {'email': False, 'sms': False}
        
        # Send email
        if user.email:
            results['email'] = NotificationService.send_email(
                user=user,
                email_address=user.email,
                subject=subject,
                message=message
            )
        
        # Send SMS
        try:
            personnel = user.personnel_profile
            if personnel.phone:
                results['sms'] = NotificationService.send_sms(
                    user=user,
                    phone_number=personnel.phone,
                    message=message
                )
        except:
            pass
        
        return results

