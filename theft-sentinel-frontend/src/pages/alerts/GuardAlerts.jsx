import { useState, useEffect, useCallback } from 'react';
import { listAlerts } from '../../api/alerts';
import { useNavigate } from 'react-router-dom';
import { useRecoilValue } from 'recoil';
import { isAuthenticatedState } from '../../store/authStore';
import AlertCard from '../../components/AlertCard';
import { BellAlertIcon, CheckCircleIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';

/**
 * Guard Alerts Page - read-only real-time alert view.
 */
const GuardAlerts = () => {
  const navigate = useNavigate();
  const isAuthenticated = useRecoilValue(isAuthenticatedState);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    search: '',
    severity: '',
    status: '', // ACTIVE, ACKED, RESOLVED
  });

  // Memoize fetch function
  const fetchAlerts = useCallback(async () => {
    if (!isAuthenticated) return;
    
    setLoading(true);
    try {
      // Build query params - only include non-empty values
      const params = {};
      if (filters.search) params.search = filters.search;
      if (filters.severity) params.severity = filters.severity;
      if (filters.status === 'ACKED') {
        params.acknowledged = 'true';
      } else if (filters.status === 'ACTIVE') {
        params.acknowledged = 'false';
      }
      // If status is empty or RESOLVED, don't pass acknowledged param to get all alerts
      
      const response = await listAlerts(params);
      // Handle both paginated and non-paginated responses
      const alertsData = response.data?.results || response.data || [];
      setAlerts(Array.isArray(alertsData) ? alertsData : []);
    } catch (error) {
      // Handle 401 gracefully
      if (error.response?.status === 401) {
        console.log('Unauthorized - redirecting to login');
        return;
      }
      console.error('Error fetching alerts:', error);
      console.error('Error response:', error.response?.data);
      toast.error('Failed to load alerts');
      setAlerts([]); // Ensure alerts array is empty on error
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, filters.search, filters.severity, filters.status]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  // Auto-refresh alerts every 15 seconds
  useEffect(() => {
    if (!isAuthenticated) return;
    
    const interval = setInterval(() => {
      fetchAlerts();
    }, 15000); // 15 seconds for real-time alerts

    return () => clearInterval(interval);
  }, [fetchAlerts, isAuthenticated]);

  const handleViewAlert = (alert) => {
    navigate(`/alerts/${alert.id}`);
  };

  // Filter alerts
  const filteredAlerts = alerts.filter((alert) => {
    const matchesSearch = !filters.search || 
      alert.alert_type?.toLowerCase().includes(filters.search.toLowerCase()) ||
      alert.camera_name?.toLowerCase().includes(filters.search.toLowerCase());
    const matchesSeverity = !filters.severity || alert.severity?.toUpperCase() === filters.severity;
    const matchesStatus = !filters.status || alert.status === filters.status;
    return matchesSearch && matchesSeverity && matchesStatus;
  });

  // Count stats
  const activeAlerts = alerts.filter(a => a.status === 'ACTIVE').length;
  const acknowledgedAlerts = alerts.filter(a => a.status === 'ACKED').length;
  const highAlerts = alerts.filter(a => a.severity?.toUpperCase() === 'HIGH' && a.status === 'ACTIVE').length;

  if (loading && alerts.length === 0) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-48 skeleton rounded-xl"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-4xl font-bold text-dark-text-primary mb-2">
            Security <span className="text-gradient-ai">Alerts</span>
          </h1>
          <p className="text-dark-text-muted">Real-time alerts and notifications</p>
        </div>
        <button
          onClick={fetchAlerts}
          className="glass px-4 py-2 rounded-lg border border-dark-border text-dark-text-primary hover:bg-dark-card hover:border-ai-blue/50 transition-all duration-200 flex items-center gap-2"
        >
          <ArrowPathIcon className="h-5 w-5" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass p-4 rounded-xl border border-dark-border border-l-4 border-status-error">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-dark-text-muted mb-1">Active Alerts</p>
              <p className="text-2xl font-bold text-status-error">{activeAlerts}</p>
            </div>
            <BellAlertIcon className="h-8 w-8 text-status-error opacity-50" />
          </div>
        </div>
        <div className="glass p-4 rounded-xl border border-dark-border border-l-4 border-status-warning">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-dark-text-muted mb-1">High</p>
              <p className="text-2xl font-bold text-status-warning">{highAlerts}</p>
            </div>
            <div className="w-3 h-3 bg-status-warning rounded-full animate-pulse" />
          </div>
        </div>
        <div className="glass p-4 rounded-xl border border-dark-border border-l-4 border-status-success">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-dark-text-muted mb-1">Acknowledged</p>
              <p className="text-2xl font-bold text-status-success">{acknowledgedAlerts}</p>
            </div>
            <CheckCircleIcon className="h-8 w-8 text-status-success opacity-50" />
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="glass p-4 rounded-xl border border-dark-border">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <input
            type="text"
            placeholder="Search alerts..."
            value={filters.search}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            className="px-4 py-2 bg-dark-card border border-dark-border rounded-lg text-dark-text-primary placeholder-dark-text-muted focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent transition-all duration-200"
          />
          <select
            value={filters.severity}
            onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
            className="px-4 py-2 bg-dark-card border border-dark-border rounded-lg text-dark-text-primary focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent transition-all duration-200"
          >
            <option value="">All Severity</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
          </select>
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            className="px-4 py-2 bg-dark-card border border-dark-border rounded-lg text-dark-text-primary focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent transition-all duration-200"
          >
            <option value="">All Status</option>
            <option value="ACTIVE">Active</option>
            <option value="ACKED">Acknowledged</option>
            <option value="RESOLVED">Resolved</option>
          </select>
        </div>
      </div>

      {/* Alerts Grid */}
      {filteredAlerts.length === 0 ? (
        <div className="glass p-12 rounded-xl border border-dark-border text-center">
          <BellAlertIcon className="h-16 w-16 text-dark-text-muted mx-auto mb-4 opacity-50" />
          <h3 className="text-xl font-semibold text-dark-text-primary mb-2">No Alerts Found</h3>
          <p className="text-dark-text-muted">All clear! No active alerts at this time.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredAlerts.map((alert) => (
            <div key={alert.id} className="relative">
              <AlertCard
                alert={alert}
                onClick={() => handleViewAlert(alert)}
                showDelete={false} // Guards cannot delete
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default GuardAlerts;

