import React from 'react';
import { VideoCameraIcon, ChatBubbleLeftIcon } from '@heroicons/react/24/outline';

interface SidebarProps {
  selectedTab: 'videos' | 'comments';
  onTabChange: (tab: 'videos' | 'comments') => void;
}

const Sidebar: React.FC<SidebarProps> = ({ selectedTab, onTabChange }) => {
  return (
    <div className="fixed w-64 h-screen bg-gray-800 shadow-lg border-r border-gray-700">
      <div className="p-6">
        <h1 className="text-2xl font-bold text-gray-100">Admin Panel</h1>
      </div>
      
      <nav className="mt-6">
        <div 
          className={`flex items-center px-6 py-4 cursor-pointer ${
            selectedTab === 'videos' 
              ? 'bg-gray-700 text-gray-100' 
              : 'text-gray-400 hover:bg-gray-700 hover:text-gray-100'
          }`}
          onClick={() => onTabChange('videos')}
        >
          <VideoCameraIcon className="w-6 h-6" />
          <span className="ml-3">Pending Videos</span>
        </div>
        
        <div 
          className={`flex items-center px-6 py-4 cursor-pointer ${
            selectedTab === 'comments'
              ? 'bg-gray-700 text-gray-100'
              : 'text-gray-400 hover:bg-gray-700 hover:text-gray-100'
          }`}
          onClick={() => onTabChange('comments')}
        >
          <ChatBubbleLeftIcon className="w-6 h-6" />
          <span className="ml-3">Pending Comments</span>
        </div>
      </nav>
      
      <div className="absolute bottom-0 w-full p-6">
        <p className="text-sm text-gray-400">Admin Control Panel</p>
      </div>
    </div>
  );
};

export default Sidebar; 