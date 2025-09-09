"""
Secure FastAPI Photo Uploader
A production-ready FastAPI application for uploading photos to Azure Blob Storage
using managed identity and RBAC for authentication.
"""

import os
import uuid
import logging
import platform
from typing import List, Optional
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from azure.storage.blob.aio import BlobServiceClient
from azure.identity.aio import (
    DefaultAzureCredential, ChainedTokenCredential, 
    AzureCliCredential, ManagedIdentityCredential
)
from azure.core.exceptions import ClientAuthenticationError, ResourceNotFoundError, ServiceRequestError
from azure.storage.blob import ContentSettings

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

def safe_log(level: str, message: str, emoji: str = "", alt_prefix: str = ""):
    """Log with emoji on non-Windows systems, plain text on Windows"""
    if platform.system() == 'Windows':
        prefix = f"[{alt_prefix}]" if alt_prefix else ""
        getattr(logger, level.lower())(f"{prefix} {message}")
    else:
        getattr(logger, level.lower())(f"{emoji} {message}")

# Configuration
class Config:
    """Application configuration with Azure best practices"""
    
    def __init__(self):
        self.storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        self.container_name = os.getenv("AZURE_PHOTO_CONTAINER_NAME", "photos")
        self.user_assigned_identity_client_id = os.getenv("AZURE_USER_ASSIGNED_IDENTITY_CLIENT_ID")
        
        # Validation
        if not self.storage_account_name:
            raise ValueError("AZURE_STORAGE_ACCOUNT_NAME environment variable is required")
        
        self.storage_account_url = f"https://{self.storage_account_name}.blob.core.windows.net"
        
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
    title="🖼️ Secure Photo Uploader",
    description="A secure FastAPI application for uploading photos to Azure Blob Storage",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add CORS middleware for development (configure appropriately for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Add your frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class SecurePhotoUploader:
    """Secure photo uploader using Azure managed identity and RBAC"""
    
    def __init__(self):
        self.config = config
        self._blob_service_client = None
        self._credential = None
        
    async def _get_credential(self):
        """Get Azure credential with managed identity preference"""
        if self._credential is None:
            try:
                if self.config.user_assigned_identity_client_id:
                    # Use user-assigned managed identity
                    managed_identity_credential = ManagedIdentityCredential(
                        client_id=self.config.user_assigned_identity_client_id
                    )
                    self._credential = ChainedTokenCredential(
                        managed_identity_credential,
                        AzureCliCredential(),
                        DefaultAzureCredential()
                    )
                else:
                    # Fall back to default credential chain
                    self._credential = DefaultAzureCredential()
                    
                safe_log("info", "Azure credential initialized successfully", "✅", "SUCCESS")
            except Exception as e:
                safe_log("error", f"Failed to initialize Azure credential: {e}", "❌", "ERROR")
                raise ClientAuthenticationError("Failed to initialize Azure credentials")
                
        return self._credential
    
    async def _get_blob_service_client(self):
        """Get authenticated blob service client"""
        if self._blob_service_client is None:
            credential = await self._get_credential()
            self._blob_service_client = BlobServiceClient(
                account_url=self.config.storage_account_url,
                credential=credential
            )
        return self._blob_service_client
    
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
    
    def _generate_blob_name(self, original_filename: str) -> str:
        """Generate a unique blob name with timestamp and UUID"""
        timestamp = datetime.utcnow().strftime("%Y/%m/%d")
        file_extension = Path(original_filename).suffix.lower()
        unique_id = str(uuid.uuid4())[:8]
        
        # Clean filename
        clean_name = "".join(c for c in Path(original_filename).stem if c.isalnum() or c in ('-', '_'))
        clean_name = clean_name[:50]  # Limit length
        
        return f"{timestamp}/{clean_name}_{unique_id}{file_extension}"
    
    async def upload_photo(
        self, 
        file: UploadFile, 
        blob_name: Optional[str] = None,
        tags: Optional[dict] = None
    ) -> dict:
        """Upload photo to Azure Blob Storage with error handling and retry logic"""
        try:
            # Validate file
            self._validate_file(file)
            
            # Generate blob name if not provided
            if not blob_name:
                blob_name = self._generate_blob_name(file.filename or f"photo_{uuid.uuid4()}")
            
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
            
            # Get blob service client
            blob_service_client = await self._get_blob_service_client()
            blob_client = blob_service_client.get_blob_client(
                container=self.config.container_name,
                blob=blob_name
            )
            
            # Set content settings
            content_settings = ContentSettings(
                content_type=file.content_type,
                content_disposition=f'attachment; filename="{file.filename}"'
            )
            
            # Upload with metadata and tags
            metadata = {
                'original_filename': file.filename or 'unknown',
                'upload_timestamp': datetime.utcnow().isoformat(),
                'content_type': file.content_type or 'application/octet-stream',
                'file_size': str(file_size)
            }
            
            # Add custom tags if provided
            if tags:
                for key, value in tags.items():
                    if len(key) <= 128 and len(str(value)) <= 256:  # Azure tag limits
                        metadata[f"tag_{key}"] = str(value)
            
            # Upload the blob
            await blob_client.upload_blob(
                file_content,
                overwrite=True,  # Allow overwriting existing blobs
                content_settings=content_settings,
                metadata=metadata,
                timeout=300  # 5 minutes timeout
            )
            
            safe_log("info", f"Successfully uploaded photo: {blob_name} ({file_size} bytes)", "✅", "SUCCESS")
            
            return {
                'success': True,
                'blob_name': blob_name,
                'blob_url': blob_client.url,
                'file_size': file_size,
                'content_type': file.content_type,
                'upload_timestamp': datetime.utcnow().isoformat()
            }
            
        except HTTPException:
            raise
        except ClientAuthenticationError as e:
            safe_log("error", f"Authentication error: {e}", "❌", "AUTH_ERROR")
            raise HTTPException(
                status_code=401,
                detail="Authentication failed. Check your Azure credentials and RBAC permissions."
            )
        except ResourceNotFoundError as e:
            safe_log("error", f"Resource not found: {e}", "❌", "NOT_FOUND")
            raise HTTPException(
                status_code=404,
                detail=f"Storage container '{self.config.container_name}' not found."
            )
        except ServiceRequestError as e:
            safe_log("error", f"Service request error: {e}", "❌", "SERVICE_ERROR")
            raise HTTPException(
                status_code=500,
                detail="Azure Storage service error. Please try again later."
            )
        except Exception as e:
            safe_log("error", f"Unexpected error during upload: {e}", "❌", "ERROR")
            raise HTTPException(
                status_code=500,
                detail=f"Upload failed: {str(e)}"
            )
        finally:
            # Reset file pointer for potential reuse
            await file.seek(0)
    
    async def list_photos(self, limit: int = 50, prefix: str = "") -> List[dict]:
        """List photos in the storage container"""
        try:
            blob_service_client = await self._get_blob_service_client()
            container_client = blob_service_client.get_container_client(self.config.container_name)
            
            photos = []
            async for blob in container_client.list_blobs(name_starts_with=prefix):
                # Skip folder entries (blobs with size 0 and no content type typically represent folders)
                # Only include actual image files
                if blob.size > 0 and blob.content_settings and blob.content_settings.content_type:
                    # Additional check to ensure it's an image file
                    content_type = blob.content_settings.content_type.lower()
                    if content_type.startswith('image/'):
                        photos.append({
                            'name': blob.name,
                            'size': blob.size,
                            'last_modified': blob.last_modified.isoformat() if blob.last_modified else None,
                            'content_type': blob.content_settings.content_type,
                            'url': f"{self.config.storage_account_url}/{self.config.container_name}/{blob.name}",
                            'metadata': blob.metadata or {}
                        })
                        
                        if len(photos) >= limit:
                            break
            
            safe_log("info", f"Listed {len(photos)} photo files (filtered out folders)", "✅", "SUCCESS")
            return photos
            
        except Exception as e:
            safe_log("error", f"Error listing photos: {e}", "❌", "ERROR")
            raise HTTPException(status_code=500, detail=f"Failed to list photos: {str(e)}")
    
    async def get_photo_data(self, blob_name: str) -> tuple[bytes, str]:
        """Get photo data and content type from storage"""
        try:
            blob_service_client = await self._get_blob_service_client()
            blob_client = blob_service_client.get_blob_client(
                container=self.config.container_name,
                blob=blob_name
            )
            
            # Download blob data
            blob_data = await blob_client.download_blob()
            content = await blob_data.readall()
            
            # Get blob properties for content type
            properties = await blob_client.get_blob_properties()
            content_type = (
                properties.content_settings.content_type 
                if properties.content_settings and properties.content_settings.content_type
                else 'application/octet-stream'
            )
            
            safe_log("info", f"Retrieved photo data for: {blob_name} ({len(content)} bytes)", "✅", "SUCCESS")
            return content, content_type
            
        except ResourceNotFoundError:
            raise HTTPException(status_code=404, detail="Photo not found")
        except Exception as e:
            safe_log("error", f"Error retrieving photo {blob_name}: {e}", "❌", "ERROR")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve photo: {str(e)}")

    async def delete_photo(self, blob_name: str) -> bool:
        """Delete a photo from storage"""
        try:
            blob_service_client = await self._get_blob_service_client()
            blob_client = blob_service_client.get_blob_client(
                container=self.config.container_name,
                blob=blob_name
            )
            
            await blob_client.delete_blob()
            logger.info(f"✅ Successfully deleted photo: {blob_name}")
            return True
            
        except ResourceNotFoundError:
            raise HTTPException(status_code=404, detail="Photo not found")
        except Exception as e:
            logger.error(f"❌ Error deleting photo {blob_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to delete photo: {str(e)}")

# Initialize the photo uploader
photo_uploader = SecurePhotoUploader()

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
        safe_log("error", f"Unexpected error in upload endpoint: {e}", "❌", "ERROR")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "An unexpected error occurred",
            "status_code": 500
        })

@app.get("/api/photos")
async def get_photos(limit: int = 50, prefix: str = ""):
    """API endpoint to get photos list"""
    photos = await photo_uploader.list_photos(limit=limit, prefix=prefix)
    return JSONResponse({"photos": photos, "count": len(photos)})

@app.get("/api/photos/{blob_name:path}/image")
async def get_photo_image(blob_name: str):
    """API endpoint to serve photo image data"""
    try:
        content, content_type = await photo_uploader.get_photo_data(blob_name)
        return Response(content=content, media_type=content_type)
    except HTTPException:
        raise
    except Exception as e:
        safe_log("error", f"Error serving image {blob_name}: {e}", "❌", "ERROR")
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
        safe_log("error", f"Error loading gallery: {e}", "❌", "ERROR")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load photo gallery",
            "status_code": 500
        })

@app.delete("/api/photos/{blob_name:path}")
async def delete_photo_endpoint(blob_name: str):
    """API endpoint to delete a photo"""
    success = await photo_uploader.delete_photo(blob_name)
    return JSONResponse({"success": success, "message": f"Photo {blob_name} deleted successfully"})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test Azure connection
        await photo_uploader._get_credential()
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        safe_log("error", f"Health check failed: {e}", "❌", "ERROR")
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
    safe_log("error", f"Internal server error: {exc}", "❌", "ERROR")
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
