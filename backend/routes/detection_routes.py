"""
Object Detection Routes
Handles image upload and object detection requests
"""

import logging
import os
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from pathlib import Path
from datetime import datetime
from app.db import get_db

logger = logging.getLogger(__name__)

# Create blueprint
detection_bp = Blueprint('detection', __name__)

# ...existing code...

# Add live detection endpoint after blueprint is defined
@detection_bp.route('/api/detection/live', methods=['POST'])
def detect_live():
    """
    Real-time object detection from webcam frame using YOLOv8.
    Returns bounding boxes and labels for each detected object.
    Uses global detector instance for efficiency with lazy model loading.
    
    Request: multipart/form-data with 'frame' (JPEG image)
    Response: JSON with success, objects list with bbox, class_name, confidence
    """
    try:
        if 'frame' not in request.files:
            return jsonify({'success': False, 'error': 'No frame provided'}), 400
        
        frame_file = request.files['frame']
        if not frame_file:
            return jsonify({'success': False, 'error': 'Empty frame'}), 400
        
        # Import required modules
        from PIL import Image
        import io
        from app.object_detector import get_detector
        
        # Read image from uploaded frame
        img = Image.open(io.BytesIO(frame_file.read())).convert('RGB')
        
        # Ensure image is not too large
        if img.size[0] > 1920 or img.size[1] > 1080:
            img.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
        
        # Save temporarily for detection
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            img.save(tmp.name, 'JPEG')
            temp_path = tmp.name
        
        try:
            # Get global detector instance (loads model only once on first use)
            detector = get_detector('yolov8n.pt')
            
            # Run detection with lower confidence threshold for real-time
            result = detector.detect_objects(temp_path, confidence_threshold=0.25)
            
            # Clean up temp file
            import os
            os.unlink(temp_path)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'objects': result['objects'],
                    'total': result['total_objects']
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Detection failed'),
                    'objects': [],
                    'total': 0
                }), 500
        
        except Exception as pred_err:
            logger.error(f"Detection error: {pred_err}", exc_info=True)
            # Clean up temp file
            try:
                import os
                os.unlink(temp_path)
            except:
                pass
            return jsonify({
                'success': False,
                'error': f'Detection failed: {str(pred_err)}',
                'objects': [],
                'total': 0
            }), 500
    
    except Exception as e:
        logger.error(f"Live detection error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'objects': [],
            'total': 0
        }), 500


# Configuration
UPLOAD_FOLDER = Path(__file__).parent.parent / 'static' / 'detection_uploads'
OUTPUT_FOLDER = Path(__file__).parent.parent / 'static' / 'detection_results'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'bmp', 'gif'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Create folders if they don't exist
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_filename(user_id, original_filename):
    """Generate unique filename"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = original_filename.rsplit('.', 1)[1].lower()
    return f"user_{user_id}_{timestamp}.{ext}"


@detection_bp.route('/api/detection/detect', methods=['POST'])
def detect_objects():
    """
    Detect objects in uploaded image using YOLOv5
    
    Request:
        - file: Image file (multipart/form-data)
        - user_id: User ID (optional, for logging)
        - confidence: Confidence threshold 0-1 (optional, default 0.5)
    
    Response:
        {
            'success': bool,
            'total_objects': int,
            'objects': [...],
            'result_url': str,
            'message': str
        }
    """
    try:
        logger.info("🎯 Object detection request received")
        
        # Validate file
        if 'file' not in request.files:
            logger.error("No file provided")
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Get parameters
        user_id = request.form.get('user_id', 'anonymous')
        confidence = float(request.form.get('confidence', 0.25))
        confidence = max(0.0, min(1.0, confidence))  # Clamp to 0-1
        
        logger.info(f"User: {user_id}, Confidence: {confidence}")
        
        # Save uploaded file
        filename = generate_filename(user_id, file.filename)
        filepath = UPLOAD_FOLDER / filename
        file.save(str(filepath))
        logger.info(f"✅ File saved: {filepath}")
        
        # Load YOLOv8 for object detection
        try:
            logger.info("Loading YOLOv8n model for detection...")
            from ultralytics import YOLO
            from PIL import Image, ImageDraw, ImageFont
            
            # Load lightweight YOLOv8 nano model directly (more reliable than torch.hub)
            model = YOLO('yolov8n.pt')  # Auto-downloads on first use
            logger.info(f"✅ YOLOv8n model loaded")
            
            # Run detection
            logger.info("Running object detection...")
            results = model.predict(str(filepath), conf=confidence, verbose=False)
            
            # Parse results from ultralytics
            detected_objects = []
            
            if results and len(results) > 0:
                result = results[0]  # Get first (and only) result
                boxes = result.boxes  # Get all boxes
                
                logger.info(f"Detections found: {len(boxes)}")
                
                for box in boxes:
                    # Extract coordinates and confidence
                    x1, y1, x2, y2 = box.xyxy[0].tolist()  # xyxy format
                    conf_score = float(box.conf[0])
                    class_id = int(box.cls[0])
                    class_name = result.names[class_id]
                    
                    if conf_score >= confidence:
                        detected_objects.append({
                            'class_name': class_name,
                            'confidence': conf_score,
                            'bbox': {
                                'x1': int(x1),
                                'y1': int(y1),
                                'x2': int(x2),
                                'y2': int(y2)
                            }
                        })
            else:
                logger.info("No objects detected")
            
            logger.info(f"✅ Detected {len(detected_objects)} objects above threshold")
            
            # Draw bounding boxes on image
            logger.info("Drawing bounding boxes...")
            image = Image.open(str(filepath)).convert('RGB')
            draw = ImageDraw.Draw(image)
            
            colors = [
                (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
                (255, 0, 255), (0, 255, 255), (128, 0, 0), (0, 128, 0),
                (0, 0, 128), (128, 128, 0), (128, 0, 128), (0, 128, 128)
            ]
            
            for idx, obj in enumerate(detected_objects):
                bbox = obj['bbox']
                x1, y1, x2, y2 = bbox['x1'], bbox['y1'], bbox['x2'], bbox['y2']
                color = colors[idx % len(colors)]
                
                # Draw rectangle
                draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=2)
                
                # Draw label
                label = f"{obj['class_name']} {obj['confidence']:.2f}"
                try:
                    font = ImageFont.load_default()
                except:
                    font = None
                
                # Get text size
                text_bbox = draw.textbbox((x1, y1 - 25), label, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                # Draw label background
                draw.rectangle(
                    [(x1, y1 - text_height - 4), (x1 + text_width + 4, y1)],
                    fill=color
                )
                
                # Draw label text
                draw.text((x1 + 2, y1 - text_height - 2), label, fill=(255, 255, 255), font=font)
            
            # Save result image
            result_filename = f"detected_{filename}"
            result_path = OUTPUT_FOLDER / result_filename
            image.save(str(result_path), quality=95)
            logger.info(f"✅ Result image saved: {result_path}")
            
            return jsonify({
                'success': True,
                'total_objects': len(detected_objects),
                'objects': detected_objects,
                'result_url': f'/static/detection_results/{result_filename}',
                'message': f'Detected {len(detected_objects)} object(s)'
            }), 200
        
        except Exception as model_error:
            logger.error(f"YOLOv5 detection error: {model_error}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'Detection failed: {str(model_error)}'
            }), 500
    
    except Exception as e:
        logger.error(f"Error in detect_objects: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@detection_bp.route('/history/<user_id>', methods=['GET'])
def get_detection_history(user_id):
    """Get detection history for user"""
    try:
        limit = request.args.get('limit', 10, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT * FROM detections 
            WHERE user_id = %s 
            ORDER BY timestamp DESC 
            LIMIT %s OFFSET %s
        """, (user_id, limit, offset))
        
        detections = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'detections': detections,
            'count': len(detections)
        }), 200
    
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
