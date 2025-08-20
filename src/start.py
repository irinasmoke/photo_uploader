#!/usr/bin/env python3
"""
Startup script for the Photo Uploader FastAPI application
Handles environment configuration and application initialization
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
    """Validate required environment variables"""
    required_vars = ['AZURE_STORAGE_ACCOUNT_NAME']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"[ERROR] Missing required environment variables: {', '.join(missing_vars)}")
        print("[INFO] Please set the required environment variables or run 'azd up' to deploy infrastructure first.")
        sys.exit(1)

def main():
    """Main startup function"""
    logger = setup_logging()
    
    # Validate environment
    validate_environment()
    
    # Set default values for optional environment variables
    os.environ.setdefault('AZURE_PHOTO_CONTAINER_NAME', 'photos')
    os.environ.setdefault('APP_HOST', '0.0.0.0')
    os.environ.setdefault('APP_PORT', '8000')
    
    # Use platform-appropriate logging messages
    if platform.system() == 'Windows':
        logger.info("[OK] Environment validation passed")
        logger.info(f"[STORAGE] Storage Account: {os.getenv('AZURE_STORAGE_ACCOUNT_NAME')}")
        logger.info(f"[CONTAINER] Container: {os.getenv('AZURE_PHOTO_CONTAINER_NAME')}")
    else:
        logger.info("✅ Environment validation passed")
        logger.info(f"📦 Storage Account: {os.getenv('AZURE_STORAGE_ACCOUNT_NAME')}")
        logger.info(f"🗂️ Container: {os.getenv('AZURE_PHOTO_CONTAINER_NAME')}")
    
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