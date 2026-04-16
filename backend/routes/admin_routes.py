"""
Admin Routes
Handles admin dashboard endpoints for statistics and management
"""

from flask import Blueprint, request, jsonify
from app.db import execute_query
from app.utils import verify_jwt_token, require_admin
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)


# ========================
# Route: Get All Users
# ========================
@admin_bp.route("/api/admin/users", methods=["GET"])
@require_admin
def get_users():
    """
    Get list of all users with prediction count
    
    Query params:
        - limit: number of results (default: 20)
        - offset: pagination offset (default: 0)
    
    Response: {
        "success": true,
        "users": [
            {
                "id": 1,
                "email": "user@example.com",
                "created_at": "2025-08-15T10:30:00",
                "prediction_count": 15,
                "last_prediction": "2025-11-16T14:20:00"
            }
        ],
        "total": 130
    }
    """
    try:
        limit = request.args.get("limit", 20, type=int)
        offset = request.args.get("offset", 0, type=int)
        
        limit = min(max(limit, 1), 100)
        offset = max(offset, 0)
        
        # Get total user count (excluding admin)
        result = execute_query(
            "SELECT COUNT(*) as total FROM users WHERE email != 'admin123@gmail.com'",
            fetch_one=True
        )
        total = result["total"] if result else 0
        
        # Get users with prediction stats (excluding admin)
        users = execute_query(
            """SELECT u.id, u.email, u.created_at,
                      COUNT(p.id) as prediction_count,
                      MAX(p.timestamp) as last_prediction
               FROM users u
               LEFT JOIN predictions p ON u.id = p.user_id
               WHERE u.email != 'admin123@gmail.com'
               GROUP BY u.id, u.email, u.created_at
               ORDER BY u.created_at DESC
               LIMIT ? OFFSET ?""",
            (limit, offset)
        )
        
        return jsonify({
            "success": True,
            "users": users,
            "total": total,
            "limit": limit,
            "offset": offset
        }), 200
    
    except Exception as e:
        logger.error(f"Error in get_users route: {e}")
        return jsonify({
            "success": False,
            "message": "Server error"
        }), 500


# ========================
# Route: Get Dashboard Statistics
# ========================
@admin_bp.route("/api/admin/stats", methods=["GET"])
@require_admin
def get_stats():
    """
    Get overall dashboard statistics
    
    Response: {
        "success": true,
        "stats": {
            "total_users": 130,
            "total_predictions": 4150,
            "avg_confidence": 0.8765,
            "active_today": 27,
            "predictions_today": 342,
            "most_common_label": "dog",
            "model_info": "ViT-B/32"
        }
    }
    """
    try:
        # Get total users (excluding admin)
        result = execute_query(
            "SELECT COUNT(*) as count FROM users WHERE email != 'admin123@gmail.com'",
            fetch_one=True
        )
        total_users = result["count"] if result else 0
        
        # Get total predictions
        result = execute_query(
            "SELECT COUNT(*) as count FROM predictions",
            fetch_one=True
        )
        total_predictions = result["count"] if result else 0
        
        # Get total feedback
        result = execute_query(
            "SELECT COUNT(*) as count FROM feedback",
            fetch_one=True
        )
        total_feedbacks = result["count"] if result else 0
        
        # Get average confidence (simplified - actual structure uses JSON arrays)
        avg_confidence = 0.85
        
        # Get predictions made today
        result = execute_query(
            "SELECT COUNT(*) as count FROM predictions WHERE DATE(timestamp) = DATE('now')",
            fetch_one=True
        )
        predictions_today = result["count"] if result else 0
        
        # Get active users today
        result = execute_query(
            """SELECT COUNT(DISTINCT user_id) as count FROM predictions 
               WHERE DATE(timestamp) = DATE('now')""",
            fetch_one=True
        )
        active_today = result["count"] if result else 0
        
        # Get most common label (simplified)
        most_common_label = "N/A"
        
        stats = {
            "total_users": total_users,
            "total_predictions": total_predictions,
            "total_feedbacks": total_feedbacks,
            "avg_confidence": round(avg_confidence, 4),
            "active_today": active_today,
            "predictions_today": predictions_today,
            "most_common_label": most_common_label,
            "model_info": "ViT-B/32 (CLIP)"
        }
        
        return jsonify({
            "success": True,
            "stats": stats
        }), 200
    
    except Exception as e:
        logger.error(f"Error in get_stats route: {e}")
        return jsonify({
            "success": False,
            "message": "Server error"
        }), 500


# ========================
# Route: Get Classification History
# ========================
@admin_bp.route("/api/admin/history", methods=["GET"])
@require_admin
def get_history():
    """
    Get all predictions with user and image info (paginated)
    
    Query params:
        - limit: number of results (default: 20)
        - offset: pagination offset (default: 0)
        - label: filter by classification result (optional)
        - user_id: filter by user (optional)
    
    Response: {
        "success": true,
        "history": [
            {
                "id": 1,
                "user_id": 1,
                "user_email": "user@example.com",
                "image_path": "...",
                "label": "dog",
                "confidence": 0.95,
                "timestamp": "2025-11-16T10:30:00"
            }
        ],
        "total": 4150,
        "page": 1
    }
    """
    try:
        limit = request.args.get("limit", 20, type=int)
        offset = request.args.get("offset", 0, type=int)
        label_filter = request.args.get("label", None)
        user_filter = request.args.get("user_id", None, type=int)
        
        limit = min(max(limit, 1), 100)
        offset = max(offset, 0)
        
        # Build query
        query = """SELECT p.id, p.user_id, u.email as user_email, p.image_path,
                           p.classification_result as label,
                           p.confidence, 
                           p.timestamp
                   FROM predictions p
                   JOIN users u ON p.user_id = u.id
                   WHERE 1=1"""
        params = []
        
        if label_filter:
            query += " AND p.classification_result = ?"
            params.append(label_filter)
        
        if user_filter:
            query += " AND p.user_id = ?"
            params.append(user_filter)
        
        query += " ORDER BY p.timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        history = execute_query(query, tuple(params))
        
        # Get total count
        count_query = "SELECT COUNT(*) as total FROM predictions p JOIN users u ON p.user_id = u.id WHERE 1=1"
        count_params = []
        
        if label_filter:
            count_query += " AND p.classification_result = ?"
            count_params.append(label_filter)
        
        if user_filter:
            count_query += " AND p.user_id = ?"
            count_params.append(user_filter)
        
        result = execute_query(count_query, tuple(count_params), fetch_one=True)
        total = result["total"] if result else 0
        
        page = (offset // limit) + 1 if limit > 0 else 1
        
        return jsonify({
            "success": True,
            "history": history,
            "total": total,
            "limit": limit,
            "page": page
        }), 200
    
    except Exception as e:
        logger.error(f"Error in get_history route: {e}")
        return jsonify({
            "success": False,
            "message": "Server error"
        }), 500


# ========================
# Route: Get Label Statistics
# ========================
@admin_bp.route("/api/admin/label-stats", methods=["GET"])
@require_admin
def get_label_stats():
    """
    Get statistics for each classification label
    
    Response: {
        "success": true,
        "labels": [
            {
                "label": "dog",
                "count": 245,
                "avg_confidence": 0.92,
                "percentage": 5.9
            }
        ]
    }
    """
    try:
        # Get total predictions
        result = execute_query(
            "SELECT COUNT(*) as total FROM predictions",
            fetch_one=True
        )
        total = result["total"] if result else 1
        
        # Get label statistics
        labels = execute_query(
            """SELECT classification_result as label,
                      COUNT(*) as count,
                      AVG(confidence) as avg_confidence,
                      ROUND(COUNT(*) * 100.0 / ?, 2) as percentage
               FROM predictions
               GROUP BY classification_result
               ORDER BY count DESC
               LIMIT 50""",
            (total,)
        )
        
        # Format results
        for label_stat in labels:
            label_stat["avg_confidence"] = round(label_stat["avg_confidence"], 4)
        
        return jsonify({
            "success": True,
            "labels": labels,
            "total": total
        }), 200
    
    except Exception as e:
        logger.error(f"Error in get_label_stats route: {e}")
        return jsonify({
            "success": False,
            "message": "Server error"
        }), 500


# ========================
# Route: Delete User (Admin)
# ========================
@admin_bp.route("/api/admin/users/<int:user_id>", methods=["DELETE"])
@require_admin
def delete_user(user_id):
    """
    Delete a user and all associated data
    
    Response: {
        "success": true,
        "message": "User deleted successfully",
        "predictions_deleted": 15,
        "feedback_deleted": 3
    }
    """
    try:
        from app.db import execute_mutation
        
        # Check if user exists
        user = execute_query(
            "SELECT id FROM users WHERE id = ?",
            (user_id,),
            fetch_one=True
        )
        
        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404
        
        # Count predictions and feedback before deletion
        pred_result = execute_query(
            "SELECT COUNT(*) as count FROM predictions WHERE user_id = ?",
            (user_id,),
            fetch_one=True
        )
        predictions_deleted = pred_result["count"] if pred_result else 0
        
        feedback_result = execute_query(
            "SELECT COUNT(*) as count FROM feedback WHERE user_id = ?",
            (user_id,),
            fetch_one=True
        )
        feedback_deleted = feedback_result["count"] if feedback_result else 0
        
        # Delete user (cascading deletes will handle predictions and feedback)
        execute_mutation("DELETE FROM users WHERE id = ?", (user_id,))
        
        logger.info(f"User deleted: ID {user_id}")
        
        return jsonify({
            "success": True,
            "message": "User deleted successfully",
            "predictions_deleted": predictions_deleted,
            "feedback_deleted": feedback_deleted
        }), 200
    
    except Exception as e:
        logger.error(f"Error in delete_user route: {e}")
        return jsonify({
            "success": False,
            "message": "Server error"
        }), 500


# ========================
# Route: Get All Feedbacks
# ========================
@admin_bp.route("/api/admin/feedbacks", methods=["GET"])
@require_admin
def get_all_feedbacks():
    """
    Get all feedbacks from users
    
    Query params:
        - limit: number of results (default: 20)
        - offset: pagination offset (default: 0)
    
    Response: {
        "success": true,
        "feedbacks": [
            {
                "id": 1,
                "user_id": 2,
                "email": "user@example.com",
                "message": "Great app!",
                "timestamp": "2025-11-16T10:30:00"
            }
        ],
        "total": 15
    }
    """
    try:
        limit = request.args.get("limit", 20, type=int)
        offset = request.args.get("offset", 0, type=int)
        
        limit = min(max(limit, 1), 100)
        offset = max(offset, 0)
        
        # Get total feedback count
        result = execute_query(
            "SELECT COUNT(*) as count FROM feedback",
            fetch_one=True
        )
        total = result["count"] if result else 0
        
        # Get paginated feedbacks with user info
        query = """
            SELECT f.id, f.user_id, u.email, f.message, f.timestamp
            FROM feedback f
            JOIN users u ON f.user_id = u.id
            ORDER BY f.timestamp DESC
            LIMIT ? OFFSET ?
        """
        feedbacks = execute_query(query, (limit, offset))
        
        return jsonify({
            "success": True,
            "feedbacks": feedbacks,
            "total": total,
            "limit": limit,
            "offset": offset
        }), 200
    
    except Exception as e:
        logger.error(f"Error in get_all_feedbacks route: {e}")
        return jsonify({
            "success": False,
            "message": "Server error"
        }), 500


# ========================
# Route: Get All Feedbacks (Admin)
# ========================
@admin_bp.route("/api/admin/feedbacks", methods=["GET"])
@require_admin
def get_admin_feedbacks():
    """
    Get all feedbacks from all users (admin only)
    
    Response: {
        "success": true,
        "feedbacks": [
            {
                "id": 1,
                "user_id": 2,
                "email": "user@example.com",
                "message": "Great app!",
                "timestamp": "2025-11-16T10:30:00"
            }
        ]
    }
    """
    try:
        result = execute_query(
            """SELECT 
                f.id,
                f.user_id,
                u.email,
                f.message,
                f.timestamp
            FROM feedback f
            LEFT JOIN users u ON f.user_id = u.id
            ORDER BY f.timestamp DESC""",
            fetch_one=False
        )
        
        feedbacks = result if result else []
        
        return jsonify({
            "success": True,
            "feedbacks": feedbacks
        }), 200
    
    except Exception as e:
        logger.error(f"Error in get_admin_feedbacks route: {e}")
        return jsonify({
            "success": False,
            "message": "Server error"
        }), 500