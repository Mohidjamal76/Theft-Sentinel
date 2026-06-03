import { useEffect, useState } from 'react';
import { useRecoilState } from 'recoil';
import { authUserState } from '../../store/authStore';
import CenteredModal from '../../components/CenteredModal';
import { useModal } from '../../hooks/useModal';
import { changePassword, getProfile } from '../../api/auth';
import { getBranchAdminProfile, updateBranchAdminProfile } from '../../api/tenancy';
import {
  normalizeCNIC,
  normalizePakistaniPhone,
  validateAddress,
  validateCNIC,
  validateCompanyName,
  validateEmail,
  validateName,
  validatePakistaniPhone,
  validatePassword,
} from '../../utils/validation';

const formatApiError = (data, fallback) => {
  if (!data) return fallback;
  if (typeof data === 'string') return data;
  if (data.error || data.message || data.detail) return data.error || data.message || data.detail;
  const messages = Object.entries(data).flatMap(([field, value]) => {
    const values = Array.isArray(value) ? value : [value];
    return values.map((item) => `${field.replace(/_/g, ' ')}: ${item}`);
  });
  return messages.length ? messages.join('\n') : fallback;
};

const TenantProfile = () => {
  const [user, setUser] = useRecoilState(authUserState);
  const { modalState, showSuccess, showError, hideModal } = useModal();
  const [loading, setLoading] = useState(user?.role === 'ADMIN');
  const [saving, setSaving] = useState(false);
  const [profile, setProfile] = useState(null);
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    cnic: '',
    phone_number: '',
    company_name: '',
    branch_name: '',
    address: '',
  });
  const [passwordData, setPasswordData] = useState({
    old_password: '',
    new_password: '',
    confirm_password: '',
  });
  const [changingPassword, setChangingPassword] = useState(false);

  const isBranchAdmin = user?.role === 'ADMIN';

  useEffect(() => {
    const load = async () => {
      if (!isBranchAdmin) {
        setLoading(false);
        return;
      }

      try {
        const res = await getBranchAdminProfile();
        setProfile(res.data);
        setFormData({
          full_name: res.data?.full_name || '',
          email: res.data?.email || '',
          cnic: res.data?.cnic || '',
          phone_number: res.data?.phone_number || '',
          company_name: res.data?.company_name || '',
          branch_name: res.data?.branch_name || '',
          address: res.data?.address || '',
        });
      } catch (err) {
        showError(formatApiError(err.response?.data, 'Failed to load profile.'));
      } finally {
        setLoading(false);
      }
    };

    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isBranchAdmin]);

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    const checks = [
      validateName(formData.full_name),
      validateEmail(formData.email),
      validateCNIC(formData.cnic),
      validatePakistaniPhone(formData.phone_number),
      validateCompanyName(formData.company_name),
      validateCompanyName(formData.branch_name),
      validateAddress(formData.address),
    ];
    const failed = checks.find((check) => !check.valid);
    if (failed) {
      showError(failed.message);
      return;
    }
    setSaving(true);
    try {
      const payload = Object.fromEntries(
        Object.entries(formData).map(([key, value]) => [key, value.trim()])
      );
      payload.phone_number = normalizePakistaniPhone(payload.phone_number);
      payload.cnic = normalizeCNIC(payload.cnic);
      await updateBranchAdminProfile(payload);
      const refreshed = await getProfile();
      setUser(refreshed.data);
      showSuccess('Profile updated.');
      const res = await getBranchAdminProfile();
      setProfile(res.data);
    } catch (err) {
      showError(formatApiError(err.response?.data, 'Profile update failed.'));
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    const passwordCheck = validatePassword(passwordData.new_password);
    if (!passwordCheck.valid) {
      showError(passwordCheck.message);
      return;
    }
    if (passwordData.new_password !== passwordData.confirm_password) {
      showError('Passwords do not match.');
      return;
    }

    setChangingPassword(true);
    try {
      await changePassword({
        old_password: passwordData.old_password,
        new_password: passwordData.new_password,
      });
      setPasswordData({ old_password: '', new_password: '', confirm_password: '' });
      showSuccess('Password changed successfully.');
    } catch (err) {
      showError(formatApiError(err.response?.data, 'Password change failed.'));
    } finally {
      setChangingPassword(false);
    }
  };

  if (loading) {
    return <div className="text-dark-text-muted">Loading...</div>;
  }

  const registrationDate = profile?.registration_date || user?.created_at;

  return (
    <div className="space-y-6">
      <CenteredModal show={modalState.show} type={modalState.type} message={modalState.message} onClose={hideModal} />

      <div>
        <h1 className="text-3xl font-bold text-white">Profile</h1>
        <p className="text-dark-text-muted">
          {isBranchAdmin
            ? 'Manage branch admin and company details.'
            : 'View your branch details and manage your password.'}
        </p>
      </div>

      <div className="glass rounded-2xl border border-white/10 p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Branch Details</h2>
        {isBranchAdmin ? (
          <form onSubmit={handleSave} className="space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                ['full_name', 'Full Name'],
                ['email', 'Email'],
                ['cnic', 'CNIC'],
                ['phone_number', 'Phone Number'],
                ['company_name', 'Company Name'],
                ['branch_name', 'Branch Name'],
              ].map(([field, label]) => (
                <div key={field}>
                  <label className="block text-sm text-dark-text-secondary mb-1">{label}</label>
                  <input
                    type={field === 'email' ? 'email' : 'text'}
                    value={formData[field]}
                    onChange={(e) => handleChange(field, e.target.value)}
                    required
                    className="w-full px-4 py-3 bg-dark-card border border-dark-border rounded-lg text-white"
                  />
                </div>
              ))}
              <div className="md:col-span-2">
                <label className="block text-sm text-dark-text-secondary mb-1">Address</label>
                <input
                  value={formData.address}
                  onChange={(e) => handleChange('address', e.target.value)}
                  className="w-full px-4 py-3 bg-dark-card border border-dark-border rounded-lg text-white"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="glass p-4 rounded-xl border border-white/10">
                <p className="text-xs text-dark-text-muted">Registration Date</p>
                <p className="text-white font-semibold">
                  {registrationDate ? new Date(registrationDate).toLocaleString() : '-'}
                </p>
              </div>
              <div className="glass p-4 rounded-xl border border-white/10">
                <p className="text-xs text-dark-text-muted">Role</p>
                <p className="text-white font-semibold">Branch Admin</p>
              </div>
            </div>

            <button
              type="submit"
              disabled={saving}
              className="w-full py-3 bg-gradient-to-r from-ai-blue to-ai-purple text-dark-bg font-bold rounded-lg disabled:opacity-60"
            >
              {saving ? 'Saving...' : 'Save Profile'}
            </button>
          </form>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              ['Name', user?.username],
              ['Email', user?.email],
              ['Company Name', user?.company_name],
              ['Branch Name', user?.branch_name],
              ['Branch Admin', user?.branch_admin_name],
              ['Admin Contact', user?.branch_admin_phone || user?.branch_admin_email],
              ['Address', user?.company_address],
              ['Registration Date', registrationDate ? new Date(registrationDate).toLocaleString() : '-'],
            ].map(([label, value]) => (
              <div key={label} className="glass p-4 rounded-xl border border-white/10">
                <p className="text-xs text-dark-text-muted">{label}</p>
                <p className="text-white font-semibold">{value || '-'}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="glass rounded-2xl border border-white/10 p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Change Password</h2>
        <form onSubmit={handlePasswordChange} className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <input
            type="password"
            value={passwordData.old_password}
            onChange={(e) => setPasswordData((p) => ({ ...p, old_password: e.target.value }))}
            required
            className="px-4 py-3 bg-dark-card border border-dark-border rounded-lg text-white"
            placeholder="Current password"
          />
          <input
            type="password"
            value={passwordData.new_password}
            onChange={(e) => setPasswordData((p) => ({ ...p, new_password: e.target.value }))}
            required
            className="px-4 py-3 bg-dark-card border border-dark-border rounded-lg text-white"
            placeholder="New password"
          />
          <input
            type="password"
            value={passwordData.confirm_password}
            onChange={(e) => setPasswordData((p) => ({ ...p, confirm_password: e.target.value }))}
            required
            className="px-4 py-3 bg-dark-card border border-dark-border rounded-lg text-white"
            placeholder="Confirm new password"
          />
          <button
            type="submit"
            disabled={changingPassword}
            className="md:col-span-3 py-3 bg-dark-card text-ai-blue border border-ai-blue/30 font-bold rounded-lg disabled:opacity-60 hover:bg-ai-blue/10 transition-colors"
          >
            {changingPassword ? 'Changing...' : 'Change Password'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default TenantProfile;
