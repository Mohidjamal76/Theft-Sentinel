import { useEffect, useState } from 'react';
import CenteredModal from '../../components/CenteredModal';
import { useModal } from '../../hooks/useModal';
import { deleteSuperAdminAccount, getSuperAdminProfile, updateSuperAdminProfile } from '../../api/tenancy';
import { changePassword } from '../../api/auth';
import {
  normalizeCNIC,
  normalizePakistaniPhone,
  validateCNIC,
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

const Profile = () => {
  const { modalState, showSuccess, showError, hideModal } = useModal();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [profile, setProfile] = useState(null);

  const [formData, setFormData] = useState({
    full_name: '',
    phone_number: '',
    partners_count: 0,
    partner_names: [],
    partner_cnics: [],
  });
  const [passwordData, setPasswordData] = useState({
    old_password: '',
    new_password: '',
    confirm_password: '',
  });

  const load = async () => {
    setLoading(true);
    try {
      const res = await getSuperAdminProfile();
      setProfile(res.data);
      setFormData({
        full_name: res.data?.full_name || '',
        phone_number: res.data?.phone_number || '',
        partners_count: res.data?.partners_count || 0,
        partner_names: (res.data?.partners || []).map((p) => p.name || ''),
        partner_cnics: (res.data?.partners || []).map((p) => p.cnic || ''),
      });
    } catch (err) {
      showError(err.response?.data?.error || 'Failed to load profile.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  const handlePartnerChange = (idx, key, value) => {
    setFormData((p) => {
      const arr = [...p[key]];
      arr[idx] = value;
      return { ...p, [key]: arr };
    });
  };

  const handleSave = async (e) => {
    e.preventDefault();
    const payload = {
      ...formData,
      full_name: formData.full_name.trim(),
      phone_number: formData.phone_number.trim(),
      partners_count: Number(formData.partners_count || 0),
      partner_names: (formData.partner_names || []).slice(0, Number(formData.partners_count || 0)).map((name) => name.trim()),
      partner_cnics: (formData.partner_cnics || []).slice(0, Number(formData.partners_count || 0)).map((cnic) => cnic.trim()),
    };

    const nameCheck = validateName(payload.full_name);
    if (!nameCheck.valid) {
      showError(nameCheck.message);
      return;
    }
    const phoneCheck = validatePakistaniPhone(payload.phone_number);
    if (!phoneCheck.valid) {
      showError(phoneCheck.message);
      return;
    }
    payload.phone_number = normalizePakistaniPhone(payload.phone_number);

    for (let idx = 0; idx < payload.partners_count; idx += 1) {
      const partnerNameCheck = validateName(payload.partner_names[idx]);
      if (!partnerNameCheck.valid) {
        showError(`Partner name #${idx + 1}: ${partnerNameCheck.message}`);
        return;
      }
      const partnerCnicCheck = validateCNIC(payload.partner_cnics[idx]);
      if (!partnerCnicCheck.valid) {
        showError(`Partner CNIC #${idx + 1}: ${partnerCnicCheck.message}`);
        return;
      }
    }
    payload.partner_cnics = payload.partner_cnics.map((cnic) => normalizeCNIC(cnic));

    setSaving(true);
    try {
      await updateSuperAdminProfile(payload);
      showSuccess('Profile updated.');
      await load();
    } catch (err) {
      showError(formatApiError(err.response?.data, 'Update failed.'));
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

  const handleDelete = async () => {
    if (!confirm('Delete Super Admin account? Allowed only when all branches are deleted.')) return;
    try {
      await deleteSuperAdminAccount();
      showSuccess('Account deleted.');
      setTimeout(() => {
        localStorage.clear();
        window.location.href = '/';
      }, 1000);
    } catch (err) {
      showError(err.response?.data?.error || 'Delete failed.');
    }
  };

  if (loading) return <div className="text-dark-text-muted">Loading...</div>;
  if (!profile) return <div className="text-dark-text-muted">No profile.</div>;

  return (
    <div className="space-y-6">
      <CenteredModal show={modalState.show} type={modalState.type} message={modalState.message} onClose={hideModal} />

      <div>
        <h1 className="text-3xl font-bold text-white">Super Admin Profile</h1>
        <p className="text-dark-text-muted">Manage profile details, partners, and password security.</p>
      </div>

      <div className="glass rounded-2xl border border-white/10 p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Profile Details</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div>
            <p className="text-xs text-dark-text-muted">Email</p>
            <p className="text-white font-semibold">{profile.email}</p>
          </div>
          <div>
            <p className="text-xs text-dark-text-muted">Created</p>
            <p className="text-white font-semibold">
              {profile.created_at ? new Date(profile.created_at).toLocaleString() : '-'}
            </p>
          </div>
        </div>

        <form onSubmit={handleSave} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-dark-text-secondary mb-1">Full Name</label>
              <input
                value={formData.full_name}
                onChange={(e) => setFormData((p) => ({ ...p, full_name: e.target.value }))}
                required
                className="w-full px-4 py-3 bg-dark-card border border-dark-border rounded-lg text-white"
              />
            </div>
            <div>
              <label className="block text-sm text-dark-text-secondary mb-1">Phone Number</label>
              <input
                value={formData.phone_number}
                onChange={(e) => setFormData((p) => ({ ...p, phone_number: e.target.value }))}
                required
                className="w-full px-4 py-3 bg-dark-card border border-dark-border rounded-lg text-white"
              />
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
              <h3 className="text-sm font-semibold text-white">Partner Details</h3>
              {[...Array(formData.partners_count)].map((_, idx) => (
                <div key={idx} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-dark-text-secondary mb-1">Partner Name #{idx + 1}</label>
                    <input
                      value={formData.partner_names[idx] || ''}
                      onChange={(e) => handlePartnerChange(idx, 'partner_names', e.target.value)}
                      className="w-full px-4 py-3 bg-dark-card border border-dark-border rounded-lg text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-dark-text-secondary mb-1">Partner CNIC #{idx + 1}</label>
                    <input
                      value={formData.partner_cnics[idx] || ''}
                      onChange={(e) => handlePartnerChange(idx, 'partner_cnics', e.target.value)}
                      className="w-full px-4 py-3 bg-dark-card border border-dark-border rounded-lg text-white"
                    />
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="flex flex-col sm:flex-row gap-3">
            <button
              type="submit"
              disabled={saving}
              className="w-full py-3 bg-gradient-to-r from-ai-blue to-ai-purple text-dark-bg font-bold rounded-lg disabled:opacity-60"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
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

      <div className="glass rounded-2xl border border-status-error/20 p-6">
        <h2 className="text-xl font-semibold text-white mb-2">Account Removal</h2>
        <p className="text-dark-text-muted text-sm mb-4">
          Account deletion is allowed only after all branches are deleted.
        </p>
        <button
          type="button"
          onClick={handleDelete}
          className="w-full py-3 bg-status-error/20 text-status-error border border-status-error/30 font-bold rounded-lg"
        >
          Delete Account
        </button>
      </div>
    </div>
  );
};

export default Profile;

