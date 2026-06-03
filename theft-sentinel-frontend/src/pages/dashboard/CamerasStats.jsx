import { useState, useEffect } from 'react';
import { getCameraStats } from '../../api/dashboard';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import toast from 'react-hot-toast';

const COLORS = ['#10B981', '#EF4444', '#F59E0B'];

const CamerasStats = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await getCameraStats();
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching camera stats:', error);
      toast.error('Failed to load camera statistics');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="animate-pulse h-96 bg-gray-200 rounded-lg"></div>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">Camera Statistics</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-green-500">
          <h3 className="text-sm font-medium text-gray-600">Active Cameras</h3>
          <p className="text-3xl font-bold text-green-600 mt-2">{stats?.active || 0}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-red-500">
          <h3 className="text-sm font-medium text-gray-600">Inactive Cameras</h3>
          <p className="text-3xl font-bold text-red-600 mt-2">{stats?.inactive || 0}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-yellow-500">
          <h3 className="text-sm font-medium text-gray-600">Maintenance</h3>
          <p className="text-3xl font-bold text-yellow-600 mt-2">{stats?.maintenance || 0}</p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status Distribution */}
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Status Distribution</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={stats?.status_distribution || []}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={(entry) => `${entry.name}: ${entry.value}`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {(stats?.status_distribution || []).map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Cameras by Zone */}
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Cameras by Zone</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={stats?.by_zone || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="zone" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="count" fill="#1B3C53" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Uptime */}
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">System Uptime</h2>
        <div className="text-center py-8">
          <p className="text-5xl font-bold text-green-600">
            {stats?.uptime_percentage || '99.9'}%
          </p>
          <p className="text-gray-600 mt-2">Overall system uptime</p>
        </div>
      </div>
    </div>
  );
};

export default CamerasStats;

