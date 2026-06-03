import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { useRecoilState, useRecoilValue, useSetRecoilState } from 'recoil';
import { sidebarOpenState } from '../store/uiStore';
import { authUserState, authTokensState } from '../store/authStore';
import {
  HomeIcon,
  VideoCameraIcon,
  BellAlertIcon,
  ExclamationTriangleIcon,
  ChatBubbleLeftIcon,
  UsersIcon,
  Bars3Icon,
  XMarkIcon,
  ArrowRightOnRectangleIcon,
  CpuChipIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';
import { logout } from '../api/auth';
import CenteredModal from './CenteredModal';
import { useModal } from '../hooks/useModal';

const Sidebar = () => {
  const [sidebarOpen, setSidebarOpen] = useRecoilState(sidebarOpenState);
  const user = useRecoilValue(authUserState);
  const setAuthUser = useSetRecoilState(authUserState);
  const setAuthTokens = useSetRecoilState(authTokensState);
  const location = useLocation();
  const navigate = useNavigate();
  const { modalState, showSuccess, hideModal } = useModal();

  const isActive = (path) => {
    return location.pathname.startsWith(path);
  };

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      // Even if logout fails, clear local state
      console.error('Logout error:', error);
    } finally {
      // Clear all auth state
      localStorage.clear();
      setAuthUser(null);
      setAuthTokens({ access: null, refresh: null });
      
      showSuccess('Logged out successfully');
      // Smooth redirect to login
      setTimeout(() => {
        navigate('/login', { replace: true });
      }, 1000);
    }
  };

  const menuItems = {
    SUPER_ADMIN: [
      { name: 'Branches', path: '/super-admin/branches', icon: UsersIcon },
      { name: 'Reset Requests', path: '/super-admin/reset-requests', icon: ChatBubbleLeftIcon },
      { name: 'Queries', path: '/super-admin/queries', icon: BellAlertIcon },
      { name: 'Profile', path: '/super-admin/profile', icon: HomeIcon },
    ],
    ADMIN: [
      { name: 'Dashboard', path: '/dashboard', icon: HomeIcon },
      { name: 'Historical Reporting', path: '/dashboard/historical-reporting', icon: ChartBarIcon },
      { name: 'Control Room', path: '/cameras/control-room', icon: VideoCameraIcon },
      { name: 'Alerts', path: '/alerts', icon: BellAlertIcon },
      { name: 'Incidents', path: '/incidents', icon: ExclamationTriangleIcon },
      { name: 'AI Dashboard', path: '/ai/dashboard', icon: CpuChipIcon },
      { name: 'Feedback', path: '/feedback', icon: ChatBubbleLeftIcon },
      { name: 'Personnel', path: '/personnel', icon: UsersIcon },
      { name: 'Support', path: '/support/queries', icon: ChatBubbleLeftIcon },
      { name: 'Profile', path: '/profile', icon: HomeIcon },
    ],
    SECURITY_INCHARGE: [
      { name: 'Dashboard', path: '/dashboard', icon: HomeIcon },
      { name: 'Historical Reporting', path: '/dashboard/historical-reporting', icon: ChartBarIcon },
      { name: 'Alerts', path: '/alerts', icon: BellAlertIcon },
      { name: 'Incidents', path: '/incidents', icon: ExclamationTriangleIcon },
      { name: 'Control Room', path: '/cameras/control-room', icon: VideoCameraIcon },
      { name: 'AI Dashboard', path: '/ai/dashboard', icon: CpuChipIcon },
      { name: 'Support', path: '/support/queries', icon: ChatBubbleLeftIcon },
      { name: 'Profile', path: '/profile', icon: HomeIcon },
    ],
    SECURITY_GUARD: [
      { name: 'Dashboard', path: '/dashboard/guard', icon: HomeIcon },
      { name: 'Control Room', path: '/cameras/control-room', icon: VideoCameraIcon },
      { name: 'Alerts', path: '/alerts/guard', icon: BellAlertIcon },
      { name: 'My Incidents', path: '/incidents/my', icon: ExclamationTriangleIcon },
      { name: 'Feedback', path: '/feedback/my', icon: ChatBubbleLeftIcon },
      { name: 'Support', path: '/support/queries', icon: ChatBubbleLeftIcon },
      { name: 'Profile', path: '/profile', icon: HomeIcon },
    ],
  };

  const items = menuItems[user?.role] || [];

  useEffect(() => {
    const syncSidebarForViewport = () => {
      setSidebarOpen(window.innerWidth >= 1024);
    };

    syncSidebarForViewport();
    window.addEventListener('resize', syncSidebarForViewport);
    return () => window.removeEventListener('resize', syncSidebarForViewport);
  }, [setSidebarOpen]);

  const closeOnSmallScreen = () => {
    if (window.innerWidth < 1024) setSidebarOpen(false);
  };

  return (
    <>
      <CenteredModal
        show={modalState.show}
        type={modalState.type}
        message={modalState.message}
        onClose={hideModal}
      />

      {/* Mobile toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="lg:hidden fixed top-3 left-3 z-[70] p-2 bg-dark-card border border-dark-border rounded-lg text-dark-text-primary shadow-dark hover:bg-dark-surface transition-colors"
        aria-label={sidebarOpen ? 'Close navigation menu' : 'Open navigation menu'}
      >
        {sidebarOpen ? <XMarkIcon className="h-6 w-6" /> : <Bars3Icon className="h-6 w-6" />}
      </button>

      {/* Sidebar */}
      <div
        className={`fixed left-0 top-16 h-[calc(100vh-4rem)] w-72 bg-dark-surface border-r border-dark-border transition-all duration-300 z-50 lg:z-30 overflow-y-auto ${
          sidebarOpen ? 'translate-x-0 lg:w-64' : '-translate-x-full lg:translate-x-0 lg:w-20'
        }`}
      >
        <nav className="mt-4">
          <ul className="space-y-1 px-3">
            {items.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.path);

              return (
                <li key={item.path}>
                  <Link
                    to={item.path}
                    onClick={closeOnSmallScreen}
                    className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200 group ${
                      active
                        ? 'bg-gradient-to-r from-ai-blue/20 to-ai-purple/20 text-ai-blue border-l-4 border-ai-blue shadow-glow-ai'
                        : 'text-dark-text-secondary hover:bg-dark-card hover:text-ai-blue'
                    }`}
                  >
                    <Icon className={`h-6 w-6 flex-shrink-0 ${active ? 'text-ai-blue' : 'group-hover:text-ai-blue transition-colors'}`} />
                    {sidebarOpen && (
                      <span className={`whitespace-nowrap font-medium ${active ? 'text-ai-blue' : ''}`}>
                        {item.name}
                      </span>
                    )}
                  </Link>
                </li>
              );
            })}

            {/* Logout Button */}
            <li className="pt-4 border-t border-dark-border mt-4">
              <button
                onClick={handleLogout}
                className="w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200 
                         hover:bg-status-error/20 hover:text-status-error text-dark-text-secondary group"
              >
                <ArrowRightOnRectangleIcon className="h-6 w-6 flex-shrink-0 group-hover:text-status-error transition-colors" />
                {sidebarOpen && <span className="whitespace-nowrap font-medium">Logout</span>}
              </button>
            </li>
          </ul>
        </nav>
      </div>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-dark-bg/80 backdrop-blur-sm z-40 top-16"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </>
  );
};

export default Sidebar;
