import React, { useState, useEffect } from 'react';
import VideoCard from './VideoCard';

interface Video {
  video_id: string;
  title: string;
  category: string;
  likes: number;
  comments: number;
  views: number;
  user_id: string;
  user: {
    username: string;
    profile_picture_url: string;
  };
}

const VideoFeed: React.FC = () => {
  const [videos, setVideos] = useState<Video[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRecommendedVideos = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setError('Please log in to view videos');
        setLoading(false);
        return;
      }

      const response = await fetch('/api/videos/recommendations', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch videos');
      }

      const data = await response.json();
      const videosWithUserInfo = await Promise.all(data.map(async (video: Video) => {
        const userResponse = await fetch(`/api/users/${video.user_id}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        if (userResponse.ok) {
          const userData = await userResponse.json();
          return {
            ...video,
            user: {
              username: userData.username,
              profile_picture_url: userData.profile_picture_url
            }
          };
        }
        return video;
      }));
      
      setVideos(prev => [...prev, ...videosWithUserInfo]);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load videos');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecommendedVideos();
  }, []);

  useEffect(() => {
    if (currentIndex >= videos.length - 3) {
      fetchRecommendedVideos();
    }
  }, [currentIndex]);

  const handlePrevVideo = () => {
    setCurrentIndex((prev) => Math.max(0, prev - 1));
  };

  const handleNextVideo = () => {
    setCurrentIndex((prev) => Math.min(videos.length - 1, prev + 1));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#FE2C55]"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen text-white">
        <p className="text-lg">{error}</p>
      </div>
    );
  }

  if (videos.length === 0) {
    return (
      <div className="flex items-center justify-center h-screen text-white">
        <p className="text-lg">No videos available</p>
      </div>
    );
  }

  const currentVideo = videos[currentIndex];

  return (
    <div className="flex-1 bg-black">
      <VideoCard
        video={currentVideo}
        isFirst={currentIndex === 0}
        isLast={currentIndex === videos.length - 1}
        onPrevious={handlePrevVideo}
        onNext={handleNextVideo}
      />
    </div>
  );
};

export default VideoFeed; 