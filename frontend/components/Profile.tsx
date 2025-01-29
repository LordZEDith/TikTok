import React, { useState, useEffect, useRef } from 'react';

interface ProfileProps {
  userId: string;
}

interface UserProfile {
  username: string;
  profile_picture_url: string;
  likes_count: number;
  videos: Array<{
    video_id: string;
    title: string;
    views: number;
    thumbnail_url: string;
  }>;
}

interface VideoPreviewProps {
  videoId: string;
  thumbnail: string;
  title: string;
  views: number;
}

const VideoPreview: React.FC<VideoPreviewProps> = ({ videoId, thumbnail, title, views }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isHovering, setIsHovering] = useState(false);

  const handleMouseEnter = () => {
    setIsHovering(true);
    if (videoRef.current) {
      videoRef.current.muted = false;
      videoRef.current.play().catch(err => console.error('Error playing video:', err));
    }
  };

  const handleMouseLeave = () => {
    setIsHovering(false);
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.currentTime = 0;
      videoRef.current.muted = true;
    }
  };

  return (
    <div 
      className="aspect-w-9 aspect-h-16 relative group cursor-pointer"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {isHovering ? (
        <video
          ref={videoRef}
          src={`/api/videos/${videoId}/stream`}
          className="w-full h-full object-cover rounded-lg"
          loop
          playsInline
          muted={true}
          onLoadedMetadata={(e) => {
            const video = e.target as HTMLVideoElement;
            video.volume = 0.5;
          }}
        />
      ) : (
        <img
          src={thumbnail}
          alt={title}
          className="w-full h-full object-cover rounded-lg"
        />
      )}
      <div className="absolute bottom-2 left-2 text-sm">
        <div className="flex items-center space-x-1">
          <span className="text-white">{views.toLocaleString()}</span>
          <span className="text-gray-400">views</span>
        </div>
      </div>
    </div>
  );
};

const Profile: React.FC<ProfileProps> = ({ userId }) => {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const token = localStorage.getItem('token');
        const response = await fetch(`/api/users/${userId}/profile`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (!response.ok) {
          throw new Error('Failed to fetch profile');
        }

        const data = await response.json();
        setProfile(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load profile');
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, [userId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-white text-xl">Loading...</div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-red-500 text-xl">{error || 'Profile not found'}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="max-w-4xl mx-auto pt-16 px-4">
        {/* Profile Header */}
        <div className="flex items-center space-x-6 mb-8">
          <img
            src={profile.profile_picture_url}
            alt={profile.username}
            className="w-24 h-24 rounded-full object-cover"
          />
          <div>
            <h1 className="text-2xl font-bold mb-2">@{profile.username}</h1>
            <div className="flex items-center space-x-4">
              <div>
                <span className="font-bold">{profile.likes_count}</span>
                <span className="text-gray-400 ml-2">Likes</span>
              </div>
            </div>
          </div>
        </div>

        {/* Videos Grid */}
        <div className="grid grid-cols-3 gap-4">
          {profile.videos.map((video) => (
            <VideoPreview
              key={video.video_id}
              videoId={video.video_id}
              thumbnail={video.thumbnail_url}
              title={video.title}
              views={video.views}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default Profile; 