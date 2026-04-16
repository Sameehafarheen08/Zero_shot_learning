"""
Flask Application Entry Point
Runs the Zero-Shot Image Classifier backend
"""

# Load environment variables FIRST before any other imports
import os
import sys
from dotenv import load_dotenv

# Load .env file from the backend directory (where run.py is located)
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)
from app import create_app
from app.db_unified import test_connection
import logging

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        # Test database connection
        logger.info("Testing database connection...")
        if test_connection():
            logger.info("✅ Database connection successful")
        else:
            logger.warning("⚠️ Database connection failed. Check your configuration.")
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}")
    
    # Create Flask app
    app = create_app()
    
    # Run development server
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = False
    
    logger.info("=" * 70)
    logger.info(f"🚀 Starting Flask app on port {port}")
    logger.info("✅ Server ready!")
    logger.info("=" * 70 + "\n")
    
    try:
        logger.info("Flask app is now running and accepting requests...")
        app.run(
            host="0.0.0.0",
            port=port,
            debug=debug,
            use_reloader=False,
            use_debugger=False,
            threaded=False
        )
    except KeyboardInterrupt:
        logger.info("Received SIGINT, shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"FATAL: Flask app crashed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
