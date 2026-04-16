"""
Unified Database Connection Management
Supports both MySQL and SQLite databases
"""

import os
import sqlite3
from contextlib import contextmanager

# Get database type from environment
DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///zero_shot_classifier.db")

# MySQL imports (optional if not using MySQL)
try:
    import mysql.connector
    from mysql.connector import Error, pooling
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    Error = Exception

# ============= SQLite Connection =============
class SQLiteConnection:
    def __init__(self, db_path):
        self.db_path = db_path
        
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    @contextmanager    
    def get_cursor(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

# ============= MySQL Connection =============
class MySQLConnection:
    def __init__(self, config):
        self.config = config
        try:
            self.pool = pooling.MySQLConnectionPool(**config)
        except Exception as e:
            print(f"Error creating MySQL pool: {e}")
            self.pool = None
    
    def get_connection(self):
        if not self.pool:
            raise Error("MySQL pool not initialized")
        return self.pool.get_connection()
    
    @contextmanager
    def get_cursor(self):
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

# ============= Initialize Connection =============
if DB_TYPE == "sqlite":
    # Extract path from DATABASE_URL
    db_path = DATABASE_URL.replace("sqlite:///", "")
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(__file__), '..', db_path)
    db_connection = SQLiteConnection(db_path)
    print(f"✓ Using SQLite database: {db_path}")
elif DB_TYPE == "mysql" and MYSQL_AVAILABLE:
    mysql_config = {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DB", "zero_shot_classifier"),
        "pool_name": "zero_shot_pool",
        "pool_size": 5,
    }
    db_connection = MySQLConnection(mysql_config)
    print(f"✓ Using MySQL database: {mysql_config['database']}")
else:
    # Default to SQLite
    db_path = "zero_shot_classifier.db"
    db_connection = SQLiteConnection(db_path)
    print(f"✓ Using SQLite database (default): {db_path}")

# ============= Public API =============
def get_db():
    """Get database connection (backward compatible)"""
    if isinstance(db_connection, SQLiteConnection):
        return db_connection.get_connection()
    else:
        return db_connection.get_connection()

def execute_query(query, params=None, fetch_one=False):
    """
    Execute a SELECT query
    
    Args:
        query (str): SQL query 
        params (tuple/list): Query parameters
        fetch_one (bool): Return one row or all rows
        
    Returns:
        dict or list: Query result(s)
    """
    try:
        with db_connection.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetch_one:
                result = cursor.fetchone()
                if isinstance(result, sqlite3.Row):
                    result = dict(result)
                return result
            else:
                result = cursor.fetchall()
                if isinstance(result, list) and result and isinstance(result[0], sqlite3.Row):
                    result = [dict(row) for row in result]
                return result
    except Exception as e:
        print(f"Database error in execute_query: {e}")
        raise

def execute_mutation(query, params=None):
    """
    Execute an INSERT/UPDATE/DELETE query
    
    Args:
        query (str): SQL query
        params (tuple/list): Query parameters
        
    Returns:
        int: Last inserted ID or rows affected
    """
    try:
        with db_connection.get_cursor() as cursor:
            cursor.execute(query, params or ())
            
            # Get last insert id or affected rows
            if hasattr(cursor, 'lastrowid'):
                return cursor.lastrowid
            else:
                return cursor.rowcount
    except Exception as e:
        print(f"Database error in execute_mutation:  {e}")
        raise

def test_connection():
    """Test database connection"""
    try:
        result = execute_query("SELECT 1 as test", fetch_one=True)
        print(f"✓ Database connection successful")
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False
