import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axiosInstance from '../../api/axios';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';
import CenteredModal from '../../components/CenteredModal';
import { useModal } from '../../hooks/useModal';
import { validateEmail, validateUsername, validatePassword, validatePasswordMatch, trimInput, PASSWORD_EXAMPLE } from '../../utils/validation';

const Create = () => {
  const navigate = useNavigate();
  const { modalState, showSuccess, showError, hideModal } = useModal();
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    password2: '',
    role: 'SECURITY_GUARD',
  });
  const [errors, setErrors] = useState({
    username: '',
    email: '',
    password: '',
    password2: '',
  });
  const [touched, setTouched] = useState({
    username: false,
    email: false,
    password: false,
    password2: false,
  });
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    // Trim input to prevent leading/trailing spaces
    const trimmedValue = trimInput(value);
    
    setFormData({
      ...formData,
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

  const handleBlur = (e) => {
    const { name, value } = e.target;
    setTouched({ ...touched, [name]: true });

    // Validate on blur
    let validation = { valid: true, message: '' };
    
    if (name === 'username') {
      validation = validateUsername(value);
    } else if (name === 'email') {
      validation = validateEmail(value);
    } else if (name === 'password') {
      validation = validatePassword(value);
    } else if (name === 'password2') {
      validation = validatePasswordMatch(formData.password, value);
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
      password: '',
      password2: '',
    };

    const usernameValidation = validateUsername(formData.username);
    if (!usernameValidation.valid) {
      newErrors.username = usernameValidation.message;
    }

    const emailValidation = validateEmail(formData.email);
    if (!emailValidation.valid) {
      newErrors.email = emailValidation.message;
    }

    const passwordValidation = validatePassword(formData.password);
    if (!passwordValidation.valid) {
      newErrors.password = passwordValidation.message;
    }

    const passwordMatchValidation = validatePasswordMatch(formData.password, formData.password2);
    if (!passwordMatchValidation.valid) {
      newErrors.password2 = passwordMatchValidation.message;
    }

    setErrors(newErrors);
    setTouched({
      username: true,
      email: true,
      password: true,
      password2: true,
    });

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
    if (loading) {
      return;
    }

    setLoading(true);

    try {
      // Call the /auth/register/ endpoint
      const response = await axiosInstance.post('/api/auth/register/', {
        username: formData.username,
        email: formData.email,
        password: formData.password,
        password2: formData.password2,
        role: formData.role,
      });
      
      console.log('✅ User created successfully:', response.data);
      showSuccess('User created successfully');
      
      // Clear form
      setFormData({
        username: '',
        email: '',
        password: '',
        password2: '',
        role: 'SECURITY_GUARD',
      });

      // Navigate after showing success message
      setTimeout(() => {
        navigate('/personnel');
      }, 1500);
    } catch (error) {
      console.error('❌ Error creating user:', error);
      console.error('❌ Error response:', error.response?.data);
      
      // Handle validation errors
      const errorData = error.response?.data;
      let errorMsg = 'Failed to create user';
      
      if (errorData) {
        // Handle Admin uniqueness error
        if (errorData.role && Array.isArray(errorData.role)) {
          errorMsg = errorData.role[0] || 'Admin role already exists. Only one Admin is allowed.';
        } else if (errorData.username) {
          errorMsg = `Username: ${errorData.username[0]}`;
        } else if (errorData.email) {
          errorMsg = `Email: ${errorData.email[0]}`;
        } else if (errorData.password) {
          errorMsg = `Password: ${errorData.password[0]}`;
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
      setLoading(false);
    }
  };

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
        <h1 className="text-3xl font-bold text-dark-text-primary">Add User</h1>
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
                value={formData.username}
                onChange={handleChange}
                onBlur={handleBlur}
                className={`mt-1 block w-full px-3 py-2 bg-dark-card border rounded-md text-dark-text-primary placeholder-dark-text-muted focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent ${
                  touched.username && errors.username
                    ? 'border-status-error focus:border-status-error focus:ring-status-error'
                    : 'border-dark-border'
                }`}
                placeholder="Enter username (e.g., john_doe)"
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
                value={formData.email}
                onChange={handleChange}
                onBlur={handleBlur}
                className={`mt-1 block w-full px-3 py-2 bg-dark-card border rounded-md text-dark-text-primary placeholder-dark-text-muted focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent ${
                  touched.email && errors.email
                    ? 'border-status-error focus:border-status-error focus:ring-status-error'
                    : 'border-dark-border'
                }`}
                placeholder="Enter email (e.g., abc_123@gmail.com)"
              />
              {touched.email && errors.email && (
                <p className="mt-1 text-sm text-status-error">{errors.email}</p>
              )}
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-dark-text-secondary">
                Password *
              </label>
              <input
                type="password"
                id="password"
                name="password"
                required
                value={formData.password}
                onChange={handleChange}
                onBlur={handleBlur}
                className={`mt-1 block w-full px-3 py-2 bg-dark-card border rounded-md text-dark-text-primary placeholder-dark-text-muted focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent ${
                  touched.password && errors.password
                    ? 'border-status-error focus:border-status-error focus:ring-status-error'
                    : 'border-dark-border'
                }`}
                placeholder="Min 8 chars, upper, lower, number, special"
              />
              <p className="mt-1 text-xs text-dark-text-muted">Example: {PASSWORD_EXAMPLE}</p>
              {touched.password && errors.password && (
                <p className="mt-1 text-sm text-status-error">{errors.password}</p>
              )}
            </div>

            <div>
              <label htmlFor="password2" className="block text-sm font-medium text-dark-text-secondary">
                Confirm Password *
              </label>
              <input
                type="password"
                id="password2"
                name="password2"
                required
                value={formData.password2}
                onChange={handleChange}
                onBlur={handleBlur}
                className={`mt-1 block w-full px-3 py-2 bg-dark-card border rounded-md text-dark-text-primary placeholder-dark-text-muted focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent ${
                  touched.password2 && errors.password2
                    ? 'border-status-error focus:border-status-error focus:ring-status-error'
                    : 'border-dark-border'
                }`}
                placeholder="Re-enter password"
              />
              {touched.password2 && errors.password2 && (
                <p className="mt-1 text-sm text-status-error">{errors.password2}</p>
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
          </div>

          <div className="flex justify-end space-x-4">
            <button
              type="button"
              onClick={() => navigate('/personnel')}
              className="px-6 py-2 border border-dark-border rounded-md text-dark-text-secondary hover:bg-dark-card transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || Object.values(errors).some(error => error !== '') || !formData.username || !formData.email || !formData.password || !formData.password2}
              className="px-6 py-2 bg-ai-blue text-white rounded-md hover:bg-ai-blueDark transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
            >
              {loading ? 'Creating...' : 'Create User'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Create;

