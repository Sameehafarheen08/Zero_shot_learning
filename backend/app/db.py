"""
Database Connection Management
Supports both MySQL and SQLite databases
"""

# This module now uses the unified db connection that supports both MySQL and SQLite
from .db_unified import (
    get_db,
    execute_query, 
    execute_mutation,
    test_connection,
    db_connection
)

__all__ = ['get_db', 'execute_query', 'execute_mutation', 'test_connection', 'Error']

# For backward compatibility
try:
    from mysql.connector import Error
except ImportError:
    class Error(Exception):
        pass