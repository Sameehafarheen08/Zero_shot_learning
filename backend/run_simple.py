#!/usr/bin/env python3
"""
Zero-Shot Image Classifier - Flask Application Entry Point
Simplified version that doesn't require python-dotenv
"""

import os
import sys

# Load environment variables from .env file manually
def load_env(filename='.env'):
    """Load environment variables from .env file"""
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                # Parse key=value
                if '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
                    print(f"Loaded: {key.strip()}")

# Load environment variables
load_env()

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Now import Flask app
from app import create_app
from app.db import test_connection
import logging

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        # Test database connection
        logger.info("Testing database connection...")
        if test_connection():
            logger.info("✅ Database connection successful")
        else:
            logger.warning("⚠️ Database connection test returned False. Check configuration.")
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}")
    
    # Create Flask app
    app = create_app()
    
    # Run development server
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
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
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("\n✅ Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error running Flask app: {e}")
        sys.exit(1)
