import React, { useState, useEffect } from 'react';
import { HomeIcon, MagnifyingGlassIcon, UserIcon, PlusIcon } from '@heroicons/react/24/outline';
import AuthModal from './AuthModal';

const Sidebar: React.FC = () => {
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [username, setUsername] = useState('');
  const [userId, setUserId] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      fetch('/api/auth/me', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      .then(res => {
        if (res.ok) {
          return res.json();
        }
        throw new Error('Invalid token');
      })
      .then(data => {
        setIsLoggedIn(true);
        setUsername(data.username);
        setUserId(data.user_id);
      })
      .catch(() => {
        localStorage.removeItem('token');
        setIsLoggedIn(false);
      });
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsLoggedIn(false);
    window.location.reload();
  };

  return (
    <>
      <div className="w-[240px] h-screen bg-black border-r border-gray-800 flex flex-col fixed left-0 text-white">
        {/* TikTok Title */}
        <div className="p-4 pt-6">
          <h1 className="text-2xl font-bold">TikTok</h1>
        </div>

        {/* Navigation Items */}
        <div className="flex-1">
          <div className="space-y-2">
            <a 
              href="/" 
              className="flex items-center px-4 py-3 text-lg hover:bg-gray-900"
            >
              <HomeIcon className="h-6 w-6 mr-3" />
              For You
            </a>
            <a href="#" className="flex items-center px-4 py-3 text-lg hover:bg-gray-900">
              <MagnifyingGlassIcon className="h-6 w-6 mr-3" />
              Explore
            </a>
            {isLoggedIn && (
              <a href="#" className="flex items-center px-4 py-3 text-lg hover:bg-gray-900">
                <PlusIcon className="h-6 w-6 mr-3" />
                Upload
              </a>
            )}
            {isLoggedIn && (
              <a 
                href={`/profile/${userId}`} 
                className="flex items-center px-4 py-3 text-lg hover:bg-gray-900"
              >
                <UserIcon className="h-6 w-6 mr-3" />
                Profile
              </a>
            )}
          </div>
        </div>

        {/* Login/Logout Button */}
        <div className="p-4">
          {isLoggedIn ? (
            <div className="space-y-2">
              <p className="text-sm text-gray-400">Logged in as: {username}</p>
              <button 
                onClick={handleLogout}
                className="w-full bg-gray-800 text-white rounded-md py-3 font-medium hover:bg-gray-700"
              >
                Log out
              </button>
            </div>
          ) : (
            <button 
              onClick={() => setIsAuthModalOpen(true)}
              className="w-full bg-[#FE2C55] text-white rounded-md py-3 font-medium hover:bg-[#ef233c]"
            >
              Log in
            </button>
          )}
        </div>

        {/* Copyright */}
        <div className="p-4 text-xs text-gray-400">
          © 2025 TikTok Made by ZEDith
        </div>
      </div>

      <AuthModal 
        isOpen={isAuthModalOpen} 
        onClose={() => setIsAuthModalOpen(false)} 
      />
    </>
  );
};

export default Sidebar; 