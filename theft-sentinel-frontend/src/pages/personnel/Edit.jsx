import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { getUser, updateUser, adminChangeUserPassword } from '../../api/auth';
import { ArrowLeftIcon, KeyIcon } from '@heroicons/react/24/outline';
import CenteredModal from '../../components/CenteredModal';
import { useModal } from '../../hooks/useModal';
import { validateEmail, validateUsername, validatePassword, validatePasswordMatch, trimInput, PASSWORD_EXAMPLE } from '../../utils/validation';

const Edit = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    role: 'SECURITY_GUARD',
    is_active: true,
  });
  const [passwordData, setPasswordData] = useState({
    new_password: '',
    confirm_password: '',
  });
  const [errors, setErrors] = useState({
    username: '',
    email: '',
    new_password: '',
    confirm_password: '',
  });
  const [touched, setTouched] = useState({
    username: false,
    email: false,
    new_password: false,
    confirm_password: false,
  });
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const { modalState, showSuccess, showError, hideModal } = useModal();

  useEffect(() => {
    fetchUser();
  }, [id]);

  const fetchUser = async () => {
    try {
      const response = await getUser(id);
      setFormData({
        username: response.data.username,
        email: response.data.email,
        role: response.data.role,
        is_active: response.data.is_active,
      });
    } catch (error) {
      console.error('Error fetching user:', error);
      showError('Failed to load user details');
      navigate('/personnel');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, type, checked, value } = e.target;
    const finalValue = type === 'checkbox' ? checked : trimInput(value);
    
    setFormData({
      ...formData,
      [name]: finalValue,
    });

    // Clear error when user starts typing
    if (errors[name]) {
      setErrors({
        ...errors,
        [name]: '',
      });
    }
  };

  const handleBlur = (e) => {
    const { name, value } = e.target;
    setTouched({ ...touched, [name]: true });

    // Validate on blur
    let validation = { valid: true, message: '' };
    
    if (name === 'username') {
      validation = validateUsername(value);
    } else if (name === 'email') {
      validation = validateEmail(value);
    }

    setErrors({
      ...errors,
      [name]: validation.valid ? '' : validation.message,
    });
  };

  const handlePasswordChange = (e) => {
    const { name, value } = e.target;
    const trimmedValue = trimInput(value);
    
    setPasswordData({
      ...passwordData,
      [name]: trimmedValue,
    });

    // Clear error when user starts typing
    if (errors[name]) {
      setErrors({
        ...errors,
        [name]: '',
      });
    }
  };

  const handlePasswordBlur = (e) => {
    const { name, value } = e.target;
    setTouched({ ...touched, [name]: true });

    // Validate on blur
    let validation = { valid: true, message: '' };
    
    if (name === 'new_password') {
      validation = validatePassword(value);
    } else if (name === 'confirm_password') {
      validation = validatePasswordMatch(passwordData.new_password, value);
    }

    setErrors({
      ...errors,
      [name]: validation.valid ? '' : validation.message,
    });
  };

  const validateForm = () => {
    const newErrors = {
      username: '',
      email: '',
    };

    const usernameValidation = validateUsername(formData.username);
    if (!usernameValidation.valid) {
      newErrors.username = usernameValidation.message;
    }

    const emailValidation = validateEmail(formData.email);
    if (!emailValidation.valid) {
      newErrors.email = emailValidation.message;
    }

    setErrors(prev => ({ ...prev, ...newErrors }));
    setTouched(prev => ({ ...prev, username: true, email: true }));

    return Object.values(newErrors).every(error => error === '');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validate all fields
    if (!validateForm()) {
      showError('Please fix the validation errors before submitting');
      return;
    }

    // Prevent double submission
    if (submitting) {
      return;
    }

    setSubmitting(true);

    try {
      await updateUser(id, formData);
      showSuccess('User updated successfully');
      // Navigate immediately and let the list page refresh
      navigate('/personnel', { replace: true });
    } catch (error) {
      console.error('Error updating user:', error);
      // Handle Admin uniqueness error
      const errorData = error.response?.data;
      let errorMsg = 'Failed to update user';
      
      if (errorData) {
        if (errorData.role && Array.isArray(errorData.role)) {
          errorMsg = errorData.role[0] || 'Admin role already exists. Only one Admin is allowed.';
        } else if (errorData.detail) {
          errorMsg = errorData.detail;
        } else if (errorData.error) {
          errorMsg = errorData.error;
        } else if (typeof errorData === 'string') {
          errorMsg = errorData;
        }
      }
      
      showError(errorMsg);
    } finally {
      setSubmitting(false);
    }
  };

  const validatePasswordForm = () => {
    const newErrors = {
      new_password: '',
      confirm_password: '',
    };

    const passwordValidation = validatePassword(passwordData.new_password);
    if (!passwordValidation.valid) {
      newErrors.new_password = passwordValidation.message;
    }

    const passwordMatchValidation = validatePasswordMatch(passwordData.new_password, passwordData.confirm_password);
    if (!passwordMatchValidation.valid) {
      newErrors.confirm_password = passwordMatchValidation.message;
    }

    setErrors(prev => ({ ...prev, ...newErrors }));
    setTouched(prev => ({ ...prev, new_password: true, confirm_password: true }));

    return Object.values(newErrors).every(error => error === '');
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    
    // Validate password fields
    if (!validatePasswordForm()) {
      showError('Please fix the validation errors before submitting');
      return;
    }

    // Prevent double submission
    if (changingPassword) {
      return;
    }

    setChangingPassword(true);

    try {
      await adminChangeUserPassword(id, { new_password: passwordData.new_password });
      showSuccess('Password changed successfully');
      setShowPasswordModal(false);
      setPasswordData({ new_password: '', confirm_password: '' });
    } catch (error) {
      console.error('Error changing password:', error);
      const errorMsg = error.response?.data?.detail || error.response?.data?.error || 'Failed to change password';
      showError(errorMsg);
    } finally {
      setChangingPassword(false);
    }
  };

  if (loading) {
    return <div className="animate-pulse h-96 bg-dark-card rounded-lg border border-dark-border"></div>;
  }

  return (
    <div className="space-y-6">
      <CenteredModal
        show={modalState.show}
        type={modalState.type}
        message={modalState.message}
        onClose={hideModal}
      />

      <div className="flex items-center space-x-4">
        <button
          onClick={() => navigate('/personnel')}
          className="p-2 hover:bg-dark-card rounded-full transition-colors"
        >
          <ArrowLeftIcon className="h-6 w-6 text-dark-text-secondary" />
        </button>
        <h1 className="text-3xl font-bold text-dark-text-primary">Edit User</h1>
      </div>

      <div className="glass rounded-xl border border-dark-border p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-dark-text-secondary">
                Username *
              </label>
              <input
                type="text"
                id="username"
                name="username"
                required
                value={formData.username || ''}
                onChange={handleChange}
                onBlur={handleBlur}
                className={`mt-1 block w-full px-3 py-2 bg-dark-card border rounded-md text-dark-text-primary focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent ${
                  touched.username && errors.username
                    ? 'border-status-error focus:border-status-error focus:ring-status-error'
                    : 'border-dark-border'
                }`}
              />
              {touched.username && errors.username && (
                <p className="mt-1 text-sm text-status-error">{errors.username}</p>
              )}
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-dark-text-secondary">
                Email *
              </label>
              <input
                type="text"
                id="email"
                name="email"
                required
                value={formData.email || ''}
                onChange={handleChange}
                onBlur={handleBlur}
                className={`mt-1 block w-full px-3 py-2 bg-dark-card border rounded-md text-dark-text-primary focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent ${
                  touched.email && errors.email
                    ? 'border-status-error focus:border-status-error focus:ring-status-error'
                    : 'border-dark-border'
                }`}
              />
              {touched.email && errors.email && (
                <p className="mt-1 text-sm text-status-error">{errors.email}</p>
              )}
            </div>

            <div>
              <label htmlFor="role" className="block text-sm font-medium text-dark-text-secondary">
                Role *
              </label>
              <select
                id="role"
                name="role"
                value={formData.role}
                onChange={handleChange}
                className="mt-1 block w-full px-3 py-2 bg-dark-card border border-dark-border rounded-md text-dark-text-primary focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent"
              >
                <option value="SECURITY_GUARD">Security Guard</option>
                <option value="SECURITY_INCHARGE">Security Incharge</option>
                <option value="ADMIN">Admin</option>
              </select>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="is_active"
                name="is_active"
                checked={formData.is_active}
                onChange={handleChange}
                className="h-4 w-4 text-ai-blue focus:ring-ai-blue border-dark-border rounded bg-dark-card"
              />
              <label htmlFor="is_active" className="ml-2 block text-sm font-medium text-dark-text-secondary">
                Active User
              </label>
            </div>
          </div>

          <div className="flex justify-between items-center pt-4 border-t border-dark-border">
            <button
              type="button"
              onClick={() => setShowPasswordModal(true)}
              className="px-4 py-2 bg-status-warning text-white rounded-md hover:bg-status-warning/90 transition-colors flex items-center space-x-2 font-semibold"
            >
              <KeyIcon className="h-5 w-5" />
              <span>Change Password</span>
            </button>

            <div className="flex space-x-4">
              <button
                type="button"
                onClick={() => navigate('/personnel')}
                className="px-6 py-2 border border-dark-border rounded-md text-dark-text-secondary hover:bg-dark-card transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting || errors.username || errors.email || !formData.username || !formData.email}
                className="px-6 py-2 bg-ai-blue text-white rounded-md hover:bg-ai-blueDark transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
              >
                {submitting ? 'Updating...' : 'Update User'}
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Password Change Modal */}
      {showPasswordModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 px-4">
          <div className="glass-strong rounded-xl shadow-2xl max-w-md w-full p-6 border border-dark-border">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold text-dark-text-primary">Change User Password</h3>
              <button
                onClick={() => {
                  setShowPasswordModal(false);
                  setPasswordData({ new_password: '', confirm_password: '' });
                }}
                className="text-dark-text-muted hover:text-dark-text-primary"
              >
                <ArrowLeftIcon className="h-6 w-6" />
              </button>
            </div>

            <form onSubmit={handlePasswordSubmit} className="space-y-4">
              <div>
                <label htmlFor="new_password" className="block text-sm font-medium text-dark-text-secondary">
                  New Password *
                </label>
                <input
                  type="password"
                  id="new_password"
                  name="new_password"
                  required
                  value={passwordData.new_password}
                  onChange={handlePasswordChange}
                  onBlur={handlePasswordBlur}
                  className={`mt-1 block w-full px-3 py-2 bg-dark-card border rounded-md text-dark-text-primary placeholder-dark-text-muted focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent ${
                    touched.new_password && errors.new_password
                      ? 'border-status-error focus:border-status-error focus:ring-status-error'
                      : 'border-dark-border'
                  }`}
                  placeholder="Min 8 chars, upper, lower, number, special"
                />
                <p className="mt-1 text-xs text-dark-text-muted">Example: {PASSWORD_EXAMPLE}</p>
                {touched.new_password && errors.new_password && (
                  <p className="mt-1 text-sm text-status-error">{errors.new_password}</p>
                )}
              </div>

              <div>
                <label htmlFor="confirm_password" className="block text-sm font-medium text-dark-text-secondary">
                  Confirm Password *
                </label>
                <input
                  type="password"
                  id="confirm_password"
                  name="confirm_password"
                  required
                  value={passwordData.confirm_password}
                  onChange={handlePasswordChange}
                  onBlur={handlePasswordBlur}
                  className={`mt-1 block w-full px-3 py-2 bg-dark-card border rounded-md text-dark-text-primary placeholder-dark-text-muted focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent ${
                    touched.confirm_password && errors.confirm_password
                      ? 'border-status-error focus:border-status-error focus:ring-status-error'
                      : 'border-dark-border'
                  }`}
                  placeholder="Confirm new password"
                />
                {touched.confirm_password && errors.confirm_password && (
                  <p className="mt-1 text-sm text-status-error">{errors.confirm_password}</p>
                )}
              </div>

              <div className="flex justify-end space-x-4 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowPasswordModal(false);
                    setPasswordData({ new_password: '', confirm_password: '' });
                  }}
                  className="px-4 py-2 border border-dark-border rounded-md text-dark-text-secondary hover:bg-dark-card transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={changingPassword || errors.new_password || errors.confirm_password || !passwordData.new_password || !passwordData.confirm_password}
                  className="px-4 py-2 bg-ai-blue text-white rounded-md hover:bg-ai-blueDark transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
                >
                  {changingPassword ? 'Changing...' : 'Change Password'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Edit;

