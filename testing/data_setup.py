import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv


load_dotenv()

def create_database_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL Database: {e}")
        return None

def create_tables(connection):
    cursor = connection.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id VARCHAR(255) PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            profile_picture_url VARCHAR(255),
            bio TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            preferences JSON,
            is_active BOOLEAN DEFAULT true,
            last_login TIMESTAMP
        )
    """)

    # Videos table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            video_id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255),
            title VARCHAR(255) NOT NULL,
            description TEXT,
            video_data MEDIUMBLOB,
            thumbnail_url VARCHAR(255),
            category VARCHAR(50),
            duration INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            view_count INT DEFAULT 0,
            like_count INT DEFAULT 0,
            comment_count INT DEFAULT 0,
            is_active BOOLEAN DEFAULT true,
            moderation_status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
            moderation_reason TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # Comments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            comment_id VARCHAR(255) PRIMARY KEY,
            video_id VARCHAR(255),
            user_id VARCHAR(255),
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            like_count INT DEFAULT 0,
            is_active BOOLEAN DEFAULT true,
            moderation_status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
            moderation_score FLOAT,
            moderation_labels JSON,
            moderation_reason TEXT,
            FOREIGN KEY (video_id) REFERENCES videos(video_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # Likes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS likes (
            like_id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255),
            video_id VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (video_id) REFERENCES videos(video_id),
            UNIQUE KEY unique_like (user_id, video_id)
        )
    """)

    # User Video Interactions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_video_interactions (
            interaction_id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255),
            video_id VARCHAR(255),
            interaction_type ENUM('view', 'like', 'comment', 'share'),
            interaction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            watch_duration INT,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (video_id) REFERENCES videos(video_id)
        )
    """)

    # # Video Recommendations table
    # cursor.execute("""
    #     CREATE TABLE IF NOT EXISTS video_recommendations (
    #         recommendation_id VARCHAR(255) PRIMARY KEY,
    #         user_id VARCHAR(255),
    #         video_id VARCHAR(255),
    #         recommendation_score FLOAT,
    #         generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    #         is_shown BOOLEAN DEFAULT false,
    #         is_clicked BOOLEAN DEFAULT false,
    #         FOREIGN KEY (user_id) REFERENCES users(user_id),
    #         FOREIGN KEY (video_id) REFERENCES videos(video_id)
    #     )
    # """)

    # Moderation History table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS moderation_history (
            history_id VARCHAR(255) PRIMARY KEY,
            content_type ENUM('video', 'comment'),
            content_id VARCHAR(255),
            moderation_action ENUM('flag', 'approve', 'reject', 'restore'),
            action_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            moderation_reason TEXT,
            automated BOOLEAN DEFAULT true
        )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_category ON videos(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_video_id ON comments(video_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_user_id ON user_video_interactions(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_video_id ON user_video_interactions(video_id)")
    #cursor.execute("CREATE INDEX IF NOT EXISTS idx_recommendations_user_id ON video_recommendations(user_id)")

    connection.commit()
    cursor.close()

def main():
    connection = create_database_connection()
    if connection is not None:
        create_tables(connection)
        print("Database tables created successfully!")
        connection.close()
    else:
        print("Failed to create database tables.")

if __name__ == "__main__":
    main()
