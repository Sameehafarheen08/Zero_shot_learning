"""
Utility Functions
JWT token management, validation, and decorators
"""

import jwt
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
import logging

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev_secret_key_change_in_production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


def generate_jwt_token(user_id: int, email: str) -> str:
    """
    Generate JWT token for user
    
    Args:
        user_id (int): User ID
        email (str): User email
    
    Returns:
        str: JWT token
    """
    try:
        payload = {
            "user_id": user_id,
            "email": email,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return token
    except Exception as e:
        logger.error(f"Error generating JWT token: {e}")
        raise


def verify_jwt_token(token: str) -> dict:
    """
    Verify and decode JWT token
    
    Args:
        token (str): JWT token to verify
    
    Returns:
        dict: Token payload if valid, None if invalid/expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return None


def get_token_from_request(req) -> str:
    """
    Extract JWT token from Authorization header
    
    Args:
        req: Flask request object
    
    Returns:
        str: Token or None
    """
    auth_header = req.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "")
    return None


def require_auth(f):
    """
    Decorator: Require valid JWT token
    
    Usage:
        @app.route("/api/protected")
        @require_auth
        def protected_route(user_id):
            return jsonify({"success": True})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_request(request)
        
        if not token:
            return jsonify({
                "success": False,
                "message": "Authentication token required"
            }), 401
        
        payload = verify_jwt_token(token)
        
        if not payload:
            return jsonify({
                "success": False,
                "message": "Invalid or expired token"
            }), 401
        
        # Pass user_id to decorated function
        return f(payload["user_id"], *args, **kwargs)
    
    return decorated_function


def require_admin(f):
    """
    Decorator: Require admin authentication
    
    Admin is identified by email: admin123@gmail.com
    
    Usage:
        @app.route("/api/admin/stats")
        @require_admin
        def admin_stats():
            return jsonify({"success": True})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_request(request)
        
        if not token:
            return jsonify({
                "success": False,
                "message": "Authentication required"
            }), 401
        
        payload = verify_jwt_token(token)
        
        if not payload:
            return jsonify({
                "success": False,
                "message": "Invalid or expired token"
            }), 401
        
        # Check if user email is the admin email
        admin_email = "admin123@gmail.com"
        user_email = payload.get("email", "").lower()
        
        if user_email != admin_email:
            logger.warning(f"Admin access attempt by non-admin user: {user_email}")
            return jsonify({
                "success": False,
                "message": "Admin access required"
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def validate_email(email: str) -> bool:
    """
    Basic email validation
    
    Args:
        email (str): Email address to validate
    
    Returns:
        bool: True if valid format, False otherwise
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_image_file(filename: str, allowed_extensions: set = None) -> bool:
    """
    Validate image file extension
    
    Args:
        filename (str): Filename to validate
        allowed_extensions (set): Set of allowed extensions (default: jpg, jpeg, png, webp)
    
    Returns:
        bool: True if valid, False otherwise
    """
    if allowed_extensions is None:
        allowed_extensions = {'jpg', 'jpeg', 'png', 'webp'}
    
    if '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in allowed_extensions


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage
    
    Args:
        filename (str): Original filename
    
    Returns:
        str: Sanitized filename
    """
    import re
    from werkzeug.utils import secure_filename
    return secure_filename(filename)


def format_timestamp(timestamp) -> str:
    """
    Format database timestamp to ISO format
    
    Args:
        timestamp: Database timestamp
    
    Returns:
        str: ISO format timestamp string
    """
    if isinstance(timestamp, str):
        return timestamp
    return timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)


def paginate(page: int = 1, per_page: int = 10) -> tuple:
    """
    Calculate offset and limit for pagination
    
    Args:
        page (int): Page number (1-based)
        per_page (int): Items per page
    
    Returns:
        tuple: (limit, offset)
    """
    page = max(page, 1)
    per_page = min(max(per_page, 1), 100)  # Cap at 100 items per page
    offset = (page - 1) * per_page
    return per_page, offset
