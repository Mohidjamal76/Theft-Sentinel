import axiosInstance from './axios';

// List all feedback
export const listFeedback = (params) => {
  return axiosInstance.get('/api/feedback/', { params });
};

// Get feedback by ID
export const getFeedback = (id) => {
  return axiosInstance.get(`/api/feedback/${id}/`);
};

// Create new feedback (CORRECTED)
// Body: { type: "GENERAL" | "INCIDENT" | "FALSE_POSITIVE" | "TRUE_POSITIVE", message }
export const createFeedback = (data) => {
  return axiosInstance.post('/api/feedback/', data);
};

// Update feedback
export const updateFeedback = (id, data) => {
  return axiosInstance.put(`/api/feedback/${id}/`, data);
};

// Delete feedback
export const deleteFeedback = (id) => {
  return axiosInstance.delete(`/api/feedback/${id}/`);
};

// Delete feedback (Admin only - new endpoint)
export const adminDeleteFeedback = (id) => {
  return axiosInstance.delete(`/api/feedback/${id}/delete/`);
};

// Get my feedback
export const getMyFeedback = () => {
  return axiosInstance.get('/api/feedback/me/');
};

// Get feedback statistics (Admin only)
export const getFeedbackStats = (params) => {
  return axiosInstance.get('/api/feedback/stats/', { params });
};

