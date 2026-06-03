/**
 * Reusable frontend validation utilities.
 * Backend serializers enforce the same rules; these helpers keep form feedback immediate.
 */

export const USERNAME_MESSAGE =
  'Username must be 3-30 characters, start with a letter, and contain only letters, numbers, dots, or underscores.';
export const EMAIL_MESSAGE = 'Enter a valid email address.';
export const PASSWORD_MESSAGE =
  'Password must be at least 8 characters and include uppercase, lowercase, number, and special character.';
export const PHONE_MESSAGE = 'Enter a valid Pakistani mobile number (e.g., 03001234567).';
export const CNIC_MESSAGE = 'Enter a valid CNIC (e.g., 35202-1234567-1).';
export const NAME_MESSAGE = 'Name must contain only letters and be at least 2 characters long.';
export const COMPANY_MESSAGE = 'Company name is required.';
export const ADDRESS_MESSAGE = 'Address is required and must be at least 10 characters.';
export const REASON_MESSAGE = 'Please provide a detailed reason (minimum 10 characters).';

export const PASSWORD_EXAMPLE = 'Theft@123';

const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const usernameRegex = /^[A-Za-z][A-Za-z0-9_.]{2,29}$/;
const phoneRegex = /^(\+92|92|0)3[0-9]{9}$/;
const nameRegex = /^[A-Za-z .-]+$/;
const companyRegex = /^[A-Za-z0-9 .&-]+$/;
const streamUrlRegex = /^(rtsp|rtmp|https?):\/\/\S+$/i;

export const trimInput = (value) => (typeof value === 'string' ? value.trim() : value);

export const result = (valid, message = '') => ({ valid, message });

export const validateRequired = (value, message = 'This field is required.') => {
  if (typeof value !== 'string') return value === undefined || value === null ? result(false, message) : result(true);
  return value.trim() ? result(true) : result(false, message);
};

export const validateLength = (value, min, max, message) => {
  const text = trimInput(value || '');
  if (text.length < min || text.length > max) return result(false, message);
  return result(true);
};

export const validateUsername = (username) => {
  const text = trimInput(username || '');
  if (!usernameRegex.test(text)) return result(false, USERNAME_MESSAGE);
  return result(true);
};

export const validateEmail = (email) => {
  const text = trimInput(email || '').toLowerCase();
  if (!emailRegex.test(text) || /\s/.test(text)) return result(false, EMAIL_MESSAGE);
  return result(true);
};

export const validatePassword = (password) => {
  const text = password || '';
  if (
    text.length < 8 ||
    text.length > 128 ||
    /\s/.test(text) ||
    !/[A-Z]/.test(text) ||
    !/[a-z]/.test(text) ||
    !/[0-9]/.test(text) ||
    !/[^A-Za-z0-9\s]/.test(text)
  ) {
    return result(false, PASSWORD_MESSAGE);
  }
  return result(true);
};

export const validatePasswordMatch = (password, confirmPassword) => {
  if (!confirmPassword) return result(false, 'Please confirm your password');
  if (password !== confirmPassword) return result(false, 'Passwords do not match');
  return result(true);
};

export const validatePakistaniPhone = (phone, required = true) => {
  const text = trimInput(phone || '');
  if (!text && !required) return result(true);
  if (!phoneRegex.test(text)) return result(false, PHONE_MESSAGE);
  return result(true);
};

export const normalizePakistaniPhone = (phone) => {
  const text = trimInput(phone || '');
  if (text.startsWith('+92')) return text;
  if (text.startsWith('92')) return `+${text}`;
  if (text.startsWith('0')) return `+92${text.slice(1)}`;
  return text;
};

export const validateCNIC = (cnic) => {
  const text = trimInput(cnic || '');
  const digits = text.replace(/[\s-]+/g, '');
  if (!/^\d{13}$/.test(digits)) return result(false, CNIC_MESSAGE);
  return result(true);
};

export const normalizeCNIC = (cnic) => {
  const digits = trimInput(cnic || '').replace(/[\s-]+/g, '');
  if (digits.length !== 13) return trimInput(cnic || '');
  return `${digits.slice(0, 5)}-${digits.slice(5, 12)}-${digits.slice(12)}`;
};

export const validateName = (name) => {
  const text = trimInput(name || '');
  if (text.length < 2 || text.length > 100 || !nameRegex.test(text) || /^\d+$/.test(text)) {
    return result(false, NAME_MESSAGE);
  }
  return result(true);
};

export const validateCompanyName = (name) => {
  const text = trimInput(name || '');
  if (text.length < 2 || text.length > 150 || !companyRegex.test(text)) {
    return result(false, COMPANY_MESSAGE);
  }
  return result(true);
};

export const validateAddress = (address) => {
  const text = trimInput(address || '');
  if (text.length < 10 || text.length > 300) return result(false, ADDRESS_MESSAGE);
  return result(true);
};

export const validateReason = (reason) => {
  const text = trimInput(reason || '');
  if (text.length < 10 || text.length > 1000) return result(false, REASON_MESSAGE);
  return result(true);
};

export const validateMessage = (message, min = 10, max = 5000) => {
  const text = trimInput(message || '');
  if (text.length < min || text.length > max) {
    return result(false, `Message must be ${min}-${max} characters.`);
  }
  return result(true);
};

export const validateCameraName = (value) => validateLength(value, 2, 100, 'Camera name is required.');
export const validateCameraLocation = (value) => validateLength(value, 2, 150, 'Location is required.');
export const validateStreamUrl = (value) => {
  const text = trimInput(value || '');
  if (!streamUrlRegex.test(text)) {
    return result(false, 'Stream URL must start with rtsp://, rtmp://, http://, or https://.');
  }
  return result(true);
};

export const firstInvalid = (checks) => checks.find((check) => !check.valid) || result(true);

export const scrollToFirstInvalid = () => {
  window.requestAnimationFrame(() => {
    const el = document.querySelector('[aria-invalid="true"], .border-status-error');
    if (el?.scrollIntoView) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      if (typeof el.focus === 'function') el.focus({ preventScroll: true });
    }
  });
};
