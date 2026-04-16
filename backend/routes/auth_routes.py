"""
Authentication Routes
Handles user signup, login, and logout
"""

from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from app.db import execute_query, execute_mutation, get_db
from app.utils import generate_jwt_token, verify_jwt_token
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


# ========================
# Route: User Signup
# ========================
@auth_bp.route("/api/auth/signup", methods=["POST"])
def signup():
    """
    Register a new user
    
    Request: {
        "email": "user@example.com",
        "password": "secure_password"
    }
    
    Response: {
        "success": true,
        "user_id": 1,
        "message": "Account created successfully"
    }
    """
    try:
        data = request.get_json()
        email = data.get("email", "").strip()
        password = data.get("password", "")
        
        # Validation
        if not email or not password:
            return jsonify({
                "success": False,
                "message": "Email and password are required"
            }), 400
        
        if len(password) < 6:
            return jsonify({
                "success": False,
                "message": "Password must be at least 6 characters"
            }), 400
        
        if "@" not in email:
            return jsonify({
                "success": False,
                "message": "Invalid email format"
            }), 400
        
        # Check if user already exists
        existing_user = execute_query(
            "SELECT id FROM users WHERE email = ?",
            (email,),
            fetch_one=True
        )
        
        if existing_user:
            return jsonify({
                "success": False,
                "message": "Email already registered"
            }), 409
        
        # Create user with hashed password
        password_hash = generate_password_hash(password)
        
        try:
            user_id = execute_mutation(
                "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (email, password_hash)
            )
            
            logger.info(f"New user registered: {email} (ID: {user_id})")
            
            return jsonify({
                "success": True,
                "user_id": user_id,
                "message": "Account created successfully"
            }), 201
            
        except Exception as e:
            logger.error(f"Database error during signup: {e}")
            return jsonify({
                "success": False,
                "message": "Database error during registration"
            }), 500
    
    except Exception as e:
        logger.error(f"Error in signup route: {e}")
        return jsonify({
            "success": False,
            "message": "Server error"
        }), 500


# ========================
# Route: User Login
# ========================
@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    """
    Authenticate user and return JWT token
    
    Request: {
        "email": "user@example.com",
        "password": "secure_password"
    }
    
    Response: {
        "success": true,
        "user_id": 1,
        "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "message": "Login successful"
    }
    """
    try:
        data = request.get_json()
        email = data.get("email", "").strip()
        password = data.get("password", "")
        
        if not email or not password:
            return jsonify({
                "success": False,
                "message": "Email and password are required"
            }), 400
        
        # Find user by email
        user = execute_query(
            "SELECT id, email, password_hash FROM users WHERE email = ?",
            (email,),
            fetch_one=True
        )
        
        if not user:
            logger.warning(f"Login attempt with non-existent email: {email}")
            return jsonify({
                "success": False,
                "message": "Invalid email or password"
            }), 401
        
        # Verify password
        if not check_password_hash(user["password_hash"], password):
            logger.warning(f"Failed login attempt for user: {email}")
            return jsonify({
                "success": False,
                "message": "Invalid email or password"
            }), 401
        
        # Generate JWT token
        token = generate_jwt_token(user["id"], user["email"])
        
        # Check if user is admin
        is_admin = email.lower() == "admin123@gmail.com"
        
        logger.info(f"User login successful: {email} (Admin: {is_admin})")
        
        return jsonify({
            "success": True,
            "user_id": user["id"],
            "email": user["email"],
            "token": token,
            "is_admin": is_admin,
            "message": "Login successful"
        }), 200
    
    except Exception as e:
        logger.error(f"Error in login route: {e}")
        return jsonify({
            "success": False,
            "message": "Server error"
        }), 500


# ========================
# Route: User Logout
# ========================
@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    """
    Logout user (client-side token removal)
    
    Response: {
        "success": true,
        "message": "Logged out successfully"
    }
    """
    try:
        # In a stateless JWT system, logout is mainly client-side
        # Here we just return success
        logger.info("User logout")
        
        return jsonify({
            "success": True,
            "message": "Logged out successfully"
        }), 200
    
    except Exception as e:
        logger.error(f"Error in logout route: {e}")
        return jsonify({
            "success": False,
            "message": "Server error"
        }), 500


# ========================
# Route: Verify Token
# ========================
@auth_bp.route("/api/auth/verify", methods=["GET"])
def verify_token():
    """
    Verify JWT token validity
    
    Headers: Authorization: Bearer <token>
    
    Response: {
        "success": true,
        "user_id": 1,
        "email": "user@example.com"
    }
    """
    try:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        
        if not token:
            return jsonify({
                "success": False,
                "message": "No token provided"
            }), 401
        
        payload = verify_jwt_token(token)
        
        if not payload:
            return jsonify({
                "success": False,
                "message": "Invalid or expired token"
            }), 401
        
        return jsonify({
            "success": True,
            "user_id": payload.get("user_id"),
            "email": payload.get("email")
        }), 200
    
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return jsonify({
            "success": False,
            "message": "Token verification failed"
        }), 401
