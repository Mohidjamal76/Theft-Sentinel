import axiosInstance from './axios';

// List all alerts
// Query params: ?status=ACTIVE, ?camera_id=1, ?alert_type=string, ?severity=HIGH
export const listAlerts = (params) => {
  return axiosInstance.get('/api/alerts/', { params });
};

// Get alert by ID
export const getAlert = (id) => {
  return axiosInstance.get(`/api/alerts/${id}/`);
};

// Create new alert
// Body: { camera_id, alert_type, severity, metadata: { confidence, frame_url } }
export const createAlert = (data) => {
  return axiosInstance.post('/api/alerts/', data);
};

// Update alert
export const updateAlert = (id, data) => {
  return axiosInstance.put(`/api/alerts/${id}/`, data);
};

// Partial update alert
export const patchAlert = (id, data) => {
  return axiosInstance.patch(`/api/alerts/${id}/`, data);
};

// Delete alert
export const deleteAlert = (id) => {
  return axiosInstance.delete(`/api/alerts/${id}/`);
};

// Delete alert (Admin only - new endpoint)
export const adminDeleteAlert = (id) => {
  return axiosInstance.delete(`/api/alerts/${id}/delete/`);
};

// Acknowledge alert (CORRECTED: PATCH method, body: { status, guard_email?, comment? })
// Body: { status: "ACKED" | "RESOLVED", guard_email: string (required), comment?: string }
export const acknowledgeAlert = (id, status, guardEmail = null, comment = '') => {
  const body = { status };
  if (guardEmail) {
    body.guard_email = guardEmail;
  }
  if (comment) {
    body.comment = comment;
  }
  return axiosInstance.patch(`/api/alerts/${id}/acknowledge/`, body);
};

