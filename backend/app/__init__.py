"""
Flask Application Factory
Initializes Flask app with blueprints, CORS, and error handling
"""

from flask import Flask, jsonify
from flask_cors import CORS
import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app(config=None):
    """
    Application factory function
    
    Args:
        config (dict): Optional configuration dictionary
    
    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__)
    
    # Default configuration
    app.config.update(
        DEBUG=True,
        JSON_SORT_KEYS=False,
        JSONIFY_PRETTYPRINT_REGULAR=False
    )
    
    # Update with provided config
    if config:
        app.config.update(config)
    
    # Enable CORS for all routes
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Type"]
        }
    })
    
    logger.info("CORS enabled for all API routes")
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register health check endpoint
    @app.route("/api/health", methods=["GET"])
    def health_check():
        """Health check endpoint"""
        return jsonify({
            "success": True,
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    
    # Warmup endpoint - preloads CLIP model and text embeddings
    @app.route("/api/warmup", methods=["GET"])
    def warmup():
        """Warmup endpoint to preload CLIP model and text embeddings at startup"""
        try:
            logger.info("Starting CLIP model warmup...")
            from app.clip_model import CLIPClassifier
            
            # Initialize CLIP classifier (loads model on first call)
            classifier = CLIPClassifier()
            logger.info("CLIP model loaded successfully")
            
            return jsonify({
                "success": True,
                "message": "CLIP model loaded successfully"
            }), 200
        except Exception as e:
            logger.error(f"Warmup error: {e}")
            return jsonify({
                "success": False,
                "message": f"Warmup failed: {str(e)}"
            }), 500
    
    # Root endpoint - serve login page first
    @app.route("/", methods=["GET"])
    def root():
        """Root endpoint - redirect to login page"""
        from flask import send_from_directory
        try:
            # Serve login.html from frontend folder first
            frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend")
            return send_from_directory(frontend_path, "login.html")
        except Exception as e:
            logger.warning(f"Cannot serve login.html: {e}")
            return jsonify({
                "name": "Zero-Shot Image Classifier API",
                "version": "1.0.0",
                "status": "running",
                "frontend": "Please open /login.html"
            }), 200
    
    # Serve frontend static files
    @app.route("/<path:filename>")
    def serve_frontend(filename):
        """Serve frontend files"""
        from flask import send_from_directory
        try:
            frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend")
            return send_from_directory(frontend_path, filename)
        except Exception as e:
            logger.debug(f"File not found: {filename}")
            return jsonify({"error": "File not found"}), 404
    
    logger.info("Flask app initialized successfully")
    return app


def register_blueprints(app):
    """
    Register all route blueprints
    
    Args:
        app (Flask): Flask application instance
    """
    import sys
    import os
    # Add backend directory to path so we can import routes
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    
    from routes.auth_routes import auth_bp
    from routes.prediction_routes_v2 import prediction_bp
    from routes.user_routes import user_bp
    from routes.admin_routes import admin_bp
    from routes.ask_routes import ask_bp
    from routes.ask_ai_new import ask_ai_bp
    from routes.detection_routes import detection_bp
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix="")
    logger.info("Registered auth blueprint")
    
    app.register_blueprint(prediction_bp, url_prefix="")
    logger.info("Registered prediction blueprint (v2 - redesigned)")
    
    app.register_blueprint(user_bp, url_prefix="")
    logger.info("Registered user blueprint")
    
    app.register_blueprint(admin_bp, url_prefix="")
    logger.info("Registered admin blueprint")
    
    app.register_blueprint(ask_bp, url_prefix="")
    logger.info("Registered ask-ai blueprint")
    
    app.register_blueprint(ask_ai_bp, url_prefix="")
    logger.info("Registered ask-ai-new blueprint (real AI responses)")
    
    app.register_blueprint(detection_bp, url_prefix="")
    logger.info("Registered detection blueprint (YOLO object detection)")


def register_error_handlers(app):
    """
    Register global error handlers
    
    Args:
        app (Flask): Flask application instance
    """
    
    @app.errorhandler(400)
    def bad_request(error):
        """400 Bad Request"""
        return jsonify({
            "success": False,
            "message": "Bad request",
            "error": str(error)
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        """401 Unauthorized"""
        return jsonify({
            "success": False,
            "message": "Unauthorized",
            "error": str(error)
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """403 Forbidden"""
        return jsonify({
            "success": False,
            "message": "Forbidden",
            "error": str(error)
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        """404 Not Found"""
        return jsonify({
            "success": False,
            "message": "Resource not found",
            "error": str(error)
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """500 Internal Server Error"""
        logger.error(f"Internal server error: {error}")
        return jsonify({
            "success": False,
            "message": "Internal server error",
            "error": str(error)
        }), 500
    
    logger.info("Error handlers registered")
