"""
Object Detection Module using YOLOv8
Detects objects in images and returns bounding boxes with labels
Lazy-loads imports to avoid torch initialization delays during Flask startup
"""

import logging
import cv2
import numpy as np
from PIL import Image
from pathlib import Path

logger = logging.getLogger(__name__)


class ObjectDetector:
    """YOLOv8 Object Detection wrapper with lazy imports"""
    
    def __init__(self, model_name="yolov8n.pt"):
        """
        Initialize YOLO model (lazy-loaded on first use)
        
        Args:
            model_name: Model to use (yolov8n, yolov8s, yolov8m, yolov8l, yolov8x)
                       n=nano (fastest), x=xlarge (most accurate)
        """
        self.model_name = model_name
        self.model = None
        self.device = None
        self._initialized = False
        logger.info(f"ObjectDetector created (lazy-loading '{model_name}' on first use)")
    
    def _init_model(self):
        """Initialize YOLO model on first use"""
        if self._initialized:
            return
        
        try:
            import torch
            from ultralytics import YOLO
            
            logger.info(f"Loading YOLO model '{self.model_name}'...")
            
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {self.device}")
            
            self.model = YOLO(self.model_name)
            self.model.to(self.device)
            
            self._initialized = True
            logger.info(f"✅ YOLO model '{self.model_name}' loaded on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}", exc_info=True)
            raise
    
    def detect_objects(self, image_path, confidence_threshold=0.25):
        """
        Detect objects in image and return bounding boxes
        
        Args:
            image_path: Path to image file
            confidence_threshold: Minimum confidence score (0-1), default 0.25 for better detection
        
        Returns:
            dict with detection results
        """
        try:
            # Initialize model on first use
            self._init_model()
            
            logger.info(f"Detecting objects in: {image_path}")
            
            # Run inference
            results = self.model(image_path, conf=confidence_threshold, verbose=False)
            
            # Parse results
            objects = []
            if results and len(results) > 0:
                result = results[0]
                
                # Get image dimensions
                img_height = result.orig_shape[0]
                img_width = result.orig_shape[1]
                
                # Extract bounding boxes
                if result.boxes is not None and len(result.boxes) > 0:
                    for box in result.boxes:
                        # Get coordinates - ensure Python int, not numpy int64
                        coords = box.xyxy[0].cpu().numpy()
                        x1 = int(coords[0])
                        y1 = int(coords[1])
                        x2 = int(coords[2])
                        y2 = int(coords[3])
                        
                        # Get class and confidence
                        class_idx = int(box.cls[0].cpu().numpy())
                        class_name = self.model.names[class_idx]
                        confidence = float(box.conf[0].cpu().numpy())
                        
                        # Calculate center
                        center_x = int((x1 + x2) // 2)
                        center_y = int((y1 + y2) // 2)
                        
                        objects.append({
                            'class_name': str(class_name),
                            'confidence': float(round(confidence, 4)),
                            'bbox': {
                                'x1': x1,
                                'y1': y1,
                                'x2': x2,
                                'y2': y2
                            },
                            'center': {
                                'x': center_x,
                                'y': center_y
                            }
                        })
                
                logger.info(f"Detected {len(objects)} objects")
                
                return {
                    'success': True,
                    'image_path': str(image_path),
                    'objects': objects,
                    'total_objects': len(objects),
                    'image_width': img_width,
                    'image_height': img_height
                }
        
        except Exception as e:
            logger.error(f"Detection error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'objects': [],
                'total_objects': 0
            }
    
    def detect_and_visualize(self, image_path, output_path, confidence_threshold=0.25):
        """
        Detect objects and draw bounding boxes with labels
        
        Args:
            image_path: Path to input image
            output_path: Path to save visualization
            confidence_threshold: Minimum confidence score (0-1), default 0.25 for better detection
        
        Returns:
            dict with detection results and visualization path
        """
        try:
            # Initialize model on first use
            self._init_model()
            
            logger.info(f"Creating visualization: {output_path}")
            
            # Read image
            image = cv2.imread(str(image_path))
            if image is None:
                raise ValueError(f"Cannot read image: {image_path}")
            
            # Run detection
            results = self.model(image_path, conf=confidence_threshold, verbose=False)
            
            objects = []
            img_height, img_width = image.shape[:2]
            
            if results and len(results) > 0:
                result = results[0]
                
                # Draw boxes on image
                if result.boxes is not None and len(result.boxes) > 0:
                    for box in result.boxes:
                        # Get coordinates - ensure Python int, not numpy int64
                        coords = box.xyxy[0].cpu().numpy()
                        x1 = int(coords[0])
                        y1 = int(coords[1])
                        x2 = int(coords[2])
                        y2 = int(coords[3])
                        
                        # Get class and confidence
                        class_idx = int(box.cls[0].cpu().numpy())
                        class_name = self.model.names[class_idx]
                        confidence = float(box.conf[0].cpu().numpy())
                        
                        # Store object info
                        objects.append({
                            'class_name': str(class_name),
                            'confidence': float(round(confidence, 4)),
                            'bbox': {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2},
                            'center': {'x': int((x1 + x2) // 2), 'y': int((y1 + y2) // 2)}
                        })
                        
                        # Draw rectangle (green)
                        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        
                        # Draw label above box
                        label = f"{class_name} ({confidence:.2f})"
                        font = cv2.FONT_HERSHEY_SIMPLEX
                        font_scale = 0.5
                        thickness = 1
                        
                        # Get text size for background
                        text_size = cv2.getTextSize(label, font, font_scale, thickness)[0]
                        
                        # Draw text background
                        cv2.rectangle(image,
                                    (x1, y1 - text_size[1] - 4),
                                    (x1 + text_size[0] + 4, y1),
                                    (0, 255, 0), -1)
                        
                        # Draw text
                        cv2.putText(image, label,
                                  (x1 + 2, y1 - 2),
                                  font, font_scale, (0, 0, 0), thickness)
            
            # Save visualization
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(output_path), image)
            
            logger.info(f"Visualization saved: {output_path}")
            
            return {
                'success': True,
                'image_path': str(image_path),
                'result_path': str(output_path),
                'objects': objects,
                'total_objects': len(objects),
                'image_width': img_width,
                'image_height': img_height
            }
        
        except Exception as e:
            logger.error(f"Visualization error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'image_path': str(image_path)
            }


# Global detector instance
_detector_instance = None


def get_detector(model_name="yolov8n.pt"):
    """
    Get or create global detector instance (singleton)
    Lazy-loads YOLO model on first detection request
    
    Args:
        model_name: YOLO model to use
    
    Returns:
        ObjectDetector: Global detector instance
    """
    global _detector_instance
    
    if _detector_instance is None:
        logger.info("Creating global ObjectDetector instance")
        _detector_instance = ObjectDetector(model_name)
    
    return _detector_instance
