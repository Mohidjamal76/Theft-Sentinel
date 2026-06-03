import axiosInstance from './axios';

// Get dashboard overview
export const getDashboardOverview = (params = {}) => {
  return axiosInstance.get('/api/dashboard/overview/', { params });
};

// Get alert statistics
export const getAlertStats = (params = {}) => {
  return axiosInstance.get('/api/dashboard/alerts-stats/', { params });
};

// Get incident statistics
export const getIncidentStats = (params = {}) => {
  return axiosInstance.get('/api/dashboard/incidents-stats/', { params });
};

// Get camera statistics
export const getCameraStats = (params = {}) => {
  return axiosInstance.get('/api/dashboard/cameras-stats/', { params });
};

// Get recent activity
export const getRecentActivity = (params = {}) => {
  return axiosInstance.get('/api/dashboard/recent-activity/', { params });
};

// Get system health (if needed, otherwise remove)
export const getSystemHealth = (params = {}) => {
  return axiosInstance.get('/api/dashboard/overview/', { params });
};

// Get real-time analytics
export const getRealTimeAnalytics = (params = {}) => {
  return axiosInstance.get('/api/dashboard/realtime-analytics/', { params });
};

// Get historical alert reporting data (ALERTS ONLY - no incidents)
export const getHistoricalAlerts = (params = {}) => {
  return axiosInstance.get('/api/dashboard/historical-alerts/', { params });
};

// Export alert reports (ALERTS ONLY - no incidents)
export const exportAlertReport = (params = {}) => {
  // Use 'export_type' instead of 'format' to avoid DRF format negotiation
  const { format, ...restParams } = params;
  return axiosInstance.get('/api/dashboard/export-alerts/', {
    params: {
      ...restParams,
      export_type: format || 'csv', // Map 'format' to 'export_type'
    },
    responseType: 'blob', // Required for binary file downloads
  });
};

