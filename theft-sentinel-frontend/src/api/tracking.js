import axiosInstance from './axios';

// Ingest tracking data (CORRECTED)
// Body: { camera_id, vector, person_id }
export const ingestTracking = (data) => {
  return axiosInstance.post('/api/tracking/ingest/', data);
};

// List tracking records (CORRECTED - using base endpoint with query params)
// Query params: ?person_id=PERSON_xyz, ?camera_id=1, ?time_window=60
export const listTrackingRecords = (params) => {
  return axiosInstance.get('/api/tracking/', { params });
};

// Get person path/trajectory (use query params instead)
export const getPersonPath = (personId, params = {}) => {
  return axiosInstance.get('/api/tracking/', { params: { person_id: personId, ...params } });
};

// Get tracking by camera (use query params)
export const getTrackingByCamera = (cameraId, params = {}) => {
  return axiosInstance.get('/api/tracking/', { 
    params: { camera_id: cameraId, ...params } 
  });
};

