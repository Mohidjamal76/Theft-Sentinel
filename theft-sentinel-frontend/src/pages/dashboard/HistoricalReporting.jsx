import { useState, useEffect, useCallback, useRef } from 'react';
import { getRealTimeAnalytics, getHistoricalAlerts, exportAlertReport } from '../../api/dashboard';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import toast from 'react-hot-toast';
import {
  BellAlertIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  VideoCameraIcon,
  ArrowDownTrayIcon,
} from '@heroicons/react/24/outline';
import StatsCard from '../../components/StatsCard';

const HistoricalReporting = () => {
  const [realTimeData, setRealTimeData] = useState(null);
  const [historicalData, setHistoricalData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [historicalLoading, setHistoricalLoading] = useState(true);
  const [period, setPeriod] = useState('daily');
  const [days, setDays] = useState(30);
  const [exporting, setExporting] = useState(false);
  
  // Use refs to track mounted state and interval
  const mountedRef = useRef(true);
  const intervalRef = useRef(null);

  // Memoize fetchRealTimeData to prevent unnecessary re-renders
  const fetchRealTimeData = useCallback(async () => {
    if (!mountedRef.current) return;
    
    try {
      const response = await getRealTimeAnalytics();
      if (mountedRef.current) {
        setRealTimeData(response.data);
        setLoading(false);
      }
    } catch (error) {
      // Handle 401 gracefully - don't show error toast, let ProtectedRoute handle redirect
      if (error.response?.status === 401) {
        console.log('Unauthorized - redirecting to login');
        return;
      }
      if (mountedRef.current) {
        console.error('Error fetching real-time analytics:', error);
        toast.error('Failed to load real-time analytics');
        setLoading(false);
      }
    }
  }, []);

  // Auto-refresh real-time data every 30 seconds (reasonable polling interval)
  // Reduced from 5 seconds to prevent excessive API calls and improve performance
  useEffect(() => {
    mountedRef.current = true;
    
    // Initial fetch
    fetchRealTimeData();
    
    // Set up polling interval - 30 seconds is a good balance for historical reporting
    // Historical data doesn't need sub-second updates
    intervalRef.current = setInterval(() => {
      if (mountedRef.current) {
        fetchRealTimeData();
      }
    }, 30000); // Refresh every 30 seconds (30000 milliseconds)

    // Cleanup function - CRITICAL to prevent memory leaks and infinite loops
    return () => {
      mountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [fetchRealTimeData]);

  // Memoize fetchHistoricalData to prevent unnecessary re-renders
  const fetchHistoricalData = useCallback(async () => {
    if (!mountedRef.current) return;
    
    setHistoricalLoading(true);
    try {
      const response = await getHistoricalAlerts({ period, days });
      if (mountedRef.current) {
        setHistoricalData(response.data);
      }
    } catch (error) {
      // Handle 401 gracefully
      if (error.response?.status === 401) {
        console.log('Unauthorized - redirecting to login');
        return;
      }
      if (mountedRef.current) {
        console.error('Error fetching historical data:', error);
        toast.error('Failed to load historical alert data');
      }
    } finally {
      if (mountedRef.current) {
        setHistoricalLoading(false);
      }
    }
  }, [period, days]);

  // Fetch historical data when period or days change
  useEffect(() => {
    fetchHistoricalData();
  }, [fetchHistoricalData]);

  const handleExport = async (format) => {
    setExporting(true);
    try {
      const response = await exportAlertReport({ format, days, period });
      
      // Check HTTP status
      if (response.status < 200 || response.status >= 300) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      // Check if response is actually an error (blob with error message)
      if (response.data instanceof Blob) {
        // For small blobs, check if it might be an error message
        if (response.data.size < 1000) {
          const text = await response.data.text();
          // Check if it's JSON error or HTML error page
          try {
            const errorData = JSON.parse(text);
            if (errorData.error || errorData.detail) {
              toast.error(`Export failed: ${errorData.error || errorData.detail}`);
              return;
            }
          } catch (e) {
            // Not JSON, might be HTML error page or actual small file
            if (text.includes('404') || text.includes('Not Found')) {
              toast.error('Export endpoint not found. Please restart the Django server to load the new endpoint.');
              return;
            }
            // If it's a small valid file, continue with download
          }
        }
        
        // Create blob and download
        const blob = new Blob([response.data], {
          type: format === 'pdf' ? 'application/pdf' : 'text/csv'
        });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `alert_report_${period}_${days}days_${new Date().toISOString().split('T')[0]}.${format}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        
        toast.success(`${format.toUpperCase()} report downloaded successfully`);
      } else {
        // Response is not a blob, might be JSON error
        if (response.data?.error) {
          toast.error(`Export failed: ${response.data.error}`);
        } else {
          toast.error('Unexpected response format from server');
        }
      }
    } catch (error) {
      console.error('Error exporting report:', error);
      
      // Handle different error types
      if (error.response) {
        // Server responded with error status
        const status = error.response.status;
        
        if (status === 404) {
          toast.error('Export endpoint not found. Please restart the Django server to load the new endpoint.');
        } else if (status === 403) {
          toast.error('You do not have permission to export reports.');
        } else if (status === 500) {
          // Try to extract error message
          if (error.response.data instanceof Blob) {
            try {
              const text = await error.response.data.text();
              const errorData = JSON.parse(text);
              toast.error(`Export failed: ${errorData.error || errorData.detail || 'Server error'}`);
            } catch (e) {
              toast.error('Server error during export. Please check server logs.');
            }
          } else if (error.response.data?.error) {
            toast.error(`Export failed: ${error.response.data.error}`);
          } else {
            toast.error('Server error during export. Please check server logs.');
          }
        } else {
          // Try to extract error message from response
          if (error.response.data instanceof Blob) {
            try {
              const text = await error.response.data.text();
              const errorData = JSON.parse(text);
              toast.error(`Export failed: ${errorData.error || errorData.detail || `HTTP ${status}`}`);
            } catch (e) {
              toast.error(`Export failed: HTTP ${status} ${error.response.statusText}`);
            }
          } else {
            toast.error(`Export failed: HTTP ${status} ${error.response.statusText}`);
          }
        }
      } else if (error.request) {
        // Request was made but no response received
        toast.error('No response from server. Please check if the server is running.');
      } else {
        // Error setting up request
        toast.error(`Export failed: ${error.message || 'Unknown error'}`);
      }
    } finally {
      setExporting(false);
    }
  };

  const getHealthColor = (status) => {
    switch (status) {
      case 'EXCELLENT':
        return 'text-status-success';
      case 'GOOD':
        return 'text-status-success';
      case 'DEGRADED':
        return 'text-status-warning';
      case 'CRITICAL':
        return 'text-status-error';
      case 'POOR':
        return 'text-status-error';
      case 'OK':
        return 'text-status-success';
      case 'WARNING':
        return 'text-status-warning';
      case 'OFFLINE':
        return 'text-status-error';
      default:
        return 'text-dark-text-muted';
    }
  };

  const getHealthBgColor = (status) => {
    switch (status) {
      case 'EXCELLENT':
        return 'bg-status-success/20 border-status-success/50';
      case 'GOOD':
        return 'bg-status-success/20 border-status-success/50';
      case 'DEGRADED':
        return 'bg-status-warning/20 border-status-warning/50';
      case 'CRITICAL':
        return 'bg-status-error/20 border-status-error/50';
      case 'POOR':
        return 'bg-status-error/20 border-status-error/50';
      case 'OK':
        return 'bg-status-success/20 border-status-success/50';
      case 'WARNING':
        return 'bg-status-warning/20 border-status-warning/50';
      case 'OFFLINE':
        return 'bg-status-error/20 border-status-error/50';
      default:
        return 'bg-dark-card border-dark-border';
    }
  };

  const getHealthIcon = (status) => {
    switch (status) {
      case 'EXCELLENT':
      case 'GOOD':
      case 'OK':
        return <CheckCircleIcon className="h-8 w-8 text-status-success" />;
      case 'DEGRADED':
      case 'WARNING':
        return <ExclamationTriangleIcon className="h-8 w-8 text-status-warning" />;
      case 'CRITICAL':
      case 'POOR':
      case 'OFFLINE':
        return <XCircleIcon className="h-8 w-8 text-status-error" />;
      default:
        return <ExclamationTriangleIcon className="h-8 w-8 text-dark-text-muted" />;
    }
  };

  // Calculate trend from chart data (last two comparable periods with actual data)
  const calculateTrendFromChartData = (data) => {
    if (!data || !Array.isArray(data) || data.length < 2) {
      return 'stable';
    }
    
    // Ensure data is sorted chronologically (oldest to newest)
    // Backend returns reversed data, but we'll ensure it's sorted by date/month
    const sortedData = [...data].sort((a, b) => {
      // Sort by date field (daily), week_start (weekly), or month (monthly)
      const dateA = a.date || a.week_start || a.month || '';
      const dateB = b.date || b.week_start || b.month || '';
      return dateA.localeCompare(dateB);
    });
    
    // Filter out trailing zero-only periods, keeping only periods with actual alerts
    // Work backwards from the end to find the last period with data
    let lastValidIndex = sortedData.length - 1;
    while (lastValidIndex >= 0 && (sortedData[lastValidIndex]?.count || 0) === 0) {
      lastValidIndex--;
    }
    
    // Need at least two periods with data to calculate trend
    if (lastValidIndex < 1) {
      return 'stable';
    }
    
    // Get the last two periods that have actual data (skip trailing zeros)
    const latest = sortedData[lastValidIndex];
    const previous = sortedData[lastValidIndex - 1];
    
    // Compare total alerts (count) between latest and previous valid period
    const latestCount = latest?.count || 0;
    const previousCount = previous?.count || 0;
    
    if (latestCount > previousCount) {
      return 'increasing';
    } else if (latestCount < previousCount) {
      return 'decreasing';
    } else {
      return 'stable';
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
            Historical <span className="text-gradient-ai">Data Reporting</span>
          </h1>
          <p className="text-dark-text-muted">Real-time monitoring and historical alert analysis</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleExport('csv')}
            disabled={exporting}
            className="px-4 py-2 bg-status-success text-dark-bg rounded-lg hover:bg-status-success/90 
                     transition-all duration-200 disabled:opacity-50 flex items-center gap-2
                     font-semibold shadow-glow-success hover:shadow-glow-success"
          >
            <ArrowDownTrayIcon className="h-5 w-5" />
            Export CSV
          </button>
          <button
            onClick={() => handleExport('pdf')}
            disabled={exporting}
            className="px-4 py-2 bg-status-error text-dark-bg rounded-lg hover:bg-status-error/90 
                     transition-all duration-200 disabled:opacity-50 flex items-center gap-2
                     font-semibold shadow-glow-error hover:shadow-glow-error"
          >
            <ArrowDownTrayIcon className="h-5 w-5" />
            Export PDF
          </button>
        </div>
      </div>

      {/* Real-Time Analytics Panel */}
      <div className="glass rounded-xl p-6 border border-dark-border">
        <h2 className="text-xl font-semibold text-dark-text-primary mb-4">Real-Time Analytics</h2>
        
        {/* Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <StatsCard
            title="Active Alerts"
            value={realTimeData?.active_alerts || 0}
            icon={BellAlertIcon}
            color="bg-red-500"
          />
          <div className={`glass p-6 rounded-xl border-l-4 ${getHealthBgColor(realTimeData?.system_health?.status)}`}>
            <h3 className="text-sm font-medium text-dark-text-muted uppercase tracking-wider mb-2">System Health</h3>
            <div className="flex items-center gap-3 mt-2">
              {getHealthIcon(realTimeData?.system_health?.status)}
              <div>
                <p className={`text-2xl font-bold ${getHealthColor(realTimeData?.system_health?.status)}`}>
                  {realTimeData?.system_health?.status || 'UNKNOWN'}
                </p>
                <p className="text-sm text-dark-text-secondary mt-1">{realTimeData?.system_health?.message || ''}</p>
                {realTimeData?.system_health?.online_cameras !== undefined && (
                  <p className="text-xs text-dark-text-muted mt-1">
                    {realTimeData.system_health.online_cameras}/{realTimeData.system_health.total_cameras} cameras online
                  </p>
                )}
              </div>
            </div>
          </div>
          <StatsCard
            title="Online Cameras"
            value={`${realTimeData?.system_health?.online_cameras || 0}/${realTimeData?.system_health?.total_cameras || 0}`}
            icon={VideoCameraIcon}
            color="bg-ai-blue"
          />
        </div>

        {/* Camera Feeds Status */}
        <div className="mt-6">
          <h3 className="text-lg font-semibold text-dark-text-primary mb-3">Camera Feeds Status</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {realTimeData?.camera_feeds?.map((camera) => (
              <div
                key={camera.id}
                className={`glass p-4 rounded-lg border-l-4 transition-all duration-200 hover:scale-[1.02] ${
                  camera.is_online 
                    ? 'border-status-success bg-status-success/10' 
                    : 'border-status-error bg-status-error/10'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-dark-text-primary">{camera.name}</p>
                    <p className="text-sm text-dark-text-secondary">{camera.location}</p>
                    <p className="text-xs text-dark-text-muted mt-1">Zone: {camera.zone}</p>
                  </div>
                  <div className={`px-3 py-1 rounded-full text-xs font-semibold ${
                    camera.is_online 
                      ? 'bg-status-success/20 text-status-success border border-status-success/50' 
                      : 'bg-status-error/20 text-status-error border border-status-error/50'
                  }`}>
                    {camera.status}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Historical Alert Reporting */}
      <div className="glass rounded-xl p-6 border border-dark-border">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-dark-text-primary">Historical Alert Reporting</h2>
          <div className="flex gap-2">
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="px-3 py-2 bg-dark-card border border-dark-border rounded-lg text-dark-text-primary
                       focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent
                       transition-all duration-200"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="px-3 py-2 bg-dark-card border border-dark-border rounded-lg text-dark-text-primary
                       focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent
                       transition-all duration-200"
            >
              <option value="7">Last 7 days</option>
              <option value="30">Last 30 days</option>
              <option value="60">Last 60 days</option>
              <option value="90">Last 90 days</option>
            </select>
          </div>
        </div>

        {historicalLoading ? (
          <div className="h-96 skeleton rounded-lg"></div>
        ) : (
          <>
            {/* Summary Cards */}
            {historicalData?.summary && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className="glass p-4 rounded-lg border-l-4 border-ai-blue">
                  <h3 className="text-sm font-medium text-dark-text-muted uppercase tracking-wider">Total Alerts</h3>
                  <p className="text-3xl font-bold text-dark-text-primary mt-2">{historicalData.summary.total_alerts}</p>
                </div>
                <div className="glass p-4 rounded-lg border-l-4 border-status-success">
                  <h3 className="text-sm font-medium text-dark-text-muted uppercase tracking-wider">Resolved</h3>
                  <p className="text-3xl font-bold text-status-success mt-2">{historicalData.summary.resolved}</p>
                </div>
                <div className="glass p-4 rounded-lg border-l-4 border-status-warning">
                  <h3 className="text-sm font-medium text-dark-text-muted uppercase tracking-wider">Active</h3>
                  <p className="text-3xl font-bold text-status-warning mt-2">{historicalData.summary.active}</p>
                </div>
                <div className="glass p-4 rounded-lg border-l-4 border-ai-purple">
                  <h3 className="text-sm font-medium text-dark-text-muted uppercase tracking-wider">Trend</h3>
                  <p className="text-2xl font-bold text-dark-text-primary mt-2 capitalize">
                    {historicalData?.data ? calculateTrendFromChartData(historicalData.data) : 'N/A'}
                  </p>
                </div>
              </div>
            )}

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Line Chart - Alert Trends */}
              <div className="glass p-6 rounded-xl border border-dark-border">
                <h3 className="text-lg font-semibold text-dark-text-primary mb-4">
                  Alert Trends ({period.charAt(0).toUpperCase() + period.slice(1)})
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={historicalData?.data || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis 
                      dataKey={period === 'daily' ? 'date' : period === 'weekly' ? 'week_start' : 'month'}
                      angle={-45}
                      textAnchor="end"
                      height={80}
                      stroke="#9CA3AF"
                      tick={{ fill: '#9CA3AF' }}
                    />
                    <YAxis stroke="#9CA3AF" tick={{ fill: '#9CA3AF' }} />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: '#1F2933', 
                        border: '1px solid #374151',
                        borderRadius: '8px',
                        color: '#F9FAFB'
                      }}
                    />
                    <Legend wrapperStyle={{ color: '#D1D5DB' }} />
                    <Line 
                      type="monotone" 
                      dataKey="count" 
                      stroke="#00D9FF" 
                      strokeWidth={2}
                      name="Total Alerts"
                      dot={{ fill: '#00D9FF', r: 4 }}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="resolved" 
                      stroke="#10B981" 
                      strokeWidth={2}
                      name="Resolved"
                      dot={{ fill: '#10B981', r: 4 }}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="active" 
                      stroke="#F59E0B" 
                      strokeWidth={2}
                      name="Active"
                      dot={{ fill: '#F59E0B', r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Bar Chart - Alert Counts */}
              <div className="glass p-6 rounded-xl border border-dark-border">
                <h3 className="text-lg font-semibold text-dark-text-primary mb-4">
                  Alert Counts ({period.charAt(0).toUpperCase() + period.slice(1)})
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={historicalData?.data || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis 
                      dataKey={period === 'daily' ? 'date' : period === 'weekly' ? 'week_start' : 'month'}
                      angle={-45}
                      textAnchor="end"
                      height={80}
                      stroke="#9CA3AF"
                      tick={{ fill: '#9CA3AF' }}
                    />
                    <YAxis stroke="#9CA3AF" tick={{ fill: '#9CA3AF' }} />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: '#1F2933', 
                        border: '1px solid #374151',
                        borderRadius: '8px',
                        color: '#F9FAFB'
                      }}
                    />
                    <Legend wrapperStyle={{ color: '#D1D5DB' }} />
                    <Bar dataKey="count" fill="#00D9FF" name="Total" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="resolved" fill="#10B981" name="Resolved" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="active" fill="#F59E0B" name="Active" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Data Table */}
            <div className="mt-6">
              <h3 className="text-lg font-semibold text-dark-text-primary mb-4">Alert Summary Table</h3>
              <div className="overflow-x-auto rounded-lg border border-dark-border">
                <table className="min-w-full divide-y divide-dark-border">
                  <thead className="bg-dark-card">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-dark-text-muted uppercase tracking-wider">
                        {period === 'daily' ? 'Date' : period === 'weekly' ? 'Week' : 'Month'}
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-dark-text-muted uppercase tracking-wider">
                        Total
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-dark-text-muted uppercase tracking-wider">
                        Resolved
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-dark-text-muted uppercase tracking-wider">
                        Active
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-dark-surface divide-y divide-dark-border">
                    {historicalData?.data?.slice().reverse().map((item, index) => (
                      <tr key={index} className="hover:bg-dark-card transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-dark-text-primary">
                          {period === 'daily' 
                            ? item.date 
                            : period === 'weekly' 
                            ? `${item.week_start} to ${item.week_end}`
                            : item.month_name || item.month
                          }
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-dark-text-primary font-medium">{item.count}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-status-success font-medium">{item.resolved}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-status-warning font-medium">{item.active}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default HistoricalReporting;

