import { useState } from 'react';
import { PhotoIcon, ArrowPathIcon, XMarkIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { useAIEngine } from '../../hooks/useAIEngine';
import { fileToBase64, resizeImage, validateImageFile, createImagePreview, revokeImagePreview } from '../../utils/image';

/**
 * Frame Analyzer Component
 * Upload and analyze images for theft detection
 */
const FrameAnalyzer = () => {
  const { loading, error, result, analyze, reset } = useAIEngine();
  const [preview, setPreview] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file
    const validation = validateImageFile(file);
    if (!validation.valid) {
      toast.error(validation.error);
      return;
    }

    // Clear previous results
    reset();
    
    // Create preview
    const previewUrl = createImagePreview(file);
    setPreview(previewUrl);
    setSelectedFile(file);
  };

  const handleAnalyze = async () => {
    if (!selectedFile) {
      toast.error('Please select an image first');
      return;
    }

    try {
      // Resize image for better performance
      const resizedBlob = await resizeImage(selectedFile, 1280, 720, 0.8);
      const resizedFile = new File([resizedBlob], selectedFile.name, { type: 'image/jpeg' });
      
      // Convert to base64
      const base64 = await fileToBase64(resizedFile);

      // Analyze frame
      await analyze({
        frame: base64,
        save_to_db: false,
        create_alert_on_theft: false,
      });

      toast.success('Analysis complete!');
    } catch (err) {
      toast.error(err.message || 'Analysis failed');
    }
  };

  const handleClear = () => {
    if (preview) {
      revokeImagePreview(preview);
    }
    setPreview(null);
    setSelectedFile(null);
    reset();
  };

  return (
    <div className="glass rounded-xl border border-dark-border p-6">
      <h2 className="text-2xl font-bold text-dark-text-primary mb-6">Theft Detection Analysis</h2>

      {/* Upload Section */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-dark-text-secondary mb-2">
          Upload Image for Analysis
        </label>
        <div className="flex items-center gap-3">
          <label className="flex-1 flex items-center justify-center px-4 py-3 border-2 border-dashed border-dark-border rounded-lg cursor-pointer hover:border-ai-blue transition bg-dark-card">
            <PhotoIcon className="h-6 w-6 text-dark-text-muted mr-2" />
            <span className="text-sm text-dark-text-secondary">
              {selectedFile ? selectedFile.name : 'Choose an image...'}
            </span>
            <input
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              className="hidden"
              disabled={loading}
            />
          </label>
          {selectedFile && (
            <button
              onClick={handleClear}
              className="px-4 py-3 bg-dark-card border border-dark-border text-dark-text-secondary rounded-lg hover:bg-dark-surface transition"
              disabled={loading}
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          )}
        </div>
      </div>

      {/* Preview and Analyze Button */}
      {preview && (
        <div className="mb-6">
          <img
            src={preview}
            alt="Preview"
            className="w-full max-h-96 object-contain rounded-lg border border-dark-border mb-3"
          />
          <button
            onClick={handleAnalyze}
            disabled={loading}
            className="w-full px-6 py-3 bg-ai-blue text-white font-semibold rounded-lg hover:bg-ai-blueDark transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center justify-center">
                <ArrowPathIcon className="h-5 w-5 animate-spin mr-2" />
                Analyzing...
              </span>
            ) : (
              'Analyze Frame'
            )}
          </button>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="mb-6 bg-status-error/10 border border-status-error/50 rounded-lg p-4">
          <p className="text-status-error">❌ Error: {error}</p>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-dark-text-primary">Analysis Results</h3>

          {/* Classification Badge */}
          <div className={`p-4 rounded-lg border ${
            result.classification === 'theft'
              ? 'bg-status-error/10 border-status-error'
              : 'bg-status-success/10 border-status-success'
          }`}>
            <div className={`text-2xl font-bold ${result.classification === 'theft' ? 'text-status-error' : 'text-status-success'}`}>
              {result.classification === 'theft' ? '🚨 THEFT DETECTED' : '✓ Normal Activity'}
            </div>
            <div className="mt-2 text-lg text-dark-text-primary">
              Confidence: <span className="font-semibold">{(result.confidence * 100).toFixed(1)}%</span>
            </div>
          </div>

          {/* Statistics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-dark-card border border-dark-border p-4 rounded-lg">
              <p className="text-sm text-dark-text-muted">Objects</p>
              <p className="text-2xl font-bold text-dark-text-primary">{result.objects || 0}</p>
            </div>
            <div className="bg-dark-card border border-dark-border p-4 rounded-lg">
              <p className="text-sm text-dark-text-muted">Persons</p>
              <p className="text-2xl font-bold text-dark-text-primary">{result.persons || 0}</p>
            </div>
            <div className="bg-dark-card border border-dark-border p-4 rounded-lg">
              <p className="text-sm text-dark-text-muted">Tracks</p>
              <p className="text-2xl font-bold text-dark-text-primary">{result.tracks || 0}</p>
            </div>
            <div className="bg-dark-card border border-dark-border p-4 rounded-lg">
              <p className="text-sm text-dark-text-muted">Processing Time</p>
              <p className="text-2xl font-bold text-dark-text-primary">{result.processing_time_ms?.toFixed(0)}ms</p>
            </div>
          </div>

          {/* Suspicious Tracks */}
          {Array.isArray(result.suspicious_tracks) && result.suspicious_tracks.length > 0 && (
            <div className="bg-status-warning/10 border border-status-warning/50 rounded-lg p-4">
              <h4 className="font-semibold text-dark-text-primary mb-3">⚠️ Suspicious Behavior Detected</h4>
              <div className="space-y-3">
                {result.suspicious_tracks.map((track, idx) => {
                  const trackId = track?.track_id ?? idx;
                  const mlScore = typeof track?.ml_score === 'number' ? track.ml_score : 0;
                  const handInBag = track?.behavior?.hand_in_bag ?? 0;
                  const concealmentEvents = track?.behavior?.concealment_events ?? 0;
                  const pocketTouch = track?.behavior?.pocket_touch ?? 0;

                  return (
                    <div key={idx} className="bg-dark-card border border-dark-border p-3 rounded">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold text-dark-text-primary">Track #{trackId}</span>
                        <span className="text-sm font-semibold text-status-warning">
                          Score: {(mlScore * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="text-xs text-dark-text-secondary space-y-1">
                        <div>Hand in bag: <span className="text-dark-text-primary font-medium">{handInBag}</span> frames</div>
                        <div>Concealment events: <span className="text-dark-text-primary font-medium">{concealmentEvents}</span></div>
                        <div>Pocket touch: <span className="text-dark-text-primary font-medium">{pocketTouch}</span> frames</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Alert Info */}
          {result.alert_created && (
            <div className="bg-status-warning/10 border border-status-warning/50 rounded-lg p-4">
              <div className="font-semibold text-dark-text-primary">📢 Alert Created</div>
              <div className="text-sm text-dark-text-secondary mt-1">ID: {result.alert_id}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default FrameAnalyzer;

