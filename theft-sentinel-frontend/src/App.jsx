import { useEffect } from 'react';
import { RecoilRoot, useSetRecoilState } from 'recoil';
import { Toaster } from 'react-hot-toast';
import AppRouter from './router/AppRouter';
import { authUserState, authTokensState } from './store/authStore';
import { getProfile } from './api/auth';

function AppContent() {
  const setAuthUser = useSetRecoilState(authUserState);
  const setAuthTokens = useSetRecoilState(authTokensState);

  useEffect(() => {
    // Check for existing tokens and load user data
    // Only run this if we're not on a public route to avoid unnecessary API calls
    const loadUser = async () => {
      const accessToken = localStorage.getItem('access_token');
      const refreshToken = localStorage.getItem('refresh_token');

      // Only attempt to load user if we have a token and we're not on a public route
      const currentPath = window.location.pathname;
      const isPublicRoute = currentPath === '/' || 
                           currentPath === '/login' || 
                           currentPath.startsWith('/forgot-password') || 
                           currentPath.startsWith('/reset-password') ||
                           currentPath === '/create-super-admin' ||
                           currentPath === '/register-branch';

      if (accessToken && !isPublicRoute) {
        setAuthTokens({ access: accessToken, refresh: refreshToken });
        
        try {
          const response = await getProfile();
          setAuthUser(response.data);
        } catch (error) {
          // Silently handle errors - don't block rendering
          // If token is invalid, clear storage
          if (error.response?.status === 401) {
            localStorage.clear();
            setAuthTokens({ access: null, refresh: null });
            setAuthUser(null);
          }
        }
      } else if (accessToken) {
        // We have a token but we're on a public route - just set tokens without API call
        setAuthTokens({ access: accessToken, refresh: refreshToken });
      }
    };

    loadUser();
  }, [setAuthUser, setAuthTokens]);

  return (
    <>
      <AppRouter />
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 3000,
          style: {
            background: '#363636',
            color: '#fff',
          },
          success: {
            duration: 3000,
            iconTheme: {
              primary: '#10B981',
              secondary: '#fff',
            },
          },
          error: {
            duration: 4000,
            iconTheme: {
              primary: '#EF4444',
              secondary: '#fff',
            },
          },
        }}
      />
    </>
  );
}

function App() {
  return (
    <RecoilRoot>
      <AppContent />
    </RecoilRoot>
  );
}

export default App;

