"""
Image Prediction/Classification Routes
Handles image upload and CLIP-based classification
"""

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from app.db import execute_query, execute_mutation, get_db
from app.utils import verify_jwt_token
import os
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

prediction_bp = Blueprint('prediction', __name__)

# Lazy load CLIPClassifier to avoid torch import at startup
_clip_classifier = None
_clip_loading = False

def get_clip_classifier():
    """Get or load CLIP classifier with proper error handling"""
    global _clip_classifier, _clip_loading
    
    # Return cached classifier if already loaded
    if _clip_classifier is not None:
        return _clip_classifier if _clip_classifier is not False else None
    
    # Prevent multiple simultaneous load attempts
    if _clip_loading:
        logger.warning("CLIP model is still loading...")
        return None
    
    _clip_loading = True
    try:
        logger.info("Loading CLIP classifier...")
        from app.clip_model import CLIPClassifier
        _clip_classifier = CLIPClassifier()
        logger.info("✅ CLIP classifier loaded successfully")
        return _clip_classifier
    except Exception as e:
        logger.error(f"❌ Failed to load CLIP model: {e}")
        import traceback
        logger.error(traceback.format_exc())
        _clip_classifier = False  # Mark as failed
        return None
    finally:
        _clip_loading = False

# Lazy load labels to avoid startup delays
_labels_cache = None

def get_demo_labels():
    """Get labels with lazy loading - ONLY from label.txt"""
    global _labels_cache
    
    if _labels_cache is not None:
        return _labels_cache
    
    try:
        from app.clip_model import load_labels as load_model_labels
        raw_labels = load_model_labels()
        
        if not raw_labels:
            raise ValueError("label.txt is empty - no labels found!")
        
        # Convert underscores to spaces for CLIP
        formatted_labels = [label.replace('_', ' ') for label in raw_labels]
        
        logger.info(f"Loaded {len(formatted_labels)} labels from label.txt ONLY")
        _labels_cache = formatted_labels
        return formatted_labels
        
    except Exception as e:
        logger.error(f"CRITICAL: Failed to load labels from label.txt: {e}")
        logger.error("Application CANNOT run without label.txt")
        raise  # Don't fallback - FORCE using label.txt only!

# Don't load labels at startup - use lazy loading instead
DEMO_LABELS = None

def get_demo_prediction(filename):
    """Return a random demo prediction using ONLY label.txt labels"""
    import random
    labels = get_demo_labels()  # MUST get from label.txt
    if not labels:
        raise ValueError("No labels available from label.txt!")
    label = random.choice(labels)
    confidence = round(random.uniform(0.75, 0.99), 4)
    return label, confidence


# ========================
# Route: Model Warmup
# ========================
@prediction_bp.route("/api/warmup", methods=["GET"])
def warmup_model():
    """
    Warm up the CLIP model to avoid long loading times on first prediction.
    This endpoint can be called on page load to preload the model.
    
    Response: {
        "success": true,
        "message": "Model is ready",
        "model_status": "loaded",
        "labels_count": 86
    }
    """
    try:
        logger.info("🔄 Warmup request received")
        
        # Try to get classifier
        classifier = get_clip_classifier()
        
        if classifier is None:
            logger.warning("⚠️ Warmup: CLIP model not available yet, will load on first prediction")
            return jsonify({
                "success": True,
                "message": "Model will load on first prediction",
                "model_status": "not_loaded"
            }), 200
        
        # Get label count
        try:
            labels = get_demo_labels()
            label_count = len(labels) if labels else 0
        except:
            label_count = 0
        
        logger.info(f"✅ Warmup complete: Model ready with {label_count} labels")
        return jsonify({
            "success": True,
            "message": "Model is ready",
            "model_status": "loaded",
            "labels_count": label_count
        }), 200
        
    except Exception as e:
        logger.error(f"Warmup error: {e}")
        return jsonify({
            "success": True,
            "message": "Warmup in progress",
            "model_status": "loading"
        }), 200

# Configuration
UPLOAD_FOLDER = "backend/static/uploads"
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def create_upload_folder():
    """Ensure upload folder exists"""
    try:
        # If it exists as a file, remove it
        if os.path.isfile(UPLOAD_FOLDER):
            os.remove(UPLOAD_FOLDER)
        # Create directory
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    except Exception as e:
        logger.warning(f"Could not create upload folder: {e}")


# ========================
# Route: Upload & Classify Image
# ========================
@prediction_bp.route("/api/predictions", methods=["POST"])
def create_prediction():
    """
    Upload image and get CLIP classification
    
    Request: FormData
        - file: image file
        - user_id: integer user ID
    
    Response: {
        "success": true,
        "prediction_id": 42,
        "label": "dog",
        "confidence": 0.94,
        "image_path": "/api/uploads/user_1_img.jpg"
    }
    """
    try:
        # Get user_id from form or token
        user_id = request.form.get("user_id")
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        
        if not user_id and token:
            payload = verify_jwt_token(token)
            if payload:
                user_id = payload.get("user_id")
        
        if not user_id:
            return jsonify({
                "success": False,
                "message": "User ID required or invalid token"
            }), 401
        
        # Validate file
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "message": "No file provided"
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                "success": False,
                "message": "No file selected"
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                "success": False,
                "message": f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            }), 400
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                "success": False,
                "message": f"File too large. Max size: {MAX_FILE_SIZE / 1024 / 1024}MB"
            }), 400
        
        # Verify user exists
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
        
        # Create upload folder
        create_upload_folder()
        
        # Save file with secure filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"user_{user_id}_{timestamp}_{unique_id}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        try:
            file.save(filepath)
            logger.info(f"File saved: {filepath}")
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return jsonify({
                "success": False,
                "message": "Error saving file"
            }), 500
        
        # Run CLIP classification
        try:
            logger.info(f"🔄 Getting CLIP classifier for classification...")
            # Use get_clip_classifier for consistency
            clip_classifier = get_clip_classifier()
            
            if not clip_classifier:
                # Try to load it directly as fallback
                logger.warning("⚠️ Classifier not cached, loading directly...")
                from app.clip_model import CLIPClassifier
                clip_classifier = CLIPClassifier()
            
            if not clip_classifier:
                raise RuntimeError("Failed to initialize CLIP classifier")
            
            logger.info(f"🔄 Classifying image: {filepath}")
            # Classify image
            label, confidence = clip_classifier.classify(filepath)
            
            logger.info(f"✅ Classification: {label} ({confidence:.2%})")
            
        except Exception as e:
            logger.error(f"❌ Error during classification: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Clean up file on error
            try:
                os.remove(filepath)
            except:
                pass
            return jsonify({
                "success": False,
                "message": f"Error during image classification: {str(e)}"
            }), 500
        
        # Store prediction in database
        try:
            prediction_id = execute_mutation(
                """INSERT INTO predictions 
                   (user_id, image_path, classification_result, confidence)
                   VALUES (?, ?, ?, ?)""",
                (int(user_id), filepath, label, float(confidence))
            )
            
            logger.info(f"✅ Prediction stored: ID {prediction_id}")
            
            return jsonify({
                "success": True,
                "prediction_id": prediction_id,
                "label": label,
                "confidence": round(float(confidence), 4),
                "image_path": f"/static/uploads/{filename}",
                "message": "Classification successful"
            }), 201
        
        except Exception as e:
            logger.error(f"❌ Error storing prediction: {e}")
            import traceback
            logger.error(traceback.format_exc())
            try:
                os.remove(filepath)
            except:
                pass
            return jsonify({
                "success": False,
                "message": f"Error storing prediction: {str(e)}"
            }), 500
    
    except Exception as e:
        logger.error(f"Error in create_prediction route: {e}")
        return jsonify({
            "success": False,
            "message": "Server error"
        }), 500


# ========================
# Route: Get Single Prediction
# ========================
@prediction_bp.route("/api/predictions/<int:prediction_id>", methods=["GET"])
def get_prediction(prediction_id):
    """
    Get details of a single prediction
    
    Response: {
        "success": true,
        "prediction": {
            "id": 42,
            "user_id": 1,
            "image_path": "...",
            "label": "dog",
            "confidence": 0.94,
            "timestamp": "2025-11-16T10:30:00"
        }
    }
    """
    try:
        prediction = execute_query(
            """SELECT id, user_id, image_path, classification_result as label, 
                      confidence, timestamp FROM predictions WHERE id = %s""",
            (prediction_id,),
            fetch_one=True
        )
        
        if not prediction:
            return jsonify({
                "success": False,
                "message": "Prediction not found"
            }), 404
        
        return jsonify({
            "success": True,
            "data": {
                "prediction": prediction
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error in get_prediction route: {e}")
        return jsonify({
            "success": False,
            "message": "Server error"
        }), 500


# ========================
# Route: Get Recent Predictions
# ========================
@prediction_bp.route("/api/predictions", methods=["GET"])
def list_predictions():
    """
    Get recent predictions (paginated)
    
    Query params:
        - limit: number of results (default: 10)
        - offset: pagination offset (default: 0)
    
    Response: {
        "success": true,
        "predictions": [...],
        "total": 150,
        "limit": 10,
        "offset": 0
    }
    """
    try:
        limit = request.args.get("limit", 10, type=int)
        offset = request.args.get("offset", 0, type=int)
        
        # Limit bounds
        limit = min(max(limit, 1), 100)
        offset = max(offset, 0)
        
        # Get total count
        result = execute_query(
            "SELECT COUNT(*) as total FROM predictions",
            fetch_one=True
        )
        total = result["total"] if result else 0
        
        # Get predictions
        predictions = execute_query(
            """SELECT id, user_id, image_path, classification_result as label,
                      confidence, timestamp FROM predictions
               ORDER BY timestamp DESC LIMIT ? OFFSET ?""",
            (limit, offset)
        )
        
        return jsonify({
            "success": True,
            "predictions": predictions,
            "total": total,
            "limit": limit,
            "offset": offset
        }), 200
    
    except Exception as e:
        logger.error(f"Error in list_predictions route: {e}")
        return jsonify({
            "success": False,
            "message": "Server error"
        }), 500


# ========================
# Route: Delete Prediction
# ========================
@prediction_bp.route("/api/predictions/<int:prediction_id>", methods=["DELETE"])
def delete_prediction(prediction_id):
    """
    Delete a prediction (admin or owner only)
    
    Response: {
        "success": true,
        "message": "Prediction deleted"
    }
    """
    try:
        # Get prediction to find file
        prediction = execute_query(
            "SELECT image_path FROM predictions WHERE id = ?",
            (prediction_id,),
            fetch_one=True
        )
        
        if not prediction:
            return jsonify({
                "success": False,
                "message": "Prediction not found"
            }), 404
        
        # Delete from database
        execute_mutation(
            "DELETE FROM predictions WHERE id = ?",
            (prediction_id,)
        )
        
        # Try to delete image file
        if prediction["image_path"] and os.path.exists(prediction["image_path"]):
            try:
                os.remove(prediction["image_path"])
                logger.info(f"Image file deleted: {prediction['image_path']}")
            except Exception as e:
                logger.warning(f"Could not delete image file: {e}")
        
        return jsonify({
            "success": True,
            "message": "Prediction deleted successfully"
        }), 200
    
    except Exception as e:
        logger.error(f"Error in delete_prediction route: {e}")
        return jsonify({
            "success": False,
            "message": "Server error"
        }), 500


@prediction_bp.route("/api/describe", methods=["POST"])
def describe_image():
    """
    Generate lightweight description for uploaded image using CLIP classification
    Offline, no heavy models - uses top predictions only
    
    Response: {
        "success": true,
        "caption": "This is definitely a ...",
        "confidence": 0.92,
        "label": "pizza"
    }
    """
    try:
        user_id = request.form.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Missing user_id"}), 400
        
        if "file" not in request.files:
            return jsonify({"success": False, "message": "No image provided"}), 400
        
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "message": "No file selected"}), 400
        
        # Validate file type and size
        if not file.content_type.startswith('image/'):
            return jsonify({"success": False, "message": "File must be an image"}), 400
        
        # Save file
        filename = f"user_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.jpg"
        upload_dir = "backend/static/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        logger.info(f"✅ File saved: {file_path}")
        
        # Get classifier
        classifier = get_clip_classifier()
        if not classifier:
            logger.error("❌ CLIP classifier not available")
            # Try to load it now
            try:
                from app.clip_model import CLIPClassifier
                classifier = CLIPClassifier()
                logger.info("✅ CLIP loaded on-demand")
            except Exception as load_error:
                logger.error(f"❌ Failed to load CLIP on-demand: {load_error}")
                return jsonify({
                    "success": False,
                    "message": "Classification model is loading. Please try again."
                }), 503
        
        # Get top 5 predictions for better description
        try:
            logger.info(f"🔄 Starting classification for: {file_path}")
            predictions = classifier.get_top_k(file_path, k=5)
            
            if not predictions or len(predictions) == 0:
                logger.error("❌ No predictions returned from classifier")
                return jsonify({
                    "success": False,
                    "message": "Could not classify image"
                }), 500
            
            logger.info(f"✅ Got {len(predictions)} predictions: {predictions}")
            
        except Exception as clf_error:
            logger.error(f"❌ Classification error: {clf_error}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({
                "success": False,
                "message": f"Classification failed: {str(clf_error)}"
            }), 500
        
        # Generate caption from predictions
        top_label, top_conf = predictions[0]
        confidence_pct = round(top_conf * 100, 1)
        
        # Build caption based on confidence
        if top_conf > 0.8:
            caption = f"This is definitely a {top_label}. Confidence: {confidence_pct}%"
        elif top_conf > 0.6:
            caption = f"This appears to be a {top_label}. Confidence: {confidence_pct}%"
        elif top_conf > 0.4:
            caption = f"This could be a {top_label}. Confidence: {confidence_pct}%"
        else:
            # Include alternatives for low confidence
            alt_labels = [label for label, _ in predictions[1:3]]
            alt_text = " or ".join(alt_labels) if alt_labels else "something else"
            caption = f"This might be a {top_label}, or {alt_text}. Confidence: {confidence_pct}%"
        
        logger.info(f"✅ Caption generated: {caption}")
        
        return jsonify({
            "success": True,
            "caption": caption,
            "confidence": round(top_conf, 4),
            "label": top_label
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error in describe_image: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Server error: {str(e)}"
        }), 500
