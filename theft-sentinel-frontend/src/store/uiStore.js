import { atom } from 'recoil';

// Sidebar state
export const sidebarOpenState = atom({
  key: 'sidebarOpenState',
  default: false,
});

// Loading state
export const loadingState = atom({
  key: 'loadingState',
  default: false,
});

// Modal state
export const modalState = atom({
  key: 'modalState',
  default: {
    isOpen: false,
    type: null,
    data: null,
  },
});

// Notification state
export const notificationState = atom({
  key: 'notificationState',
  default: {
    show: false,
    message: '',
    type: 'info', // info, success, warning, error
  },
});

