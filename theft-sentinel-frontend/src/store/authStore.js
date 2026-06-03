import { atom, selector } from 'recoil';

// Auth user atom
export const authUserState = atom({
  key: 'authUserState',
  default: null,
});

// Auth tokens atom
export const authTokensState = atom({
  key: 'authTokensState',
  default: {
    access: localStorage.getItem('access_token'),
    refresh: localStorage.getItem('refresh_token'),
  },
});

// Is authenticated selector
export const isAuthenticatedState = selector({
  key: 'isAuthenticatedState',
  get: ({ get }) => {
    const tokens = get(authTokensState);
    return !!tokens.access;
  },
});

// User role selector
export const userRoleState = selector({
  key: 'userRoleState',
  get: ({ get }) => {
    const user = get(authUserState);
    return user?.role || null;
  },
});

// Permission helpers
export const hasPermission = (user, permission) => {
  if (!user) return false;
  
  const rolePermissions = {
    ADMIN: ['all'],
    SECURITY_INCHARGE: [
      'view_alerts',
      'acknowledge_alerts',
      'view_incidents',
      'assign_incidents',
      'view_cameras',
      'view_tracking',
      'view_personnel',
      'control_ai_monitoring',   // Security Incharge can start / stop AI monitors
    ],
    GUARD: [
      'view_my_incidents',
      'update_my_incidents',
      'create_feedback',
      'view_my_feedback',
    ],
  };

  const permissions = rolePermissions[user.role] || [];
  return permissions.includes('all') || permissions.includes(permission);
};

