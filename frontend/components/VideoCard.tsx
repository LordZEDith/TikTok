import React, { useRef, useState, useEffect, lazy, Suspense } from 'react';
import { FaHeart, FaComment, FaShare, FaUser } from 'react-icons/fa';
import { IoIosArrowUp, IoIosArrowDown } from 'react-icons/io';
import { HiVolumeUp, HiVolumeOff } from 'react-icons/hi';

const Comments = lazy(() => import('./Comments'));

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

interface VideoCardProps {
  video: Video;
  isFirst: boolean;
  isLast: boolean;
  onPrevious: () => void;
  onNext: () => void;
}

const VideoCard: React.FC<VideoCardProps> = ({
  video,
  isFirst,
  isLast,
  onPrevious,
  onNext
}) => {
  const videoUrl = `/api/videos/${video.video_id}/stream`;
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isMuted, setIsMuted] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isLiked, setIsLiked] = useState(false);
  const [likesCount, setLikesCount] = useState(video.likes);
  const [commentsCount, setCommentsCount] = useState(video.comments);
  const [showComments, setShowComments] = useState(false);
  const [hasRecordedView, setHasRecordedView] = useState(false);

  useEffect(() => {
    setIsLoading(true);
    setError(null);
    setLikesCount(video.likes);
    setCommentsCount(video.comments);
    setHasRecordedView(false);

    const fetchVideoData = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) return;

        const videoResponse = await fetch(`/api/videos/${video.video_id}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (videoResponse.ok) {
          const videoData = await videoResponse.json();
          setLikesCount(videoData.likes);
          setCommentsCount(videoData.comments);
        }

        const likeResponse = await fetch(`/api/videos/${video.video_id}/like-status`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (likeResponse.ok) {
          const { liked } = await likeResponse.json();
          setIsLiked(liked);
        }
      } catch (err) {
        console.error('Error fetching video data:', err);
      }
    };

    fetchVideoData();
  }, [video.video_id]);

  useEffect(() => {
    const handleTimeUpdate = () => {
      if (videoRef.current && !hasRecordedView && videoRef.current.currentTime >= 3) {
        // Record view after 3 seconds
        const recordView = async () => {
          try {
            const token = localStorage.getItem('token');
            if (!token) return;

            await fetch(`/api/videos/${video.video_id}/view`, {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
              }
            });
            setHasRecordedView(true);
          } catch (err) {
            console.error('Error recording view:', err);
          }
        };

        recordView();
      }
    };

    if (videoRef.current) {
      videoRef.current.addEventListener('timeupdate', handleTimeUpdate);
    }

    return () => {
      if (videoRef.current) {
        videoRef.current.removeEventListener('timeupdate', handleTimeUpdate);
      }
    };
  }, [video.video_id, hasRecordedView]);

  const handleVideoClick = () => {
    if (videoRef.current) {
      if (videoRef.current.paused) {
        videoRef.current.play();
      } else {
        videoRef.current.pause();
      }
    }
  };

  const toggleMute = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (videoRef.current) {
      videoRef.current.muted = !videoRef.current.muted;
      setIsMuted(!isMuted);
    }
  };

  const handleVideoError = (e: React.SyntheticEvent<HTMLVideoElement, Event>) => {
    console.error('Video Error:', e);
    const videoElement = e.target as HTMLVideoElement;
    setError(`Failed to load video: ${videoElement.error?.message || 'Unknown error'}`);
    setIsLoading(false);
  };

  const handleVideoLoadStart = () => {
    setIsLoading(true);
    setError(null);
  };

  const handleVideoCanPlay = () => {
    setIsLoading(false);
    setError(null);
  };

  const handleLike = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        return;
      }

      const response = await fetch(`/api/videos/${video.video_id}/like`, {
        method: isLiked ? 'DELETE' : 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        setIsLiked(!isLiked);
        setLikesCount(prev => isLiked ? prev - 1 : prev + 1);
      }
    } catch (err) {
      console.error('Error toggling like:', err);
    }
  };

  const handleComment = () => {
    setShowComments(!showComments);
  };

  const handleCommentCountUpdate = (newCount: number) => {
    setCommentsCount(newCount);
  };

  const handleProfileClick = () => {
    window.location.href = `/profile/${video.user_id}`;
  };

  return (
    <div className="w-full h-screen flex items-center justify-center snap-start">
      <div className="relative w-[500px] h-[89vh] max-w-[500px]">
        {/* Video Container */}
        <div className="w-full h-full bg-black rounded-lg overflow-hidden relative">
          <style>
            {`
              video::-webkit-media-controls {
                display: none !important;
              }
              video::-webkit-media-controls-panel {
                display: none !important;
              }
            `}
          </style>
          <video
            ref={videoRef}
            key={video.video_id}
            className="w-full h-full cursor-pointer"
            src={videoUrl}
            autoPlay
            playsInline
            loop
            disablePictureInPicture
            controlsList="nodownload nofullscreen noplaybackrate"
            onClick={handleVideoClick}
            style={{
              objectFit: 'contain',
              backgroundColor: 'black'
            }}
            onError={handleVideoError}
            onLoadStart={handleVideoLoadStart}
            onCanPlay={handleVideoCanPlay}
          />

          {/* Loading Indicator */}
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-white"></div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50">
              <div className="text-white text-center p-4 bg-red-500 rounded-lg">
                {error}
              </div>
            </div>
          )}

          {/* Volume Control */}
          <button
            onClick={toggleMute}
            className="absolute bottom-4 right-4 z-20 w-10 h-10 bg-gray-900/80 rounded-full flex items-center justify-center hover:bg-gray-700/80"
          >
            {isMuted ? (
              <HiVolumeOff className="w-6 h-6 text-white" />
            ) : (
              <HiVolumeUp className="w-6 h-6 text-white" />
            )}
          </button>
        </div>
        
        {/* User Info - Positioned at the bottom of the video */}
        <div className="absolute left-4 bottom-6 z-10 max-w-[80%]">
          <div 
            className="flex items-center gap-3 cursor-pointer hover:opacity-90"
            onClick={handleProfileClick}
          >
            <img 
              src={video.user.profile_picture_url || '/default-avatar.png'} 
              alt={video.user.username}
              className="w-12 h-12 rounded-full object-cover border-2 border-white"
            />
            <div>
              <h3 className="font-semibold text-white text-lg">{video.user.username}</h3>
              <p className="text-white text-sm mt-1">{video.title}</p>
              <p className="text-white/80 text-sm mt-1">{video.category}</p>
            </div>
          </div>
        </div>

        {/* Interaction Buttons */}
        <div className="absolute -right-24 bottom-20 space-y-6 z-10">
          {/* Profile Button */}
          <button 
            className="flex flex-col items-center"
            onClick={handleProfileClick}
          >
            <div className="w-16 h-16 bg-gray-900/80 rounded-full flex items-center justify-center hover:bg-gray-700/80 overflow-hidden">
              <img 
                src={video.user.profile_picture_url || '/default-avatar.png'}
                alt={video.user.username}
                className="w-full h-full object-cover"
              />
            </div>
          </button>

          {/* Like Button */}
          <button className="flex flex-col items-center" onClick={handleLike}>
            <div className={`w-16 h-16 ${isLiked ? 'bg-[#FE2C55]' : 'bg-gray-900/80'} rounded-full flex items-center justify-center hover:bg-gray-700/80`}>
              <FaHeart className={`w-8 h-8 ${isLiked ? 'text-white' : 'text-white'}`} />
            </div>
            <span className="text-white text-sm font-medium mt-1.5">{likesCount.toLocaleString()}</span>
          </button>
          
          {/* Comment Button */}
          <button className="flex flex-col items-center" onClick={handleComment}>
            <div className={`w-16 h-16 ${showComments ? 'bg-[#FE2C55]' : 'bg-gray-900/80'} rounded-full flex items-center justify-center hover:bg-gray-700/80`}>
              <FaComment className="w-8 h-8 text-white" />
            </div>
            <span className="text-white text-sm font-medium mt-1.5">{commentsCount.toLocaleString()}</span>
          </button>
          
          {/* Share Button */}
          <button className="flex flex-col items-center">
            <div className="w-16 h-16 bg-gray-900/80 rounded-full flex items-center justify-center hover:bg-gray-700/80">
              <FaShare className="w-8 h-8 text-white" />
            </div>
          </button>
        </div>

        {/* Comments Section */}
        {showComments && (
          <div className="absolute right-[-320px] top-0 h-full">
            <Suspense fallback={
              <div className="w-[300px] h-full bg-gray-900/95 rounded-lg flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-white"></div>
              </div>
            }>
              <Comments 
                videoId={video.video_id} 
                onClose={() => setShowComments(false)}
                onCommentCountUpdate={handleCommentCountUpdate}
              />
            </Suspense>
          </div>
        )}

        {/* Navigation Arrows */}
        <div className="fixed right-8 top-1/2 -translate-y-1/2 space-y-6 z-20">
          <button
            onClick={onPrevious}
            disabled={isFirst}
            className={`w-20 h-20 rounded-full flex items-center justify-center transition-colors ${
              isFirst 
                ? 'bg-gray-800/20 cursor-not-allowed' 
                : 'bg-gray-900/60 hover:bg-gray-700/60 cursor-pointer'
            }`}
          >
            <IoIosArrowUp className={`w-12 h-12 ${isFirst ? 'text-gray-600' : 'text-white'}`} />
          </button>

          <button
            onClick={onNext}
            disabled={isLast}
            className={`w-20 h-20 rounded-full flex items-center justify-center transition-colors ${
              isLast 
                ? 'bg-gray-800/20 cursor-not-allowed' 
                : 'bg-gray-900/60 hover:bg-gray-700/60 cursor-pointer'
            }`}
          >
            <IoIosArrowDown className={`w-12 h-12 ${isLast ? 'text-gray-600' : 'text-white'}`} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default VideoCard; 