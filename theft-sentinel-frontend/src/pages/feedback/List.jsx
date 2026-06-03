import { useState, useEffect } from 'react';
import { listFeedback, adminDeleteFeedback } from '../../api/feedback';
import Table, { Pagination } from '../../components/Table';
import { useNavigate } from 'react-router-dom';
import { PlusIcon, TrashIcon } from '@heroicons/react/24/outline';
import CenteredModal from '../../components/CenteredModal';
import ConfirmationModal from '../../components/ConfirmationModal';
import { useModal } from '../../hooks/useModal';

const List = () => {
  const navigate = useNavigate();
  const [feedback, setFeedback] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const { modalState, showSuccess, showError, hideModal } = useModal();
  const [deleteConfirmation, setDeleteConfirmation] = useState({ show: false, feedback: null });

  useEffect(() => {
    fetchFeedback();
  }, [currentPage]);

  const fetchFeedback = async () => {
    setLoading(true);
    try {
      const response = await listFeedback({ page: currentPage });
      const feedbackList = Array.isArray(response.data) ? response.data : (response.data.results || []);
      setFeedback(feedbackList);
      setTotalPages(Math.ceil((response.data.count || feedbackList.length) / 10));
    } catch (error) {
      console.error('Error fetching feedback:', error);
      showError('Failed to load feedback');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteClick = (feedbackItem) => {
    setDeleteConfirmation({ show: true, feedback: feedbackItem });
  };

  const handleDeleteConfirm = async () => {
    const feedbackId = deleteConfirmation.feedback.id;
    setDeleteConfirmation({ show: false, feedback: null });
    
    try {
      await adminDeleteFeedback(feedbackId);
      showSuccess('Feedback deleted successfully');
      fetchFeedback();
    } catch (error) {
      console.error('Error deleting feedback:', error);
      const errorMsg = error.response?.data?.detail || error.response?.data?.error || 'Failed to delete feedback';
      showError(errorMsg);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteConfirmation({ show: false, feedback: null });
  };

  const columns = [
    {       key: 'type', label: 'Type', render: (row) => (
      <span className="px-2 py-1 bg-status-info/20 text-status-info border border-status-info/50 rounded text-xs font-semibold">
        {row.type || 'GENERAL'}
      </span>
    )},
    { key: 'message', label: 'Message', render: (row) => (
      <span className="text-sm text-dark-text-primary line-clamp-2">{row.message}</span>
    )},
    { key: 'user_name', label: 'Submitted By', render: (row) => row.user_name || row.user_id },
    { key: 'created_at', label: 'Date', render: (row) => new Date(row.created_at).toLocaleDateString() },
    {
      key: 'actions',
      label: 'Actions',
      render: (row) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleDeleteClick(row);
          }}
          className="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600 text-sm flex items-center space-x-1"
        >
          <TrashIcon className="h-4 w-4" />
          <span>Delete</span>
        </button>
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
        title="Delete Feedback"
        message={`Are you sure you want to delete this feedback? This action cannot be undone.`}
        onConfirm={handleDeleteConfirm}
        onCancel={handleDeleteCancel}
        confirmText="Delete"
        cancelText="Cancel"
        type="danger"
      />

      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-white">Feedback Management</h1>
        <button
          onClick={() => navigate('/feedback/create')}
          className="px-4 py-2 bg-ai-blue text-white rounded-md hover:bg-ai-blueDark transition-colors flex items-center space-x-2 font-semibold"
        >
          <PlusIcon className="h-5 w-5" />
          <span>Submit Feedback</span>
        </button>
      </div>

      <Table columns={columns} data={feedback} loading={loading} />

      {totalPages > 1 && (
        <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={setCurrentPage} />
      )}
    </div>
  );
};

export default List;

