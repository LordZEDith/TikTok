import os
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from mysql.connector import Error
from dotenv import load_dotenv
from sqlalchemy import create_engine
import pickle
from datetime import datetime
from pathlib import Path
import time

load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

DATABASE_URL = f"mysql+mysqlconnector://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
engine = create_engine(DATABASE_URL)

def load_video_data_from_mysql():
    try:
        query = """
            SELECT 
                v.video_id,
                v.user_id,
                v.title,
                v.category,
                v.is_active,
                COALESCE(COUNT(DISTINCT l.like_id), 0) as likes,
                COALESCE(COUNT(DISTINCT c.comment_id), 0) as comments,
                COALESCE(COUNT(DISTINCT i.interaction_id), 0) as views
            FROM videos v
            LEFT JOIN likes l ON v.video_id = l.video_id
            LEFT JOIN comments c ON v.video_id = c.video_id
            LEFT JOIN user_video_interactions i ON v.video_id = i.video_id AND i.interaction_type = 'view'
            WHERE v.is_active = true
            GROUP BY v.video_id, v.user_id, v.title, v.category, v.is_active
        """
        
        df = pd.read_sql(query, engine)
        return df
        
    except Exception as e:
        print(f"Error loading video data: {e}")
        return None

def train_recommendation_model(df):
    """Train and save the recommendation model."""
    try:
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
        
        with open('recommendation_model.pkl', 'wb') as f:
            pickle.dump(model_data, f)
            
        return model_data
        
    except Exception as e:
        print(f"Error training model: {e}")
        return None

def cleanup_old_models(model_dir: Path):
    try:
        model_files = [f for f in model_dir.glob('recommendation_model_*.pkl')]
        
        if not model_files:
            return
            
        model_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        latest_model = model_files[0]
        print(f"Keeping latest model: {latest_model.name}")
        
        for model_file in model_files[1:]:
            print(f"Removing old model: {model_file}")
            model_file.unlink()
                
    except Exception as e:
        print(f"Error cleaning up old models: {e}")

def load_recommendation_model():
    try:
        model_dir = Path(__file__).parent / 'model'
        
        model_files = list(model_dir.glob('recommendation_model_*.pkl'))
        
        if not model_files:
            print("No recommendation models found")
            return None
            
        latest_model = max(model_files, key=lambda x: x.stat().st_mtime)
        print(f"Loading model: {latest_model.name}")
        
        cleanup_old_models(model_dir)
            
        with open(latest_model, 'rb') as f:
            return pickle.load(f)
            
    except Exception as e:
        print(f"Error loading recommendation model: {e}")
        return None

def get_user_preferences(user_id):
    """Get user's viewing preferences from their history."""
    try:
        query = """
            SELECT DISTINCT v.category
            FROM user_video_interactions i
            JOIN videos v ON i.video_id = v.video_id
            WHERE i.user_id = %s
            AND i.interaction_timestamp >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        """
        
        df = pd.read_sql(query, engine, params=(user_id,))
        return df['category'].unique().tolist()
        
    except Exception as e:
        print(f"Error getting user preferences: {e}")
        return []

def get_user_viewed_videos(user_id):
    try:
        query = """
            SELECT DISTINCT video_id 
            FROM user_video_interactions 
            WHERE user_id = %s
        """
        
        df = pd.read_sql(query, engine, params=(user_id,))
        return df['video_id'].tolist()
        
    except Exception as e:
        print(f"Error getting viewed videos: {e}")
        return []

def recommend_videos(categories, viewed_video_ids=None, top_n=8):
    """
    Recommend videos based on categories and viewing history.
    
    Args:
        categories (list): List of category names to base recommendations on
        viewed_video_ids (list, optional): List of video IDs to exclude from recommendations
        top_n (int, optional): Number of recommendations to return. Defaults to 8.
    
    Returns:
        list: List of recommended video dictionaries
    """
    try:
        viewed_video_ids = viewed_video_ids or []
        
        model_data = load_recommendation_model()
        if not model_data:
            print("No recommendation model available")
            return []
        
        df = model_data['video_data']
        
        df_filtered = df[~df['video_id'].isin(viewed_video_ids)]
        
        if categories:
            # Convert categories to lowercase for case-insensitive matching
            categories_lower = [cat.lower() for cat in categories]
            df_filtered = df_filtered[
                df_filtered['category'].str.lower().apply(
                    lambda x: any(cat in x.lower() for cat in categories_lower)
                )
            ]
        
        # Calculate recommendation scores
        similarity_scores = model_data['similarity_matrix']
        
        # Combine similarity and engagement scores
        final_scores = []
        for idx, row in df_filtered.iterrows():
            # Get average similarity with preferred categories
            category_sim = np.mean([
                similarity_scores[i][idx]
                for i in range(len(df))
                if any(cat.lower() in df.iloc[i]['category'].lower() for cat in categories)
            ]) if categories else 0.5
            
            # Combine with engagement score
            final_score = (category_sim * 0.7) + (row['engagement_score'] * 0.3)
            final_scores.append(final_score)
        
        df_filtered['final_score'] = final_scores
        
        # Sort and get top recommendations
        recommendations = df_filtered.nlargest(top_n, 'final_score')
        
        # Return recommendations with user_id
        return recommendations[['video_id', 'user_id', 'title', 'category', 'likes', 'comments', 'views']].to_dict(orient='records')
        
    except Exception as e:
        print(f"Error generating recommendations: {e}")
        return []