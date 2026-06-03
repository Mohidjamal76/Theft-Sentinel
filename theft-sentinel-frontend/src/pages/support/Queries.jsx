import { useEffect, useState } from 'react';
import { useRecoilValue } from 'recoil';
import { authUserState } from '../../store/authStore';
import CenteredModal from '../../components/CenteredModal';
import { useModal } from '../../hooks/useModal';
import {
  branchAdminQueryAction,
  createMyQuery,
  deleteBranchAdminAnsweredQuery,
  deleteMyAnsweredQuery,
  listBranchAdminAnsweredQueries,
  listBranchAdminPendingQueries,
  listMyQueries,
} from '../../api/support';
import { validateMessage } from '../../utils/validation';

const pill = (status) => {
  const base = 'px-3 py-1 rounded-full text-xs font-semibold';
  if (status === 'ANSWERED') return `${base} bg-status-success/20 text-status-success border border-status-success/30`;
  if (status === 'PENDING_SUPER_ADMIN') return `${base} bg-ai-blue/10 text-ai-blue border border-ai-blue/20`;
  return `${base} bg-ai-purple/10 text-ai-purple border border-ai-purple/20`;
};

const Queries = () => {
  const user = useRecoilValue(authUserState);
  const { modalState, showSuccess, showError, hideModal } = useModal();

  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [myQueries, setMyQueries] = useState([]);
  const [pending, setPending] = useState([]);
  const [answered, setAnswered] = useState([]);

  const load = async () => {
    setLoading(true);
    try {
      const [myRes, pendingRes, answeredRes] = await Promise.all([
        listMyQueries(),
        user?.role === 'ADMIN' ? listBranchAdminPendingQueries() : Promise.resolve({ data: [] }),
        user?.role === 'ADMIN' ? listBranchAdminAnsweredQueries() : Promise.resolve({ data: [] }),
      ]);
      setMyQueries(myRes.data || []);
      setPending(pendingRes.data || []);
      setAnswered(answeredRes.data || []);
    } catch (err) {
      showError(err.response?.data?.error || 'Failed to load queries.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    const messageCheck = validateMessage(message);
    if (!messageCheck.valid) {
      showError(messageCheck.message);
      return;
    }
    try {
      await createMyQuery(message.trim());
      setMessage('');
      showSuccess('Query submitted.');
      await load();
    } catch (err) {
      showError(err.response?.data?.error || 'Failed to submit query.');
    }
  };

  const deleteMine = async (id) => {
    try {
      await deleteMyAnsweredQuery(id);
      showSuccess('Deleted.');
      await load();
    } catch (err) {
      showError(err.response?.data?.error || 'Delete failed.');
    }
  };

  const actPending = async (id, action) => {
    try {
      await branchAdminQueryAction(id, action);
      showSuccess('Done.');
      await load();
    } catch (err) {
      showError(err.response?.data?.error || 'Action failed.');
    }
  };

  const deleteAnsweredForBranch = async (id) => {
    try {
      await deleteBranchAdminAnsweredQuery(id);
      showSuccess('Deleted.');
      await load();
    } catch (err) {
      showError(err.response?.data?.error || 'Delete failed.');
    }
  };

  return (
    <div className="space-y-6">
      <CenteredModal show={modalState.show} type={modalState.type} message={modalState.message} onClose={hideModal} />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Support Queries</h1>
          <p className="text-dark-text-muted">
            {user?.role === 'ADMIN'
              ? 'Send queries to Super Admin. Review staff queries and escalate.'
              : 'Submit a query. Your Branch Admin will review/escalate if needed.'}
          </p>
        </div>
        <button onClick={load} className="text-sm text-ai-blue hover:underline">
          Refresh
        </button>
      </div>

      <div className="glass rounded-2xl border border-white/10 p-6">
        <h2 className="text-lg font-semibold text-white mb-3">New Query</h2>
        <form onSubmit={submit} className="space-y-3">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            required
            rows={4}
            className="w-full px-4 py-3 bg-dark-card border border-dark-border rounded-lg text-white"
            placeholder="Type your query..."
          />
          <button className="px-6 py-3 bg-gradient-to-r from-ai-blue to-ai-purple text-dark-bg font-bold rounded-lg">
            Submit
          </button>
        </form>
      </div>

      {user?.role === 'ADMIN' && (
        <div className="glass rounded-2xl border border-white/10 overflow-hidden">
          <div className="p-4 border-b border-white/10">
            <h2 className="text-lg font-semibold text-white">Pending Staff Queries</h2>
          </div>
          {loading ? (
            <div className="p-6 text-dark-text-muted">Loading...</div>
          ) : pending.length === 0 ? (
            <div className="p-6 text-dark-text-muted">No pending queries.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-dark-card/50">
                  <tr className="text-left text-dark-text-secondary">
                    <th className="p-3">Sender</th>
                    <th className="p-3">Role</th>
                    <th className="p-3">Message</th>
                    <th className="p-3">Time</th>
                    <th className="p-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {pending.map((q) => (
                    <tr key={q.id} className="border-t border-white/5">
                      <td className="p-3 text-white">{q.sender_username}</td>
                      <td className="p-3 text-dark-text-secondary">{q.sender_role}</td>
                      <td className="p-3 text-dark-text-secondary whitespace-pre-wrap max-w-[520px]">{q.message}</td>
                      <td className="p-3 text-dark-text-secondary">
                        {q.created_at ? new Date(q.created_at).toLocaleString() : '-'}
                      </td>
                      <td className="p-3">
                        <div className="flex gap-2">
                          <button
                            onClick={() => actPending(q.id, 'approve_to_super_admin')}
                            className="px-3 py-1 rounded-md bg-ai-blue/10 text-ai-blue border border-ai-blue/20"
                          >
                            Escalate
                          </button>
                          <button
                            onClick={() => actPending(q.id, 'delete')}
                            className="px-3 py-1 rounded-md bg-dark-card text-status-error border border-dark-border hover:bg-status-error/10"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {user?.role === 'ADMIN' && (
        <div className="glass rounded-2xl border border-white/10 overflow-hidden">
          <div className="p-4 border-b border-white/10">
            <h2 className="text-lg font-semibold text-white">Answered Staff Queries</h2>
            <p className="text-sm text-dark-text-muted">
              View responses for Security Guard and Security In-Charge queries in your branch.
            </p>
          </div>
          {loading ? (
            <div className="p-6 text-dark-text-muted">Loading...</div>
          ) : answered.length === 0 ? (
            <div className="p-6 text-dark-text-muted">No answered staff queries.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-dark-card/50">
                  <tr className="text-left text-dark-text-secondary">
                    <th className="p-3">Sender</th>
                    <th className="p-3">Role</th>
                    <th className="p-3">Message</th>
                    <th className="p-3">Answer</th>
                    <th className="p-3">Answered</th>
                    <th className="p-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {answered.map((q) => (
                    <tr key={q.id} className="border-t border-white/5">
                      <td className="p-3 text-white">{q.sender_username}</td>
                      <td className="p-3 text-dark-text-secondary">{q.sender_role}</td>
                      <td className="p-3 text-dark-text-secondary whitespace-pre-wrap max-w-[360px]">{q.message}</td>
                      <td className="p-3 text-dark-text-secondary whitespace-pre-wrap max-w-[420px]">
                        {q.answer || '-'}
                      </td>
                      <td className="p-3 text-dark-text-secondary">
                        {q.answered_at ? new Date(q.answered_at).toLocaleString() : '-'}
                      </td>
                      <td className="p-3">
                        <button
                          onClick={() => deleteAnsweredForBranch(q.id)}
                          className="px-3 py-1 rounded-md bg-dark-card text-status-error border border-dark-border hover:bg-status-error/10"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <div className="glass rounded-2xl border border-white/10 overflow-hidden">
        <div className="p-4 border-b border-white/10">
          <h2 className="text-lg font-semibold text-white">My Queries</h2>
        </div>
        {loading ? (
          <div className="p-6 text-dark-text-muted">Loading...</div>
        ) : myQueries.length === 0 ? (
          <div className="p-6 text-dark-text-muted">No queries.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-dark-card/50">
                <tr className="text-left text-dark-text-secondary">
                  <th className="p-3">Status</th>
                  <th className="p-3">Message</th>
                  <th className="p-3">Answer</th>
                  <th className="p-3">Time</th>
                  <th className="p-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {myQueries.map((q) => (
                  <tr key={q.id} className="border-t border-white/5">
                    <td className="p-3">
                      <span className={pill(q.status)}>{q.status}</span>
                    </td>
                    <td className="p-3 text-dark-text-secondary whitespace-pre-wrap max-w-[520px]">{q.message}</td>
                    <td className="p-3 text-dark-text-secondary whitespace-pre-wrap max-w-[520px]">
                      {q.answer || '-'}
                    </td>
                    <td className="p-3 text-dark-text-secondary">
                      {q.created_at ? new Date(q.created_at).toLocaleString() : '-'}
                    </td>
                    <td className="p-3">
                      {q.status === 'ANSWERED' ? (
                        <button
                          onClick={() => deleteMine(q.id)}
                          className="px-3 py-1 rounded-md bg-dark-card text-status-error border border-dark-border hover:bg-status-error/10"
                        >
                          Delete
                        </button>
                      ) : (
                        <span className="text-xs text-dark-text-muted">-</span>
                      )}
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

export default Queries;

