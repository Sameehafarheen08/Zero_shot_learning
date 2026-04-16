#!/usr/bin/env python3
"""
Database migration script to create detections table for object detection module
Run this once before using object detection features
"""

import mysql.connector
from mysql.connector import Error
import os
import sys
import logging
from pathlib import Path

# Load .env file
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                os.environ[key] = value

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_detections_table():
    """Create detections table in database"""
    conn = None
    cursor = None
    
    try:
        # Get credentials from environment
        config = {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", ""),
            "database": os.getenv("MYSQL_DB", "zero_shot_classifier")
        }
        
        logger.info(f"Connecting to {config['host']} as {config['user']}...")
        
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        logger.info("✅ Connected to database")
        
        # Create detections table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS detections (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id VARCHAR(255),
            image_path VARCHAR(512) NOT NULL,
            result_path VARCHAR(512) NOT NULL,
            object_count INT DEFAULT 0,
            confidence DECIMAL(3,2) DEFAULT 0.5,
            data LONGTEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_user_id (user_id),
            INDEX idx_timestamp (timestamp)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        cursor.execute(create_table_sql)
        conn.commit()
        
        logger.info("✅ Detections table created successfully")
        
        # Verify table was created
        cursor.execute("DESCRIBE detections")
        columns = cursor.fetchall()
        logger.info(f"Table structure (6 columns):")
        for col in columns:
            logger.info(f"  - {col[0]}: {col[1]}")
        
        return True
        
    except Error as e:
        logger.error(f"❌ Database error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            logger.info("Database connection closed")


if __name__ == "__main__":
    logger.info("Starting database migration...")
    logger.info("Creating detections table...")
    
    success = create_detections_table()
    
    if success:
        logger.info("✅ Migration completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Migration failed!")
        sys.exit(1)
