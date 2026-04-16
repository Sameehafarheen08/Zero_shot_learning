"""
Image Prediction/Classification Routes (REDESIGNED)
Uses single labels.txt file and simplified pipeline
"""

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from app.db import execute_query, execute_mutation
from app.utils import verify_jwt_token
import os
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

prediction_bp = Blueprint('prediction', __name__)

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
        if os.path.isfile(UPLOAD_FOLDER):
            os.remove(UPLOAD_FOLDER)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    except Exception as e:
        logger.warning(f"Could not create upload folder: {e}")


@prediction_bp.route('/api/predictions', methods=['POST'])
def upload_and_predict():
    """
    Upload image and classify using unified CLIP pipeline
    
    Returns top-3 predictions with confidence scores
    """
    try:
        # Get user ID
        user_id = request.form.get('user_id')
        if not user_id:
            return jsonify({
                "success": False,
                "message": "user_id is required"
            }), 400
        
        # Get file
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
        
        # Save file
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
        
        # Classify image - get top prediction only
        try:
            logger.info(f"Starting classification for: {filepath}")
            from app.clip_model import CLIPClassifier
            
            # Create classifier and get predictions
            try:
                classifier = CLIPClassifier("all")
                logger.info(f"Classifier created, labels count: {len(classifier.labels)}")
            except Exception as init_error:
                logger.error(f"Failed to create classifier: {init_error}")
                raise init_error
            
            try:
                predictions = classifier.get_top_k(filepath, k=1)
                logger.info(f"Predictions received: {predictions}")
            except Exception as pred_error:
                logger.error(f"Failed to get predictions: {pred_error}")
                raise pred_error
            
            # Get only top prediction
            top_label, top_conf = predictions[0]
            logger.info(f"✅ Top prediction: {top_label} ({top_conf*100:.2f}%)")
            
            # Store in database
            try:
                prediction_id = execute_mutation(
                    """INSERT INTO predictions 
                       (user_id, image_path, classification_result, confidence)
                       VALUES (?, ?, ?, ?)""",
                    (int(user_id), filepath, top_label, float(top_conf))
                )
                
                logger.info(f"Prediction stored: ID {prediction_id}")
                
                return jsonify({
                    "success": True,
                    "prediction_id": prediction_id,
                    "label": top_label,
                    "confidence": round(top_conf, 4),
                    "top_label": top_label,
                    "top_confidence": round(top_conf, 4),
                    "image_path": f"/static/uploads/{filename}",
                    "message": "Classification successful"
                }), 201
            
            except Exception as e:
                logger.error(f"Error storing prediction: {e}")
                try:
                    os.remove(filepath)
                except:
                    pass
                return jsonify({
                    "success": False,
                    "message": "Error storing prediction"
                }), 500
        
        except Exception as e:
            logger.error(f"Classification error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            try:
                os.remove(filepath)
            except:
                pass
            return jsonify({
                "success": False,
                "message": f"Classification error: {str(e)}"
            }), 500
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "message": "Unexpected server error"
        }), 500


@prediction_bp.route('/api/predictions/<int:prediction_id>', methods=['GET'])
def get_prediction(prediction_id):
    """Get a specific prediction"""
    try:
        result = execute_query(
            """SELECT id, user_id, image_path, predicted_labels, confidence_scores, created_at 
               FROM predictions WHERE id = ?""",
            (prediction_id,),
            fetch_one=True
        )
        
        if not result:
            return jsonify({
                "success": False,
                "message": "Prediction not found"
            }), 404
        
        return jsonify({
            "success": True,
            "prediction": {
                "id": result['id'],
                "user_id": result['user_id'],
                "image_path": result['image_path'],
                "predictions": result['predicted_labels'],
                "confidence_scores": result['confidence_scores'],
                "created_at": str(result['created_at'])
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error retrieving prediction: {e}")
        return jsonify({
            "success": False,
            "message": "Error retrieving prediction"
        }), 500


@prediction_bp.route('/api/user/<int:user_id>/predictions', methods=['GET'])
def get_user_predictions(user_id):
    """Get all predictions for a user"""
    try:
        results = execute_query(
            """SELECT id, predicted_labels, confidence_scores, image_path, created_at 
               FROM predictions WHERE user_id = ? ORDER BY created_at DESC LIMIT 50""",
            (user_id,),
            fetch_one=False
        )
        
        if not results:
            return jsonify({
                "success": True,
                "predictions": [],
                "total": 0
            }), 200
        
        predictions = [
            {
                "id": r['id'],
                "predictions": r['predicted_labels'],
                "confidence": r['confidence_scores'],
                "image_path": r['image_path'],
                "created_at": str(r['created_at'])
            }
            for r in results
        ]
        
        return jsonify({
            "success": True,
            "predictions": predictions,
            "total": len(predictions)
        }), 200
    
    except Exception as e:
        logger.error(f"Error retrieving user predictions: {e}")
        return jsonify({
            "success": False,
            "message": "Error retrieving predictions"
        }), 500


@prediction_bp.route('/api/compare', methods=['POST'])
def compare_images():
    """
    Compare two images using the SAME unified pipeline
    Returns predictions for both images side-by-side
    """
    try:
        user_id = request.form.get('user_id')
        
        if 'image1' not in request.files or 'image2' not in request.files:
            return jsonify({
                "success": False,
                "message": "Two images required"
            }), 400
        
        image1_file = request.files['image1']
        image2_file = request.files['image2']
        
        if not allowed_file(image1_file.filename) or not allowed_file(image2_file.filename):
            return jsonify({
                "success": False,
                "message": "Invalid file types"
            }), 400
        
        create_upload_folder()
        
        # Save both images
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        
        filename1 = f"compare_{user_id}_{timestamp}_{unique_id}_1.jpg"
        filepath1 = os.path.join(UPLOAD_FOLDER, filename1)
        image1_file.save(filepath1)
        
        filename2 = f"compare_{user_id}_{timestamp}_{unique_id}_2.jpg"
        filepath2 = os.path.join(UPLOAD_FOLDER, filename2)
        image2_file.save(filepath2)
        
        # Return both images WITHOUT predictions
        try:
            return jsonify({
                "success": True,
                "image1": {
                    "path": f"/static/uploads/{filename1}"
                },
                "image2": {
                    "path": f"/static/uploads/{filename2}"
                },
                "message": "Images uploaded successfully for comparison"
            }), 200
        
        except Exception as e:
            logger.error(f"Comparison error: {e}")
            return jsonify({
                "success": False,
                "message": f"Comparison failed: {str(e)}"
            }), 500
    
    except Exception as e:
        logger.error(f"Error in compare: {e}")
        return jsonify({
            "success": False,
            "message": "Comparison error"
        }), 500


@prediction_bp.route("/api/describe", methods=["POST"])
def describe_image():
    """
    Generate realistic descriptions using CLIP top-5 predictions
    Combines multiple predictions to create contextual sentences
    """
    try:
        logger.info("=== DESCRIBE REQUEST RECEIVED ===")
        
        user_id = request.form.get("user_id")
        logger.info(f"User ID: {user_id}")
        
        if not user_id:
            return jsonify({"success": False, "message": "Missing user_id"}), 400
        
        if "file" not in request.files:
            return jsonify({"success": False, "message": "No image provided"}), 400
        
        file = request.files["file"]
        if file.filename == "" or not file.content_type.startswith('image/'):
            return jsonify({"success": False, "message": "Invalid image file"}), 400
        
        # Save file
        filename = f"user_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.jpg"
        upload_dir = "backend/static/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        logger.info(f"File saved: {file_path}")
        
        # Load CLIP classifier
        try:
            from app.clip_model import CLIPClassifier
            classifier = CLIPClassifier()
        except Exception as e:
            logger.error(f"Failed to load CLIP: {e}", exc_info=True)
            return jsonify({"success": False, "message": "Classification model unavailable"}), 500
        
        # Get top 10 predictions for context
        try:
            predictions = classifier.get_top_k(file_path, k=10)
            logger.info(f"Top 10 Predictions: {predictions}")
        except Exception as e:
            logger.error(f"Prediction error: {e}", exc_info=True)
            return jsonify({"success": False, "message": "Could not analyze image"}), 500
        
        if not predictions:
            return jsonify({"success": False, "message": "Could not analyze image"}), 500
        
        # Extract top labels and confidence
        top_label, top_conf = predictions[0]
        top_conf_pct = round(top_conf * 100, 2)
        
        logger.info(f"Top prediction: {top_label} ({top_conf_pct}%)")
        
        # Smart description generator using multiple predictions
        def generate_realistic_description(predictions):
            """Generate description by analyzing top predictions"""
            
            labels = [label.lower() for label, conf in predictions[:5]]
            
            # Extract main subject and context
            main_subject = labels[0]
            
            # Check for context clues in top 5 predictions
            context_words = []
            for label in labels[1:]:
                if any(word in label for word in ['table', 'plate', 'bowl', 'kitchen', 'food', 'dish']):
                    context_words.append('on a table')
                    break
                elif any(word in label for word in ['grass', 'field', 'outdoor', 'nature', 'park']):
                    context_words.append('outdoors on grass')
                    break
                elif any(word in label for word in ['bench', 'chair', 'sofa', 'furniture']):
                    context_words.append('on furniture')
                    break
                elif any(word in label for word in ['room', 'indoor', 'inside', 'wall']):
                    context_words.append('indoors')
                    break
            
            # Build realistic sentence based on confidence
            if top_conf > 0.85:
                # Very high confidence - direct statement
                if context_words:
                    description = f"a {main_subject} {context_words[0]}"
                else:
                    # Check what type it is
                    if any(word in main_subject for word in ['dog', 'cat', 'bird', 'animal', 'person']):
                        description = f"a {main_subject} in focus"
                    elif any(word in main_subject for word in ['food', 'cake', 'bread', 'vegetable', 'fruit']):
                        description = f"a {main_subject} displayed"
                    elif any(word in main_subject for word in ['table', 'chair', 'bed', 'furniture']):
                        description = f"a {main_subject} in view"
                    elif any(word in main_subject for word in ['tree', 'flower', 'grass', 'plant']):
                        description = f"a {main_subject} in nature"
                    else:
                        description = f"a {main_subject}"
                        
            elif top_conf > 0.65:
                # High confidence
                if context_words:
                    description = f"what appears to be a {main_subject} {context_words[0]}"
                else:
                    description = f"a clear image of {main_subject}"
                    
            elif top_conf > 0.4:
                # Medium confidence - use context from predictions
                second_label = labels[1] if len(labels) > 1 else "item"
                
                if context_words:
                    description = f"possibly a {main_subject} or {second_label} {context_words[0]}"
                else:
                    description = f"could be a {main_subject} or {second_label}"
                    
            else:
                # Low confidence - list possibilities
                alt_labels = labels[1:4]
                alts = ", ".join(alt_labels[:2])
                if context_words:
                    description = f"might be a {main_subject} or {alts} {context_words[0]}"
                else:
                    description = f"image containing {main_subject} or {alts}"
            
            return description
        
        # Generate description
        caption = generate_realistic_description(predictions)
        logger.info(f"Generated description: {caption}")
        
        return jsonify({
            "success": True,
            "caption": caption,
            "label": top_label,
            "confidence": round(top_conf, 4),
            "confidence_percent": top_conf_pct,
            "message": "Description generated successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"DESCRIBE ERROR: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500




