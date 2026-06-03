import { useEffect, useState } from 'react';
import CenteredModal from '../../components/CenteredModal';
import { useModal } from '../../hooks/useModal';
import { deleteBranch, listBranchesForSuperAdmin, updateBranchStatus } from '../../api/tenancy';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

const CHART_COLORS = ['#00D9FF', '#10B981', '#EF4444', '#8B5CF6'];

const chartTooltip = {
  backgroundColor: '#1F2933',
  border: '1px solid #374151',
  borderRadius: '8px',
  color: '#F9FAFB',
};

const statusPill = (status) => {
  const base = 'px-3 py-1 rounded-full text-xs font-semibold';
  if (status === 'APPROVED') return `${base} bg-status-success/20 text-status-success border border-status-success/30`;
  if (status === 'SUSPENDED') return `${base} bg-status-error/20 text-status-error border border-status-error/30`;
  return `${base} bg-ai-blue/10 text-ai-blue border border-ai-blue/20`;
};

const Branches = () => {
  const { modalState, showSuccess, showError, hideModal } = useModal();
  const [loading, setLoading] = useState(true);
  const [counts, setCounts] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [branches, setBranches] = useState([]);

  const load = async () => {
    setLoading(true);
    try {
      const res = await listBranchesForSuperAdmin();
      setCounts(res.data?.counts || null);
      setAnalytics(res.data?.analytics || null);
      setBranches(res.data?.branches || []);
    } catch (err) {
      showError(err.response?.data?.error || 'Failed to load branches.');
    } finally {
      setLoading(false);
    }
  };

  const statusDistribution = analytics?.branch_status_distribution || [];
  const approvedVsSuspended = analytics?.approved_vs_suspended || [];
  const registrationTrend = analytics?.registration_trend || [];
  const resetCounts = analytics?.password_reset_requests || {};
  const queryCounts = analytics?.query_status_counts || {};
  const queryStatusData = [
    { name: 'Branch Review', value: queryCounts.pending_branch_admin || 0 },
    { name: 'Super Admin', value: queryCounts.pending_super_admin || 0 },
    { name: 'Answered', value: queryCounts.answered || 0 },
  ];
  const resetStatusData = [
    { name: 'Pending', value: resetCounts.pending || 0 },
    { name: 'Approved', value: resetCounts.approved || 0 },
    { name: 'Rejected', value: resetCounts.rejected || 0 },
  ];

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const doAction = async (branchId, action) => {
    try {
      await updateBranchStatus(branchId, action);
      showSuccess('Updated successfully.');
      await load();
    } catch (err) {
      showError(err.response?.data?.error || 'Action failed.');
    }
  };

  const doDelete = async (branchId) => {
    if (!confirm('Delete this branch? This will delete all linked users and branch data.')) return;
    try {
      await deleteBranch(branchId);
      showSuccess('Branch deleted.');
      await load();
    } catch (err) {
      showError(err.response?.data?.error || 'Delete failed.');
    }
  };

  return (
    <div className="space-y-6">
      <CenteredModal show={modalState.show} type={modalState.type} message={modalState.message} onClose={hideModal} />

      <div>
        <h1 className="text-3xl font-bold text-white">Branch Management</h1>
        <p className="text-dark-text-muted">Approve, suspend, re-approve, or delete branches.</p>
      </div>

      {counts && (
        <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-6 gap-4">
          <div className="glass p-4 rounded-xl border border-white/10">
            <p className="text-xs text-dark-text-muted">Total</p>
            <p className="text-2xl font-bold text-white">{counts.total_branches}</p>
          </div>
          <div className="glass p-4 rounded-xl border border-white/10">
            <p className="text-xs text-dark-text-muted">Approved</p>
            <p className="text-2xl font-bold text-white">{counts.approved_branches}</p>
          </div>
          <div className="glass p-4 rounded-xl border border-white/10">
            <p className="text-xs text-dark-text-muted">Suspended</p>
            <p className="text-2xl font-bold text-white">{counts.suspended_branches}</p>
          </div>
          <div className="glass p-4 rounded-xl border border-white/10">
            <p className="text-xs text-dark-text-muted">Pending</p>
            <p className="text-2xl font-bold text-white">{counts.pending_branches}</p>
          </div>
          <div className="glass p-4 rounded-xl border border-white/10">
            <p className="text-xs text-dark-text-muted">Queries</p>
            <p className="text-2xl font-bold text-white">{counts.query_count}</p>
          </div>
          <div className="glass p-4 rounded-xl border border-white/10">
            <p className="text-xs text-dark-text-muted">Reset Requests</p>
            <p className="text-2xl font-bold text-white">{resetCounts.total || 0}</p>
            <p className="text-xs text-dark-text-muted">{resetCounts.pending || 0} pending</p>
          </div>
        </div>
      )}

      {analytics && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <div className="glass rounded-2xl border border-white/10 p-5">
            <h2 className="text-lg font-semibold text-white mb-4">Approved vs Suspended Branches</h2>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={approvedVsSuspended}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" stroke="#9CA3AF" tick={{ fill: '#9CA3AF' }} />
                <YAxis stroke="#9CA3AF" tick={{ fill: '#9CA3AF' }} allowDecimals={false} />
                <Tooltip contentStyle={chartTooltip} />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  {approvedVsSuspended.map((entry, index) => (
                    <Cell key={entry.name} fill={index === 0 ? '#10B981' : '#EF4444'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="glass rounded-2xl border border-white/10 p-5">
            <h2 className="text-lg font-semibold text-white mb-4">Branch Status Distribution</h2>
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={statusDistribution} dataKey="value" nameKey="name" outerRadius={90} label>
                  {statusDistribution.map((entry, index) => (
                    <Cell key={entry.name} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={chartTooltip} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="glass rounded-2xl border border-white/10 p-5">
            <h2 className="text-lg font-semibold text-white mb-4">Branch Registration Trend</h2>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={registrationTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="date" stroke="#9CA3AF" tick={{ fill: '#9CA3AF' }} />
                <YAxis stroke="#9CA3AF" tick={{ fill: '#9CA3AF' }} allowDecimals={false} />
                <Tooltip contentStyle={chartTooltip} />
                <Line type="monotone" dataKey="count" stroke="#00D9FF" strokeWidth={3} dot={{ fill: '#00D9FF' }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="glass rounded-2xl border border-white/10 p-5">
            <h2 className="text-lg font-semibold text-white mb-4">Queries and Reset Requests</h2>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={queryStatusData.concat(resetStatusData.map((item) => ({ ...item, name: `Reset ${item.name}` })))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" stroke="#9CA3AF" tick={{ fill: '#9CA3AF', fontSize: 11 }} />
                <YAxis stroke="#9CA3AF" tick={{ fill: '#9CA3AF' }} allowDecimals={false} />
                <Tooltip contentStyle={chartTooltip} />
                <Bar dataKey="value" fill="#8B5CF6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <div className="glass rounded-2xl border border-white/10 overflow-hidden">
        <div className="p-4 border-b border-white/10 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Branches</h2>
          <button onClick={load} className="text-sm text-ai-blue hover:underline">
            Refresh
          </button>
        </div>

        {loading ? (
          <div className="p-6 text-dark-text-muted">Loading...</div>
        ) : branches.length === 0 ? (
          <div className="p-6 text-dark-text-muted">No branches.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-dark-card/50">
                <tr className="text-left text-dark-text-secondary">
                  <th className="p-3">Company</th>
                  <th className="p-3">Branch</th>
                  <th className="p-3">Admin</th>
                  <th className="p-3">Email</th>
                  <th className="p-3">Phone</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Created</th>
                  <th className="p-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {branches.map((b) => (
                  <tr key={b.id} className="border-t border-white/5">
                    <td className="p-3 text-white">{b.company_name}</td>
                    <td className="p-3 text-white">{b.branch_name}</td>
                    <td className="p-3 text-white">{b.admin_name}</td>
                    <td className="p-3 text-dark-text-secondary">{b.admin_email}</td>
                    <td className="p-3 text-dark-text-secondary">{b.admin_phone}</td>
                    <td className="p-3">
                      <span className={statusPill(b.status)}>{b.status}</span>
                    </td>
                    <td className="p-3 text-dark-text-secondary">
                      {b.created_at ? new Date(b.created_at).toLocaleString() : '-'}
                    </td>
                    <td className="p-3">
                      <div className="flex flex-wrap gap-2">
                        {b.status === 'PENDING' && (
                          <button
                            onClick={() => doAction(b.id, 'approve')}
                            className="px-3 py-1 rounded-md bg-status-success/20 text-status-success border border-status-success/30"
                          >
                            Approve
                          </button>
                        )}
                        {b.status === 'APPROVED' && (
                          <button
                            onClick={() => doAction(b.id, 'suspend')}
                            className="px-3 py-1 rounded-md bg-status-error/20 text-status-error border border-status-error/30"
                          >
                            Suspend
                          </button>
                        )}
                        {b.status === 'SUSPENDED' && (
                          <button
                            onClick={() => doAction(b.id, 'reapprove')}
                            className="px-3 py-1 rounded-md bg-status-success/20 text-status-success border border-status-success/30"
                          >
                            Re-Approve
                          </button>
                        )}
                        <button
                          onClick={() => doDelete(b.id)}
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
    </div>
  );
};

export default Branches;

