import { Outlet } from 'react-router-dom';
import { useRecoilValue } from 'recoil';
import { sidebarOpenState } from '../store/uiStore';
import { authUserState } from '../store/authStore';
import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import TenantContextBanner from '../components/TenantContextBanner';

const AdminLayout = () => {
  const sidebarOpen = useRecoilValue(sidebarOpenState);
  const user = useRecoilValue(authUserState);

  return (
    <div className="min-h-screen bg-dark-bg">
      <Navbar />
      <Sidebar />
      <main
        className={`transition-all duration-300 pt-20 ml-0 ${
          sidebarOpen ? 'lg:ml-64' : 'lg:ml-20'
        }`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-8">
          <TenantContextBanner user={user} />
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default AdminLayout;

