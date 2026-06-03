import { useState, useEffect, useRef } from 'react';
import { useRecoilValue } from 'recoil';
import { listUsers, deleteUser } from '../../api/auth';
import Table, { Pagination } from '../../components/Table';
import { useNavigate, useLocation } from 'react-router-dom';
import { PlusIcon } from '@heroicons/react/24/outline';
import CenteredModal from '../../components/CenteredModal';
import ConfirmationModal from '../../components/ConfirmationModal';
import { useModal } from '../../hooks/useModal';
import { authUserState } from '../../store/authStore';

const ADMIN_SELF_DELETE_MESSAGE = 'Admin cannot delete their own account.';

const List = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const authUser = useRecoilValue(authUserState);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const { modalState, showSuccess, showError, hideModal } = useModal();
  const [deleteConfirmation, setDeleteConfirmation] = useState({ show: false, user: null });
  const prevLocationRef = useRef(location.pathname);

  useEffect(() => {
    fetchUsers();
  }, [currentPage]);

  // Refresh when navigating back from edit page
  useEffect(() => {
    // If we navigated back to this page from another page, refresh
    if (prevLocationRef.current !== location.pathname && location.pathname === '/personnel') {
      fetchUsers();
    }
    prevLocationRef.current = location.pathname;
  }, [location.pathname]);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const response = await listUsers({ page: currentPage });
      setUsers(response.data.results || response.data);
      setTotalPages(Math.ceil((response.data.count || users.length) / 10));
    } catch (error) {
      console.error('Error fetching users:', error);
      showError('Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const isAdminDeletingSelf = (user) =>
    authUser?.role === 'ADMIN' && user && String(user.id) === String(authUser.id);

  const handleDeleteClick = (user) => {
    if (isAdminDeletingSelf(user)) {
      showError(ADMIN_SELF_DELETE_MESSAGE);
      return;
    }
    setDeleteConfirmation({ show: true, user });
  };

  const handleDeleteConfirm = async () => {
    const targetUser = deleteConfirmation.user;
    if (isAdminDeletingSelf(targetUser)) {
      setDeleteConfirmation({ show: false, user: null });
      showError(ADMIN_SELF_DELETE_MESSAGE);
      return;
    }

    const userId = targetUser.id;
    setDeleteConfirmation({ show: false, user: null });

    try {
      await deleteUser(userId);
      showSuccess('User deleted successfully');
      fetchUsers();
    } catch (error) {
      console.error('Error deleting user:', error);
      const errorMsg =
        error.response?.data?.detail ||
        error.response?.data?.error ||
        error.response?.data?.message ||
        'Failed to delete user';
      showError(errorMsg);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteConfirmation({ show: false, user: null });
  };

  const columns = [
    { key: 'username', label: 'Username' },
    { key: 'email', label: 'Email' },
    { 
      key: 'role', 
      label: 'Role',
      render: (row) => (
        <span className={`px-2 py-1 rounded text-xs font-semibold border ${
          row.role === 'ADMIN' ? 'bg-ai-purple/20 text-ai-purple border-ai-purple/50' :
          row.role === 'SECURITY_INCHARGE' ? 'bg-status-info/20 text-status-info border-status-info/50' :
          'bg-status-success/20 text-status-success border-status-success/50'
        }`}>
          {row.role}
        </span>
      )
    },
    { 
      key: 'is_active', 
      label: 'Status',
      render: (row) => (
        <span className={`px-2 py-1 rounded text-xs font-semibold border ${
          row.is_active ? 'bg-status-success/20 text-status-success border-status-success/50' : 'bg-status-error/20 text-status-error border-status-error/50'
        }`}>
          {row.is_active ? 'Active' : 'Inactive'}
        </span>
      )
    },
    {
      key: 'actions',
      label: 'Actions',
      render: (row) => (
        <div className="flex space-x-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              navigate(`/personnel/edit/${row.id}`);
            }}
            className="px-3 py-1 bg-ai-blue text-white rounded hover:bg-ai-blueDark text-sm font-medium"
          >
            View/Edit
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleDeleteClick(row);
            }}
            className="px-3 py-1 bg-status-error text-white rounded hover:bg-status-error/90 text-sm font-medium"
          >
            Delete
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <CenteredModal
        show={modalState.show}
        type={modalState.type}
        message={modalState.message}
        onClose={hideModal}
      />

      <ConfirmationModal
        show={deleteConfirmation.show}
        title="Delete User"
        message={`Are you sure you want to delete user "${deleteConfirmation.user?.username}"? This action cannot be undone.`}
        onConfirm={handleDeleteConfirm}
        onCancel={handleDeleteCancel}
        confirmText="Delete"
        cancelText="Cancel"
        type="danger"
      />
      
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-dark-text-primary">User Management</h1>
        <button
          onClick={() => navigate('/personnel/create')}
          className="px-4 py-2 bg-ai-blue text-white rounded-md hover:bg-ai-blueDark transition-colors flex items-center space-x-2 font-semibold"
        >
          <PlusIcon className="h-5 w-5" />
          <span>Add User</span>
        </button>
      </div>

      <Table columns={columns} data={users} loading={loading} />

      {totalPages > 1 && (
        <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={setCurrentPage} />
      )}
    </div>
  );
};

export default List;

