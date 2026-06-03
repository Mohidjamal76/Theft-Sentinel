import { useState } from 'react';

export const useModal = () => {
  const [modalState, setModalState] = useState({
    show: false,
    type: 'info',
    message: '',
  });

  const showModal = (type, message) => {
    setModalState({
      show: true,
      type,
      message,
    });
  };

  const hideModal = () => {
    setModalState({
      show: false,
      type: 'info',
      message: '',
    });
  };

  const showSuccess = (message) => showModal('success', message);
  const showError = (message) => showModal('error', message);
  const showWarning = (message) => showModal('warning', message);
  const showInfo = (message) => showModal('info', message);

  return {
    modalState,
    showModal,
    hideModal,
    showSuccess,
    showError,
    showWarning,
    showInfo,
  };
};

