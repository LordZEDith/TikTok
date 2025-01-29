from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, JSON, Enum, Float, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    user_id = Column(String(255), primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    profile_picture_url = Column(String(255))
    bio = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    preferences = Column(JSON)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))

class Video(Base):
    __tablename__ = "videos"

    video_id = Column(String(255), primary_key=True)
    user_id = Column(String(255), ForeignKey('users.user_id'))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    video_data = Column(String(255)) 
    thumbnail_url = Column(String(255))
    category = Column(String(50))
    duration = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    moderation_status = Column(Enum('pending', 'approved', 'rejected', name='moderation_status'), default='pending')
    moderation_reason = Column(Text)

class Comment(Base):
    __tablename__ = "comments"

    comment_id = Column(String(255), primary_key=True)
    video_id = Column(String(255), ForeignKey('videos.video_id'))
    user_id = Column(String(255), ForeignKey('users.user_id'))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    like_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    moderation_status = Column(Enum('pending', 'approved', 'rejected', name='moderation_status'), default='pending')
    moderation_score = Column(Float)
    moderation_labels = Column(JSON)
    moderation_reason = Column(Text)

class Like(Base):
    __tablename__ = "likes"

    like_id = Column(String(255), primary_key=True)
    user_id = Column(String(255), ForeignKey('users.user_id'))
    video_id = Column(String(255), ForeignKey('videos.video_id'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('user_id', 'video_id', name='unique_like'),)

class UserVideoInteraction(Base):
    __tablename__ = "user_video_interactions"

    interaction_id = Column(String(255), primary_key=True)
    user_id = Column(String(255), ForeignKey('users.user_id'))
    video_id = Column(String(255), ForeignKey('videos.video_id'))
    interaction_type = Column(Enum('view', 'like', 'comment', 'share', name='interaction_type'))
    interaction_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    watch_duration = Column(Integer)

class VideoRecommendation(Base):
    __tablename__ = "video_recommendations"

    recommendation_id = Column(String(255), primary_key=True)
    user_id = Column(String(255), ForeignKey('users.user_id'))
    video_id = Column(String(255), ForeignKey('videos.video_id'))
    recommendation_score = Column(Float)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    is_shown = Column(Boolean, default=False)
    is_clicked = Column(Boolean, default=False)

class ModerationHistory(Base):
    __tablename__ = "moderation_history"

    history_id = Column(String(255), primary_key=True)
    content_type = Column(Enum('video', 'comment', name='content_type'))
    content_id = Column(String(255))
    moderation_action = Column(Enum('flag', 'approve', 'reject', 'restore', name='moderation_action'))
    action_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    moderation_reason = Column(Text)
    automated = Column(Boolean, default=True) 