# 🖼️ Local Photo Uploader - FastAPI Web Application

A simple, fast FastAPI web application for uploading and managing photos locally with a modern web interface.

## ✨ Features

### 🌟 Modern Web Interface
- **FastAPI Application** - Modern, responsive web interface
- **Drag & Drop Upload** - Intuitive file upload with drag-and-drop support
- **Real-time Progress** - Visual upload progress and feedback
- **Photo Gallery** - Browse and manage uploaded photos
- **Responsive Design** - Works perfectly on desktop and mobile devices

### 🛡️ File Management Features
- **Local Storage** - All photos stored securely on your local filesystem
- **File Validation** - Supports multiple image formats (JPEG, PNG, GIF, WebP, BMP, TIFF)
- **Metadata Storage** - JSON metadata files store upload information and tags
- **File Size Limits** - Configurable maximum file size (default: 100MB)
- **Album Organization** - Tag photos with album names and descriptions

### 📁 Storage Structure
```
src/
├── uploads/
│   └── photos/
│       ├── 2024-01-15_vacation_photo_abc123.jpg
│       ├── 2024-01-15_vacation_photo_abc123.jpg.metadata.json
│       └── ...
├── static/
├── templates/
└── main.py
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   FastAPI App   │    │  Local File System   │    │   JSON Metadata     │
│                 │───▶│                      │───▶│   Files             │
│ • Web Interface │    │ • Image Storage      │    │ • Upload Info       │
│ • File Upload   │    │ • Directory Based    │    │ • Tags & Albums     │
│ • Photo Gallery │    │ • Filename Based     │    │ • File Details      │
│ • REST API      │    │                      │    │                     │
└─────────────────┘    └──────────────────────┘    └─────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+ installed
- Git (for cloning the repository)

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd photo_uploader

# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate     # On Windows

# Install dependencies
cd src
pip install -r requirements.txt
```

### 2. Run the Application

There are two ways to start the application:

**Option A: Using the startup script (recommended)**
```bash
# Make the script executable (first time only)
chmod +x run.sh

# Start the application
./run.sh
```

**Option B: Manual startup**
```bash
# Navigate to src directory
cd src

# Run the FastAPI application
uvicorn main:app --reload --host 127.0.0.1 --port 8080
```

### 3. Access the Application

Open your browser and navigate to:
- **Main Application**: http://localhost:8000
- **Photo Gallery**: http://localhost:8000/gallery
- **API Documentation**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/health

## 📸 Usage

### Upload Photos
1. Go to http://localhost:8000
2. Drag and drop image files or click to select
3. Optionally add album name and description
4. Click "Upload Photo"

### View Gallery
1. Navigate to http://localhost:8000/gallery
2. Browse your uploaded photos
3. Photos are displayed with metadata
4. Click on photos to view details or delete them

### API Usage
Use the REST API endpoints:
- `GET /api/photos` - List all photos
- `GET /api/photos/{filename}/image` - Get photo image
- `GET /api/photos/{filename}/details` - Get photo details
- `DELETE /api/photos/{filename}` - Delete a photo

## 📁 Project Structure

```
photo_uploader/
├── src/
│   ├── main.py              # Main FastAPI application
│   ├── requirements.txt     # Python dependencies
│   ├── uploads/
│   │   ├── photos/          # Local photo storage
│   │   └── metadata/        # JSON metadata files
│   ├── static/
│   │   ├── style.css
│   │   └── script.js
│   └── templates/
│       ├── index.html       # Upload page
│       ├── gallery.html     # Photo gallery
│       ├── upload_success.html
│       └── error.html
├── run.sh                   # Startup script
├── README.md
└── SETUP_COMPLETE.md
```

## ⚙️ Configuration

The application can be configured by modifying the `Config` class in `main.py`:

```python
class Config:
    def __init__(self):
        self.upload_dir = Path("uploads/photos")  # Change upload directory
        self.metadata_dir = Path("uploads/metadata")  # Metadata storage
        self.max_file_size = 100 * 1024 * 1024   # 100MB max file size
        self.allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
```

## 🔧 Features

### File Support
- **Supported Formats**: JPEG, PNG, GIF, WebP, BMP, TIFF
- **File Size Limit**: 100MB (configurable)
- **Metadata Storage**: JSON files alongside images
- **Unique Filenames**: Automatic timestamp-based naming to prevent conflicts

### Web Interface
- **Modern UI**: Tailwind CSS styling
- **Responsive Design**: Works on desktop and mobile
- **Drag & Drop**: Easy file upload
- **Real-time Feedback**: Upload progress and status
- **Photo Gallery**: Grid view with details modal

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you've activated the virtual environment and installed dependencies
   ```bash
   source .venv/bin/activate  # Activate virtual environment
   pip install -r src/requirements.txt  # Install dependencies
   ```

2. **Permission Errors**: Ensure the application has write permissions to the uploads directory
   ```bash
   chmod 755 src/uploads/  # Set directory permissions
   ```

3. **Port in Use**: Change the port if 8000 is already in use
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8080  # Use port 8080 instead
   ```

4. **Upload Directory Not Found**: The application will create directories automatically, but ensure the src directory exists

### Development

To run in development mode with auto-reload:
```bash
cd src
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 📝 API Documentation

Once running, visit http://localhost:8000/api/docs for interactive API documentation with Swagger UI.

## 🚀 Deployment

This application is designed to run locally, but you can also deploy it to various platforms:

### Local Production
```bash
# Install production dependencies
pip install gunicorn

# Run with gunicorn
cd src
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker (Optional)
If you want to containerize the application:
```bash
# Build the Docker image
docker build -t local-photo-uploader .

# Run the container
docker run -p 8000:8000 -v ./uploads:/app/uploads local-photo-uploader
```

## 🔒 Security Considerations

### Local Deployment

1. **File System Permissions**: Ensure proper permissions on upload directories
2. **Input Validation**: The app validates file types and sizes
3. **Local Access**: By default, the app binds to all interfaces (0.0.0.0) - use 127.0.0.1 for localhost-only access
4. **File Storage**: Photos are stored locally with unique filenames to prevent conflicts

### Network Security
- **HTTPS**: Consider using a reverse proxy (nginx) with SSL for production
- **Firewall**: Configure firewall rules if exposing to network
- **Access Control**: Add authentication if needed for multi-user scenarios

## 📖 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Python Virtual Environments](https://docs.python.org/3/tutorial/venv.html)
- [Uvicorn Server](https://www.uvicorn.org/)
- [Tailwind CSS](https://tailwindcss.com/)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests for any improvements.

---

**⚡ Simple, fast, and reliable local photo management**