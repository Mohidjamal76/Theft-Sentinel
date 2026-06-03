import axiosInstance from './axios';

// List all personnel
// Query params: ?zone=Zone_A
export const listPersonnel = (params) => {
  return axiosInstance.get('/api/personnel/', { params });
};

// Get personnel by ID
export const getPersonnel = (id) => {
  return axiosInstance.get(`/api/personnel/${id}/`);
};

// Create new personnel (CORRECTED)
// Body: { user, phone, assigned_zones: ["Zone A", "Zone B"] }
export const createPersonnel = (data) => {
  return axiosInstance.post('/api/personnel/', data);
};

// Update personnel
export const updatePersonnel = (id, data) => {
  return axiosInstance.put(`/api/personnel/${id}/`, data);
};

// Partial update personnel
export const patchPersonnel = (id, data) => {
  return axiosInstance.patch(`/api/personnel/${id}/`, data);
};

// Delete personnel
export const deletePersonnel = (id) => {
  return axiosInstance.delete(`/api/personnel/${id}/`);
};

