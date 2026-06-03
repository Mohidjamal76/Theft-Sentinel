import axiosInstance from './axios';

// Login
export const login = (credentials) => {
  return axiosInstance.post('/api/auth/login/', credentials);
};

// Logout
export const logout = () => {
  const refreshToken = localStorage.getItem('refresh_token');
  return axiosInstance.post('/api/auth/logout/', {
    refresh_token: refreshToken
  });
};

// Get current user profile
export const getProfile = () => {
  return axiosInstance.get('/api/auth/profile/');
};

// Update profile
export const updateProfile = (data) => {
  return axiosInstance.put('/api/auth/profile/', data);
};

// Change password
export const changePassword = (data) => {
  return axiosInstance.post('/api/auth/change-password/', data);
};

// List all users (Admin only)
export const listUsers = (params) => {
  return axiosInstance.get('/api/auth/users/', { params });
};

// Get user by ID (Admin only)
export const getUser = (id) => {
  return axiosInstance.get(`/api/auth/users/${id}/`);
};

// Update user (Admin only)
export const updateUser = (id, data) => {
  return axiosInstance.put(`/api/auth/users/${id}/`, data);
};

// Partial update user (Admin only)
export const patchUser = (id, data) => {
  return axiosInstance.patch(`/api/auth/users/${id}/`, data);
};

// Delete user (Admin only)
export const deleteUser = (id) => {
  return axiosInstance.delete(`/api/auth/users/${id}/`);
};

// Admin change user password (Admin only)
export const adminChangeUserPassword = (userId, data) => {
  return axiosInstance.post(`/api/auth/users/${userId}/change-password/`, data);
};

// Token refresh (handled by interceptor, but exposed if needed)
export const refreshToken = (refresh) => {
  return axiosInstance.post('/api/auth/token/refresh/', { refresh });
};

// Forgot Password (Admin Only)
export const forgotPassword = (email) => {
  return axiosInstance.post('/api/auth/forgot-password/', { email });
};

// Reset Password (Admin Only)
export const resetPassword = (token, newPassword, confirmPassword) => {
  return axiosInstance.post('/api/auth/reset-password/', {
    token,
    new_password: newPassword,
    confirm_password: confirmPassword
  });
};

