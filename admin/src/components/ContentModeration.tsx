import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';
import ReactPlayer from 'react-player';

interface ContentModerationProps {
  type: 'videos' | 'comments';
}

interface Video {
  video_id: string;
  title: string;
  user_id: string;
  username: string;
  created_at: string;
  moderation_reason: string;
  video_url: string;
}

interface Comment {
  comment_id: string;
  content: string;
  user_id: string;
  username: string;
  created_at: string;
  moderation_reason: string;
  moderation_score: number;
  moderation_labels: string;
}

interface LabelInfo {
  label: string;
  description: string;
  color: string;
}

const LABEL_INFO: { [key: string]: LabelInfo } = {
  'S': { label: 'Sexual', description: 'Sexual content', color: 'bg-pink-600' },
  'H': { label: 'Hate', description: 'Hate speech', color: 'bg-red-600' },
  'V': { label: 'Violence', description: 'Violence', color: 'bg-orange-600' },
  'HR': { label: 'Harassment', description: 'Harassment', color: 'bg-yellow-600' },
  'SH': { label: 'Self-Harm', description: 'Self-harm content', color: 'bg-purple-600' },
  'S3': { label: 'Sexual/Minors', description: 'Sexual content with minors', color: 'bg-red-800' },
  'H2': { label: 'Hate/Threat', description: 'Hate with threats', color: 'bg-red-700' },
  'V2': { label: 'Violence/Graphic', description: 'Graphic violence', color: 'bg-orange-800' },
  'OK': { label: 'Safe', description: 'Safe content', color: 'bg-green-600' }
};

const ContentModeration: React.FC<ContentModerationProps> = ({ type }) => {
  const [videos, setVideos] = useState<Video[]>([]);
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchItems();
  }, [type]);

  const fetchItems = async () => {
    setLoading(true);
    try {
      const endpoint = type === 'videos' ? '/api/admin/videos/rejected' : '/api/admin/comments/rejected';
      const response = await fetch(endpoint);
      if (!response.ok) throw new Error('Failed to fetch items');
      const data = await response.json();
      
      if (type === 'videos') {
        setVideos(data);
        setComments([]);
      } else {
        setComments(data);
        setVideos([]);
      }
    } catch (error) {
      console.error('Error fetching items:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      const endpoint = type === 'videos' 
        ? `/api/admin/videos/${id}/approve` 
        : `/api/admin/comments/${id}/approve`;
      
      const response = await fetch(endpoint, {
        method: 'POST',
      });
      
      if (!response.ok) throw new Error('Failed to approve item');
      
      if (type === 'videos') {
        setVideos(videos.filter(video => video.video_id !== id));
      } else {
        setComments(comments.filter(comment => comment.comment_id !== id));
      }
    } catch (error) {
      console.error('Error approving item:', error);
    }
  };

  const formatModerationLabels = (labels: any) => {
    try {
      const parsedLabels = typeof labels === 'string' ? JSON.parse(labels) : labels;
      
      if (!parsedLabels || typeof parsedLabels !== 'object') {
        throw new Error('Invalid labels format');
      }

      const entries = Object.entries(parsedLabels)
        .map(([key, value]) => ({ key, value: value as number }))
        .sort((a, b) => b.value - a.value);

      const mainViolation = entries[0];
      const formattedLabels = entries.map(({ key, value }) => ({
        key,
        percentage: (value * 100).toFixed(1),
        isMain: key === mainViolation.key
      }));

      return {
        mainViolation: {
          key: mainViolation.key,
          percentage: (mainViolation.value * 100).toFixed(1)
        },
        allLabels: formattedLabels
      };
    } catch (e) {
      console.error('Error parsing moderation labels:', e);
      return {
        mainViolation: { key: 'ERROR', percentage: '0' },
        allLabels: []
      };
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-xl text-gray-300">Loading...</div>
      </div>
    );
  }

  if (type === 'videos') {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold text-gray-100">Rejected Videos</h2>
        <div className="space-y-4">
          {videos.map(video => (
            <div key={video.video_id} className="bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-700">
              <div className="space-y-4">
                <div className="aspect-w-16 aspect-h-9 max-w-2xl">
                  <ReactPlayer
                    url={video.video_url}
                    controls
                    width="100%"
                    height="100%"
                  />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-100">{video.title}</h3>
                  <p className="text-sm text-gray-400">
                    By {video.username} • {format(new Date(video.created_at), 'PPpp')}
                  </p>
                </div>
              </div>
              <div className="mt-4 space-y-2">
                <p className="text-red-400">
                  <span className="font-semibold">Rejection Reason:</span> {video.moderation_reason}
                </p>
                <button
                  onClick={() => handleApprove(video.video_id)}
                  className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition-colors"
                >
                  Override & Approve
                </button>
              </div>
            </div>
          ))}
          {videos.length === 0 && (
            <div className="text-center py-12 bg-gray-800 rounded-lg border border-gray-700">
              <p className="text-gray-400">No rejected videos found</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 max-w-3xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-100 mb-6">Rejected Comments</h2>
      <div className="space-y-2">
        {comments.map(comment => {
          const { mainViolation, allLabels } = formatModerationLabels(comment.moderation_labels);
          const mainLabelInfo = LABEL_INFO[mainViolation.key];

          return (
            <div key={comment.comment_id} className="bg-gray-800 rounded-lg shadow p-4 border border-gray-700">
              <div className="flex items-start space-x-4">
                {/* User Avatar */}
                <div className="flex-shrink-0">
                  <div className="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center">
                    <span className="text-lg text-gray-300">{comment.username[0]?.toUpperCase()}</span>
                  </div>
                </div>

                {/* Comment Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-medium text-gray-200">{comment.username}</span>
                      <span className="text-sm text-gray-400">•</span>
                      <span className="text-sm text-gray-400">{format(new Date(comment.created_at), 'MMM d, yyyy')}</span>
                    </div>
                    {mainLabelInfo && (
                      <div className={`px-2 py-0.5 text-xs font-medium text-white rounded ${mainLabelInfo.color}`}>
                        {mainLabelInfo.label} ({mainViolation.percentage}%)
                      </div>
                    )}
                  </div>
                  
                  <p className="text-gray-100 mb-2">{comment.content}</p>
                  
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4 text-sm text-gray-400">
                      <div className="flex items-center space-x-1">
                        <span>Score: {comment.moderation_score}</span>
                      </div>
                    </div>
                    <button
                      onClick={() => handleApprove(comment.comment_id)}
                      className="text-sm bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700 transition-colors"
                    >
                      Approve
                    </button>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
        {comments.length === 0 && (
          <div className="text-center py-8 bg-gray-800 rounded-lg border border-gray-700">
            <p className="text-gray-400">No rejected comments found</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ContentModeration; 