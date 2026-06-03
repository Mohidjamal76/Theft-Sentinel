import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import CenteredModal from '../../components/CenteredModal';
import { useModal } from '../../hooks/useModal';
import { registerBranch } from '../../api/tenancy';
import {
  firstInvalid,
  normalizeCNIC,
  normalizePakistaniPhone,
  scrollToFirstInvalid,
  validateAddress,
  validateCNIC,
  validateCompanyName,
  validateEmail,
  validateName,
  validatePakistaniPhone,
  validatePassword,
  validateUsername,
} from '../../utils/validation';

const formatApiError = (data) => {
  if (!data) return 'Registration failed.';
  if (typeof data === 'string') return data;
  if (data.error || data.message || data.detail) {
    return data.error || data.message || data.detail;
  }

  if (typeof data === 'object') {
    const messages = Object.entries(data).flatMap(([field, value]) => {
      const label = field.replace(/_/g, ' ');
      const values = Array.isArray(value) ? value : [value];
      return values.map((item) => `${label}: ${item}`);
    });
    if (messages.length > 0) return messages.join('\n');
  }

  return 'Registration failed.';
};

const BranchRegister = () => {
  const navigate = useNavigate();
  const { modalState, showSuccess, showError, hideModal } = useModal();

  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    company_name: '',
    branch_name: '',
    admin_name: '',
    username: '',
    cnic: '',
    email: '',
    phone_number: '',
    company_address: '',
    password: '',
  });
  const [errors, setErrors] = useState({});

  const handleChange = (e) => {
    setFormData((p) => ({ ...p, [e.target.name]: e.target.value }));
    if (errors[e.target.name]) setErrors((prev) => ({ ...prev, [e.target.name]: '' }));
  };

  const validateForm = () => {
    const checks = [
      ['company_name', validateCompanyName(formData.company_name)],
      ['branch_name', validateCompanyName(formData.branch_name)],
      ['admin_name', validateName(formData.admin_name)],
      ['username', validateUsername(formData.username)],
      ['cnic', validateCNIC(formData.cnic)],
      ['email', validateEmail(formData.email)],
      ['phone_number', validatePakistaniPhone(formData.phone_number)],
      ['company_address', validateAddress(formData.company_address)],
      ['password', validatePassword(formData.password)],
    ];
    const nextErrors = {};
    checks.forEach(([field, check]) => {
      if (!check.valid) nextErrors[field] = check.message;
    });
    setErrors(nextErrors);
    return firstInvalid(checks.map(([, check]) => check)).valid;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      showError('Please fix the validation errors before submitting');
      scrollToFirstInvalid();
      return;
    }

    setLoading(true);
    try {
      const payload = Object.fromEntries(
        Object.entries(formData).map(([key, value]) => [
          key,
          key === 'password'
            ? value
            : key === 'phone_number'
              ? normalizePakistaniPhone(value)
              : key === 'cnic'
                ? normalizeCNIC(value)
                : value.trim(),
        ])
      );

      await registerBranch(payload);
      showSuccess('Registration submitted. Your branch is pending Super Admin approval.');
      setTimeout(() => navigate('/login'), 2000);
    } catch (err) {
      showError(formatApiError(err.response?.data));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-bg px-4 py-12">
      <CenteredModal show={modalState.show} type={modalState.type} message={modalState.message} onClose={hideModal} />

      <div className="w-full max-w-2xl glass-strong rounded-2xl p-8 border border-white/10">
        <h1 className="text-3xl font-bold text-white mb-2">Branch Registration</h1>
        <p className="text-dark-text-muted mb-8">Create your company branch (approval required).</p>

        <form className="space-y-6" onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-dark-text-secondary mb-1">Company Name</label>
              <input
                name="company_name"
                value={formData.company_name}
                onChange={handleChange}
                required
                aria-invalid={!!errors.company_name}
                className={`w-full px-4 py-3 bg-dark-card border rounded-lg text-white ${errors.company_name ? 'border-status-error' : 'border-dark-border'}`}
              />
              {errors.company_name && <p className="mt-1 text-sm text-status-error">{errors.company_name}</p>}
            </div>
            <div>
              <label className="block text-sm text-dark-text-secondary mb-1">Branch Name</label>
              <input
                name="branch_name"
                value={formData.branch_name}
                onChange={handleChange}
                required
                aria-invalid={!!errors.branch_name}
                className={`w-full px-4 py-3 bg-dark-card border rounded-lg text-white ${errors.branch_name ? 'border-status-error' : 'border-dark-border'}`}
              />
              {errors.branch_name && <p className="mt-1 text-sm text-status-error">{errors.branch_name}</p>}
            </div>
            <div>
              <label className="block text-sm text-dark-text-secondary mb-1">Admin Name</label>
              <input
                name="admin_name"
                value={formData.admin_name}
                onChange={handleChange}
                required
                aria-invalid={!!errors.admin_name}
                className={`w-full px-4 py-3 bg-dark-card border rounded-lg text-white ${errors.admin_name ? 'border-status-error' : 'border-dark-border'}`}
              />
              {errors.admin_name && <p className="mt-1 text-sm text-status-error">{errors.admin_name}</p>}
            </div>
            <div>
              <label className="block text-sm text-dark-text-secondary mb-1">Username</label>
              <input
                name="username"
                value={formData.username}
                onChange={handleChange}
                required
                aria-invalid={!!errors.username}
                className={`w-full px-4 py-3 bg-dark-card border rounded-lg text-white ${errors.username ? 'border-status-error' : 'border-dark-border'}`}
              />
              {errors.username && <p className="mt-1 text-sm text-status-error">{errors.username}</p>}
            </div>
            <div>
              <label className="block text-sm text-dark-text-secondary mb-1">CNIC</label>
              <input
                name="cnic"
                value={formData.cnic}
                onChange={handleChange}
                required
                aria-invalid={!!errors.cnic}
                className={`w-full px-4 py-3 bg-dark-card border rounded-lg text-white ${errors.cnic ? 'border-status-error' : 'border-dark-border'}`}
              />
              {errors.cnic && <p className="mt-1 text-sm text-status-error">{errors.cnic}</p>}
            </div>
            <div>
              <label className="block text-sm text-dark-text-secondary mb-1">Email</label>
              <input
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                required
                aria-invalid={!!errors.email}
                className={`w-full px-4 py-3 bg-dark-card border rounded-lg text-white ${errors.email ? 'border-status-error' : 'border-dark-border'}`}
              />
              {errors.email && <p className="mt-1 text-sm text-status-error">{errors.email}</p>}
            </div>
            <div>
              <label className="block text-sm text-dark-text-secondary mb-1">Phone Number (alerts)</label>
              <input
                name="phone_number"
                value={formData.phone_number}
                onChange={handleChange}
                required
                aria-invalid={!!errors.phone_number}
                className={`w-full px-4 py-3 bg-dark-card border rounded-lg text-white ${errors.phone_number ? 'border-status-error' : 'border-dark-border'}`}
              />
              {errors.phone_number && <p className="mt-1 text-sm text-status-error">{errors.phone_number}</p>}
            </div>
          </div>

          <div>
            <label className="block text-sm text-dark-text-secondary mb-1">Company Address</label>
            <input
              name="company_address"
              value={formData.company_address}
              onChange={handleChange}
              required
              aria-invalid={!!errors.company_address}
              className={`w-full px-4 py-3 bg-dark-card border rounded-lg text-white ${errors.company_address ? 'border-status-error' : 'border-dark-border'}`}
            />
            {errors.company_address && <p className="mt-1 text-sm text-status-error">{errors.company_address}</p>}
          </div>

          <div>
            <label className="block text-sm text-dark-text-secondary mb-1">Password</label>
            <input
              name="password"
              type="password"
              value={formData.password}
              onChange={handleChange}
              required
              aria-invalid={!!errors.password}
              className={`w-full px-4 py-3 bg-dark-card border rounded-lg text-white ${errors.password ? 'border-status-error' : 'border-dark-border'}`}
            />
            {errors.password && <p className="mt-1 text-sm text-status-error">{errors.password}</p>}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-ai-blue to-ai-purple text-dark-bg font-bold rounded-lg disabled:opacity-60"
          >
            {loading ? 'Submitting...' : 'Submit Registration'}
          </button>

          <button type="button" onClick={() => navigate('/')} className="w-full py-2 text-sm text-ai-blue">
            ← Back to Home
          </button>
        </form>
      </div>
    </div>
  );
};

export default BranchRegister;

