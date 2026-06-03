import { useNavigate } from 'react-router-dom';
import { 
  VideoCameraIcon, 
  BellAlertIcon, 
  ChatBubbleLeftIcon,
  ArrowRightIcon,
  ShieldCheckIcon
} from '@heroicons/react/24/outline';
import { useRecoilValue } from 'recoil';
import { authUserState } from '../../store/authStore';

/**
 * Guard Dashboard Overview
 * Quick access to Control Room, Alerts, and Feedback
 */
const GuardDashboard = () => {
  const navigate = useNavigate();
  const user = useRecoilValue(authUserState);

  const quickActions = [
    {
      title: 'Control Room',
      description: 'View live camera feeds and monitor security cameras',
      icon: VideoCameraIcon,
      path: '/cameras/control-room',
      color: 'from-ai-blue to-cyan-400',
      bgColor: 'bg-ai-blue/10',
      iconColor: 'text-ai-blue',
    },
    {
      title: 'Alerts',
      description: 'View and acknowledge real-time security alerts',
      icon: BellAlertIcon,
      path: '/alerts/guard',
      color: 'from-status-error to-red-500',
      bgColor: 'bg-status-error/10',
      iconColor: 'text-status-error',
    },
    {
      title: 'Submit Feedback',
      description: 'Report incidents, false positives, or provide feedback',
      icon: ChatBubbleLeftIcon,
      path: '/feedback/create',
      color: 'from-status-success to-green-500',
      bgColor: 'bg-status-success/10',
      iconColor: 'text-status-success',
    },
  ];

  return (
    <div className="space-y-8">
      {/* Welcome Header */}
      <div className="glass rounded-xl border border-dark-border p-8">
        <div className="flex items-center gap-4 mb-4">
          <div className="w-16 h-16 bg-gradient-to-br from-ai-blue to-cyan-400 rounded-xl flex items-center justify-center shadow-glow-ai">
            <ShieldCheckIcon className="h-8 w-8 text-white" />
          </div>
          <div>
            <h1 className="text-4xl font-bold text-dark-text-primary mb-2">
              Welcome, <span className="text-gradient-ai">{user?.username || 'Guard'}</span>
            </h1>
            <p className="text-dark-text-muted">Security Operations Dashboard</p>
          </div>
        </div>
      </div>

      {/* Quick Actions Grid */}
      <div>
        <h2 className="text-2xl font-bold text-dark-text-primary mb-6">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {quickActions.map((action) => {
            const Icon = action.icon;
            return (
              <button
                key={action.path}
                onClick={() => navigate(action.path)}
                className="group glass rounded-xl border border-dark-border p-6 text-left hover:border-ai-blue/50 transition-all duration-300 transform hover:scale-[1.02] hover:shadow-glow-ai"
              >
                <div className={`w-14 h-14 ${action.bgColor} rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300`}>
                  <Icon className={`h-7 w-7 ${action.iconColor}`} />
                </div>
                <h3 className="text-xl font-bold text-dark-text-primary mb-2 group-hover:text-ai-blue transition-colors">
                  {action.title}
                </h3>
                <p className="text-dark-text-muted text-sm mb-4 leading-relaxed">
                  {action.description}
                </p>
                <div className="flex items-center gap-2 text-ai-blue font-semibold text-sm group-hover:gap-3 transition-all duration-300">
                  <span>Open</span>
                  <ArrowRightIcon className="h-4 w-4" />
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Additional Links */}
      <div className="glass rounded-xl border border-dark-border p-6">
        <h3 className="text-lg font-semibold text-dark-text-primary mb-4">Other Resources</h3>
        <div className="flex flex-wrap gap-4">
          <button
            onClick={() => navigate('/incidents/my')}
            className="px-4 py-2 glass border border-dark-border rounded-lg text-dark-text-primary hover:border-ai-blue/50 hover:text-ai-blue transition-all duration-200 text-sm font-medium"
          >
            My Incidents
          </button>
          <button
            onClick={() => navigate('/feedback/my')}
            className="px-4 py-2 glass border border-dark-border rounded-lg text-dark-text-primary hover:border-ai-blue/50 hover:text-ai-blue transition-all duration-200 text-sm font-medium"
          >
            My Feedback
          </button>
        </div>
      </div>
    </div>
  );
};

export default GuardDashboard;

