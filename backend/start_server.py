#!/usr/bin/env python
"""
Simple server starter with better error handling
"""
import sys
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    logger.info("="*60)
    logger.info("STARTING ZERO-SHOT IMAGE CLASSIFIER")
    logger.info("="*60)
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    logger.info("[1/4] Creating Flask app...")
    from app import create_app
    app = create_app()
    logger.info("✅ Flask app created")
    
    logger.info("[2/4] Pre-initializing CLIP model...")
    from app.clip_model_v2 import initialize_at_startup
    if initialize_at_startup():
        logger.info("✅ CLIP model initialized")
    else:
        logger.warning("⚠️ CLIP initialization returned False (non-critical)")
    
    logger.info("[3/4] Starting Flask server...")
    port = int(os.getenv("FLASK_PORT", 5000))
    
    logger.info("="*60)
    logger.info(f"✅ SERVER READY AT http://127.0.0.1:{port}")
    logger.info("="*60)
    
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False,
        use_debugger=False,
        threaded=True
    )
    
except KeyboardInterrupt:
    logger.info("⏹️ Server stopped by user")
    sys.exit(0)
except Exception as e:
    logger.error(f"❌ FATAL ERROR: {e}", exc_info=True)
    sys.exit(1)
