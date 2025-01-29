import os
import time
import uuid
import json
import google.generativeai as genai
from mysql.connector import Error
from dotenv import load_dotenv
from data_setup import create_database_connection
import hashlib
from google.ai.generativelanguage_v1beta.types import content
import random
import subprocess
import tempfile

load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

TEST_USERS = [
    {"username": "influencer_vibes", "email": "influencer@test.com"},
    {"username": "trending_now", "email": "trending@test.com"},
    {"username": "viral_moments", "email": "viral@test.com"},
    {"username": "social_butterfly", "email": "social@test.com"},
    {"username": "content_creator", "email": "creator@test.com"}
]

def ensure_connection(connection):
    try:
        if connection and connection.is_connected():
            return connection
        return create_database_connection()
    except Error:
        return create_database_connection()

def create_test_users(connection):
    try:
        cursor = connection.cursor()
        user_ids = []
        
        for user in TEST_USERS:
            cursor.execute("SELECT user_id FROM users WHERE email = %s", (user["email"],))
            result = cursor.fetchone()
            
            if result:
                user_ids.append(result[0])
                continue
                
            user_id = str(uuid.uuid4())
            password = "test123test123"
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            profile_picture_url = f"https://api.dicebear.com/9.x/adventurer/svg?seed={user['username']}"
            
            insert_query = """
                INSERT INTO users (user_id, username, email, password_hash, profile_picture_url)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (user_id, user["username"], user["email"], password_hash, profile_picture_url))
            connection.commit()
            user_ids.append(user_id)
        
        cursor.close()
        return user_ids
        
    except Error as e:
        print(f"Error creating test users: {e}")
        return None

def upload_to_gemini(path, mime_type=None):
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"Uploaded file '{file.display_name}' as: {file.uri}")
    return file

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
    print()

def get_video_categories(video_path):
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
        system_instruction="""Give me back the category it belongs in these are the only option and also u can make it so they belong in multiple if you see fit:
None
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
Pets & Animals"""
    )

    files = [upload_to_gemini(video_path, mime_type="video/mp4")]
    wait_for_files_active(files)

    chat_session = model.start_chat(
        history=[
            {
                "role": "user",
                "parts": [files[0]],
            },
        ]
    )

    response = chat_session.send_message("What categories does this video belong to?")
    try:
        response_json = json.loads(response.text)
        return response_json.get("categories", [])
    except json.JSONDecodeError:
        return [cat.strip() for cat in response.text.split('\n') if cat.strip()]

def save_video_to_database(connection, video_path, categories, user_ids):
    try:
        connection = ensure_connection(connection)
        if not connection:
            raise Exception("Could not establish database connection")
            
        cursor = connection.cursor()
        
        user_id = random.choice(user_ids)
        
        # Read video file as binary
        with open(video_path, 'rb') as file:
            video_data = file.read()
        
        # Generate a unique video ID
        video_id = str(uuid.uuid4())
        
        # Insert video using MEDIUMBLOB
        video_insert_query = """
            INSERT INTO videos (video_id, user_id, title, video_data, category)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        title = os.path.splitext(os.path.basename(video_path))[0]
        
        categories_str = ', '.join(categories)
        
        cursor.execute(video_insert_query, (video_id, user_id, title, video_data, categories_str))
        connection.commit()
        
        cursor.execute("SELECT username FROM users WHERE user_id = %s", (user_id,))
        username = cursor.fetchone()[0]
        
        print(f"Successfully uploaded video: {title}")
        print(f"Uploaded by user: {username}")
        print(f"Categories: {categories_str}")
        
        cursor.close()
        return True
        
    except Error as e:
        print(f"Error saving video to database: {e}")
        return False

def transcode_video(input_path):
    try:
        # Create a temporary file for the transcoded video
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            output_path = temp_file.name

        # FFmpeg command to convert to H.264/AAC format
        command = [
            'ffmpeg',
            '-i', input_path,  # Input file
            '-c:v', 'libx264',  # Video codec: H.264
            '-preset', 'medium',  # Encoding preset (balance between speed and quality)
            '-crf', '23',  # Constant Rate Factor (quality: 0-51, lower is better)
            '-c:a', 'aac',  # Audio codec: AAC
            '-b:a', '128k',  # Audio bitrate
            '-movflags', '+faststart',  # Enable fast start for web playback
            '-y',  # Overwrite output file if it exists
            output_path
        ]

        # Run FFmpeg
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr}")
            return None
            
        return output_path
        
    except Exception as e:
        print(f"Error transcoding video: {e}")
        return None

def process_videos_in_directory(directory_path):
    connection = create_database_connection()
    if not connection:
        print("Failed to connect to database")
        return

    # Create test users first
    user_ids = create_test_users(connection)
    if not user_ids:
        print("Failed to create test users")
        return

    for filename in os.listdir(directory_path):
        if filename.lower().endswith(('.mp4', '.avi', '.mov', '.wmv')):
            video_path = os.path.join(directory_path, filename)
            print(f"\nProcessing video: {filename}")
            
            try:
                connection = ensure_connection(connection)
                if not connection:
                    raise Exception("Could not establish database connection")
                
                # Transcode video to web-compatible format
                print("Transcoding video to web-compatible format...")
                transcoded_path = transcode_video(video_path)
                
                if not transcoded_path:
                    print(f"Failed to transcode {filename}")
                    continue
                
                categories = get_video_categories(transcoded_path)
                
                if save_video_to_database(connection, transcoded_path, categories, user_ids):
                    print(f"Successfully processed and uploaded: {filename}")
                else:
                    print(f"Failed to save {filename} to database")
                
                os.unlink(transcoded_path)
                    
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                connection = create_database_connection()

    if connection:
        connection.close()

def transcode_existing_videos(connection):
    try:
        connection = ensure_connection(connection)
        if not connection:
            raise Exception("Could not establish database connection")
            
        cursor = connection.cursor()
        

        cursor.execute("SELECT video_id, video_data FROM videos")
        videos = cursor.fetchall()
        
        print(f"Found {len(videos)} videos to process")
        
        for video_id, video_data in videos:
            print(f"\nProcessing video ID: {video_id}")
            
            try:

                connection = ensure_connection(connection)
                if not connection:
                    raise Exception("Could not establish database connection")
                cursor = connection.cursor()
                
                with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_input:
                    temp_input.write(video_data)
                    input_path = temp_input.name
                
                print("Transcoding video...")
                transcoded_path = transcode_video(input_path)
                
                if not transcoded_path:
                    print(f"Failed to transcode video {video_id}")
                    os.unlink(input_path)
                    continue
                
                # Read transcoded video
                with open(transcoded_path, 'rb') as file:
                    transcoded_data = file.read()
                
                # Ensure connection is still active before update
                connection = ensure_connection(connection)
                if not connection:
                    raise Exception("Could not establish database connection")
                cursor = connection.cursor()
                
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        update_query = "UPDATE videos SET video_data = %s WHERE video_id = %s"
                        cursor.execute(update_query, (transcoded_data, video_id))
                        connection.commit()
                        print(f"Successfully transcoded and updated video: {video_id}")
                        break
                    except Error as e:
                        if attempt < max_retries - 1:
                            print(f"Update failed, retrying... (Attempt {attempt + 1}/{max_retries})")
                            connection = ensure_connection(connection)
                            if connection:
                                cursor = connection.cursor()
                            time.sleep(1)
                        else:
                            raise e
                
                os.unlink(input_path)
                os.unlink(transcoded_path)
                
            except Exception as e:
                print(f"Error processing video {video_id}: {e}")
                try:
                    connection = create_database_connection()
                    if connection:
                        cursor = connection.cursor()
                except:
                    pass
                continue
        
        if cursor:
            cursor.close()
        print("\nFinished processing all videos")
        
    except Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if connection and connection.is_connected():
            connection.close()

if __name__ == "__main__":
    while True:
        print("\nChoose an option:")
        print("1. Process and upload new videos from directory")
        print("2. Transcode existing videos in database")
        print("3. Exit")
        
        choice = input("Enter your choice (1-3): ")
        
        if choice == "1":
            download_directory = "../download"
            process_videos_in_directory(download_directory)
        elif choice == "2":
            connection = create_database_connection()
            if connection:
                transcode_existing_videos(connection)
                connection.close()
            else:
                print("Failed to connect to database")
        elif choice == "3":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.") 