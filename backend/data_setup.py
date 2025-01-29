import os
import mysql.connector
from dotenv import load_dotenv

def create_database_connection():

    try:
        load_dotenv()

        config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD'),
            'database': os.getenv('DB_NAME'),
            'port': int(os.getenv('DB_PORT', '3306')),
            'raise_on_warnings': True
        }
        
        connection = mysql.connector.connect(**config)
        
        if connection.is_connected():
            print("Successfully connected to MySQL database")
            return connection
            
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL database: {e}")
        return None

if __name__ == "__main__":
    conn = create_database_connection()
    if conn:
        conn.close() 