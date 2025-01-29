import React, { useState, useEffect } from 'react';

interface Video {
  video_id: string;
  title: string;
  category: string;
  likes: number;
  comments: number;
  views: number;
}

const VideoDebug: React.FC = () => {
  const [videoId, setVideoId] = useState<string>('');
  const [video, setVideo] = useState<Video | null>(null);
  const [error, setError] = useState<string>('');
  const [debugInfo, setDebugInfo] = useState<any>({});


  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('id');
    if (id) {
      setVideoId(id);
      fetchVideoInfo(id);
    } else {
      setError('No video ID provided. Use ?id=VIDEO_ID in the URL.');
    }
  }, []);

  const fetchVideoInfo = async (id: string) => {
    try {
      const response = await fetch(`/api/videos/${id}`);
      if (!response.ok) throw new Error('Failed to fetch video info');
      const data = await response.json();
      setVideo(data);
    } catch (err) {
      setError('Error fetching video info: ' + (err as Error).message);
    }
  };

  const videoUrl = videoId ? `/api/videos/${videoId}/stream` : '';

  const checkVideoHeaders = async () => {
    try {
      const response = await fetch(videoUrl, { method: 'HEAD' });
      setDebugInfo(prev => ({
        ...prev,
        headers: {
          contentType: response.headers.get('content-type'),
          contentLength: response.headers.get('content-length'),
          acceptRanges: response.headers.get('accept-ranges')
        }
      }));
    } catch (err) {
      setDebugInfo(prev => ({
        ...prev,
        headerError: (err as Error).message
      }));
    }
  };

  const checkVideoData = async () => {
    try {
      const response = await fetch(videoUrl);
      const blob = await response.blob();
      setDebugInfo(prev => ({
        ...prev,
        blob: {
          size: blob.size,
          type: blob.type
        }
      }));
    } catch (err) {
      setDebugInfo(prev => ({
        ...prev,
        blobError: (err as Error).message
      }));
    }
  };

  return (
    <div className="min-h-screen bg-black p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-white text-2xl mb-4">Video Debug Page</h1>
        
        {error && (
          <div className="bg-red-500 text-white p-4 rounded mb-4">
            {error}
          </div>
        )}

        {video && (
          <div className="bg-gray-900 p-4 rounded mb-4 text-white">
            <h2>Video Info:</h2>
            <pre className="mt-2 overflow-auto">
              {JSON.stringify(video, null, 2)}
            </pre>
          </div>
        )}

        <div className="space-y-4 mb-4">
          <button
            onClick={checkVideoHeaders}
            className="bg-blue-500 text-white px-4 py-2 rounded mr-2"
          >
            Check Headers
          </button>
          <button
            onClick={checkVideoData}
            className="bg-green-500 text-white px-4 py-2 rounded"
          >
            Check Video Data
          </button>
        </div>

        <div className="bg-gray-900 p-4 rounded mb-4 text-white">
          <h2>Debug Info:</h2>
          <pre className="mt-2 overflow-auto">
            {JSON.stringify(debugInfo, null, 2)}
          </pre>
        </div>

        {videoUrl && (
          <>
            <h2 className="text-white text-xl mb-4">Native Video Player</h2>
            <div className="bg-black rounded-lg overflow-hidden mb-4">
              <video
                className="w-full"
                src={videoUrl}
                controls
                autoPlay
                playsInline
                style={{
                  backgroundColor: 'black',
                  maxHeight: '70vh'
                }}
                onError={(e) => {
                  setDebugInfo(prev => ({
                    ...prev,
                    videoError: (e.target as HTMLVideoElement).error
                  }));
                }}
              />
            </div>

            <h2 className="text-white text-xl mb-4">Direct Video URL</h2>
            <div className="bg-gray-900 p-4 rounded text-white break-all">
              <a 
                href={videoUrl} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-blue-400 hover:text-blue-300"
              >
                {videoUrl}
              </a>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default VideoDebug; 