import axiosInstance from './axios';

export const superAdminExists = () => {
  return axiosInstance.get('/api/tenancy/super-admin/exists/');
};

export const createSuperAdmin = (payload) => {
  return axiosInstance.post('/api/tenancy/super-admin/create/', payload);
};

export const registerBranch = (payload) => {
  return axiosInstance.post('/api/tenancy/branches/register/', payload);
};

export const superAdminForgotPassword = (email) => {
  return axiosInstance.post('/api/tenancy/super-admin/forgot-password/', { email });
};

export const branchAdminResetRequest = (email, reason) => {
  return axiosInstance.post('/api/tenancy/branch-admin/reset-request/', { email, reason });
};

export const listBranchesForSuperAdmin = () => {
  return axiosInstance.get('/api/tenancy/super-admin/branches/');
};

export const updateBranchStatus = (branchId, action) => {
  return axiosInstance.patch(`/api/tenancy/super-admin/branches/${branchId}/status/`, { action });
};

export const deleteBranch = (branchId) => {
  return axiosInstance.delete(`/api/tenancy/super-admin/branches/${branchId}/`);
};

export const getSuperAdminProfile = () => {
  return axiosInstance.get('/api/tenancy/super-admin/profile/');
};

export const updateSuperAdminProfile = (payload) => {
  return axiosInstance.put('/api/tenancy/super-admin/profile/', payload);
};

export const deleteSuperAdminAccount = () => {
  return axiosInstance.delete('/api/tenancy/super-admin/profile/');
};

export const getBranchAdminProfile = () => {
  return axiosInstance.get('/api/tenancy/branch-admin/profile/');
};

export const updateBranchAdminProfile = (payload) => {
  return axiosInstance.put('/api/tenancy/branch-admin/profile/', payload);
};

export const listResetRequests = () => {
  return axiosInstance.get('/api/tenancy/super-admin/reset-requests/');
};

export const actOnResetRequest = (requestId, action) => {
  return axiosInstance.post(`/api/tenancy/super-admin/reset-requests/${requestId}/action/`, { action });
};

