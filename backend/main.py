from fastapi import FastAPI, HTTPException, Depends, status, Response, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_
from datetime import datetime, timedelta
from typing import Optional
import os
import uuid
from dotenv import load_dotenv
from pathlib import Path
import cv2
import numpy as np
import io
from PIL import Image
import tempfile
import json

load_dotenv()

env_local_path = Path(__file__).parent.parent / '.env.local'
if env_local_path.exists():
    load_dotenv(env_local_path)

backend_port = int(os.getenv("BACKEND_PORT", "5176"))
frontend_port = int(os.getenv("FRONTEND_PORT", "5175"))

print(f"Backend starting on port: {backend_port}")
print(f"Frontend expected on port: {frontend_port}")

from models import Base, User, Like, Video, UserVideoInteraction, Comment
from database import SessionLocal, engine
from schemas import UserCreate, UserOut, Token, CommentCreate
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    create_refresh_token,
    verify_token
)
from recommend_videos import (
    recommend_videos,
    get_user_preferences,
    get_user_viewed_videos,
    load_video_data_from_mysql
)

Base.metadata.create_all(bind=engine)

app = FastAPI()

frontend_url = f"http://localhost:{frontend_port}"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/auth/register", response_model=UserOut)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    hashed_password = get_password_hash(user.password)
    db_user = User(
        user_id=str(uuid.uuid4()),
        email=user.email,
        username=user.username,
        password_hash=hashed_password,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/auth/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user.last_login = datetime.utcnow()
    db.commit()
    
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@app.post("/auth/refresh", response_model=Token)
async def refresh_token(
    current_token: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db)
):
    try:
        if current_token.startswith("Bearer "):
            current_token = current_token[7:]


        token_data = verify_token(current_token)
        if token_data["type"] != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = db.query(User).filter(User.email == token_data["email"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = create_access_token(data={"sub": user.email})
        refresh_token = create_refresh_token(data={"sub": user.email})

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

@app.get("/auth/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_user)):
    try:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        return {
            "user_id": current_user.user_id,
            "email": current_user.email,
            "username": current_user.username,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at,
            "last_login": current_user.last_login,
            "preferences": current_user.preferences
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@app.get("/health")
async def health_check():
    return {"status": "ok", "port": backend_port}

@app.get("/videos/recommendations")
async def get_video_recommendations(
    current_user: User = Depends(get_current_user),
    video_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    try:
        categories = None
        if current_user.preferences:
            try:
                # Handle both string and dictionary formats
                if isinstance(current_user.preferences, dict):
                    preferences_data = current_user.preferences
                else:
                    preferences_data = json.loads(current_user.preferences)
                
                categories = preferences_data.get('categories', [])
            except (json.JSONDecodeError, AttributeError):
                categories = get_user_preferences(current_user.user_id)
        else:
            categories = get_user_preferences(current_user.user_id)
        
        viewed_videos = get_user_viewed_videos(current_user.user_id)
        if video_id:
            viewed_videos = [v for v in viewed_videos if v != video_id]
        
        recommended_videos = recommend_videos(
            categories=categories,
            viewed_video_ids=viewed_videos,
            top_n=8
        )
        
        all_videos = load_video_data_from_mysql()
        if all_videos is not None:
            try:
                available_videos = all_videos[
                    ~all_videos['video_id'].isin(viewed_videos) &
                    ~all_videos['video_id'].isin([v['video_id'] for v in recommended_videos])
                ]
                if not available_videos.empty:
                    random_videos = available_videos.sample(n=min(2, len(available_videos)))
                    random_videos_list = random_videos[['video_id', 'user_id', 'title', 'category', 'likes', 'comments', 'views']].to_dict(orient='records')
                    recommended_videos.extend(random_videos_list)
            except Exception as e:
                print(f"Error getting random videos: {e}")

        for video in recommended_videos:
            like_count = db.query(Like).filter(Like.video_id == video['video_id']).count()
            video['likes'] = like_count

            comment_count = db.query(Comment).filter(
                Comment.video_id == video['video_id'],
                Comment.is_active == True,
                Comment.moderation_status == 'approved'
            ).count()
            video['comments'] = comment_count

            user = db.query(User).filter(User.user_id == video['user_id']).first()
            if user:
                video['user'] = {
                    'username': user.username,
                    'profile_picture_url': user.profile_picture_url or '/default-avatar.png'
                }
            else:
                video['user'] = {
                    'username': 'Unknown User',
                    'profile_picture_url': '/default-avatar.png'
                }

        return recommended_videos or []
        
    except Exception as e:
        print(f"Error in video recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting video recommendations: {str(e)}"
        )

@app.get("/videos/{video_id}/stream")
async def stream_video(
    video_id: str,
    range: str = Header(None),
    db: Session = Depends(get_db)
):
    try:
        query = text("SELECT video_data, title FROM videos WHERE video_id = :video_id")
        result = db.execute(query, {"video_id": video_id})
        video = result.first()
        
        if not video or not video.video_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )

        video_data = video.video_data
        total_size = len(video_data)

        start = 0
        end = total_size - 1
        
        if range:
            try:
                range_str = range.replace("bytes=", "")
                start_str, end_str = range_str.split("-")
                start = int(start_str) if start_str else 0
                end = int(end_str) if end_str else total_size - 1
            except ValueError:
                start = 0
                end = total_size - 1

        end = min(end, total_size - 1)
        content_length = end - start + 1

        headers = {
            "Content-Range": f"bytes {start}-{end}/{total_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Type": "video/mp4",
            "Cache-Control": "no-cache"
        }

        if range:
            return Response(
                content=video_data[start:end + 1],
                status_code=status.HTTP_206_PARTIAL_CONTENT,
                headers=headers
            )
        
        return Response(
            content=video_data,
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(total_size),
                "Cache-Control": "no-cache",
                "Content-Type": "video/mp4"
            }
        )

    except Exception as e:
        print(f"Error streaming video: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/users/{user_id}")
async def get_user(user_id: str, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "username": user.username,
            "profile_picture_url": user.profile_picture_url or "/default-avatar.png",
            "bio": user.bio
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/videos/{video_id}/like-status")
async def get_like_status(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        like = db.query(Like).filter(
            Like.video_id == video_id,
            Like.user_id == current_user.user_id
        ).first()
        
        return {"liked": bool(like)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/videos/{video_id}/like")
async def like_video(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        video = db.query(Video).filter(Video.video_id == video_id).first()
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        existing_like = db.query(Like).filter(
            Like.video_id == video_id,
            Like.user_id == current_user.user_id
        ).first()
        
        if existing_like:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Video already liked"
            )
        
        new_like = Like(
            like_id=str(uuid.uuid4()),
            user_id=current_user.user_id,
            video_id=video_id
        )
        db.add(new_like)
        
        video.like_count = video.like_count + 1
        
        interaction = UserVideoInteraction(
            interaction_id=str(uuid.uuid4()),
            user_id=current_user.user_id,
            video_id=video_id,
            interaction_type='like'
        )
        db.add(interaction)
        
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.delete("/videos/{video_id}/like")
async def unlike_video(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        video = db.query(Video).filter(Video.video_id == video_id).first()
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        like = db.query(Like).filter(
            Like.video_id == video_id,
            Like.user_id == current_user.user_id
        ).first()
        
        if not like:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Like not found"
            )
        
        db.delete(like)
        
        video.like_count = max(0, video.like_count - 1)
        
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/videos/{video_id}/comments")
async def get_video_comments(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        query = """
            SELECT 
                c.comment_id,
                c.video_id,
                c.user_id,
                c.content,
                c.created_at,
                c.like_count,
                c.moderation_status,
                u.username,
                u.profile_picture_url
            FROM comments c
            JOIN users u ON c.user_id = u.user_id
            WHERE c.video_id = :video_id
                AND c.is_active = true
                AND (c.moderation_status = 'approved' OR c.moderation_status = 'pending')
            ORDER BY c.created_at DESC
        """
        
        result = db.execute(text(query), {"video_id": video_id})
        comments = []
        
        for row in result:
            comments.append({
                "comment_id": row.comment_id,
                "video_id": row.video_id,
                "user_id": row.user_id,
                "content": row.content,
                "created_at": row.created_at.isoformat(),
                "like_count": row.like_count,
                "moderation_status": row.moderation_status,
                "user": {
                    "username": row.username,
                    "profile_picture_url": row.profile_picture_url or "/default-avatar.png"
                }
            })
        
        return comments
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/videos/{video_id}/comments")
async def create_comment(
    video_id: str,
    comment: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        video = db.query(Video).filter(Video.video_id == video_id).first()
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        new_comment = Comment(
            comment_id=str(uuid.uuid4()),
            video_id=video_id,
            user_id=current_user.user_id,
            content=comment.content,
            created_at=datetime.utcnow(),
            is_active=True,
            moderation_status='pending'
        )
        db.add(new_comment)
        
        video.comment_count = video.comment_count + 1
        
        interaction = UserVideoInteraction(
            interaction_id=str(uuid.uuid4()),
            user_id=current_user.user_id,
            video_id=video_id,
            interaction_type='comment'
        )
        db.add(interaction)
        
        db.commit()
        db.refresh(new_comment)
        
        return {
            "comment_id": new_comment.comment_id,
            "video_id": new_comment.video_id,
            "user_id": new_comment.user_id,
            "content": new_comment.content,
            "created_at": new_comment.created_at.isoformat(),
            "like_count": 0,
            "user": {
                "username": current_user.username,
                "profile_picture_url": current_user.profile_picture_url or "/default-avatar.png"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/videos/{video_id}")
async def get_video(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        video = db.query(Video).filter(Video.video_id == video_id).first()
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )

        like_count = db.query(Like).filter(Like.video_id == video_id).count()
        comment_count = db.query(Comment).filter(
            Comment.video_id == video_id,
            Comment.is_active == True,
            Comment.moderation_status == 'approved'
        ).count()
        view_count = db.query(UserVideoInteraction).filter(
            UserVideoInteraction.video_id == video_id,
            UserVideoInteraction.interaction_type == 'view'
        ).count()

        user = db.query(User).filter(User.user_id == video.user_id).first()

        return {
            "video_id": video.video_id,
            "user_id": video.user_id,
            "title": video.title,
            "category": video.category,
            "likes": like_count,
            "comments": comment_count,
            "views": view_count,
            "user": {
                "username": user.username if user else "Unknown User",
                "profile_picture_url": user.profile_picture_url if user else "/default-avatar.png"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/videos/{video_id}/view")
async def record_video_view(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        video = db.query(Video).filter(Video.video_id == video_id).first()
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        interaction = UserVideoInteraction(
            interaction_id=str(uuid.uuid4()),
            user_id=current_user.user_id,
            video_id=video_id,
            interaction_type='view'
        )
        db.add(interaction)
        
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/users/{user_id}/profile")
async def get_user_profile(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        likes_subquery = db.query(Video.user_id, func.count(Like.like_id).label('total_likes'))\
            .join(Like, Video.video_id == Like.video_id)\
            .group_by(Video.user_id)\
            .subquery()
            
        likes_count = db.query(likes_subquery.c.total_likes)\
            .filter(likes_subquery.c.user_id == user_id)\
            .scalar() or 0

        videos = db.query(
            Video.video_id,
            Video.title,
            func.count(UserVideoInteraction.interaction_id).label('views')
        ).outerjoin(
            UserVideoInteraction,
            and_(
                Video.video_id == UserVideoInteraction.video_id,
                UserVideoInteraction.interaction_type == 'view'
            )
        ).filter(
            Video.user_id == user_id,
            Video.is_active == True
        ).group_by(
            Video.video_id,
            Video.title
        ).all()

        videos_list = [{
            'video_id': video.video_id,
            'title': video.title,
            'views': video.views,
            'thumbnail_url': f'/api/videos/{video.video_id}/thumbnail'
        } for video in videos]

        return {
            "username": user.username,
            "profile_picture_url": user.profile_picture_url or "/default-avatar.png",
            "likes_count": likes_count,
            "videos": videos_list
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/videos/{video_id}/thumbnail")
async def get_video_thumbnail(
    video_id: str,
    db: Session = Depends(get_db)
):
    try:
        query = text("SELECT video_data FROM videos WHERE video_id = :video_id")
        result = db.execute(query, {"video_id": video_id})
        video_row = result.first()
        
        if not video_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )

        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_file.write(video_row.video_data)
            temp_path = temp_file.name

        try:
            cap = cv2.VideoCapture(temp_path)
            
            success, frame = cap.read()
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not extract thumbnail"
                )
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            image = Image.fromarray(frame_rgb)
            
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG', quality=85)
            img_byte_arr = img_byte_arr.getvalue()
            
            cap.release()
            
            return Response(
                content=img_byte_arr,
                media_type="image/jpeg",
                headers={
                    "Cache-Control": "public, max-age=31536000"
                }
            )
        finally:
            try:
                os.unlink(temp_path)
            except Exception as e:
                print(f"Error removing temporary file: {e}")
        
    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Admin endpoints - no auth required (Should be added for production)
@app.get("/admin/videos/rejected")
async def get_rejected_videos(db: Session = Depends(get_db)):
    try:
        videos = db.query(
            Video, User.username
        ).join(
            User, Video.user_id == User.user_id
        ).filter(
            Video.moderation_status == 'rejected'
        ).all()
        
        return [
            {
                "video_id": video.Video.video_id,
                "title": video.Video.title,
                "user_id": video.Video.user_id,
                "username": video.username,
                "created_at": video.Video.created_at,
                "moderation_reason": video.Video.moderation_reason,
                "video_url": f"/api/videos/{video.Video.video_id}/stream"
            }
            for video in videos
        ]
    except Exception as e:
        print(f"Error getting rejected videos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching rejected videos"
        )

@app.get("/admin/comments/rejected")
async def get_rejected_comments(db: Session = Depends(get_db)):
    try:
        comments = db.query(
            Comment, User.username
        ).join(
            User, Comment.user_id == User.user_id
        ).filter(
            Comment.moderation_status == 'rejected'
        ).all()
        
        return [
            {
                "comment_id": comment.Comment.comment_id,
                "content": comment.Comment.content,
                "user_id": comment.Comment.user_id,
                "username": comment.username,
                "created_at": comment.Comment.created_at,
                "moderation_reason": comment.Comment.moderation_reason,
                "moderation_score": comment.Comment.moderation_score,
                "moderation_labels": comment.Comment.moderation_labels
            }
            for comment in comments
        ]
    except Exception as e:
        print(f"Error getting rejected comments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching rejected comments"
        )

@app.post("/admin/videos/{video_id}/approve")
async def approve_video(video_id: str, db: Session = Depends(get_db)):
    try:
        video = db.query(Video).filter(Video.video_id == video_id).first()
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
            
        video.moderation_status = 'approved'
        video.moderation_reason = 'Manually approved by admin'
        db.commit()
        
        return {"message": "Video approved successfully"}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error approving video: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error approving video"
        )

@app.post("/admin/comments/{comment_id}/approve")
async def approve_comment(comment_id: str, db: Session = Depends(get_db)):
    try:
        comment = db.query(Comment).filter(Comment.comment_id == comment_id).first()
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )
            
        comment.moderation_status = 'approved'
        comment.moderation_reason = 'Manually approved by admin'
        db.commit()
        
        return {"message": "Comment approved successfully"}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error approving comment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error approving comment"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",  # Listen on both IPv6 and IPv4
        port=backend_port,
        reload=True
    ) 