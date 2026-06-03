import { useState, useEffect } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { useRecoilValue } from 'recoil';
import { authUserState, hasPermission } from '../store/authStore';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const LiveTrackingNodeGraph = () => {
  const [suspectHistory, setSuspectHistory] = useState({});
  const currentUser = useRecoilValue(authUserState);
  const canControlAI = hasPermission(currentUser, 'control_ai_monitoring');

  useEffect(() => {
    const handleSuspectDetected = (e) => {
      const { globalId, cameraName } = e.detail;
      setSuspectHistory(prev => {
        const history = prev[globalId] || [];
        if (history[history.length - 1] === cameraName) return prev; // prevent spam
        return { ...prev, [globalId]: [...history, cameraName] };
      });
    };
    window.addEventListener('ai-suspect-detected', handleSuspectDetected);
    return () => window.removeEventListener('ai-suspect-detected', handleSuspectDetected);
  }, []);

  const handleStopTracking = async (globalId) => {
    if (!canControlAI) return;
    try {
      await axios.post(`${API_BASE_URL}/api/ai/suspects/${globalId}/stop-tracking/`, {}, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });
      toast.success(`Stopped tracking suspect ${globalId}`);
      window.dispatchEvent(new CustomEvent('ai-suspect-cleared', { detail: { globalId } }));

      setSuspectHistory(prev => {
        const next = { ...prev };
        delete next[globalId];
        return next;
      });
    } catch (error) {
      console.error(error);
      toast.error('Failed to stop tracking');
    }
  };

  const activeIds = Object.keys(suspectHistory);

  if (activeIds.length === 0) {
    return (
      <div className="p-4 bg-dark-surface border-t border-dark-border text-dark-text-muted text-center">
        🔴 Live Tracking System Active &mdash; No suspects currently tracked.
      </div>
    );
  }

  return (
    <div className="p-6 bg-dark-surface border-t border-red-900 shadow-[0_-4px_20px_rgba(255,0,0,0.15)]">
      <h2 className="text-2xl font-bold text-dark-text-primary mb-4 flex items-center gap-2">
        <span className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></span>
        Live Tracking Nodes
      </h2>
      <div className="flex flex-col gap-4">
        {activeIds.map(id => (
          <div key={id} className="flex flex-col md:flex-row items-center gap-6 bg-dark-card p-4 rounded-lg border border-dark-border">
            {/* Left Side */}
            <div className="flex flex-col items-center md:items-start gap-2 min-w-[200px]">
              <span className="font-mono font-bold text-lg text-white">Global ID: {id}</span>
              <button
                onClick={() => handleStopTracking(id)}
                disabled={!canControlAI}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Stop Tracking
              </button>
            </div>

            {/* Right Side: Camera Path Graph */}
            <div className="flex flex-wrap items-center gap-2 flex-1 overflow-x-auto p-2">
              {suspectHistory[id].map((camName, index) => (
                <div key={`${camName}-${index}`} className="flex items-center gap-2 shrink-0">
                  <div className="px-4 py-2 bg-ai-blue/20 border border-ai-blue text-ai-blue font-semibold rounded-full shadow-glow-ai">
                    {camName}
                  </div>
                  {index < suspectHistory[id].length - 1 && (
                    <span className="text-ai-blue/50 font-bold">→</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default LiveTrackingNodeGraph;
