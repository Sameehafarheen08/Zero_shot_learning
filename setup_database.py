#!/usr/bin/env python3
"""
Database Setup Script - No MySQL Workbench Required
This script initializes the database using Python and mysql-connector
"""

import subprocess
import sys
import os

def install_mysql_connector():
    """Install mysql-connector-python if not available"""
    print("Installing mysql-connector-python...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mysql-connector-python"])

def setup_database():
    """Setup database with schema"""
    import mysql.connector
    from mysql.connector import Error

    # Load credentials from env file
    env_file = '/home/boss/Documents/zero_shot_full_html_frontend/backend/.env'
    config = {}
    
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    
    # Database connection parameters
    host = config.get('MYSQL_HOST', 'localhost')
    user = config.get('MYSQL_USER', 'root')
    password = config.get('MYSQL_PASSWORD', '')
    database = config.get('MYSQL_DB', 'zero_shot_classifier')
    
    print(f"Connecting to MySQL on {host}...")
    print(f"User: {user}")
    
    try:
        # Connect to MySQL
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            auth_plugin='mysql_native_password'
        )
        cursor = conn.cursor()
        print("✓ Connected to MySQL successfully!")
        
        # Read and execute schema file
        schema_path = '/home/boss/Documents/zero_shot_full_html_frontend/database/schema.sql'
        
        print(f"Reading schema from {schema_path}...")
        with open(schema_path, 'r') as f:
            schema_content = f.read()
        
        # Split by semicolon and execute each statement
        statements = [s.strip() for s in schema_content.split(';') if s.strip()]
        
        for i, statement in enumerate(statements, 1):
            print(f"Executing statement {i}/{len(statements)}...")
            try:
                cursor.execute(statement)
            except Exception as e:
                print(f"Warning: {e}")
        
        conn.commit()
        print("✓ Database schema created successfully!")
        
        # Verify tables were created
        cursor.execute(f"USE {database}")
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        print("\n✓ Tables created:")
        for table in tables:
            print(f"  - {table[0]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Database Setup Script")
    print("=" * 60)
    
    if setup_database():
        print("\n✓ Database setup completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Database setup failed!")
        sys.exit(1)
