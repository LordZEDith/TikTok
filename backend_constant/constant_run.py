import os
import time
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import pickle
from datetime import datetime
import schedule
from pathlib import Path
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch
import google.generativeai as genai
import json
import tempfile
from google.ai.generativelanguage_v1beta.types import content

load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DATABASE_URL = f"mysql+mysqlconnector://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"

def get_db_connection():
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            engine = create_engine(
                DATABASE_URL,
                pool_pre_ping=True,  # Enable connection health checks
                pool_recycle=3600,   # Recycle connections after 1 hour
                pool_timeout=30      # Wait up to 30 seconds for a connection
            )
            # Test the connection
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return engine
        except Exception as e:
            print(f"[{datetime.now()}] Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"[{datetime.now()}] Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"[{datetime.now()}] All database connection attempts failed")
                raise

def execute_with_retry(query, params=None):
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            engine = get_db_connection()
            with engine.connect() as connection:
                if params:
                    result = connection.execute(text(query), params)
                else:
                    result = connection.execute(text(query))
                connection.commit()
                return result
        except Exception as e:
            print(f"[{datetime.now()}] Database query attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"[{datetime.now()}] Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"[{datetime.now()}] All query attempts failed")
                raise

print("Loading comment moderation model...")
moderation_model = AutoModelForSequenceClassification.from_pretrained("Vrandan/Comment-Moderation")
moderation_tokenizer = AutoTokenizer.from_pretrained("Vrandan/Comment-Moderation")
print("Comment moderation model loaded successfully")

def analyze_comment(text):
    try:
        inputs = moderation_tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = moderation_model(**inputs)
        probabilities = outputs.logits.softmax(dim=-1).squeeze()
        
        labels = [moderation_model.config.id2label[i] for i in range(len(probabilities))]
        predictions = sorted(zip(labels, probabilities), key=lambda x: x[1], reverse=True)
        
        top_label, top_prob = predictions[0]
        
        return {
            'status': 'approved' if top_label == 'OK' else 'rejected',
            'label': top_label,
            'confidence': float(top_prob),
            'all_predictions': predictions
        }
    except Exception as e:
        print(f"Error analyzing comment: {e}")
        return None

def wait_for_files_active(files):
    print("Waiting for file processing...")
    for name in (file.name for file in files):
        file = genai.get_file(name)
        while file.state.name == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(10)
            file = genai.get_file(name)
        if file.state.name != "ACTIVE":
            raise Exception(f"File {file.name} failed to process")
    print("...all files ready")

def analyze_video_content(video_data):
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_file.write(video_data)
            temp_path = temp_file.name
        
        if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
            print(f"Error: Temporary file {temp_path} is empty or does not exist")
            return None

        try:
            generation_config = {
                "temperature": 0,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
                "response_schema": content.Schema(
                    type=content.Type.OBJECT,
                    required=["is_safe", "reason"],
                    properties={
                        "is_safe": content.Schema(
                            type=content.Type.BOOLEAN,
                            description="Whether the video is safe for the platform"
                        ),
                        "reason": content.Schema(
                            type=content.Type.STRING,
                            description="Explanation of why the video is safe or unsafe"
                        ),
                    },
                ),
                "response_mime_type": "application/json",
            }

            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash-exp",
                generation_config=generation_config,
                system_instruction="""Analyze the video for safety and appropriateness. Check for:
                1. Explicit adult content or nudity
                2. Graphic violence or gore
                3. Hate speech or extremist content
                4. Dangerous or illegal activities
                5. Harassment or bullying
                6. Self-harm or suicide content
                7. Child exploitation
                8. Misleading or harmful misinformation

                Respond with whether the video is safe for a general audience platform.
                A video should be marked unsafe if it contains any of the above content."""
            )

            max_retries = 3
            retry_delay = 2
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    video_file = genai.upload_file(temp_path, mime_type="video/mp4")
                    
                    wait_for_files_active([video_file])
                    
                    chat = model.start_chat(history=[{"role": "user", "parts": [video_file]}])
                    response = chat.send_message("Is this video safe and appropriate for our platform? Analyze it thoroughly.")
                    
                    try:
                        result = json.loads(response.text)
                        return {
                            'status': 'approved' if result['is_safe'] else 'rejected',
                            'reason': result['reason']
                        }
                    except json.JSONDecodeError:
                        print(f"Error parsing Gemini response: {response.text}")
                        last_error = "Failed to parse Gemini response"
                        continue
                        
                except Exception as e:
                    print(f"Attempt {attempt + 1} failed: {str(e)}")
                    last_error = str(e)
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                    continue
            
            print(f"All retry attempts failed. Last error: {last_error}")
            return None

        except Exception as e:
            print(f"Error in Gemini analysis: {e}")
            return None

    except Exception as e:
        print(f"Error preparing video for analysis: {e}")
        return None
        
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception as e:
                print(f"Error removing temporary file: {e}")

def moderate_pending_videos():
    try:
        print(f"\n[{datetime.now()}] Starting video moderation...")
        
        query = """
            SELECT video_id, video_data, title, description
            FROM videos
            WHERE moderation_status = 'pending'
        """
        
        try:
            result = execute_with_retry(query)
            pending_videos = result.fetchall()
        except Exception as e:
            print(f"[{datetime.now()}] Failed to fetch pending videos: {e}")
            return
            
        if not pending_videos:
            print(f"[{datetime.now()}] No pending videos to moderate")
            return
            
        print(f"[{datetime.now()}] Found {len(pending_videos)} pending videos")
        
        for video in pending_videos:
            print(f"[{datetime.now()}] Processing video {video.video_id}: {video.title}")
            
            if video.video_data is None:
                print(f"[{datetime.now()}] No video data found for {video.video_id}, skipping...")
                continue
                
            analysis = analyze_video_content(video.video_data)
            
            if analysis is None:
                print(f"[{datetime.now()}] Failed to analyze video {video.video_id}, skipping...")
                continue
                
            update_query = """
                UPDATE videos
                SET 
                    moderation_status = :status,
                    moderation_reason = :reason
                WHERE video_id = :video_id
            """
            
            update_data = {
                'status': analysis['status'],
                'reason': analysis['reason'],
                'video_id': video.video_id
            }
            
            try:
                execute_with_retry(update_query, update_data)
                print(f"[{datetime.now()}] Moderated video {video.video_id} - {video.title}: {analysis['status']}")
                print(f"[{datetime.now()}] Reason: {analysis['reason']}")
            except Exception as e:
                print(f"[{datetime.now()}] Failed to update video {video.video_id}: {e}")
                continue
        
        print(f"[{datetime.now()}] Completed video moderation")
        
    except Exception as e:
        print(f"[{datetime.now()}] Error in video moderation: {e}")

def moderate_pending_comments():
    try:
        print(f"\n[{datetime.now()}] Starting comment moderation...")
        
        query = """
            SELECT comment_id, content
            FROM comments
            WHERE moderation_status = 'pending'
        """
        
        try:
            result = execute_with_retry(query)
            pending_comments = result.fetchall()
        except Exception as e:
            print(f"[{datetime.now()}] Failed to fetch pending comments: {e}")
            return
            
        if not pending_comments:
            print(f"[{datetime.now()}] No pending comments to moderate")
            return
            
        print(f"[{datetime.now()}] Found {len(pending_comments)} pending comments")
        
        for comment in pending_comments:
            analysis = analyze_comment(comment.content)
            
            if analysis is None:
                continue
                
            update_query = """
                UPDATE comments
                SET 
                    moderation_status = :status,
                    moderation_labels = :labels,
                    moderation_score = :score,
                    moderation_reason = :reason
                WHERE comment_id = :comment_id
            """
            
            labels_json = json.dumps({label: float(prob) for label, prob in analysis['all_predictions']})
            
            top_label = analysis['all_predictions'][0][0]
            confidence = analysis['all_predictions'][0][1]
            reason = f"Comment classified as {top_label} with {confidence:.2%} confidence"
            
            update_data = {
                'status': analysis['status'],
                'labels': labels_json,
                'score': float(analysis['confidence']),
                'reason': reason,
                'comment_id': comment.comment_id
            }
            
            try:
                execute_with_retry(update_query, update_data)
                print(f"[{datetime.now()}] Moderated comment {comment.comment_id}: {analysis['status']} ({top_label} - {confidence:.4f})")
            except Exception as e:
                print(f"[{datetime.now()}] Failed to update comment {comment.comment_id}: {e}")
                continue
        
        print(f"[{datetime.now()}] Completed comment moderation")
        
    except Exception as e:
        print(f"[{datetime.now()}] Error in comment moderation: {e}")

def load_video_data_from_mysql():
    try:
        query = """
            SELECT 
                v.video_id,
                v.user_id,
                v.title,
                v.category,
                COALESCE(COUNT(DISTINCT l.like_id), 0) as likes,
                COALESCE(COUNT(DISTINCT c.comment_id), 0) as comments,
                COALESCE(COUNT(DISTINCT i.interaction_id), 0) as views
            FROM videos v
            LEFT JOIN likes l ON v.video_id = l.video_id
            LEFT JOIN comments c ON v.video_id = c.video_id
            LEFT JOIN user_video_interactions i ON v.video_id = i.video_id AND i.interaction_type = 'view'
            WHERE v.moderation_status != 'rejected'
            GROUP BY v.video_id, v.user_id, v.title, v.category
        """
        
        engine = get_db_connection()
        df = pd.read_sql(query, engine)
        return df
        
    except Exception as e:
        print(f"Error loading video data: {e}")
        return None

def train_recommendation_model():
    try:
        print(f"\n[{datetime.now()}] Starting daily model training...")
        
        # Load video data
        df = load_video_data_from_mysql()
        if df is None or df.empty:
            print("No video data available for training")
            return None
            
        # Create TF-IDF matrix from categories
        vectorizer = TfidfVectorizer()
        category_matrix = vectorizer.fit_transform(df['category'])
        
        # Compute similarity matrix
        similarity_matrix = cosine_similarity(category_matrix)
        
        # Calculate engagement scores
        df['engagement_score'] = (
            df['likes'] * 1.0 +
            df['comments'] * 2.0 +
            df['views'] * 0.5
        )
        
        # Normalize scores
        df['engagement_score'] = (df['engagement_score'] - df['engagement_score'].min()) / (df['engagement_score'].max() - df['engagement_score'].min())
        
        # Save the model artifacts
        model_data = {
            'vectorizer': vectorizer,
            'similarity_matrix': similarity_matrix,
            'video_data': df,
            'trained_at': datetime.now()
        }
        
        model_dir = Path(__file__).parent.parent / 'backend' / 'model'
        model_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_path = model_dir / f'recommendation_model_{timestamp}.pkl'
        
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"[{datetime.now()}] Successfully trained and saved new model: {model_path}")
            
        return model_data
        
    except Exception as e:
        print(f"[{datetime.now()}] Error training model: {e}")
        return None

def analyze_user_preferences():
    try:
        print(f"\n[{datetime.now()}] Starting user preference analysis...")
        
        # Get users with interactions in the last 30 days, broken down by category
        query = """
            WITH user_stats AS (
                SELECT 
                    u.user_id,
                    u.username,
                    v.category,
                    COUNT(DISTINCT CASE WHEN i.interaction_type = 'view' THEN i.interaction_id END) as total_views,
                    COUNT(DISTINCT CASE WHEN i.interaction_type = 'like' THEN i.interaction_id END) as total_likes,
                    COUNT(DISTINCT c.comment_id) as total_comments
                FROM users u
                INNER JOIN user_video_interactions i ON u.user_id = i.user_id
                INNER JOIN videos v ON i.video_id = v.video_id
                LEFT JOIN comments c ON v.video_id = c.video_id AND c.user_id = u.user_id
                WHERE i.interaction_timestamp >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY u.user_id, u.username, v.category
            )
            SELECT *
            FROM user_stats
            WHERE total_views > 0 OR total_likes > 0 OR total_comments > 0
            ORDER BY 
                user_id,
                (total_views + total_likes + total_comments) DESC
        """
        
        result = execute_with_retry(query)
        all_interactions = result.fetchall()
        
        if not all_interactions:
            print(f"[{datetime.now()}] No users with recent interactions found")
            return
            
        # Group interactions by user
        users = {}
        for interaction in all_interactions:
            if interaction.user_id not in users:
                users[interaction.user_id] = {
                    'username': interaction.username,
                    'categories': []
                }
            users[interaction.user_id]['categories'].append({
                'category': interaction.category,
                'views': interaction.total_views,
                'likes': interaction.total_likes,
                'comments': interaction.total_comments
            })
            
        print(f"[{datetime.now()}] Found {len(users)} users to analyze")
        
        generation_config = {
            "temperature": 0,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
            "response_schema": content.Schema(
                type=content.Type.OBJECT,
                required=["categories"],
                properties={
                    "categories": content.Schema(
                        type=content.Type.ARRAY,
                        items=content.Schema(
                            type=content.Type.STRING,
                        ),
                    ),
                },
            ),
            "response_mime_type": "application/json",
        }

        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            generation_config=generation_config,
            system_instruction="""You are a content recommendation system. Your task is to analyze user interaction data and suggest relevant content categories.
            
            Rules:
            1. Return EXACTLY 1-3 categories based on relevance
            2. Consider higher weight for categories with more likes and comments
            3. Look for categories with consistent engagement across all metrics
            4. Consider recent viewing patterns
            5. Choose ONLY from the provided category list"""
        )

        for user_id, user_data in users.items():
            try:
                category_stats = []
                for cat in user_data['categories']:
                    category_stats.append(
                        f"- {cat['category']}:\n"
                        f"  * Views: {cat['views']}\n"
                        f"  * Likes: {cat['likes']}\n"
                        f"  * Comments: {cat['comments']}"
                    )

                prompt = f"""Based on this user's detailed interaction data, suggest up to 3 most relevant content categories from the following list:

Entertainment & Pop Culture
Sports & Fitness
Music & Performance Arts
Technology & Gadgets
Education & How-To
News & Current Affairs
Health & Wellness
Food & Cooking
Travel & Exploration
Gaming & Esports
Science & Nature
Finance & Business
Lifestyle & Fashion
Movies & TV Shows
Motivation & Personal Development
Comedy & Fun
Automobiles & Vehicles
Home & DIY
Pets & Animals

User Interaction Data by Category:
{chr(10).join(category_stats)}"""

                response = model.generate_content(prompt)
                
                try:
                    if hasattr(response, 'text'):
                        categories_data = json.loads(response.text)
                    else:
                        categories_data = json.loads(str(response))
                        
                    if not isinstance(categories_data, dict) or 'categories' not in categories_data:
                        raise ValueError("Invalid response format")
                        
                    categories = categories_data['categories']
                    
                    if not isinstance(categories, list) or not categories:
                        raise ValueError("No valid categories returned")
                    
                    update_query = """
                        UPDATE users 
                        SET preferences = :preferences
                        WHERE user_id = :user_id
                    """
                    
                    preferences_json = json.dumps({
                        "categories": categories,
                        "updated_at": datetime.now().isoformat()
                    })
                    
                    execute_with_retry(update_query, {
                        'preferences': preferences_json,
                        'user_id': user_id
                    })
                    
                    print(f"[{datetime.now()}] Updated preferences for {user_data['username']}: {categories}")
                    
                except json.JSONDecodeError as e:
                    print(f"[{datetime.now()}] Error parsing Gemini response for user {user_data['username']}: {e}")
                    print(f"Raw response: {response.text if hasattr(response, 'text') else response}")
                    continue
                    
                except ValueError as e:
                    print(f"[{datetime.now()}] Invalid response format for user {user_data['username']}: {e}")
                    continue
                
            except Exception as e:
                print(f"[{datetime.now()}] Error analyzing preferences for user {user_data['username']}: {e}")
                continue
        
        print(f"[{datetime.now()}] Completed user preference analysis")
        
    except Exception as e:
        print(f"[{datetime.now()}] Error in user preference analysis: {e}")

def main():
    print(f"[{datetime.now()}] Starting services...")
    
    # Schedule daily model training at 3 AM
    schedule.every().day.at("03:00").do(train_recommendation_model)
    
    # Schedule comment moderation every 5 minutes
    schedule.every(5).minutes.do(moderate_pending_comments)
    
    # Schedule video moderation every 10 minutes
    schedule.every(10).minutes.do(moderate_pending_videos)
    
    # Schedule user preference analysis daily at 4 AM
    schedule.every().day.at("04:00").do(analyze_user_preferences)
    
    # Run all tasks immediately on startup
    train_recommendation_model()
    moderate_pending_comments()
    moderate_pending_videos()
    analyze_user_preferences()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()
