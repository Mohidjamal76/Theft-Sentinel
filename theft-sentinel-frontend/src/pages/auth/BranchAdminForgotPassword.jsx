import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { branchAdminResetRequest } from '../../api/tenancy';
import CenteredModal from '../../components/CenteredModal';
import { useModal } from '../../hooks/useModal';
import { validateEmail, validateReason } from '../../utils/validation';

const BranchAdminForgotPassword = () => {
  const navigate = useNavigate();
  const { modalState, showSuccess, showError, hideModal } = useModal();
  const [email, setEmail] = useState('');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const emailCheck = validateEmail(email);
    if (!emailCheck.valid) {
      showError(emailCheck.message);
      return;
    }
    const reasonCheck = validateReason(reason);
    if (!reasonCheck.valid) {
      showError(reasonCheck.message);
      return;
    }
    setLoading(true);
    try {
      await branchAdminResetRequest(email.trim().toLowerCase(), reason.trim());
      showSuccess('Request submitted for Super Admin review.');
      setTimeout(() => navigate('/login'), 2000);
    } catch (err) {
      const msg = err.response?.data?.error || 'Failed to submit request.';
      showError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-bg px-4">
      <CenteredModal show={modalState.show} type={modalState.type} message={modalState.message} onClose={hideModal} />
      <div className="w-full max-w-md glass-strong rounded-2xl p-8 border border-white/10">
        <h1 className="text-3xl font-bold text-white mb-2">Branch Admin Reset</h1>
        <p className="text-dark-text-muted mb-6">Submit a reset request (Super Admin approval required).</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-dark-text-secondary mb-1">Email</label>
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              required
              className="w-full px-4 py-3 bg-dark-card border border-dark-border rounded-lg text-white"
              placeholder="admin@example.com"
            />
          </div>
          <div>
            <label className="block text-sm text-dark-text-secondary mb-1">Reason (required)</label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              required
              rows={4}
              className="w-full px-4 py-3 bg-dark-card border border-dark-border rounded-lg text-white"
              placeholder="Explain why you need a password reset..."
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-ai-blue to-ai-purple text-dark-bg font-bold rounded-lg disabled:opacity-60"
          >
            {loading ? 'Submitting...' : 'Submit Request'}
          </button>
          <button type="button" onClick={() => navigate('/login')} className="w-full py-2 text-sm text-ai-blue">
            ← Back to Login
          </button>
        </form>
      </div>
    </div>
  );
};

export default BranchAdminForgotPassword;

