import axiosInstance from './axios';

// List all cameras
// Query params: ?zone=Zone_A, ?status=ONLINE
export const listCameras = (params) => {
  return axiosInstance.get('/api/cameras/', { params });
};

// Get camera by ID
export const getCamera = (id) => {
  return axiosInstance.get(`/api/cameras/${id}/`);
};

// Create new camera (CORRECTED)
// Body: { name, rtsp_url, location, zone, status: "ONLINE" | "OFFLINE" }
export const createCamera = (data) => {
  return axiosInstance.post('/api/cameras/', data);
};

// Update camera
export const updateCamera = (id, data) => {
  return axiosInstance.put(`/api/cameras/${id}/`, data);
};

// Partial update camera
export const patchCamera = (id, data) => {
  return axiosInstance.patch(`/api/cameras/${id}/`, data);
};

// Update camera status after backend feed validation
export const updateCameraStatus = (id, status) => {
  return axiosInstance.patch(`/api/cameras/${id}/status/`, { status });
};

// Delete camera
export const deleteCamera = (id) => {
  return axiosInstance.delete(`/api/cameras/${id}/`);
};

