import os
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from mysql.connector import Error
from dotenv import load_dotenv
from data_setup import create_database_connection
import pickle
from datetime import datetime

load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

def load_video_data_from_mysql():
    try:
        connection = create_database_connection()
        if not connection:
            raise Exception("Could not establish database connection")

        # Query to get video data with user interactions
        query = """
            SELECT 
                v.video_id,
                v.user_id,
                v.title,
                v.category,
                COUNT(DISTINCT l.like_id) as likes,
                COUNT(DISTINCT c.comment_id) as comments,
                COUNT(DISTINCT i.interaction_id) as views
            FROM videos v
            LEFT JOIN likes l ON v.video_id = l.video_id
            LEFT JOIN comments c ON v.video_id = c.video_id
            LEFT JOIN user_video_interactions i ON v.video_id = i.video_id
            WHERE v.is_active = true
            GROUP BY v.video_id, v.user_id, v.title, v.category
        """
        
        df = pd.read_sql(query, connection)
        connection.close()
        return df
        
    except Error as e:
        print(f"Error loading video data: {e}")
        return None

def train_recommendation_model(df):
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

def load_recommendation_model():
    try:
        with open('recommendation_model.pkl', 'rb') as f:
            return pickle.load(f)
    except:
        return None

def get_user_preferences(user_id):
    try:
        connection = create_database_connection()
        if not connection:
            raise Exception("Could not establish database connection")

        # Query to get user's video interaction history
        query = """
            SELECT DISTINCT v.category
            FROM user_video_interactions i
            JOIN videos v ON i.video_id = v.video_id
            WHERE i.user_id = %s
            AND i.interaction_timestamp >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        """
        
        df = pd.read_sql(query, connection, params=(user_id,))
        connection.close()
        
        return df['category'].unique().tolist()
        
    except Error as e:
        print(f"Error getting user preferences: {e}")
        return []

def get_user_viewed_videos(user_id):
    try:
        connection = create_database_connection()
        if not connection:
            raise Exception("Could not establish database connection")

        query = """
            SELECT DISTINCT video_id 
            FROM user_video_interactions 
            WHERE user_id = %s
        """
        
        df = pd.read_sql(query, connection, params=(user_id,))
        connection.close()
        
        return df['video_id'].tolist()
        
    except Error as e:
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
        
        # Load or train the model
        model_data = load_recommendation_model()
        if not model_data:
            print("Training new recommendation model...")
            df = load_video_data_from_mysql()
            if df is None:
                raise Exception("Could not load video data")
            model_data = train_recommendation_model(df)
            if model_data is None:
                raise Exception("Could not train model")
        
        # Get video data
        df = model_data['video_data']
        
        # Filter out viewed videos
        df_filtered = df[~df['video_id'].isin(viewed_video_ids)]
        
        # Filter by categories if provided
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
        
        # Return recommendations
        return recommendations[['video_id', 'title', 'category', 'likes', 'comments', 'views']].to_dict(orient='records')
        
    except Exception as e:
        print(f"Error generating recommendations: {e}")
        return []

if __name__ == "__main__":
    # Example usage
    example_categories = ["Entertainment & Pop Culture", "Gaming & Esports"]
    example_viewed_videos = []
    
    recommendations = recommend_videos(
        categories=example_categories,
        viewed_video_ids=example_viewed_videos
    )
    
    print("\nRecommended Videos:")
    for i, video in enumerate(recommendations, 1):
        print(f"\n{i}. Title: {video['title']}")
        print(f"   Category: {video['category']}")
        print(f"   Engagement: {video['likes']} likes, {video['comments']} comments, {video['views']} views") 