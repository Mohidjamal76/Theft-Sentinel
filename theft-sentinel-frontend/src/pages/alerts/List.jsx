import { useState, useEffect } from 'react';
import { listAlerts, adminDeleteAlert } from '../../api/alerts';
import { useNavigate } from 'react-router-dom';
import { useRecoilValue } from 'recoil';
import { authUserState } from '../../store/authStore';
import AlertCard from '../../components/AlertCard';
import { Pagination } from '../../components/Table';
import CenteredModal from '../../components/CenteredModal';
import ConfirmDismissModal from '../../components/ConfirmDismissModal';
import { useModal } from '../../hooks/useModal';

const List = () => {
  const navigate = useNavigate();
  const user = useRecoilValue(authUserState);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filters, setFilters] = useState({
    search: '',
    severity: '',
    acknowledged: '',
  });
  const [showDismissModal, setShowDismissModal] = useState(false);
  const [alertToDismiss, setAlertToDismiss] = useState(null);
  const { modalState, showSuccess, showError, hideModal } = useModal();

  const isAdmin = user?.role === 'ADMIN';

  useEffect(() => {
    fetchAlerts();
  }, [currentPage, filters]);

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const params = {
        page: currentPage,
        search: filters.search,
        acknowledged: filters.acknowledged,
      };
      if (filters.severity) params.severity = filters.severity;
      const response = await listAlerts(params);
      setAlerts(response.data.results || response.data);
      setTotalPages(Math.ceil((response.data.count || alerts.length) / 10));
    } catch (error) {
      console.error('Error fetching alerts:', error);
      showError('Failed to load alerts');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAlert = (alertId) => {
    setAlertToDismiss(alertId);
    setShowDismissModal(true);
  };

  const confirmDismiss = async () => {
    try {
      await adminDeleteAlert(alertToDismiss);
      showSuccess('Alert dismissed successfully');
      setShowDismissModal(false);
      setAlertToDismiss(null);
      fetchAlerts();
    } catch (error) {
      console.error('Error dismissing alert:', error);
      const errorMsg = error.response?.data?.detail || error.response?.data?.error || 'Failed to dismiss alert';
      showError(errorMsg);
      setShowDismissModal(false);
      setAlertToDismiss(null);
    }
  };

  const cancelDismiss = () => {
    setShowDismissModal(false);
    setAlertToDismiss(null);
  };

  return (
    <div className="space-y-6">
      <CenteredModal
        show={modalState.show}
        type={modalState.type}
        message={modalState.message}
        onClose={hideModal}
      />
      
      <ConfirmDismissModal
        show={showDismissModal}
        onConfirm={confirmDismiss}
        onCancel={cancelDismiss}
        alertType="alert"
      />

      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
        <h1 className="text-3xl font-bold text-dark-text-primary">Alerts</h1>
        <button
          onClick={fetchAlerts}
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
            placeholder="Search alerts..."
            value={filters.search}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            className="px-4 py-2 bg-dark-card border border-dark-border rounded-md text-dark-text-primary placeholder-dark-text-muted focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent"
          />
          <select
            value={filters.severity}
            onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
            className="px-4 py-2 bg-dark-card border border-dark-border rounded-md text-dark-text-primary focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent"
          >
            <option value="">All Severity</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
          </select>
          <select
            value={filters.acknowledged}
            onChange={(e) => setFilters({ ...filters, acknowledged: e.target.value })}
            className="px-4 py-2 bg-dark-card border border-dark-border rounded-md text-dark-text-primary focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent"
          >
            <option value="">All Status</option>
            <option value="true">Acknowledged</option>
            <option value="false">Pending</option>
          </select>
        </div>
      </div>

      {/* Alerts Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          [...Array(6)].map((_, i) => (
            <div key={i} className="h-48 bg-dark-card rounded-lg animate-pulse border border-dark-border"></div>
          ))
        ) : alerts.length === 0 ? (
          <div className="col-span-3 text-center py-12 text-dark-text-muted">
            No alerts found
          </div>
        ) : (
          alerts.map((alert) => (
            <AlertCard
              key={alert.id}
              alert={alert}
              onClick={() => navigate(`/alerts/${alert.id}`)}
              onDelete={handleDeleteAlert}
              showDelete={isAdmin}
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

