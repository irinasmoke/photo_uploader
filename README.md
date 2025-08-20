# �️ Secure Photo Uploader - FastAPI Web Application

A sleek, production-ready FastAPI web application for uploading photos to Azure Blob Storage with enterprise-grade security using Azure RBAC (Role-Based Access Control) and managed identity.

## ✨ Features

### 🌟 Modern Web Interface
- **Sleek FastAPI Application** - Modern, responsive web interface
- **Drag & Drop Upload** - Intuitive file upload with drag-and-drop support
- **Real-time Progress** - Visual upload progress and feedback
- **Photo Gallery** - Browse and manage uploaded photos
- **Responsive Design** - Works perfectly on desktop and mobile devices

### 🛡️ Security Features

This solution implements **zero-trust security principles** and Azure security best practices:

### Authentication & Authorization
- ✅ **Azure Managed Identity** - No hardcoded keys or secrets
- ✅ **Azure RBAC** - Fine-grained access control using built-in roles
- ✅ **Principle of Least Privilege** - Minimal required permissions only
- ✅ **Identity-based Authentication** - Shared key access disabled

### Data Protection
- ✅ **HTTPS Only** - All communications encrypted in transit (TLS 1.2+)
- ✅ **Encryption at Rest** - Server-side encryption with infrastructure encryption
- ✅ **Private Container Access** - No anonymous access allowed
- ✅ **Blob Versioning** - Data protection and recovery capabilities

### Network Security
- ✅ **Configurable Network Access** - Can be restricted to private endpoints
- ✅ **IP Whitelisting Support** - Network-level access controls
- ✅ **Azure Services Bypass** - Secure access for trusted Azure services

### Compliance & Monitoring
- ✅ **Audit Trail** - Comprehensive logging and monitoring
- ✅ **Retention Policies** - Automated data lifecycle management
- ✅ **Change Feed** - Track all blob modifications
- ✅ **Soft Delete** - Protection against accidental deletion

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   FastAPI App   │    │  User-Assigned       │    │   Azure Storage     │
│                 │───▶│  Managed Identity    │───▶│   Account           │
│ • Web Interface │    │                      │    │ • RBAC Enabled      │
│ • File Upload   │    │ • No Secrets         │    │ • Private Access    │
│ • Photo Gallery │    │ • RBAC Permissions   │    │ • Encrypted         │
│ • REST API      │    │                      │    │                     │
└─────────────────┘    └──────────────────────┘    └─────────────────────┘
        │                                                       
        ▼                                                       
┌─────────────────┐    ┌──────────────────────┐                
│ Container Apps  │    │  Container Registry  │                
│                 │───▶│                      │                
│ • Auto Scaling  │    │ • Managed Identity   │                
│ • HTTPS Only    │    │ • Secure Images      │                
│ • Health Checks │    │                      │                
└─────────────────┘    └──────────────────────┘                
```

## 🚀 Quick Start

### 1. Prerequisites

- Azure CLI installed and authenticated
- Azure Developer CLI (`azd`) installed
- Python 3.8+ installed
- Appropriate Azure permissions to create resources

### 2. Deploy Infrastructure

```powershell
# Initialize the project
azd init

# Set your environment variables
azd env set AZURE_LOCATION "eastus"
azd env set AZURE_ENV_NAME "photo-secure"

# Deploy to Azure
azd up
```

### 3. Run the Application Locally

For local development:

```powershell
# Run the development script (handles everything automatically)
.\run.ps1
```

Or manually:

```powershell
# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1  # On Windows PowerShell

# Install dependencies
pip install -r requirements.txt

# Copy environment template and update with your values
copy .env.example .env
# Edit .env with your Azure configuration

# Start the FastAPI application
cd src
python start.py
```

The web application will be available at:
- **Main App**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs
- **Gallery**: http://localhost:8000/gallery

### 4. Deploy to Azure

```powershell
# Deploy both infrastructure and application
azd up
```

After deployment, your app will be available at the generated Container App URL.

## 📋 Configuration

### Environment Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `AZURE_STORAGE_ACCOUNT_NAME` | Storage account name | Yes | `st7a8b9c0d1e2f3` |
| `AZURE_PHOTO_CONTAINER_NAME` | Container name for photos | No | `photos` (default) |
| `AZURE_USER_ASSIGNED_IDENTITY_CLIENT_ID` | Managed identity client ID | No* | `12345678-1234-1234-1234-123456789abc` |

*Required when using user-assigned managed identity. Falls back to DefaultAzureCredential if not provided.

### Infrastructure Parameters

| Parameter | Description | Default | Options |
|-----------|-------------|---------|---------|
| `environmentName` | Environment name for resources | - | `dev`, `prod`, etc. |
| `location` | Azure region | - | `eastus`, `westeurope`, etc. |
| `principalId` | User principal ID for RBAC | - | Your Azure AD user ID |

## 🔧 Advanced Configuration

### Network Security

To restrict access to private endpoints only, modify the storage account in `infra/main.bicep`:

```bicep
properties: {
  publicNetworkAccess: 'Disabled'  // Change from 'Enabled'
  networkAcls: {
    defaultAction: 'Deny'          // Change from 'Allow'
    // Add your IP ranges or virtual networks
    ipRules: [
      {
        value: 'your.ip.address.range/24'
        action: 'Allow'
      }
    ]
  }
}
```

### Custom RBAC Roles

The solution uses built-in Azure roles. Available roles:

- **Storage Blob Data Reader** (`2a2b9908-6ea1-4ae2-8e65-a410df84e7d1`) - Read only
- **Storage Blob Data Contributor** (`ba92f5b4-2d11-453d-a403-e96b0029c9fe`) - Read/Write (default)
- **Storage Blob Data Owner** (`b7e6dc6d-f1e8-4753-8033-0f276bb0955b`) - Full control

### Monitoring and Alerts

Enable Azure Monitor and set up alerts:

```powershell
# Enable diagnostic settings
az monitor diagnostic-settings create \
  --resource $STORAGE_ACCOUNT_ID \
  --name "storage-diagnostics" \
  --logs '[{"category": "StorageRead", "enabled": true}, {"category": "StorageWrite", "enabled": true}]' \
  --workspace $LOG_ANALYTICS_WORKSPACE_ID
```

## 🧪 Testing

### Local Development

For local development, use Azure CLI authentication:

```powershell
# Login to Azure
az login

# Set subscription (if needed)
az account set --subscription "your-subscription-id"

# Run the application
python src/photo_uploader.py
```

### Production Testing

In Azure environments (App Service, Container Apps, etc.), managed identity will be used automatically.

## 📚 Code Examples

### Using the Web Interface

1. **Upload Photos**: Open http://localhost:8000 and drag-drop photos or click to select
2. **Browse Gallery**: Visit http://localhost:8000/gallery to see all uploaded photos
3. **API Access**: Use http://localhost:8000/api/docs for API documentation

### Using the REST API

```python
import httpx

# Upload a photo via API
with open("photo.jpg", "rb") as f:
    response = httpx.post(
        "http://localhost:8000/upload",
        files={"file": f},
        data={"album": "vacation", "description": "Beach sunset"}
    )

# Get photos list
response = httpx.get("http://localhost:8000/api/photos")
photos = response.json()["photos"]
```

### Programmatic Access (Azure SDK)

```python
from src.main import SecurePhotoUploader

# Initialize uploader
uploader = SecurePhotoUploader()

# Upload a photo with metadata
result = await uploader.upload_photo(
    file=uploaded_file,
    blob_name="2024/vacation/beach.jpg",
    tags={
        "album": "summer_vacation",
        "location": "Malibu Beach",
        "photographer": "John Doe"
    }
)

print(f"Uploaded: {result['blob_url']}")
```

## 🔍 Troubleshooting

### Common Issues

**Authentication Errors**
```
ClientAuthenticationError: Authentication failed
```
- ✅ Verify you're logged into Azure CLI: `az login`
- ✅ Check your managed identity has the correct RBAC roles
- ✅ Ensure the storage account has shared key access disabled

**Permission Errors**
```
Access denied to container 'photos'
```
- ✅ Verify RBAC role assignments in the Azure portal
- ✅ Check the managed identity is assigned to the storage account
- ✅ Wait a few minutes for role assignments to propagate

**Container Not Found**
```
ResourceNotFoundError: Container 'photos' not found
```
- ✅ Check the container was created during deployment
- ✅ Verify the container name in environment variables
- ✅ Check storage account and container exist in the portal

### Debugging Steps

1. **Check Authentication**:
   ```powershell
   az account show  # Verify logged in user
   az identity show --name "id-<your-resource-token>" --resource-group "<your-rg>"
   ```

2. **Verify RBAC Assignments**:
   ```powershell
   az role assignment list --assignee "<managed-identity-principal-id>" --scope "<storage-account-id>"
   ```

3. **Test Storage Access**:
   ```powershell
   az storage blob list --container-name "photos" --account-name "<storage-account-name>" --auth-mode login
   ```

## 🔒 Security Considerations

### Production Deployment

1. **Network Isolation**: Consider using private endpoints for maximum security
2. **Key Rotation**: While not using keys, rotate managed identity credentials regularly
3. **Monitoring**: Set up alerts for unusual access patterns
4. **Backup**: Implement cross-region replication for critical data
5. **Compliance**: Review data residency and compliance requirements

### Data Classification

- **Public Data**: Use public containers with appropriate access policies
- **Confidential Data**: Use private containers with strict RBAC
- **Highly Sensitive**: Consider customer-managed encryption keys (CMEK)

## 📖 Additional Resources

- [Azure Storage Security Guide](https://docs.microsoft.com/azure/storage/common/security-recommendations)
- [Azure RBAC Best Practices](https://docs.microsoft.com/azure/role-based-access-control/best-practices)
- [Managed Identity Documentation](https://docs.microsoft.com/azure/active-directory/managed-identities-azure-resources/)
- [Azure Blob Storage Pricing](https://azure.microsoft.com/pricing/details/storage/blobs/)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests for any improvements.

---

**⚡ Built with Azure security best practices for production workloads**