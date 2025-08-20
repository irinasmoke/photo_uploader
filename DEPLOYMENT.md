# 🚀 Deployment Guide

This guide provides detailed instructions for deploying the Secure Photo Uploader FastAPI application to Azure.

## Prerequisites

- [Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli) installed and authenticated
- [Azure Developer CLI (azd)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) installed
- [Python 3.8+](https://python.org) installed
- [Docker](https://docker.com) (optional, for local container testing)

## Deployment Options

### Option 1: Automated Deployment with Azure Developer CLI (Recommended)

1. **Clone and Initialize**
   ```powershell
   cd photo_uploader
   azd auth login
   ```

2. **Deploy Infrastructure and Application**
   ```powershell
   azd up
   ```
   
   This command will:
   - Provision Azure resources (Storage, Container Registry, Container Apps, etc.)
   - Build and deploy the FastAPI application
   - Configure managed identity and RBAC permissions
   - Output the application URL

3. **Access Your Application**
   After deployment, `azd up` will output the application URL:
   ```
   SUCCESS: Your app is running at: https://ca-abc123.region.azurecontainerapps.io
   ```

### Option 2: Manual Deployment

#### Step 1: Deploy Infrastructure

```powershell
# Deploy only the infrastructure
az deployment group create \
  --resource-group "rg-photo-uploader" \
  --template-file "infra/main.bicep" \
  --parameters environmentName="prod" location="eastus" principalId="YOUR_USER_OBJECT_ID"
```

#### Step 2: Build and Push Container Image

```powershell
# Login to Azure Container Registry
az acr login --name "crab123"

# Build and push the image
cd src
docker build -t photo-uploader .
docker tag photo-uploader crab123.azurecr.io/photo-uploader:latest
docker push crab123.azurecr.io/photo-uploader:latest
```

#### Step 3: Update Container App

```powershell
# Update the container app with the new image
az containerapp update \
  --name "ca-abc123" \
  --resource-group "rg-photo-uploader" \
  --image "crab123.azurecr.io/photo-uploader:latest"
```

## Environment Configuration

### Required Environment Variables

The application automatically configures these environment variables in Azure:

| Variable | Description | Set By |
|----------|-------------|---------|
| `AZURE_STORAGE_ACCOUNT_NAME` | Storage account name | Bicep template |
| `AZURE_PHOTO_CONTAINER_NAME` | Container name for photos | Bicep template |
| `AZURE_USER_ASSIGNED_IDENTITY_CLIENT_ID` | Managed identity client ID | Bicep template |

### Optional Configuration

You can customize the deployment by modifying `infra/main.parameters.json`:

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "environmentName": {
      "value": "prod"
    },
    "location": {
      "value": "eastus"
    },
    "principalId": {
      "value": "your-user-object-id"
    }
  }
}
```

## Post-Deployment Configuration

### 1. Verify Deployment

```powershell
# Check application health
curl https://your-app-url.azurecontainerapps.io/health

# List deployed resources
az resource list --resource-group "rg-photo-uploader-prod" --output table
```

### 2. Test Photo Upload

1. Open your application URL in a browser
2. Upload a test photo using the web interface
3. Check the photo appears in the gallery
4. Verify the photo is stored in Azure Blob Storage

### 3. Monitor Application

```powershell
# View application logs
az containerapp logs show --name "ca-abc123" --resource-group "rg-photo-uploader-prod"

# View metrics in Azure portal
az monitor metrics list --resource "/subscriptions/YOUR_SUBSCRIPTION/resourceGroups/rg-photo-uploader-prod/providers/Microsoft.App/containerApps/ca-abc123"
```

## Security Configuration

### 1. Network Security (Optional)

To restrict storage account access to private networks only:

```bicep
// In infra/main.bicep, update storage account properties
properties: {
  publicNetworkAccess: 'Disabled'
  networkAcls: {
    defaultAction: 'Deny'
    virtualNetworkRules: [
      {
        id: containerAppsSubnet.id
        action: 'Allow'
      }
    ]
  }
}
```

### 2. Custom Domain (Optional)

```powershell
# Add custom domain to Container App
az containerapp hostname add \
  --name "ca-abc123" \
  --resource-group "rg-photo-uploader-prod" \
  --hostname "photos.yourdomain.com"
```

### 3. SSL Certificate

```powershell
# Bind SSL certificate
az containerapp ssl upload \
  --name "ca-abc123" \
  --resource-group "rg-photo-uploader-prod" \
  --certificate-file "certificate.pfx" \
  --certificate-password "password"
```

## Scaling Configuration

### Auto-scaling Rules

The application is configured with HTTP-based auto-scaling:

- **Min replicas**: 1
- **Max replicas**: 3
- **Scale trigger**: 10 concurrent requests

To modify scaling rules:

```powershell
az containerapp revision copy \
  --name "ca-abc123" \
  --resource-group "rg-photo-uploader-prod" \
  --scale-rule-name "http-scale" \
  --scale-rule-http-concurrency 20
```

## Troubleshooting

### Common Issues

1. **Application not starting**
   ```powershell
   # Check container app logs
   az containerapp logs show --name "ca-abc123" --resource-group "rg-photo-uploader-prod" --follow
   ```

2. **Authentication errors**
   ```powershell
   # Verify managed identity permissions
   az role assignment list --assignee "MANAGED_IDENTITY_OBJECT_ID" --scope "/subscriptions/SUBSCRIPTION_ID/resourceGroups/rg-photo-uploader-prod/providers/Microsoft.Storage/storageAccounts/stab123"
   ```

3. **Image pull errors**
   ```powershell
   # Check container registry access
   az acr check-health --name "crab123"
   ```

### Debugging Steps

1. **Check Resource Status**
   ```powershell
   az containerapp show --name "ca-abc123" --resource-group "rg-photo-uploader-prod" --query "properties.provisioningState"
   ```

2. **Validate Network Connectivity**
   ```powershell
   # Test from container app to storage account
   az containerapp exec --name "ca-abc123" --resource-group "rg-photo-uploader-prod" --command "nslookup stab123.blob.core.windows.net"
   ```

3. **Review Configuration**
   ```powershell
   az containerapp show --name "ca-abc123" --resource-group "rg-photo-uploader-prod" --query "properties.template.containers[0].env"
   ```

## Cost Optimization

### 1. Resource Sizing

- **Container Apps**: Start with 0.5 CPU / 1Gi memory
- **Storage**: Use Standard_LRS for development, consider ZRS for production
- **Container Registry**: Basic tier is sufficient for most scenarios

### 2. Scaling Policies

```powershell
# Configure scale-to-zero for development environments
az containerapp update \
  --name "ca-abc123" \
  --resource-group "rg-photo-uploader-dev" \
  --min-replicas 0
```

### 3. Storage Lifecycle Management

```powershell
# Set up lifecycle management for old photos
az storage account management-policy create \
  --account-name "stab123" \
  --policy @lifecycle-policy.json
```

## Monitoring and Alerting

### 1. Application Insights (Optional)

```powershell
# Create Application Insights
az monitor app-insights component create \
  --app "photo-uploader-insights" \
  --location "eastus" \
  --resource-group "rg-photo-uploader-prod"
```

### 2. Set up Alerts

```powershell
# Alert on high error rate
az monitor metrics alert create \
  --name "High Error Rate" \
  --resource-group "rg-photo-uploader-prod" \
  --scopes "/subscriptions/SUBSCRIPTION_ID/resourceGroups/rg-photo-uploader-prod/providers/Microsoft.App/containerApps/ca-abc123" \
  --condition "avg Requests > 100" \
  --description "Alert when error rate is high"
```

## Backup and Recovery

### 1. Storage Account Backup

```powershell
# Enable point-in-time restore
az storage account blob-service-properties update \
  --account-name "stab123" \
  --enable-restore-policy true \
  --restore-days 7
```

### 2. Configuration Backup

```powershell
# Export ARM template
az group export --name "rg-photo-uploader-prod" > backup-template.json
```

## Next Steps

1. **Production Readiness**: Review the [Production Checklist](production-checklist.md)
2. **Security**: Implement [Security Best Practices](security-guide.md)
3. **Monitoring**: Set up [Comprehensive Monitoring](monitoring-guide.md)
4. **CI/CD**: Configure [GitHub Actions](cicd-guide.md) for automated deployments

## Support

For issues and questions:
- Review the [troubleshooting section](#troubleshooting)
- Check [Azure Container Apps documentation](https://docs.microsoft.com/azure/container-apps/)
- Open an issue in the project repository