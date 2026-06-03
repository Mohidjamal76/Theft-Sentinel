import { useEffect, useState } from 'react';
import CenteredModal from '../../components/CenteredModal';
import { useModal } from '../../hooks/useModal';
import {
  answerSuperAdminQuery,
  deleteAnsweredSuperAdminQuery,
  listSuperAdminPendingQueries,
} from '../../api/support';
import { validateReason } from '../../utils/validation';

const Queries = () => {
  const { modalState, showSuccess, showError, hideModal } = useModal();
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState([]);
  const [answerDrafts, setAnswerDrafts] = useState({});

  const load = async () => {
    setLoading(true);
    try {
      const res = await listSuperAdminPendingQueries();
      setItems(res.data || []);
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

  const answer = async (id) => {
    const text = answerDrafts[id] || '';
    const answerCheck = validateReason(text);
    if (!answerCheck.valid) {
      showError(answerCheck.message);
      return;
    }
    try {
      await answerSuperAdminQuery(id, text.trim());
      showSuccess('Answered.');
      setAnswerDrafts((p) => ({ ...p, [id]: '' }));
      await load();
    } catch (err) {
      showError(err.response?.data?.error || 'Failed to answer.');
    }
  };

  const deleteAnswered = async (id) => {
    try {
      await deleteAnsweredSuperAdminQuery(id);
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
          <h1 className="text-3xl font-bold text-white">Tenant Queries</h1>
          <p className="text-dark-text-muted">Answer pending queries from branches.</p>
        </div>
        <button onClick={load} className="text-sm text-ai-blue hover:underline">
          Refresh
        </button>
      </div>

      <div className="glass rounded-2xl border border-white/10 overflow-hidden">
        {loading ? (
          <div className="p-6 text-dark-text-muted">Loading...</div>
        ) : items.length === 0 ? (
          <div className="p-6 text-dark-text-muted">No pending queries.</div>
        ) : (
          <div className="divide-y divide-white/5">
            {items.map((q) => (
              <div key={q.id} className="p-6 space-y-3">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                  <div>
                    <p className="text-white font-semibold">
                      {q.company_name} — {q.branch_name}
                    </p>
                    <p className="text-sm text-dark-text-secondary">
                      From: {q.sender_username} ({q.sender_role}) • {q.sender_email}
                    </p>
                  </div>
                  <p className="text-xs text-dark-text-muted">{q.created_at ? new Date(q.created_at).toLocaleString() : '-'}</p>
                </div>

                <div className="glass p-4 rounded-xl border border-white/10">
                  <p className="text-sm text-dark-text-secondary whitespace-pre-wrap">{q.message}</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                  <textarea
                    value={answerDrafts[q.id] || ''}
                    onChange={(e) => setAnswerDrafts((p) => ({ ...p, [q.id]: e.target.value }))}
                    rows={3}
                    className="md:col-span-3 w-full px-4 py-3 bg-dark-card border border-dark-border rounded-lg text-white"
                    placeholder="Type your answer..."
                  />
                  <div className="flex md:flex-col gap-2">
                    <button
                      onClick={() => answer(q.id)}
                      className="flex-1 px-4 py-3 rounded-lg bg-status-success/20 text-status-success border border-status-success/30 font-bold"
                    >
                      Answer
                    </button>
                    <button
                      onClick={() => deleteAnswered(q.id)}
                      className="flex-1 px-4 py-3 rounded-lg bg-dark-card text-status-error border border-dark-border font-bold"
                      title="Only works after answered (backend enforced)."
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Queries;

