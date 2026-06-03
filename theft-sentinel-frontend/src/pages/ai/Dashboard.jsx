import AIHealthStatus from '../../components/AI/AIHealthStatus';
import AIModelInfo from '../../components/AI/AIModelInfo';
import FrameAnalyzer from '../../components/AI/FrameAnalyzer';

/**
 * AI Dashboard Page
 * Main dashboard for AI system status and frame analysis
 */
const AIDashboard = () => {
  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">AI Dashboard</h1>
        <p className="text-dark-text-secondary mt-1">Manage and monitor AI theft detection system</p>
      </div>

      {/* Status Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <AIHealthStatus />
        <AIModelInfo />
      </div>

      {/* Frame Analyzer */}
      <FrameAnalyzer />
    </div>
  );
};

export default AIDashboard;

