import { useState, useEffect } from 'react';
import { listIncidents, updateIncidentStatus } from '../../api/incidents';
import { useNavigate } from 'react-router-dom';
import IncidentCard from '../../components/IncidentCard';
import toast from 'react-hot-toast';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

const MyIncidents = () => {
  const navigate = useNavigate();
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);

  // Log when component mounts
  console.log('🚀 [MyIncidents] Component mounted/rendered');

  useEffect(() => {
    console.log('🎯 [MyIncidents] useEffect triggered');
    fetchMyIncidents();
  }, []);

  const fetchMyIncidents = async () => {
    setLoading(true);
    console.log('🔍 [MyIncidents] Fetching my incidents...');
    try {
      // CORRECTED: Use listIncidents with my_incidents=true query param
      const response = await listIncidents({ my_incidents: true });
      console.log('✅ [MyIncidents] Response received:', response.data);
      
      // Backend returns paginated response: {count, next, previous, results: []}
      const incidentsList = response.data.results || response.data;
      console.log('📊 [MyIncidents] Number of incidents:', incidentsList.length);
      setIncidents(incidentsList);
      
      if (incidentsList.length === 0) {
        console.log('ℹ️ [MyIncidents] No incidents found - showing empty state');
      }
    } catch (error) {
      console.error('❌ [MyIncidents] Error fetching incidents:', error);
      console.error('❌ [MyIncidents] Error details:', error.response?.data);
      console.error('❌ [MyIncidents] Error status:', error.response?.status);
      toast.error('Failed to load your incidents');
    } finally {
      setLoading(false);
      console.log('🏁 [MyIncidents] Loading complete');
    }
  };

  console.log('🖼️ [MyIncidents] About to render, loading:', loading, 'incidents count:', incidents.length);
  
  return (
    <div className="space-y-6">
      {/* Always visible header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-dark-text-primary">My Assigned Incidents</h1>
        <button
          onClick={fetchMyIncidents}
          className="px-4 py-2 bg-ai-blue text-white rounded-md hover:bg-ai-blueDark transition-colors font-semibold"
        >
          Refresh
        </button>
      </div>

      {/* Incidents Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          [...Array(3)].map((_, i) => (
            <div key={i} className="h-48 bg-dark-card rounded-lg animate-pulse border border-dark-border"></div>
          ))
        ) : incidents.length === 0 ? (
          <div className="col-span-3 text-center py-12 glass rounded-xl border border-dark-border">
            <ExclamationTriangleIcon className="h-16 w-16 text-dark-text-muted mx-auto mb-4 opacity-50" />
            <p className="text-dark-text-primary text-xl font-semibold">No incidents assigned to you</p>
            <p className="text-dark-text-secondary mt-2">You'll see your assigned incidents here once they are assigned by an administrator.</p>
            <p className="text-dark-text-muted text-sm mt-4">
              To test: Login as Admin → Create Incident → Assign to Guard
            </p>
          </div>
        ) : (
          incidents.map((incident) => (
            <IncidentCard
              key={incident.id}
              incident={incident}
              onClick={() => navigate(`/incidents/${incident.id}`)}
            />
          ))
        )}
      </div>
    </div>
  );
};

export default MyIncidents;

