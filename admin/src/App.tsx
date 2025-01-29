import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ContentModeration from './components/ContentModeration';

function App() {
  const [selectedTab, setSelectedTab] = useState<'videos' | 'comments'>('videos');

  return (
    <div className="min-h-screen bg-gray-900">
      <div className="flex">
        {/* Sidebar */}
        <Sidebar selectedTab={selectedTab} onTabChange={setSelectedTab} />
        
        {/* Main content */}
        <main className="flex-1 p-8 ml-64">
          <ContentModeration type={selectedTab} />
        </main>
      </div>
    </div>
  );
}

export default App; 