"""
Local Photo Uploader
A FastAPI application for uploading and managing photos locally
"""

import os
import uuid
import logging
import json
from typing import List, Optional
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import aiofiles
from PIL import Image

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
class Config:
    """Application configuration for local storage"""
    
    def __init__(self):
        self.upload_dir = Path("uploads/photos")
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # File upload limits
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
        self.allowed_mime_types = {
            'image/jpeg', 'image/png', 'image/gif', 'image/webp', 
            'image/bmp', 'image/tiff'
        }

config = Config()

# Initialize FastAPI app
app = FastAPI(
    title="🖼️ Local Photo Uploader",
    description="A FastAPI application for uploading and managing photos locally",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class LocalPhotoUploader:
    """Local photo uploader using file system storage"""
    
    def __init__(self):
        self.config = config
        
    def _validate_file(self, file: UploadFile) -> None:
        """Validate uploaded file"""
        # Check file extension
        file_extension = Path(file.filename or "").suffix.lower()
        if file_extension not in self.config.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{file_extension}' not allowed. "
                       f"Allowed types: {', '.join(self.config.allowed_extensions)}"
            )
        
        # Check MIME type
        if file.content_type not in self.config.allowed_mime_types:
            raise HTTPException(
                status_code=400,
                detail=f"MIME type '{file.content_type}' not allowed"
            )
    
    def _generate_filename(self, original_filename: str) -> str:
        """Generate a unique filename with timestamp and UUID"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d")
        file_extension = Path(original_filename).suffix.lower()
        unique_id = str(uuid.uuid4())[:8]
        
        # Clean filename
        clean_name = "".join(c for c in Path(original_filename).stem if c.isalnum() or c in ('-', '_'))
        clean_name = clean_name[:50]  # Limit length
        
        return f"{timestamp}_{clean_name}_{unique_id}{file_extension}"
    
    def _get_file_path(self, filename: str) -> Path:
        """Get full file path for a given filename"""
        return self.config.upload_dir / filename
    
    def _get_metadata_path(self, filename: str) -> Path:
        """Get metadata file path for a given filename"""
        return self.config.upload_dir / f"{filename}.metadata.json"
    
    async def upload_photo(
        self, 
        file: UploadFile, 
        tags: Optional[dict] = None
    ) -> dict:
        """Upload photo to local storage with metadata"""
        try:
            # Validate file
            self._validate_file(file)
            
            # Read file content
            file_content = await file.read()
            file_size = len(file_content)
            
            # Check file size
            if file_size > self.config.max_file_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size: {self.config.max_file_size // 1024 // 1024}MB"
                )
            
            if file_size == 0:
                raise HTTPException(status_code=400, detail="Empty file not allowed")
            
            # Generate unique filename
            filename = self._generate_filename(file.filename or f"photo_{uuid.uuid4()}")
            file_path = self._get_file_path(filename)
            metadata_path = self._get_metadata_path(filename)
            
            # Save file
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_content)
            
            # Create metadata
            metadata = {
                'original_filename': file.filename or 'unknown',
                'upload_timestamp': datetime.utcnow().isoformat(),
                'content_type': file.content_type or 'application/octet-stream',
                'file_size': file_size,
                'filename': filename
            }
            
            # Add custom tags if provided
            if tags:
                metadata['tags'] = tags
            
            # Save metadata
            async with aiofiles.open(metadata_path, 'w') as f:
                await f.write(json.dumps(metadata, indent=2))
            
            logger.info(f"✅ Successfully uploaded photo: {filename} ({file_size} bytes)")
            
            return {
                'success': True,
                'filename': filename,
                'file_path': str(file_path),
                'file_size': file_size,
                'content_type': file.content_type,
                'upload_timestamp': datetime.utcnow().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error during upload: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Upload failed: {str(e)}"
            )
        finally:
            # Reset file pointer for potential reuse
            await file.seek(0)
    
    async def list_photos(self, limit: int = 50) -> List[dict]:
        """List photos in the local storage"""
        try:
            photos = []
            
            # Get all image files
            for file_path in self.config.upload_dir.glob("*"):
                if file_path.is_file() and file_path.suffix.lower() in self.config.allowed_extensions:
                    # Try to load metadata
                    metadata_path = self._get_metadata_path(file_path.name)
                    metadata = {}
                    
                    if metadata_path.exists():
                        try:
                            async with aiofiles.open(metadata_path, 'r') as f:
                                content = await f.read()
                                metadata = json.loads(content)
                        except Exception as e:
                            logger.warning(f"Failed to load metadata for {file_path.name}: {e}")
                    
                    # Get file stats
                    stat = file_path.stat()
                    
                    photo_info = {
                        'filename': file_path.name,
                        'size': stat.st_size,
                        'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'content_type': metadata.get('content_type', 'image/jpeg'),
                        'url': f"/api/photos/{file_path.name}/image",
                        'metadata': metadata
                    }
                    
                    photos.append(photo_info)
                    
                    if len(photos) >= limit:
                        break
            
            # Sort by upload time (newest first)
            photos.sort(key=lambda x: x.get('metadata', {}).get('upload_timestamp', ''), reverse=True)
            
            logger.info(f"✅ Listed {len(photos)} photos")
            return photos
            
        except Exception as e:
            logger.error(f"❌ Error listing photos: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to list photos: {str(e)}")
    
    async def get_photo_data(self, filename: str) -> tuple[bytes, str]:
        """Get photo data and content type from local storage"""
        try:
            file_path = self._get_file_path(filename)
            
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="Photo not found")
            
            # Read file
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()
            
            # Try to get content type from metadata
            metadata_path = self._get_metadata_path(filename)
            content_type = 'image/jpeg'  # default
            
            if metadata_path.exists():
                try:
                    async with aiofiles.open(metadata_path, 'r') as f:
                        metadata_content = await f.read()
                        metadata = json.loads(metadata_content)
                        content_type = metadata.get('content_type', content_type)
                except Exception as e:
                    logger.warning(f"Failed to load metadata for content type: {e}")
            
            logger.info(f"✅ Retrieved photo data for: {filename} ({len(content)} bytes)")
            return content, content_type
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Error retrieving photo {filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve photo: {str(e)}")

    async def delete_photo(self, filename: str) -> bool:
        """Delete a photo from local storage"""
        try:
            file_path = self._get_file_path(filename)
            metadata_path = self._get_metadata_path(filename)
            
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="Photo not found")
            
            # Delete main file
            file_path.unlink()
            
            # Delete metadata file if it exists
            if metadata_path.exists():
                metadata_path.unlink()
            
            logger.info(f"✅ Successfully deleted photo: {filename}")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Error deleting photo {filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to delete photo: {str(e)}")

# Initialize the photo uploader
photo_uploader = LocalPhotoUploader()

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with photo upload form"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload_photo(
    request: Request,
    file: UploadFile = File(...),
    album: str = Form(""),
    description: str = Form("")
):
    """Upload photo endpoint"""
    try:
        # Prepare tags from form data
        tags = {}
        if album:
            tags['album'] = album
        if description:
            tags['description'] = description
        
        result = await photo_uploader.upload_photo(file, tags=tags)
        
        # Return success response
        return templates.TemplateResponse("upload_success.html", {
            "request": request,
            "result": result,
            "filename": file.filename
        })
        
    except HTTPException as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": e.detail,
            "status_code": e.status_code
        })
    except Exception as e:
        logger.error(f"❌ Unexpected error in upload endpoint: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "An unexpected error occurred",
            "status_code": 500
        })

@app.get("/api/photos")
async def get_photos(limit: int = 50):
    """API endpoint to get photos list"""
    photos = await photo_uploader.list_photos(limit=limit)
    return JSONResponse({"photos": photos, "count": len(photos)})

@app.get("/api/photos/{filename}/details")
async def get_photo_details(filename: str):
    """API endpoint to get details for a specific photo"""
    try:
        # Get photo data (this will validate the file exists and load metadata)
        photo_data = await photo_uploader.get_photo_data(filename)
        if photo_data:
            return JSONResponse(photo_data)
        else:
            raise HTTPException(status_code=404, detail="Photo not found")
    except Exception as e:
        logger.error(f"Error getting photo details for {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get photo details")

@app.get("/api/photos/{filename}/image")
async def get_photo_image(filename: str):
    """API endpoint to serve photo image data"""
    try:
        file_path = photo_uploader._get_file_path(filename)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Photo not found")
        
        return FileResponse(
            path=str(file_path),
            media_type="image/jpeg",
            filename=filename
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error serving image {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to serve image")

@app.get("/gallery", response_class=HTMLResponse)
async def photo_gallery(request: Request, limit: int = 20):
    """Photo gallery page"""
    try:
        photos = await photo_uploader.list_photos(limit=limit)
        return templates.TemplateResponse("gallery.html", {
            "request": request,
            "photos": photos
        })
    except Exception as e:
        logger.error(f"❌ Error loading gallery: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load photo gallery",
            "status_code": 500
        })

@app.delete("/api/photos/{filename}")
async def delete_photo_endpoint(filename: str):
    """API endpoint to delete a photo"""
    success = await photo_uploader.delete_photo(filename)
    return JSONResponse({"success": success, "message": f"Photo {filename} deleted successfully"})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Simple health check - verify upload directory exists
        if config.upload_dir.exists():
            return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
        else:
            return {"status": "unhealthy", "error": "Upload directory not found", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e), "timestamp": datetime.utcnow().isoformat()}

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse("error.html", {
        "request": request,
        "error": "Page not found",
        "status_code": 404
    })

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error(f"❌ Internal server error: {exc}")
    return templates.TemplateResponse("error.html", {
        "request": request,
        "error": "Internal server error",
        "status_code": 500
    })

if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
