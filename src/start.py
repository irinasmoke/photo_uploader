#!/usr/bin/env python3
"""
Startup script for the Local Photo Uploader FastAPI application
Handles local environment configuration and application initialization
"""

import os
import sys
import logging
import platform
from pathlib import Path

def setup_logging():
    """Configure application logging with proper Unicode handling"""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_file = os.getenv('LOG_FILE', 'app.log')
    
    # Configure handlers with UTF-8 encoding
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    
    # For Windows, configure console handler with UTF-8 encoding
    if platform.system() == 'Windows':
        # Try to set console to UTF-8, fallback to safe logging
        try:
            import codecs
            stream_handler = logging.StreamHandler()
            stream_handler.stream = codecs.getwriter('utf-8')(sys.stderr.buffer)
        except (AttributeError, UnicodeError):
            # Fallback to standard handler for older Python or encoding issues
            stream_handler = logging.StreamHandler()
    else:
        stream_handler = logging.StreamHandler()
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[file_handler, stream_handler],
        force=True  # Override any existing configuration
    )
    
    logger = logging.getLogger(__name__)
    
    # Use platform-appropriate messages
    if platform.system() == 'Windows':
        logger.info(f"[STARTING] Photo Uploader application with log level: {log_level}")
    else:
        logger.info(f"🚀 Starting Photo Uploader application with log level: {log_level}")
    
    return logger

def validate_environment():
    """Validate required environment variables and setup"""
    # For local application, just ensure basic directories exist
    upload_dir = Path("uploads/photos")
    metadata_dir = Path("uploads/metadata")
    
    # Create directories if they don't exist
    upload_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger(__name__)
    logger.info("✅ Upload directories created/verified")
    
    return True

def main():
    """Main startup function"""
    logger = setup_logging()
    
    # Validate environment and setup directories
    validate_environment()
    
    # Set default values for application configuration
    os.environ.setdefault('APP_HOST', '0.0.0.0')
    os.environ.setdefault('APP_PORT', '8000')
    
    # Use platform-appropriate logging messages
    if platform.system() == 'Windows':
        logger.info("[OK] Local photo uploader ready")
        logger.info("[STORAGE] Using local file system storage")
    else:
        logger.info("✅ Local photo uploader ready")
        logger.info("� Using local file system storage")
    
    # Import and run the FastAPI application
    import uvicorn
    
    host = os.getenv('APP_HOST', '0.0.0.0')
    port = int(os.getenv('APP_PORT', '8000'))
    debug = os.getenv('APP_DEBUG', 'false').lower() == 'true'
    
    if platform.system() == 'Windows':
        logger.info(f"[SERVER] Starting server on http://{host}:{port}")
    else:
        logger.info(f"🌐 Starting server on http://{host}:{port}")
    
    # Use import string when reload is enabled, otherwise import the app object
    if debug:
        uvicorn.run(
            "main:app",  # Import string for reload mode
            host=host,
            port=port,
            reload=True,
            log_level=os.getenv('LOG_LEVEL', 'info').lower()
        )
    else:
        # Import app object for production mode
        from main import app
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=False,
            log_level=os.getenv('LOG_LEVEL', 'info').lower()
        )

if __name__ == "__main__":
    main()