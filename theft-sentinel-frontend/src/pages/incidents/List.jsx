import { useState, useEffect } from 'react';
import { listIncidents } from '../../api/incidents';
import { useNavigate } from 'react-router-dom';
import IncidentCard from '../../components/IncidentCard';
import { Pagination } from '../../components/Table';
import toast from 'react-hot-toast';

const List = () => {
  const navigate = useNavigate();
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filters, setFilters] = useState({
    search: '',
    status: '',
    priority: '',
  });

  useEffect(() => {
    fetchIncidents();
  }, [currentPage, filters]);

  const fetchIncidents = async () => {
    setLoading(true);
    try {
      // Map frontend filter values to backend status values
      let statusFilter = filters.status;
      if (filters.status === 'pending') {
        // Pending includes CREATED and ASSIGNED
        statusFilter = undefined; // We'll filter on frontend for pending
      } else if (filters.status === 'resolved') {
        statusFilter = 'RESOLVED';
      }
      
      const response = await listIncidents({
        page: currentPage,
        search: filters.search,
        status: statusFilter,
        priority: filters.priority,
      });
      
      let incidentsList = response.data.results || response.data;
      
      // Frontend filter for pending (CREATED or ASSIGNED)
      if (filters.status === 'pending') {
        incidentsList = incidentsList.filter(inc => 
          inc.status === 'CREATED' || inc.status === 'ASSIGNED'
        );
      }
      
      setIncidents(incidentsList);
      setTotalPages(Math.ceil((response.data.count || incidents.length) / 10));
    } catch (error) {
      console.error('Error fetching incidents:', error);
      toast.error('Failed to load incidents');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-dark-text-primary">All Incidents</h1>
        <button
          onClick={fetchIncidents}
          className="px-4 py-2 bg-ai-blue text-white rounded-md hover:bg-ai-blueDark transition-colors font-semibold"
        >
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="glass p-4 rounded-xl border border-dark-border">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <input
            type="text"
            placeholder="Search incidents..."
            value={filters.search}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            className="px-4 py-2 bg-dark-card border border-dark-border rounded-md text-dark-text-primary placeholder-dark-text-muted focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent"
          />
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            className="px-4 py-2 bg-dark-card border border-dark-border rounded-md text-dark-text-primary focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent"
          >
            <option value="">All Status</option>
            <option value="pending">Pending</option>
            <option value="resolved">Resolved</option>
          </select>
          <select
            value={filters.priority}
            onChange={(e) => setFilters({ ...filters, priority: e.target.value })}
            className="px-4 py-2 bg-dark-card border border-dark-border rounded-md text-dark-text-primary focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent"
          >
            <option value="">All Priority</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>
      </div>

      {/* Incidents Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          [...Array(6)].map((_, i) => (
            <div key={i} className="h-48 bg-dark-card rounded-lg animate-pulse border border-dark-border"></div>
          ))
        ) : incidents.length === 0 ? (
          <div className="col-span-3 text-center py-12 text-dark-text-muted">
            No incidents found
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

      {/* Pagination */}
      {totalPages > 1 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={setCurrentPage}
        />
      )}
    </div>
  );
};

export default List;

