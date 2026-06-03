import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { resetPassword } from '../../api/auth';
import { LockClosedIcon, CheckCircleIcon, EyeIcon, EyeSlashIcon, ArrowLeftIcon } from '@heroicons/react/24/outline';
import CenteredModal from '../../components/CenteredModal';
import { useModal } from '../../hooks/useModal';
import { validatePassword as validatePasswordRules, PASSWORD_EXAMPLE } from '../../utils/validation';

const ResetPassword = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { modalState, showSuccess, showError, hideModal } = useModal();
  
  const [formData, setFormData] = useState({
    new_password: '',
    confirm_password: '',
  });
  const [loading, setLoading] = useState(false);
  const [token, setToken] = useState(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [focusedField, setFocusedField] = useState(null);

  useEffect(() => {
    const tokenParam = searchParams.get('token');
    if (tokenParam) {
      setToken(tokenParam);
    } else {
      showError('Invalid reset link. Please request a new password reset.');
      setTimeout(() => {
        navigate('/forgot-password');
      }, 3000);
    }
  }, [searchParams, navigate, showError]);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const passwordCheck = validatePasswordRules(formData.new_password);
    if (!passwordCheck.valid) {
      showError(passwordCheck.message);
      return;
    }

    if (formData.new_password !== formData.confirm_password) {
      showError('Passwords do not match');
      return;
    }

    if (!token) {
      showError('Invalid reset token. Please request a new password reset.');
      return;
    }

    setLoading(true);

    try {
      const response = await resetPassword(
        token,
        formData.new_password,
        formData.confirm_password
      );
      
      showSuccess(
        response.data.message || 
        'Password successfully updated. You may now log in.'
      );
      
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    } catch (error) {
      const d = error.response?.data;
      const np = d?.new_password;
      const errorMsg =
        (Array.isArray(np) ? np[0] : np) ||
        d?.error ||
        d?.message ||
        d?.non_field_errors?.[0] ||
        'Failed to reset password. Please try again.';
      showError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-dark-bg">
        <div className="glass-strong rounded-xl p-6 text-center">
          <p className="text-dark-text-secondary">Loading...</p>
        </div>
      </div>
    );
  }

  const newPasswordValidation = validatePasswordRules(formData.new_password);

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

      {/* Reset Password Card */}
      <div className="relative z-10 w-full max-w-md px-4">
        <div className="glass-strong rounded-2xl p-8 shadow-dark-lg animate-fadeIn">
          {/* Logo & Title */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-ai-blue to-ai-purple mb-4 shadow-glow-ai">
              <LockClosedIcon className="h-10 w-10 text-dark-bg" />
            </div>
            <h1 className="text-4xl font-bold mb-2">
              <span className="text-gradient-ai">Reset Password</span>
            </h1>
            <p className="text-dark-text-muted text-sm">
              Enter your new password
            </p>
          </div>

          {/* Form */}
          <form className="space-y-6" onSubmit={handleSubmit}>
            {/* New Password */}
            <div className="space-y-2">
              <label 
                htmlFor="new_password" 
                className={`block text-sm font-medium transition-colors ${
                  focusedField === 'new_password' ? 'text-ai-blue' : 'text-dark-text-secondary'
                }`}
              >
                New Password
              </label>
              <div className="relative">
                <input
                  id="new_password"
                  name="new_password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  minLength={8}
                  value={formData.new_password}
                  onChange={handleChange}
                  onFocus={() => setFocusedField('new_password')}
                  onBlur={() => setFocusedField(null)}
                  className="w-full px-4 py-3 pr-12 bg-dark-card border border-dark-border rounded-lg
                           text-dark-text-primary placeholder-dark-text-muted
                           focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent
                           transition-all duration-200"
                  placeholder="Enter new password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-dark-text-muted hover:text-ai-blue transition-colors"
                >
                  {showPassword ? (
                    <EyeSlashIcon className="h-5 w-5" />
                  ) : (
                    <EyeIcon className="h-5 w-5" />
                  )}
                </button>
                {focusedField === 'new_password' && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-ai-blue to-ai-purple animate-slideIn" />
                )}
              </div>
              <p className="mt-1 text-xs text-dark-text-muted">
                Example: {PASSWORD_EXAMPLE}
              </p>
              {formData.new_password && !newPasswordValidation.valid && (
                <p className="mt-1 text-xs text-status-error">{newPasswordValidation.message}</p>
              )}
            </div>

            {/* Confirm Password */}
            <div className="space-y-2">
              <label 
                htmlFor="confirm_password" 
                className={`block text-sm font-medium transition-colors ${
                  focusedField === 'confirm_password' ? 'text-ai-blue' : 'text-dark-text-secondary'
                }`}
              >
                Confirm Password
              </label>
              <div className="relative">
                <input
                  id="confirm_password"
                  name="confirm_password"
                  type={showConfirmPassword ? 'text' : 'password'}
                  required
                  minLength={8}
                  value={formData.confirm_password}
                  onChange={handleChange}
                  onFocus={() => setFocusedField('confirm_password')}
                  onBlur={() => setFocusedField(null)}
                  className="w-full px-4 py-3 pr-12 bg-dark-card border border-dark-border rounded-lg
                           text-dark-text-primary placeholder-dark-text-muted
                           focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent
                           transition-all duration-200"
                  placeholder="Confirm new password"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-dark-text-muted hover:text-ai-blue transition-colors"
                >
                  {showConfirmPassword ? (
                    <EyeSlashIcon className="h-5 w-5" />
                  ) : (
                    <EyeIcon className="h-5 w-5" />
                  )}
                </button>
                {focusedField === 'confirm_password' && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-ai-blue to-ai-purple animate-slideIn" />
                )}
              </div>
              {formData.confirm_password && formData.new_password !== formData.confirm_password && (
                <p className="mt-1 text-xs text-status-error">Passwords do not match</p>
              )}
              {formData.confirm_password && formData.new_password === formData.confirm_password && newPasswordValidation.valid && (
                <p className="mt-1 text-xs text-status-success flex items-center">
                  <CheckCircleIcon className="h-4 w-4 mr-1" />
                  Passwords match
                </p>
              )}
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || !newPasswordValidation.valid || formData.new_password !== formData.confirm_password}
              className="group relative w-full py-3 px-4 bg-gradient-to-r from-ai-blue to-ai-purple
                       text-dark-bg font-semibold rounded-lg
                       hover:shadow-glow-ai-lg transition-all duration-300
                       disabled:opacity-50 disabled:cursor-not-allowed
                       transform hover:scale-[1.02] active:scale-[0.98]"
            >
              <span className="relative z-10">
                {loading ? 'Resetting...' : 'Reset Password'}
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

export default ResetPassword;
