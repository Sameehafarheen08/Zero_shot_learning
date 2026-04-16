"""
Database Initialization Script
Run this script to initialize the MySQL database with schema and sample data
"""

import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "zero_shot_classifier")

def read_sql_file(filepath):
    """Read SQL schema from file"""
    try:
        with open(filepath, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading SQL file: {e}")
        return None

def init_database():
    """Initialize database with schema"""
    try:
        # Connect to MySQL without selecting database first
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD
        )
        cursor = conn.cursor()
        
        print(f"Connected to MySQL server at {MYSQL_HOST}")
        
        # Read schema file
        schema_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'schema.sql')
        schema = read_sql_file(schema_path)
        
        if not schema:
            print("Failed to read schema.sql")
            return False
        
        # Execute schema statements
        for statement in schema.split(';'):
            statement = statement.strip()
            if statement:
                try:
                    cursor.execute(statement)
                    print(f"✓ Executed: {statement[:50]}...")
                except Error as e:
                    # Skip errors for existing tables
                    if "already exists" not in str(e):
                        print(f"✗ Error: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n✅ Database initialized successfully!")
        print(f"Database: {MYSQL_DB}")
        print(f"Tables created: users, predictions, feedback")
        print(f"Admin user: admin123@gmail.com / admin123")
        
        return True
        
    except Error as e:
        print(f"❌ Database connection error: {e}")
        print("\nMake sure:")
        print("1. MySQL server is running")
        print("2. Credentials in .env are correct")
        print("3. User has privileges to create databases")
        return False

if __name__ == "__main__":
    print("Zero-Shot Image Classifier - Database Initialization")
    print("=" * 50)
    
    success = init_database()
    
    if success:
        print("\n✅ Ready to start the backend!")
        print("Run: python backend/run.py")
    else:
        print("\n❌ Database initialization failed")
        exit(1)
