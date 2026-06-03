import { useState, useEffect } from 'react';
import { useRecoilValue } from 'recoil';
import { isAuthenticatedState } from '../../store/authStore';
import { getDashboardOverview } from '../../api/dashboard';
import StatsCard from '../../components/StatsCard';
import {
  VideoCameraIcon,
  BellAlertIcon,
  ExclamationTriangleIcon,
  UsersIcon,
  ArrowPathIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { Link } from 'react-router-dom';

const Overview = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const isAuthenticated = useRecoilValue(isAuthenticatedState);

  useEffect(() => {
    // Only fetch data if authenticated
    if (isAuthenticated) {
      fetchDashboardData();
    } else {
      setLoading(false);
    }
  }, [isAuthenticated]);

  const fetchDashboardData = async () => {
    try {
      const response = await getDashboardOverview();
      setData(response.data);
    } catch (error) {
      // Handle 401 gracefully - don't show error toast, let ProtectedRoute handle redirect
      if (error.response?.status === 401) {
        console.log('Unauthorized - redirecting to login');
        return;
      }
      console.error('Error fetching dashboard:', error);
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-32 skeleton rounded-xl"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-4xl font-bold text-dark-text-primary mb-2">
            Dashboard <span className="text-gradient-ai">Overview</span>
          </h1>
          <p className="text-dark-text-muted">Real-time system monitoring and analytics</p>
        </div>
        <button
          onClick={fetchDashboardData}
          className="flex items-center space-x-2 px-4 py-2 glass border border-dark-border rounded-lg
                   text-dark-text-primary hover:bg-dark-card hover:border-ai-blue/50
                   transition-all duration-200"
        >
          <ArrowPathIcon className="h-5 w-5" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="Total Cameras"
          value={data?.cameras?.total || 0}
          icon={VideoCameraIcon}
          color="bg-ai-blue"
          subtitle={`${data?.cameras?.online || 0} online`}
        />
        <StatsCard
          title="Active Alerts"
          value={data?.alerts?.active || 0}
          icon={BellAlertIcon}
          color="bg-red-500"
          subtitle={`${data?.alerts?.today || 0} today`}
        />
        <StatsCard
          title="Open Incidents"
          value={data?.incidents?.active || 0}
          icon={ExclamationTriangleIcon}
          color="bg-yellow-500"
          subtitle={`${data?.incidents?.resolved || 0} resolved`}
        />
        <StatsCard
          title="Total Personnel"
          value={data?.personnel?.total_users || 0}
          icon={UsersIcon}
          color="bg-green-500"
          subtitle={`${data?.personnel?.total_personnel || 0} personnel`}
        />
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
        <Link
          to="/alerts"
          className="group glass rounded-xl p-6 hover:shadow-glow-error transition-all duration-300 
                   border-l-4 border-status-error transform hover:scale-[1.02]"
        >
          <div className="flex items-center space-x-3 mb-3">
            <div className="w-12 h-12 bg-status-error/20 rounded-lg flex items-center justify-center">
              <BellAlertIcon className="h-6 w-6 text-status-error" />
            </div>
            <h3 className="text-lg font-semibold text-dark-text-primary group-hover:text-status-error transition-colors">
              View Alerts
            </h3>
          </div>
          <p className="text-dark-text-muted">Monitor and acknowledge security alerts</p>
        </Link>

        <Link
          to="/incidents"
          className="group glass rounded-xl p-6 hover:shadow-glow transition-all duration-300 
                   border-l-4 border-status-warning transform hover:scale-[1.02]"
        >
          <div className="flex items-center space-x-3 mb-3">
            <div className="w-12 h-12 bg-status-warning/20 rounded-lg flex items-center justify-center">
              <ExclamationTriangleIcon className="h-6 w-6 text-status-warning" />
            </div>
            <h3 className="text-lg font-semibold text-dark-text-primary group-hover:text-status-warning transition-colors">
              Manage Incidents
            </h3>
          </div>
          <p className="text-dark-text-muted">Track and resolve security incidents</p>
        </Link>

        <Link
          to="/cameras/control-room"
          className="group glass rounded-xl p-6 hover:shadow-glow-ai transition-all duration-300 
                   border-l-4 border-ai-blue transform hover:scale-[1.02]"
        >
          <div className="flex items-center space-x-3 mb-3">
            <div className="w-12 h-12 bg-ai-blue/20 rounded-lg flex items-center justify-center">
              <VideoCameraIcon className="h-6 w-6 text-ai-blue" />
            </div>
            <h3 className="text-lg font-semibold text-dark-text-primary group-hover:text-ai-blue transition-colors">
              Control Room
            </h3>
          </div>
          <p className="text-dark-text-muted">Monitor and manage surveillance cameras</p>
        </Link>
      </div>

      {/* System Status */}
      <div className="glass rounded-xl p-6 mt-6 border border-dark-border">
        <div className="flex items-center space-x-2 mb-6">
          <ChartBarIcon className="h-6 w-6 text-ai-blue" />
          <h2 className="text-xl font-semibold text-dark-text-primary">System Status</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="glass rounded-lg p-4 border border-status-success/30">
            <div className="flex items-center justify-between">
              <span className="text-dark-text-secondary text-sm">Cameras Online</span>
              <span className="text-2xl font-bold text-status-success">
                {data?.cameras?.online || 0}
              </span>
            </div>
            <div className="mt-2">
              <div className="h-2 bg-dark-card rounded-full overflow-hidden">
                <div
                  className="h-full bg-status-success rounded-full transition-all duration-500"
                  style={{ width: `${data?.cameras?.total ? (data.cameras.online / data.cameras.total * 100) : 0}%` }}
                />
              </div>
            </div>
          </div>
          <div className="glass rounded-lg p-4 border border-status-warning/30">
            <div className="flex items-center justify-between">
              <span className="text-dark-text-secondary text-sm">Pending Incidents</span>
              <span className="text-2xl font-bold text-status-warning">
                {data?.incidents?.active || 0}
              </span>
            </div>
            <p className="text-xs text-dark-text-muted mt-2">
              {data?.incidents?.resolved || 0} resolved
            </p>
          </div>
          <div className="glass rounded-lg p-4 border border-ai-blue/30">
            <div className="flex items-center justify-between">
              <span className="text-dark-text-secondary text-sm">Today's Alerts</span>
              <span className="text-2xl font-bold text-ai-blue">
                {data?.alerts?.today || 0}
              </span>
            </div>
            <p className="text-xs text-dark-text-muted mt-2">
              {data?.alerts?.this_week || 0} this week
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Overview;
