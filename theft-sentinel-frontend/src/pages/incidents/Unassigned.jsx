import { useState, useEffect } from 'react';
import { listIncidents, assignIncident } from '../../api/incidents';
import { listPersonnel } from '../../api/personnel';
import { useNavigate } from 'react-router-dom';
import IncidentCard from '../../components/IncidentCard';
import toast from 'react-hot-toast';

const Unassigned = () => {
  const navigate = useNavigate();
  const [incidents, setIncidents] = useState([]);
  const [guards, setGuards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [selectedGuard, setSelectedGuard] = useState('');
  const [assigning, setAssigning] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [incidentsRes, personnelRes] = await Promise.all([
        // CORRECTED: Use listIncidents with status filter
        listIncidents({ status: 'CREATED' }), // CREATED = unassigned
        // CORRECTED: Use listPersonnel and filter for guards
        listPersonnel(),
      ]);
      setIncidents(incidentsRes.data);
      // Filter for guards only
      setGuards(personnelRes.data.filter(p => p.role === 'SECURITY_GUARD' || p.user?.role === 'SECURITY_GUARD'));
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load unassigned incidents');
    } finally {
      setLoading(false);
    }
  };

  const handleAssign = async () => {
    if (!selectedGuard) {
      toast.error('Please select a guard');
      return;
    }

    setAssigning(true);
    try {
      // CORRECTED: assignIncident now takes (id, assigned_to, notes)
      await assignIncident(selectedIncident.id, selectedGuard, 'Assigned from unassigned list');
      toast.success('Incident assigned successfully');
      setSelectedIncident(null);
      setSelectedGuard('');
      fetchData();
    } catch (error) {
      console.error('Error assigning incident:', error);
      toast.error('Failed to assign incident');
    } finally {
      setAssigning(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Unassigned Incidents</h1>
        <button
          onClick={fetchData}
          className="px-4 py-2 bg-primary text-white rounded-md hover:bg-secondary transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Incidents Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          [...Array(3)].map((_, i) => (
            <div key={i} className="h-48 bg-gray-200 rounded-lg animate-pulse"></div>
          ))
        ) : incidents.length === 0 ? (
          <div className="col-span-3 text-center py-12">
            <p className="text-gray-500 text-lg">No unassigned incidents</p>
            <p className="text-gray-400 mt-2">All incidents have been assigned</p>
          </div>
        ) : (
          incidents.map((incident) => (
            <div key={incident.id} className="relative">
              <IncidentCard
                incident={incident}
                onClick={() => navigate(`/incidents/${incident.id}`)}
              />
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedIncident(incident);
                }}
                className="absolute top-2 right-2 px-3 py-1 bg-blue-500 text-white rounded-md hover:bg-blue-600 text-sm"
              >
                Assign
              </button>
            </div>
          ))
        )}
      </div>

      {/* Assignment Modal */}
      {selectedIncident && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Assign Incident</h2>
            <p className="text-gray-600 mb-4">
              Assigning: <span className="font-semibold">{selectedIncident.incident_type}</span>
            </p>
            
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Guard
              </label>
              <select
                value={selectedGuard}
                onChange={(e) => setSelectedGuard(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary focus:border-primary"
              >
                <option value="">-- Select a Guard --</option>
                {guards.map((guard) => (
                  <option key={guard.id} value={guard.id}>
                    {guard.name || guard.user_name} - {guard.badge_number || 'N/A'}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex space-x-4">
              <button
                onClick={() => {
                  setSelectedIncident(null);
                  setSelectedGuard('');
                }}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAssign}
                disabled={assigning || !selectedGuard}
                className="flex-1 px-4 py-2 bg-primary text-white rounded-md hover:bg-secondary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {assigning ? 'Assigning...' : 'Assign'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Unassigned;

