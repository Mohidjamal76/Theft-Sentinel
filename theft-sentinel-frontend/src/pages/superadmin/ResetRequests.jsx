import { useEffect, useState } from 'react';
import CenteredModal from '../../components/CenteredModal';
import { useModal } from '../../hooks/useModal';
import { actOnResetRequest, listResetRequests } from '../../api/tenancy';

const pill = (status) => {
  const base = 'px-3 py-1 rounded-full text-xs font-semibold';
  if (status === 'APPROVED') return `${base} bg-status-success/20 text-status-success border border-status-success/30`;
  if (status === 'REJECTED') return `${base} bg-status-error/20 text-status-error border border-status-error/30`;
  return `${base} bg-ai-blue/10 text-ai-blue border border-ai-blue/20`;
};

const ResetRequests = () => {
  const { modalState, showSuccess, showError, hideModal } = useModal();
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState([]);

  const load = async () => {
    setLoading(true);
    try {
      const res = await listResetRequests();
      setItems(res.data || []);
    } catch (err) {
      showError(err.response?.data?.error || 'Failed to load requests.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const act = async (id, action) => {
    try {
      await actOnResetRequest(id, action);
      showSuccess('Done.');
      await load();
    } catch (err) {
      showError(err.response?.data?.error || 'Action failed.');
    }
  };

  return (
    <div className="space-y-6">
      <CenteredModal show={modalState.show} type={modalState.type} message={modalState.message} onClose={hideModal} />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Password Reset Requests</h1>
          <p className="text-dark-text-muted">Approve or reject Branch Admin password reset requests.</p>
        </div>
        <button onClick={load} className="text-sm text-ai-blue hover:underline">
          Refresh
        </button>
      </div>

      <div className="glass rounded-2xl border border-white/10 overflow-hidden">
        {loading ? (
          <div className="p-6 text-dark-text-muted">Loading...</div>
        ) : items.length === 0 ? (
          <div className="p-6 text-dark-text-muted">No reset requests.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-dark-card/50">
                <tr className="text-left text-dark-text-secondary">
                  <th className="p-3">User</th>
                  <th className="p-3">Email</th>
                  <th className="p-3">Branch</th>
                  <th className="p-3">Company</th>
                  <th className="p-3">Reason</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Time</th>
                  <th className="p-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((r) => (
                  <tr key={r.id} className="border-t border-white/5">
                    <td className="p-3 text-white">{r.username}</td>
                    <td className="p-3 text-dark-text-secondary">{r.user_email}</td>
                    <td className="p-3 text-white">{r.branch_name}</td>
                    <td className="p-3 text-white">{r.company_name}</td>
                    <td className="p-3 text-dark-text-secondary max-w-[360px] whitespace-pre-wrap">{r.reason}</td>
                    <td className="p-3">
                      <span className={pill(r.status)}>{r.status}</span>
                    </td>
                    <td className="p-3 text-dark-text-secondary">
                      {r.created_at ? new Date(r.created_at).toLocaleString() : '-'}
                    </td>
                    <td className="p-3">
                      <div className="flex flex-wrap gap-2">
                        {r.status === 'PENDING' ? (
                          <>
                            <button
                              onClick={() => act(r.id, 'approve')}
                              className="px-3 py-1 rounded-md bg-status-success/20 text-status-success border border-status-success/30"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => act(r.id, 'reject')}
                              className="px-3 py-1 rounded-md bg-status-error/20 text-status-error border border-status-error/30"
                            >
                              Reject
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => act(r.id, 'delete')}
                            className="px-3 py-1 rounded-md bg-dark-card text-status-error border border-dark-border hover:bg-status-error/10"
                          >
                            Delete
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default ResetRequests;

