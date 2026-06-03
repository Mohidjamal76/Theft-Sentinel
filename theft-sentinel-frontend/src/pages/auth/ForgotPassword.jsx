import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { forgotPassword } from '../../api/auth';
import { EnvelopeIcon, ArrowLeftIcon } from '@heroicons/react/24/outline';
import CenteredModal from '../../components/CenteredModal';
import { useModal } from '../../hooks/useModal';
import { validateEmail } from '../../utils/validation';

const ForgotPassword = () => {
  const navigate = useNavigate();
  const { modalState, showSuccess, showError, hideModal } = useModal();
  
  const [formData, setFormData] = useState({
    email: '',
  });
  const [loading, setLoading] = useState(false);
  const [focusedField, setFocusedField] = useState(null);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const emailCheck = validateEmail(formData.email);
    if (!emailCheck.valid) {
      showError(emailCheck.message);
      return;
    }
    setLoading(true);

    try {
      const response = await forgotPassword(formData.email.trim().toLowerCase());
      showSuccess(
        response.data.message || 
        'If this email is registered as an admin, a password reset link has been sent to your email.'
      );
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    } catch (error) {
      const data = error.response?.data;
      const emailErr = data?.email;
      const errorMsg =
        (Array.isArray(emailErr) ? emailErr[0] : emailErr) ||
        data?.error ||
        data?.message ||
        'Failed to process request. Please try again.';
      showError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-bg relative overflow-hidden">
      <CenteredModal
        show={modalState.show}
        type={modalState.type}
        message={modalState.message}
        onClose={hideModal}
      />
      
      {/* Animated Background */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-ai-blue/20 rounded-full blur-3xl animate-pulse-slow" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-ai-purple/20 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }} />
      </div>

      {/* Forgot Password Card */}
      <div className="relative z-10 w-full max-w-md px-4">
        <div className="glass-strong rounded-2xl p-8 shadow-dark-lg animate-fadeIn">
          {/* Logo & Title */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-ai-blue to-ai-purple mb-4 shadow-glow-ai">
              <EnvelopeIcon className="h-10 w-10 text-dark-bg" />
            </div>
            <h1 className="text-4xl font-bold mb-2">
              <span className="text-gradient-ai">Forgot Password</span>
            </h1>
            <p className="text-dark-text-muted text-sm">
              Admin Password Reset
            </p>
          </div>

          {/* Admin-Only Notice */}
          <div className="mb-6 p-4 glass rounded-lg border border-ai-blue/30">
            <p className="text-sm text-ai-blue font-medium mb-1">
              <strong>Admin Only:</strong> Only Admin users can reset passwords using this flow.
            </p>
            <p className="text-xs text-dark-text-muted">
              Security personnel and guards must contact the admin to change passwords.
            </p>
          </div>

          {/* Form */}
          <form className="space-y-6" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label 
                htmlFor="email" 
                className={`block text-sm font-medium transition-colors ${
                  focusedField === 'email' ? 'text-ai-blue' : 'text-dark-text-secondary'
                }`}
              >
                Gmail Address
              </label>
              <div className="relative">
                <input
                  id="email"
                  name="email"
                  type="email"
                  required
                  value={formData.email}
                  onChange={handleChange}
                  onFocus={() => setFocusedField('email')}
                  onBlur={() => setFocusedField(null)}
                  className="w-full px-4 py-3 bg-dark-card border border-dark-border rounded-lg
                           text-dark-text-primary placeholder-dark-text-muted
                           focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent
                           transition-all duration-200"
                  placeholder="admin@example.com"
                />
                {focusedField === 'email' && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-ai-blue to-ai-purple animate-slideIn" />
                )}
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="group relative w-full py-3 px-4 bg-gradient-to-r from-ai-blue to-ai-purple
                       text-dark-bg font-semibold rounded-lg
                       hover:shadow-glow-ai-lg transition-all duration-300
                       disabled:opacity-50 disabled:cursor-not-allowed
                       transform hover:scale-[1.02] active:scale-[0.98]"
            >
              <span className="relative z-10">
                {loading ? 'Sending...' : 'Send Reset Link'}
              </span>
              <div className="absolute inset-0 bg-gradient-to-r from-ai-blue to-ai-purple rounded-lg blur-xl opacity-50 group-hover:opacity-75 transition-opacity" />
            </button>
          </form>

          {/* Back to Login / Home */}
          <div className="mt-6 pt-6 border-t border-dark-border space-y-2">
            <button
              onClick={() => navigate('/login')}
              className="w-full flex items-center justify-center space-x-2 px-4 py-2 glass border border-dark-border rounded-lg
                       text-dark-text-secondary hover:bg-dark-card hover:text-ai-blue
                       transition-all duration-200"
            >
              <ArrowLeftIcon className="h-5 w-5" />
              <span>Back to Login</span>
            </button>
            <button
              onClick={() => navigate('/')}
              className="w-full text-xs text-ai-blue hover:text-ai-blueDark transition-colors"
            >
              ← Back to Home
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ForgotPassword;
