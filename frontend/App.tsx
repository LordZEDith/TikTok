import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import VideoFeed from './components/VideoFeed';
import AuthModal from './components/AuthModal';
import VideoDebug from './components/VideoDebug';
import Profile from './components/Profile';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const refreshToken = async () => {
    try {
      const token = localStorage.getItem('refresh_token');
      if (!token) {
        throw new Error('No refresh token');
      }

      const response = await fetch('/api/auth/refresh', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to refresh token');
      }

      const data = await response.json();
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      return true;
    } catch (err) {
      console.error('Error refreshing token:', err);
      localStorage.removeItem('token');
      localStorage.removeItem('refresh_token');
      return false;
    }
  };

  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('token');
      if (!token) {
        const refreshSuccessful = await refreshToken();
        setIsLoggedIn(refreshSuccessful);
        setIsLoading(false);
        return;
      }

      try {
        const response = await fetch('/api/auth/me', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.ok) {
          setIsLoggedIn(true);
        } else if (response.status === 401) {
          // Token expired, try to refresh
          const refreshSuccessful = await refreshToken();
          setIsLoggedIn(refreshSuccessful);
        } else {
          localStorage.removeItem('token');
          localStorage.removeItem('refresh_token');
        }
      } catch (err) {
        console.error('Auth check error:', err);
        localStorage.removeItem('token');
        localStorage.removeItem('refresh_token');
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();

    // Set up periodic token refresh
    const refreshInterval = setInterval(async () => {
      if (isLoggedIn) {
        const refreshSuccessful = await refreshToken();
        if (!refreshSuccessful) {
          setIsLoggedIn(false);
        }
      }
    }, 25 * 60 * 1000); // Refresh every 25 minutes

    return () => clearInterval(refreshInterval);
  }, [isLoggedIn]);

  // Simple route handling
  const path = window.location.pathname;
  const profileMatch = path.match(/^\/profile\/([^\/]+)$/);

  if (path === '/debug') {
    return <VideoDebug />;
  }

  if (isLoading) {
    return (
      <div className="h-screen bg-black flex items-center justify-center">
        <div className="text-white text-xl">Loading...</div>
      </div>
    );
  }

  if (profileMatch) {
    const userId = profileMatch[1];
    return (
      <div className="min-h-screen bg-black">
        {!isLoggedIn && (
          <AuthModal 
            isOpen={true} 
            onClose={() => {}} 
          />
        )}
        <div className={!isLoggedIn ? 'pointer-events-none' : ''}>
          <Sidebar />
          <main className="ml-[240px] h-screen">
            <Profile userId={userId} />
          </main>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black">
      {!isLoggedIn && (
        <AuthModal 
          isOpen={true} 
          onClose={() => {}} 
        />
      )}
      <div className={!isLoggedIn ? 'pointer-events-none' : ''}>
        <Sidebar />
        <main className="ml-[240px] h-screen">
          <VideoFeed />
        </main>
      </div>
    </div>
  );
}

export default App; 