import { useState, useEffect } from 'react';
import { getRecentActivity } from '../../api/dashboard';
import toast from 'react-hot-toast';
import { ClockIcon } from '@heroicons/react/24/outline';

const RecentActivity = () => {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchActivities();
  }, []);

  const fetchActivities = async () => {
    try {
      const response = await getRecentActivity({ limit: 50 });
      setActivities(response.data.results || response.data);
    } catch (error) {
      console.error('Error fetching activities:', error);
      toast.error('Failed to load recent activity');
    } finally {
      setLoading(false);
    }
  };

  const getActivityIcon = (type) => {
    const colors = {
      alert: 'bg-red-100 text-red-600',
      incident: 'bg-yellow-100 text-yellow-600',
      camera: 'bg-blue-100 text-blue-600',
      user: 'bg-green-100 text-green-600',
    };
    return colors[type] || 'bg-gray-100 text-gray-600';
  };

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-20 bg-gray-200 rounded-lg"></div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">Recent Activity</h1>

      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="divide-y divide-gray-200">
          {activities.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No recent activity
            </div>
          ) : (
            activities.map((activity, index) => (
              <div key={index} className="p-6 hover:bg-sand-light transition-colors">
                <div className="flex items-start space-x-4">
                  <div className={`p-2 rounded-lg ${getActivityIcon(activity.type)}`}>
                    <ClockIcon className="h-6 w-6" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">
                      {activity.title || activity.description}
                    </p>
                    <p className="text-sm text-gray-600 mt-1">
                      {activity.details || activity.message}
                    </p>
                    <p className="text-xs text-gray-500 mt-2">
                      {new Date(activity.timestamp || activity.created_at).toLocaleString()}
                    </p>
                  </div>
                  <span
                    className={`px-3 py-1 text-xs font-semibold rounded-full ${
                      activity.status === 'success'
                        ? 'bg-green-100 text-green-800'
                        : activity.status === 'warning'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {activity.type}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default RecentActivity;

