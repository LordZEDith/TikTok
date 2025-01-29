import React, { useState, useEffect } from 'react';
import { FaHeart, FaReply } from 'react-icons/fa';

interface Comment {
  comment_id: string;
  user_id: string;
  content: string;
  created_at: string;
  like_count: number;
  moderation_status: 'pending' | 'approved' | 'rejected';
  user: {
    username: string;
    profile_picture_url: string;
  };
}

interface CommentsProps {
  videoId: string;
  onClose: () => void;
  onCommentCountUpdate: (newCount: number) => void;
}

const Comments: React.FC<CommentsProps> = ({ videoId, onClose, onCommentCountUpdate }) => {
  const [comments, setComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchComments();
  }, [videoId]);

  const fetchComments = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;

      const response = await fetch(`/api/videos/${videoId}/comments`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch comments');
      }

      const data = await response.json();
      setComments(data);
      onCommentCountUpdate(data.length);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load comments');
      setLoading(false);
    }
  };

  const handlePostComment = async () => {
    if (!newComment.trim()) return;

    try {
      const token = localStorage.getItem('token');
      if (!token) return;

      const response = await fetch(`/api/videos/${videoId}/comments`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          content: newComment
        })
      });

      if (!response.ok) {
        let errorMessage = 'Failed to post comment';
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorMessage;
        } catch {
          errorMessage = response.statusText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      const postedComment = await response.json();
      setComments(prev => [postedComment, ...prev]);
      setNewComment('');
      onCommentCountUpdate(comments.length + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to post comment');
    }
  };

  return (
    <div className="w-[300px] h-full bg-gray-900/95 rounded-lg flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-800 flex justify-between items-center">
        <h3 className="text-white text-lg font-semibold">Comments</h3>
        <button 
          onClick={onClose}
          className="text-gray-400 hover:text-white"
        >
          ×
        </button>
      </div>

      {/* Comment Input */}
      <div className="p-4 border-b border-gray-800">
        <textarea
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          placeholder="Add a comment..."
          className="w-full bg-gray-800 text-white rounded-lg p-3 min-h-[80px] resize-none"
        />
        <div className="flex justify-end mt-2">
          <button
            onClick={handlePostComment}
            disabled={!newComment.trim()}
            className={`px-4 py-2 rounded-full ${
              newComment.trim() 
                ? 'bg-[#FE2C55] hover:bg-[#ef233c]' 
                : 'bg-gray-700 cursor-not-allowed'
            } text-white font-medium`}
          >
            Post
          </button>
        </div>
      </div>

      {/* Comments List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-white"></div>
          </div>
        ) : error ? (
          <div className="p-4 text-red-500 text-center">{error}</div>
        ) : comments.length === 0 ? (
          <div className="p-4 text-gray-400 text-center">No comments yet</div>
        ) : (
          <div className="space-y-4 p-4">
            {comments.map((comment) => (
              <div key={comment.comment_id} className="space-y-2">
                <div className="flex items-start gap-3">
                  <img
                    src={comment.user.profile_picture_url || '/default-avatar.png'}
                    alt={comment.user.username}
                    className="w-8 h-8 rounded-full object-cover"
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-white font-medium">{comment.user.username}</span>
                      <span className="text-gray-400 text-sm">
                        {new Date(comment.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <p className="text-white mt-1">{comment.content}</p>
                    <div className="flex items-center gap-4 mt-2">
                      <button className="text-gray-400 hover:text-white flex items-center gap-1">
                        <FaHeart className="w-4 h-4" />
                        <span className="text-sm">{comment.like_count}</span>
                      </button>
                      <button className="text-gray-400 hover:text-white flex items-center gap-1">
                        <FaReply className="w-4 h-4" />
                        <span className="text-sm">Reply</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Comments; 