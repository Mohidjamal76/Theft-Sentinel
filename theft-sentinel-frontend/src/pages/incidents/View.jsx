import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useRecoilValue } from 'recoil';
import { authUserState } from '../../store/authStore';
import { getIncident, updateIncidentStatus, assignIncident, deleteIncident } from '../../api/incidents';
import { listUsers } from '../../api/auth';
import toast from 'react-hot-toast';
import { ArrowLeftIcon, TrashIcon } from '@heroicons/react/24/outline';
import { validateMessage } from '../../utils/validation';

const View = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const user = useRecoilValue(authUserState);
  const [incident, setIncident] = useState(null);
  const [guards, setGuards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [newStatus, setNewStatus] = useState('');
  const [notes, setNotes] = useState(''); // CORRECTED: 'notes' instead of 'resolution'
  const [selectedGuard, setSelectedGuard] = useState('');

  const canEditStatus = user?.role === 'SECURITY_GUARD' && incident?.assigned_to === user?.id;
  const canAssign = user?.role === 'ADMIN' || user?.role === 'SECURITY_INCHARGE';
  const canDelete = (user?.role === 'ADMIN' || user?.role === 'SECURITY_INCHARGE') && incident?.status === 'RESOLVED';
  const isPending = incident?.status === 'CREATED' || incident?.status === 'ASSIGNED';

  useEffect(() => {
    fetchData();
  }, [id]);

  const fetchData = async () => {
    try {
      const incidentRes = await getIncident(id);
      setIncident(incidentRes.data);
      setNewStatus(incidentRes.data.status);

      // Only fetch guards if user can assign (Admin/Incharge)
      if (user?.role === 'ADMIN' || user?.role === 'SECURITY_INCHARGE') {
        try {
          const response = await listUsers({ role: 'SECURITY_GUARD' });
          // Handle paginated response: {count, results, next, previous} or direct array
          const guardsList = response.data?.results || response.data || [];
          setGuards(Array.isArray(guardsList) ? guardsList : []);
        } catch (guardsError) {
          // Don't fail the entire page load if guards fetch fails
          console.error('Error fetching guards:', guardsError);
          setGuards([]);
        }
      }
    } catch (error) {
      console.error('Error fetching incident:', error);
      console.error('Error response:', error.response?.data);
      toast.error('Failed to load incident details');
      // Navigate back based on user role
      if (user?.role === 'SECURITY_GUARD') {
        navigate('/incidents/my');
      } else {
        navigate('/incidents');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateStatus = async () => {
    if (notes.trim()) {
      const notesCheck = validateMessage(notes, 1, 1000);
      if (!notesCheck.valid) {
        toast.error(notesCheck.message);
        return;
      }
    }
    setUpdating(true);
    try {
      // CORRECTED: notes parameter instead of resolution
      await updateIncidentStatus(id, newStatus, notes.trim());
      toast.success('Incident status updated successfully');
      fetchData();
      setNotes(''); // Clear notes after update
    } catch (error) {
      console.error('Error updating status:', error);
      toast.error('Failed to update incident status');
    } finally {
      setUpdating(false);
    }
  };

  const handleAssign = async () => {
    if (!selectedGuard) {
      toast.error('Please select a guard');
      return;
    }

    setUpdating(true);
    try {
      // CORRECTED: assignIncident requires (id, assigned_to, notes)
      await assignIncident(id, selectedGuard, 'Assigned from incident details page');
      toast.success('Incident assigned successfully');
      fetchData();
      setSelectedGuard(''); // Clear selection after assignment
    } catch (error) {
      console.error('Error assigning incident:', error);
      toast.error('Failed to assign incident');
    } finally {
      setUpdating(false);
    }
  };

  const handleResolve = async () => {
    if (notes.trim()) {
      const notesCheck = validateMessage(notes, 1, 1000);
      if (!notesCheck.valid) {
        toast.error(notesCheck.message);
        return;
      }
    }
    setUpdating(true);
    try {
      await updateIncidentStatus(id, 'RESOLVED', notes.trim());
      toast.success('Incident resolved successfully');
      fetchData();
      setNotes('');
    } catch (error) {
      console.error('Error resolving incident:', error);
      toast.error('Failed to resolve incident');
    } finally {
      setUpdating(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this incident? This action cannot be undone.')) {
      return;
    }

    setUpdating(true);
    try {
      await deleteIncident(id);
      toast.success('Incident deleted successfully');
      navigate('/incidents');
    } catch (error) {
      console.error('Error deleting incident:', error);
      const errorMsg = error.response?.data?.error || error.response?.data?.detail || 'Failed to delete incident';
      toast.error(errorMsg);
    } finally {
      setUpdating(false);
    }
  };

  if (loading) {
    return <div className="animate-pulse h-96 bg-dark-card rounded-lg border border-dark-border"></div>;
  }

  if (!incident) return null;

  const statusColors = {
    CREATED: 'bg-status-warning/20 text-status-warning border border-status-warning/50',
    ASSIGNED: 'bg-status-info/20 text-status-info border border-status-info/50',
    ACKNOWLEDGED: 'bg-ai-purple/20 text-ai-purple border border-ai-purple/50',
    RESOLVED: 'bg-status-success/20 text-status-success border border-status-success/50',
  };
  const detectionClipUrl = incident.detection_clip_url || incident.alert_details?.video_url;
  const clipMetadata = incident.detection_clip_metadata || {};

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-4">
        <button
          onClick={() => {
            // Navigate back based on user role
            if (user?.role === 'SECURITY_GUARD') {
              navigate('/incidents/my');
            } else {
              navigate('/incidents');
            }
          }}
          className="p-2 hover:bg-dark-card rounded-full transition-colors"
        >
          <ArrowLeftIcon className="h-6 w-6 text-dark-text-secondary" />
        </button>
        <h1 className="text-3xl font-bold text-dark-text-primary">Incident Details</h1>
      </div>

      <div className="glass rounded-xl border border-dark-border p-6">
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-start justify-between pb-6 border-b border-dark-border">
            <div>
              <h2 className="text-2xl font-bold text-dark-text-primary">
                Incident #{incident.id}
              </h2>
              {incident.alert_details && (
                <p className="text-dark-text-secondary mt-2">
                  Alert: {incident.alert_details.alert_type || 'Unknown Alert Type'}
                </p>
              )}
            </div>
            <span className={`px-4 py-2 rounded-full text-sm font-semibold ${statusColors[incident.status] || 'bg-dark-card text-dark-text-muted border border-dark-border'}`}>
              {isPending ? 'PENDING' : (incident.status?.replace('_', ' ') || 'Unknown')}
            </span>
          </div>

          {/* Alert Details */}
          {incident.alert_details && (
            <div className="bg-dark-card rounded-lg p-6 mb-6 border border-dark-border">
              <h3 className="text-lg font-semibold text-dark-text-primary mb-4">Alert Details</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <h4 className="text-sm font-medium text-dark-text-muted">Camera</h4>
                  <p className="text-lg font-semibold text-dark-text-primary mt-1">
                    {incident.alert_details.camera_name || 'Unknown'}
                  </p>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-dark-text-muted">Zone</h4>
                  <p className="text-lg font-semibold text-dark-text-primary mt-1">
                    {incident.alert_details.camera_details?.zone || 'N/A'}
                  </p>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-dark-text-muted">Timestamp</h4>
                  <p className="text-lg font-semibold text-dark-text-primary mt-1">
                    {new Date(incident.alert_details.timestamp).toLocaleString()}
                  </p>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-dark-text-muted">Severity</h4>
                  <p className="text-lg font-semibold text-dark-text-primary mt-1">
                    {incident.alert_details.severity || 'Unknown'}
                  </p>
                </div>
                {incident.alert_details.metadata?.confidence && (
                  <div>
                    <h4 className="text-sm font-medium text-dark-text-muted">AI Confidence</h4>
                    <p className="text-lg font-semibold text-dark-text-primary mt-1">
                      {(incident.alert_details.metadata.confidence * 100).toFixed(1)}%
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Detection Clip */}
          <div className="bg-dark-card rounded-lg p-6 border border-dark-border">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
              <h3 className="text-lg font-semibold text-dark-text-primary">Detection Clip</h3>
              {clipMetadata.available && (
                <span className="text-xs font-medium px-2 py-1 rounded-full bg-status-success/20 text-status-success border border-status-success/40">
                  Available
                </span>
              )}
            </div>

            {detectionClipUrl ? (
              <div className="rounded-lg overflow-hidden border border-dark-border bg-black">
                <video
                  controls
                  playsInline
                  preload="metadata"
                  className="w-full max-h-[480px] object-contain bg-black"
                >
                  <source src={detectionClipUrl} type="video/mp4" />
                  <source src={detectionClipUrl} type="video/webm" />
                  Your browser does not support the video element.
                </video>
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 px-4 py-3 bg-dark-surface border-t border-dark-border">
                  <div className="text-xs text-dark-text-muted space-y-1">
                    {clipMetadata.alert_timestamp && (
                      <p>Captured: {new Date(clipMetadata.alert_timestamp).toLocaleString()}</p>
                    )}
                    {typeof clipMetadata.confidence === 'number' && (
                      <p>Confidence: {(clipMetadata.confidence * 100).toFixed(1)}%</p>
                    )}
                  </div>
                  <a
                    href={detectionClipUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-ai-blue hover:underline font-medium"
                  >
                    Open clip
                  </a>
                </div>
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-dark-border bg-dark-surface p-6 text-center">
                <p className="text-dark-text-secondary font-medium">No detection clip is available for this incident.</p>
                <p className="text-xs text-dark-text-muted mt-2">Older incidents or alerts without uploaded clips will show this fallback.</p>
              </div>
            )}
          </div>

          {/* Details Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-sm font-medium text-dark-text-muted">Assigned To</h3>
              <p className="text-lg font-semibold text-dark-text-primary mt-1">
                {incident.assigned_to_details?.username || incident.assigned_to_name || 'Unassigned'}
              </p>
            </div>
            {incident.assigned_by_details && (
              <div>
                <h3 className="text-sm font-medium text-dark-text-muted">Assigned By</h3>
                <p className="text-lg font-semibold text-dark-text-primary mt-1">
                  {incident.assigned_by_details.username} ({incident.assigned_by_details.role === 'ADMIN' ? 'Admin' : 'Security In-Charge'})
                </p>
              </div>
            )}
            <div>
              <h3 className="text-sm font-medium text-dark-text-muted">Created At</h3>
              <p className="text-lg font-semibold text-dark-text-primary mt-1">
                {new Date(incident.created_at).toLocaleString()}
              </p>
            </div>
          </div>

          {/* Admin/Incharge View - Assignment and Deletion */}
          {canAssign && (
            <>
              {/* Assignment Section */}
              {!incident.assigned_to_details && (
                <div className="border-t border-dark-border pt-6">
                  <h3 className="text-lg font-semibold text-dark-text-primary mb-4">Assign Incident</h3>
                  <div className="flex space-x-4">
                    <select
                      value={selectedGuard}
                      onChange={(e) => setSelectedGuard(e.target.value)}
                      className="flex-1 px-4 py-2 bg-dark-card border border-dark-border rounded-md text-dark-text-primary focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent"
                    >
                      <option value="">-- Select Guard --</option>
                      {guards.map((guard) => (
                        <option key={guard.id} value={guard.id}>
                          {guard.username} ({guard.email})
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={handleAssign}
                      disabled={updating || !selectedGuard}
                      className="px-6 py-2 bg-ai-blue text-white rounded-md hover:bg-ai-blueDark transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
                    >
                      {updating ? 'Assigning...' : 'Assign'}
                    </button>
                  </div>
                </div>
              )}

              {/* Deletion Section - Only for RESOLVED incidents */}
              {canDelete && (
                <div className="border-t border-dark-border pt-6">
                  <h3 className="text-lg font-semibold text-dark-text-primary mb-4">Delete Incident</h3>
                  <p className="text-sm text-dark-text-secondary mb-4">
                    This incident has been resolved. You can delete it permanently.
                  </p>
                  <button
                    onClick={handleDelete}
                    disabled={updating}
                    className="px-6 py-2 bg-status-error text-white rounded-md hover:bg-status-error/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 font-semibold"
                  >
                    <TrashIcon className="h-5 w-5" />
                    <span>{updating ? 'Deleting...' : 'Delete Incident'}</span>
                  </button>
                </div>
              )}

              {/* Warning for PENDING incidents */}
              {isPending && (
                <div className="border-t border-dark-border pt-6">
                  <div className="bg-status-warning/10 border border-status-warning/50 rounded-lg p-4">
                    <p className="text-sm text-status-warning">
                      <strong>Note:</strong> This incident is still PENDING. It cannot be deleted until it is resolved.
                    </p>
                  </div>
                </div>
              )}
            </>
          )}

          {/* Guard View - Resolve Button */}
          {canEditStatus && (
            <div className="border-t border-dark-border pt-6">
              <h3 className="text-lg font-semibold text-dark-text-primary mb-4">Resolve Incident</h3>
              <p className="text-sm text-dark-text-secondary mb-4">
                This incident was assigned to you by an Administrator or Security In-Charge.
              </p>
              {isPending ? (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-dark-text-secondary mb-2">
                      Resolution Notes (Optional)
                    </label>
                    <textarea
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      rows="4"
                      className="w-full px-4 py-2 bg-dark-card border border-dark-border rounded-md text-dark-text-primary placeholder-dark-text-muted focus:outline-none focus:ring-2 focus:ring-ai-blue focus:border-transparent"
                      placeholder="Add notes about the resolution..."
                    ></textarea>
                  </div>
                  <button
                    onClick={handleResolve}
                    disabled={updating}
                    className="px-6 py-2 bg-status-success text-white rounded-md hover:bg-status-success/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
                  >
                    {updating ? 'Resolving...' : 'Resolve Incident'}
                  </button>
                </div>
              ) : (
                <div className="bg-status-success/10 border border-status-success/50 rounded-lg p-4">
                  <p className="text-sm text-status-success">
                    This incident has been resolved.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Notes */}
          {incident.notes && (
            <div className="border-t border-dark-border pt-6">
              <h3 className="text-lg font-semibold text-dark-text-primary mb-2">Notes</h3>
              <p className="text-dark-text-secondary">{incident.notes}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default View;

