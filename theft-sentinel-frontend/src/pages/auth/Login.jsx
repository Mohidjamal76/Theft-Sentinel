import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSetRecoilState } from 'recoil';
import { authUserState, authTokensState } from '../../store/authStore';
import { login as loginAPI } from '../../api/auth';
import { LockClosedIcon, EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline';
import CenteredModal from '../../components/CenteredModal';
import { useModal } from '../../hooks/useModal';
import { validateRequired } from '../../utils/validation';

const Login = () => {
  const navigate = useNavigate();
  const setAuthUser = useSetRecoilState(authUserState);
  const setAuthTokens = useSetRecoilState(authTokensState);
  const { modalState, showSuccess, showError, hideModal } = useModal();
  
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  });
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [focusedField, setFocusedField] = useState(null);
  const [showResetOptions, setShowResetOptions] = useState(false);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const loginCheck = validateRequired(formData.username, 'Email or username is required.');
    const passwordCheck = validateRequired(formData.password, 'Password is required.');
    if (!loginCheck.valid || !passwordCheck.valid) {
      showError(!loginCheck.valid ? loginCheck.message : passwordCheck.message);
      return;
    }
    setLoading(true);

    try {
      const response = await loginAPI({
        username: formData.username.trim(),
        password: formData.password,
      });
      const { access, refresh, user } = response.data;

      // Store tokens
      localStorage.setItem('access_token', access);
      localStorage.setItem('refresh_token', refresh);

      // Update Recoil state
      setAuthTokens({ access, refresh });
      setAuthUser(user);

      showSuccess('Login successful! Redirecting to dashboard...');
      setTimeout(() => {
        // Redirect based on user role
        if (user.role === 'SECURITY_GUARD') {
          navigate('/dashboard/guard');
        } else {
          navigate('/dashboard');
        }
      }, 1500);
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 
                      error.response?.data?.error ||
                      error.response?.data?.message ||
                      'Login failed. Please check your credentials.';
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
        {/* Gradient Orbs */}
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-ai-blue/20 rounded-full blur-3xl animate-pulse-slow" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-ai-purple/20 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }} />
        
        {/* Grid Pattern */}
        <div className="absolute inset-0 opacity-10" style={{
          backgroundImage: 'linear-gradient(rgba(0, 217, 255, 0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 217, 255, 0.1) 1px, transparent 1px)',
          backgroundSize: '50px 50px',
        }} />
      </div>

      {/* Login Card */}
      <div className="relative z-10 w-full max-w-md px-4">
        <div className="glass-strong rounded-2xl p-8 shadow-dark-lg animate-fadeIn">
          {/* Logo & Title */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-ai-blue to-ai-purple mb-4 shadow-glow-ai">
              <LockClosedIcon className="h-10 w-10 text-dark-bg" />
            </div>
            <h1 className="text-4xl font-bold mb-2">
              <span className="text-gradient-ai">Theft Sentinel</span>
            </h1>
            <p className="text-dark-text-muted text-sm">
              AI-Powered Intelligent Surveillance System
            </p>
          </div>

          {/* Login Form */}
          <form className="space-y-6" onSubmit={handleSubmit}>
            {/* Email / Username Field */}
            <div className="space-y-2">
              <label 
                htmlFor="username" 
                className={`block text-sm font-medium transition-colors ${
                  focusedField === 'username' ? 'text-ai-blue' : 'text-dark-text-secondary'
                }`}
              >
                Email or Username
              </label>
              <div className="relative">
                <input
                  id="username"
                  name="username"
                  type="text"
                  required
                  value={formData.username}
                  onChange={handleChange}
                  onFocus={() => setFocusedField('username')}
                  onBlur={() => setFocusedField(null)}
                  className="w-full px-4 py-3 bg-dark-card border border-dark-border rounded-lg
                           text-dark-text-primary placeholder-dark-text-muted
                           focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent
                           transition-all duration-200"
                  placeholder="Email or Username"
                />
                {focusedField === 'username' && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-ai-blue to-ai-purple animate-slideIn" />
                )}
              </div>
            </div>

            {/* Password Field */}
            <div className="space-y-2">
              <label 
                htmlFor="password" 
                className={`block text-sm font-medium transition-colors ${
                  focusedField === 'password' ? 'text-ai-blue' : 'text-dark-text-secondary'
                }`}
              >
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={formData.password}
                  onChange={handleChange}
                  onFocus={() => setFocusedField('password')}
                  onBlur={() => setFocusedField(null)}
                  className="w-full px-4 py-3 pr-12 bg-dark-card border border-dark-border rounded-lg
                           text-dark-text-primary placeholder-dark-text-muted
                           focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent
                           transition-all duration-200"
                  placeholder="Enter your password"
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
                {focusedField === 'password' && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-ai-blue to-ai-purple animate-slideIn" />
                )}
              </div>
            </div>

            {/* Password Reset */}
            <div className="space-y-2">
              <button
                type="button"
                onClick={() => setShowResetOptions((value) => !value)}
                className="w-full text-sm px-4 py-2 glass border border-dark-border rounded-lg text-ai-blue hover:bg-dark-card transition-colors"
              >
                Forgot Password?
              </button>
              {showResetOptions && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 animate-fadeIn">
                  <button
                    type="button"
                    onClick={() => navigate('/forgot-password/super-admin')}
                    className="text-left text-sm px-4 py-3 bg-dark-card border border-dark-border rounded-lg text-dark-text-primary hover:border-ai-blue hover:text-ai-blue transition-colors"
                  >
                    <span className="block font-semibold">Super Admin Password Reset</span>
                    <span className="block text-xs text-dark-text-muted mt-1">Receive a direct reset link.</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => navigate('/forgot-password/branch-admin')}
                    className="text-left text-sm px-4 py-3 bg-dark-card border border-dark-border rounded-lg text-dark-text-primary hover:border-ai-blue hover:text-ai-blue transition-colors"
                  >
                    <span className="block font-semibold">Branch Admin Password Reset</span>
                    <span className="block text-xs text-dark-text-muted mt-1">Request Super Admin approval.</span>
                  </button>
                </div>
              )}
              <p className="text-xs text-dark-text-muted">
                Security Guard / Security In-Charge: contact your Branch Admin for password reset.
              </p>
            </div>

            {/* Submit Button */}
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
                {loading ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-dark-bg" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Signing in...
                  </span>
                ) : (
                  'Sign In'
                )}
              </span>
              <div className="absolute inset-0 bg-gradient-to-r from-ai-blue to-ai-purple rounded-lg blur-xl opacity-50 group-hover:opacity-75 transition-opacity" />
            </button>
          </form>

          {/* Footer */}
          <div className="mt-6 pt-6 border-t border-dark-border">
            <div className="text-center space-y-2">
              <p className="text-xs text-dark-text-muted">
                Contact your administrator for account access
              </p>
              <button
                type="button"
                onClick={() => navigate('/')}
                className="text-xs text-ai-blue hover:text-ai-blueDark transition-colors"
              >
                ← Back to Home
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
