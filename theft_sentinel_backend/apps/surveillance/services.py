"""
Surveillance Service - Process AI events and create alerts/incidents
"""
from apps.alerts.models import Alert
from apps.alerts.services import dispatch_theft_alert_notifications
from apps.incidents.models import Incident
from apps.cameras.models import Camera
import logging

logger = logging.getLogger(__name__)


class SurveillanceService:
    """Service to process surveillance events"""
    
    @staticmethod
    def process_event(surveillance_event):
        """
        Process a surveillance event and create alerts/incidents if needed
        
        Args:
            surveillance_event: SurveillanceEvent instance
        
        Returns:
            dict with created alert and incident info
        """
        result = {
            'alert_created': False,
            'incident_created': False,
            'alert': None,
            'incident': None
        }
        
        try:
            # Determine if event should create an alert
            should_create_alert = SurveillanceService._should_create_alert(surveillance_event)
            
            if should_create_alert:
                # Create alert
                alert = SurveillanceService._create_alert(surveillance_event)
                result['alert_created'] = True
                result['alert'] = alert
                
                # Determine severity and if incident should be created
                if SurveillanceService._should_create_incident(surveillance_event, alert):
                    incident = SurveillanceService._create_incident(alert)
                    result['incident_created'] = True
                    result['incident'] = incident
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing surveillance event: {str(e)}")
            raise
    
    @staticmethod
    def _should_create_alert(surveillance_event):
        """
        Determine if surveillance event should trigger an alert
        
        Logic can be customized based on event_type, ai_data confidence, etc.
        """
        # For MVP, create alert for specific event types
        alert_triggering_events = [
            'theft_detected',
            'intrusion_detected',
            'suspicious_activity',
            'unauthorized_access',
            'violence_detected',
            'weapon_detected'
        ]
        
        return surveillance_event.event_type.lower() in alert_triggering_events
    
    @staticmethod
    def _create_alert(surveillance_event):
        """Create an alert from surveillance event"""
        
        # Determine severity based on event type
        severity = SurveillanceService._determine_severity(surveillance_event)
        
        # Extract relevant metadata
        metadata = {
            'event_id': surveillance_event.id,
            'frame_url': surveillance_event.frame_url,
            'ai_data': surveillance_event.ai_data,
            'confidence': surveillance_event.ai_data.get('confidence', 0),
        }
        
        alert = Alert.objects.create(
            camera_id=surveillance_event.camera_id,
            alert_type=surveillance_event.event_type,
            severity=severity,
            status='ACTIVE',
            metadata=metadata
        )
        
        logger.info(f"Alert created: {alert.id} for event {surveillance_event.id}")
        try:
            dispatch_theft_alert_notifications(alert, async_send=True)
        except Exception:
            logger.exception("Failed to dispatch alert notifications for alert %s", alert.id)
        return alert
    
    @staticmethod
    def _determine_severity(surveillance_event):
        """Determine alert severity based on event type and ai_data"""
        
        high_severity_events = ['weapon_detected', 'violence_detected', 'intrusion_detected']
        medium_severity_events = ['theft_detected', 'suspicious_activity']
        
        event_type = surveillance_event.event_type.lower()
        
        if event_type in high_severity_events:
            return 'HIGH'
        elif event_type in medium_severity_events:
            return 'MEDIUM'
        else:
            # Check confidence level if available
            confidence = surveillance_event.ai_data.get('confidence', 0)
            if confidence > 0.8:
                return 'MEDIUM'
            return 'MEDIUM'
    
    @staticmethod
    def _should_create_incident(surveillance_event, alert):
        """Determine if an incident should be created"""
        
        # Create incident for high severity alerts
        if alert.severity == 'HIGH':
            return True
        
        # Create incident for medium severity with high confidence
        if alert.severity == 'MEDIUM':
            confidence = surveillance_event.ai_data.get('confidence', 0)
            if confidence > 0.75:
                return True
        
        return False
    
    @staticmethod
    def _create_incident(alert):
        """Create an incident from alert"""
        
        incident = Incident.objects.create(
            alert_id=alert,
            status='CREATED',
            notes=f"Auto-created from alert #{alert.id} - {alert.alert_type}"
        )
        
        logger.info(f"Incident created: {incident.id} for alert {alert.id}")
        return incident

