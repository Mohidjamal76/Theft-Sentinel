import axiosInstance from './axios';

// Send SMS notification (CORRECTED)
// Body: { phone_number, message }
export const sendSMS = (data) => {
  return axiosInstance.post('/api/mobile/send-sms/', data);
};

// Send email notification (CORRECTED)
// Body: { email_address, subject, message }
export const sendEmail = (data) => {
  return axiosInstance.post('/api/mobile/send-email/', data);
};

// Send bulk notifications (CORRECTED)
// Body: { user_ids: [1, 2], subject, message, send_sms: true, send_email: true }
export const sendBulkNotifications = (data) => {
  return axiosInstance.post('/api/mobile/send-bulk/', data);
};

