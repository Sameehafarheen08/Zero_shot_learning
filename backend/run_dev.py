#!/usr/bin/env python
"""
Development server with auto-restart on file changes
Uses watchdog to monitor file changes and automatically restart
"""
import sys
import os
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

def start_server():
    """Start the Flask server"""
    cmd = [sys.executable, "run.py"]
    return subprocess.Popen(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))

def monitor_and_restart():
    """Monitor for file changes and restart server"""
    import logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logger = logging.getLogger(__name__)
    
    logger.info("="*70)
    logger.info("🚀 DEVELOPMENT SERVER WITH AUTO-RESTART")
    logger.info("="*70)
    logger.info("Monitoring files for changes...")
    logger.info("Press Ctrl+C to stop")
    logger.info("="*70)
    
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        process = None
        last_restart = time.time()
        
        class ChangeHandler(FileSystemEventHandler):
            def on_modified(self, event):
                nonlocal process, last_restart
                
                # Ignore cache files and uploads
                if any(x in event.src_path for x in ['.embeddings_cache', '__pycache__', 'uploads', '.pyc']):
                    return
                
                # Debounce (wait 2 seconds after change before restarting)
                if time.time() - last_restart < 2:
                    return
                
                if event.src_path.endswith(('.py', '.html', '.css', '.txt')):
                    logger.info(f"\n📝 File changed: {os.path.basename(event.src_path)}")
                    logger.info("🔄 Restarting server...")
                    
                    # Kill old process
                    if process and process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        time.sleep(1)
                    
                    # Start new process
                    process = start_server()
                    last_restart = time.time()
                    logger.info("✅ Server restarted\n")
        
        # Start initial server
        process = start_server()
        time.sleep(3)
        logger.info("✅ Server started on http://127.0.0.1:5000\n")
        
        # Start file watcher
        observer = Observer()
        observer.schedule(ChangeHandler(), path=backend_dir, recursive=True)
        observer.start()
        
        # Keep running
        while True:
            time.sleep(1)
            if process and process.poll() is not None:
                logger.warning("⚠️ Server crashed! Restarting...")
                process = start_server()
                last_restart = time.time()
                time.sleep(3)
    
    except ImportError:
        logger.warning("⚠️ watchdog not installed. Install with: pip install watchdog")
        logger.info("Running server without auto-restart...")
        process = start_server()
        process.wait()
    
    except KeyboardInterrupt:
        logger.info("\n⏹️ Shutting down...")
        if process and process.poll() is None:
            process.terminate()
            process.wait()
        logger.info("✅ Server stopped")
        sys.exit(0)

if __name__ == "__main__":
    monitor_and_restart()
