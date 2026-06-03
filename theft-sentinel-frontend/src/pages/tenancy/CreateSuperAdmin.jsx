import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import CenteredModal from '../../components/CenteredModal';
import { useModal } from '../../hooks/useModal';
import { createSuperAdmin, superAdminExists } from '../../api/tenancy';
import {
  firstInvalid,
  normalizeCNIC,
  normalizePakistaniPhone,
  scrollToFirstInvalid,
  validateCNIC,
  validateEmail,
  validateName,
  validatePakistaniPhone,
  validatePassword,
  validateUsername,
} from '../../utils/validation';

const formatApiError = (data) => {
  if (!data) return 'Failed to create Super Admin.';
  if (typeof data === 'string') return data;
  if (data.error || data.message || data.detail) return data.error || data.message || data.detail;

  if (typeof data === 'object') {
    const messages = Object.entries(data).flatMap(([field, value]) => {
      const label = field.replace(/_/g, ' ');
      const values = Array.isArray(value) ? value : [value];
      return values.map((item) => `${label}: ${item}`);
    });
    if (messages.length > 0) return messages.join('\n');
  }

  return 'Failed to create Super Admin.';
};

const CreateSuperAdmin = () => {
  const navigate = useNavigate();
  const { modalState, showSuccess, showError, hideModal } = useModal();

  const [checking, setChecking] = useState(true);
  const [allowed, setAllowed] = useState(false);
  const [loading, setLoading] = useState(false);

  const [formData, setFormData] = useState({
    full_name: '',
    username: '',
    email: '',
    phone_number: '',
    password: '',
    partners_count: 0,
    partner_names: [],
    partner_cnics: [],
  });
  const [errors, setErrors] = useState({});

  useEffect(() => {
    const check = async () => {
      try {
        const res = await superAdminExists();
        setAllowed(!res.data?.exists);
      } catch {
        setAllowed(false);
      } finally {
        setChecking(false);
      }
    };
    check();
  }, []);

  const setPartnersCount = (count) => {
    const c = Number(count);
    setFormData((p) => {
      const names = [...(p.partner_names || [])].slice(0, c);
      const cnics = [...(p.partner_cnics || [])].slice(0, c);
      while (names.length < c) names.push('');
      while (cnics.length < c) cnics.push('');
      return { ...p, partners_count: c, partner_names: names, partner_cnics: cnics };
    });
  };

  const handleChange = (e) => {
    setFormData((p) => ({ ...p, [e.target.name]: e.target.value }));
    if (errors[e.target.name]) setErrors((prev) => ({ ...prev, [e.target.name]: '' }));
  };

  const handlePartnerChange = (idx, key, value) => {
    setFormData((p) => {
      const arr = [...p[key]];
      arr[idx] = value;
      return { ...p, [key]: arr };
    });
    const errorKey = `${key}_${idx}`;
    if (errors[errorKey]) setErrors((prev) => ({ ...prev, [errorKey]: '' }));
  };

  const validateForm = () => {
    const checks = [
      ['full_name', validateName(formData.full_name)],
      ['phone_number', validatePakistaniPhone(formData.phone_number)],
      ['email', validateEmail(formData.email)],
      ['username', validateUsername(formData.username)],
      ['password', validatePassword(formData.password)],
    ];
    for (let idx = 0; idx < Number(formData.partners_count || 0); idx += 1) {
      checks.push([`partner_names_${idx}`, validateName(formData.partner_names[idx] || '')]);
      checks.push([`partner_cnics_${idx}`, validateCNIC(formData.partner_cnics[idx] || '')]);
    }
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
              : typeof value === 'string'
                ? value.trim()
                : value,
        ])
      );
      payload.partner_names = (payload.partner_names || []).map((name) => name.trim());
      payload.partner_cnics = (payload.partner_cnics || []).map((cnic) => normalizeCNIC(cnic));

      await createSuperAdmin(payload);
      showSuccess('Super Admin created. You can now log in.');
      setTimeout(() => navigate('/login'), 1500);
    } catch (err) {
      showError(formatApiError(err.response?.data));
    } finally {
      setLoading(false);
    }
  };

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-dark-bg">
        <div className="glass-strong rounded-xl p-6 text-center">
          <p className="text-dark-text-secondary">Loading...</p>
        </div>
      </div>
    );
  }

  if (!allowed) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-dark-bg">
        <div className="glass-strong rounded-xl p-8 text-center max-w-lg">
          <h2 className="text-2xl font-bold text-white mb-2">Super Admin Already Exists</h2>
          <p className="text-dark-text-muted mb-6">You can’t create another Super Admin account.</p>
          <button
            onClick={() => navigate('/login')}
            className="px-6 py-3 bg-ai-blue text-dark-bg font-bold rounded-lg"
          >
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-bg px-4 py-12">
      <CenteredModal show={modalState.show} type={modalState.type} message={modalState.message} onClose={hideModal} />

      <div className="w-full max-w-2xl glass-strong rounded-2xl p-8 border border-white/10">
        <h1 className="text-3xl font-bold text-white mb-2">Create Super Admin</h1>
        <p className="text-dark-text-muted mb-8">One-time setup for enterprise multi-tenant management.</p>

        <form className="space-y-6" onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-dark-text-secondary mb-1">Full Name</label>
              <input
                name="full_name"
                value={formData.full_name}
                onChange={handleChange}
                required
                aria-invalid={!!errors.full_name}
                className={`w-full px-4 py-3 bg-dark-card border rounded-lg text-white ${errors.full_name ? 'border-status-error' : 'border-dark-border'}`}
              />
              {errors.full_name && <p className="mt-1 text-sm text-status-error">{errors.full_name}</p>}
            </div>
            <div>
              <label className="block text-sm text-dark-text-secondary mb-1">Phone Number</label>
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
          </div>

          <div>
            <label className="block text-sm text-dark-text-secondary mb-1">Number of Partners (max 3)</label>
            <select
              value={formData.partners_count}
              onChange={(e) => setPartnersCount(e.target.value)}
              className="w-full px-4 py-3 bg-dark-card border border-dark-border rounded-lg text-white"
            >
              <option value={0}>0</option>
              <option value={1}>1</option>
              <option value={2}>2</option>
              <option value={3}>3</option>
            </select>
          </div>

          {formData.partners_count > 0 && (
            <div className="space-y-3">
              {[...Array(formData.partners_count)].map((_, idx) => (
                <div key={idx} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-dark-text-secondary mb-1">Partner Name #{idx + 1}</label>
                    <input
                      value={formData.partner_names[idx] || ''}
                      onChange={(e) => handlePartnerChange(idx, 'partner_names', e.target.value)}
                      required
                      aria-invalid={!!errors[`partner_names_${idx}`]}
                      className={`w-full px-4 py-3 bg-dark-card border rounded-lg text-white ${errors[`partner_names_${idx}`] ? 'border-status-error' : 'border-dark-border'}`}
                    />
                    {errors[`partner_names_${idx}`] && <p className="mt-1 text-sm text-status-error">{errors[`partner_names_${idx}`]}</p>}
                  </div>
                  <div>
                    <label className="block text-sm text-dark-text-secondary mb-1">Partner CNIC #{idx + 1}</label>
                    <input
                      value={formData.partner_cnics[idx] || ''}
                      onChange={(e) => handlePartnerChange(idx, 'partner_cnics', e.target.value)}
                      required
                      aria-invalid={!!errors[`partner_cnics_${idx}`]}
                      className={`w-full px-4 py-3 bg-dark-card border rounded-lg text-white ${errors[`partner_cnics_${idx}`] ? 'border-status-error' : 'border-dark-border'}`}
                    />
                    {errors[`partner_cnics_${idx}`] && <p className="mt-1 text-sm text-status-error">{errors[`partner_cnics_${idx}`]}</p>}
                  </div>
                </div>
              ))}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-ai-blue to-ai-purple text-dark-bg font-bold rounded-lg disabled:opacity-60"
          >
            {loading ? 'Creating...' : 'Create Super Admin'}
          </button>

          <button
            type="button"
            onClick={() => navigate('/')}
            className="w-full py-2 text-sm text-ai-blue"
          >
            ← Back to Home
          </button>
        </form>
      </div>
    </div>
  );
};

export default CreateSuperAdmin;

