import axiosInstance from './axios';

// Ingest surveillance event (CORRECTED)
// Body: { camera_id, event_type, frame_url, ai_data: { confidence, bounding_boxes, detected_objects } }
export const ingestEvent = (data) => {
  return axiosInstance.post('/api/surveillance/ingest/', data);
};

// List surveillance events (NOT IN OFFICIAL SCHEMA - keeping for backward compatibility)
export const listEvents = (params) => {
  return axiosInstance.get('/api/surveillance/events/', { params });
};

// Get event by ID (NOT IN OFFICIAL SCHEMA - keeping for backward compatibility)
export const getEvent = (id) => {
  return axiosInstance.get(`/api/surveillance/events/${id}/`);
};

