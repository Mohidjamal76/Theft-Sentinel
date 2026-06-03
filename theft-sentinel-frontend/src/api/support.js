import axiosInstance from './axios';

export const listMyQueries = () => axiosInstance.get('/api/support/me/');
export const createMyQuery = (message) => axiosInstance.post('/api/support/me/', { message });
export const deleteMyAnsweredQuery = (id) => axiosInstance.delete(`/api/support/me/${id}/`);

export const listBranchAdminPendingQueries = () => axiosInstance.get('/api/support/branch-admin/pending/');
export const listBranchAdminAnsweredQueries = () => axiosInstance.get('/api/support/branch-admin/answered/');
export const deleteBranchAdminAnsweredQuery = (id) =>
  axiosInstance.delete(`/api/support/branch-admin/answered/${id}/`);
export const branchAdminQueryAction = (id, action) =>
  axiosInstance.post(`/api/support/branch-admin/${id}/action/`, { action });

export const listSuperAdminPendingQueries = () => axiosInstance.get('/api/support/super-admin/pending/');
export const answerSuperAdminQuery = (id, answer) => axiosInstance.post(`/api/support/super-admin/${id}/`, { answer });
export const deleteAnsweredSuperAdminQuery = (id) => axiosInstance.delete(`/api/support/super-admin/${id}/`);

