import axiosInstance from './axios';

// List all incidents
// Query params: ?status=ASSIGNED, ?assigned_to=2, ?my_incidents=true
export const listIncidents = (params) => {
  return axiosInstance.get('/api/incidents/', { params });
};

// Get incident by ID
export const getIncident = (id) => {
  return axiosInstance.get(`/api/incidents/${id}/`);
};

// Create new incident (CORRECTED)
// Body: { alert_id, assigned_to, notes }
export const createIncident = (data) => {
  return axiosInstance.post('/api/incidents/', data);
};

// Update incident
export const updateIncident = (id, data) => {
  return axiosInstance.put(`/api/incidents/${id}/`, data);
};

// Partial update incident
export const patchIncident = (id, data) => {
  return axiosInstance.patch(`/api/incidents/${id}/`, data);
};

// Delete incident
export const deleteIncident = (id) => {
  return axiosInstance.delete(`/api/incidents/${id}/`);
};

// Assign incident to user (CORRECTED: PATCH method, assigned_to field)
// Body: { assigned_to, notes }
export const assignIncident = (id, assigned_to, notes = '') => {
  return axiosInstance.patch(`/api/incidents/${id}/assign/`, { assigned_to, notes });
};

// Update incident status (CORRECTED: status and notes fields)
// Body: { status: "CREATED" | "ASSIGNED" | "ACKNOWLEDGED" | "RESOLVED", notes }
export const updateIncidentStatus = (id, status, notes = '') => {
  return axiosInstance.patch(`/api/incidents/${id}/status/`, { 
    status, 
    notes 
  });
};

