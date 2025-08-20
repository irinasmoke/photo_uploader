targetScope = 'resourceGroup'

// Parameters
@minLength(1)
@maxLength(64)
@description('Name of the environment that can be used as part of naming resource convention')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

@description('Id of the user or app to assign application roles')
param principalId string = ''

// Generate a unique token to be used in naming resources
var resourceToken = toLower(uniqueString(subscription().id, resourceGroup().id, location, environmentName))

// Tags that should be applied to all resources
var tags = {
  'azd-env-name': environmentName
}

// Storage Account with security best practices
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'st${resourceToken}'
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    // Security configurations
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false // Disable shared key access to enforce RBAC
    allowCrossTenantReplication: false
    publicNetworkAccess: 'Enabled' // Can be changed to 'Disabled' for private endpoint only access
    
    // Enable hierarchical namespace for better security and performance
    isHnsEnabled: true
    
    // Network access rules
    networkAcls: {
      defaultAction: 'Allow' // Can be changed to 'Deny' for stricter access control
      bypass: 'AzureServices'
      ipRules: []
      virtualNetworkRules: []
    }
    
    // Encryption configuration
    encryption: {
      services: {
        blob: {
          enabled: true
          keyType: 'Account'
        }
        file: {
          enabled: true
          keyType: 'Account'
        }
      }
      keySource: 'Microsoft.Storage'
      requireInfrastructureEncryption: true
    }
    
    // Default access tier for cost optimization
    accessTier: 'Hot'
  }
}

// User-assigned managed identity for secure access
resource userAssignedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${resourceToken}'
  location: location
  tags: tags
}

// Built-in role definition IDs for storage
var storageRoles = {
  storageBlobDataOwner: 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'
  storageBlobDataContributor: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
  storageBlobDataReader: '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
}

// Role assignment for the managed identity to access blob storage
resource storageRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storageAccount
  name: guid(storageAccount.id, userAssignedIdentity.id, storageRoles.storageBlobDataContributor)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageRoles.storageBlobDataContributor)
    principalId: userAssignedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Optional: Role assignment for the user/service principal (if principalId is provided)
resource userStorageRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  scope: storageAccount
  name: guid(storageAccount.id, principalId, storageRoles.storageBlobDataContributor)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageRoles.storageBlobDataContributor)
    principalId: principalId
    principalType: 'User'
  }
}

// Create a secure container for photos with private access
resource photoContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobServices
  name: 'photos'
  properties: {
    publicAccess: 'None' // No anonymous access
  }
}

resource blobServices 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 30
    }
    containerDeleteRetentionPolicy: {
      enabled: true
      days: 30
    }
    // Note: Versioning and Change Feed are not compatible with hierarchical namespace (Data Lake Gen2)
    // isVersioningEnabled: true
    // changeFeed: {
    //   enabled: true
    //   retentionInDays: 30
    // }
  }
}

// Outputs
output RESOURCE_GROUP_ID string = resourceGroup().id
output AZURE_STORAGE_ACCOUNT_NAME string = storageAccount.name
output AZURE_STORAGE_ACCOUNT_ID string = storageAccount.id
output AZURE_STORAGE_BLOB_ENDPOINT string = storageAccount.properties.primaryEndpoints.blob
output AZURE_USER_ASSIGNED_IDENTITY_ID string = userAssignedIdentity.id
output AZURE_USER_ASSIGNED_IDENTITY_CLIENT_ID string = userAssignedIdentity.properties.clientId
output AZURE_USER_ASSIGNED_IDENTITY_NAME string = userAssignedIdentity.name
output AZURE_PHOTO_CONTAINER_NAME string = photoContainer.name

// Container Registry for FastAPI app
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: 'cr${resourceToken}'
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false // Use managed identity for authentication
    publicNetworkAccess: 'Enabled'
  }
}

// Role assignment for managed identity to access container registry
resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: containerRegistry
  name: guid(containerRegistry.id, userAssignedIdentity.id, 'AcrPull')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d') // AcrPull
    principalId: userAssignedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Log Analytics Workspace for Container Apps
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${resourceToken}'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

// Container Apps Environment
resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: 'cae-${resourceToken}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspace.properties.customerId
        sharedKey: logAnalyticsWorkspace.listKeys().primarySharedKey
      }
    }
  }
}

// Container App for the FastAPI application
resource photoUploaderApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'ca-${resourceToken}'
  location: location
  tags: union(tags, {
    'azd-service-name': 'app'
  })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        corsPolicy: {
          allowedOrigins: ['*']
          allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
          allowedHeaders: ['*']
          allowCredentials: false
        }
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: userAssignedIdentity.id
        }
      ]
      secrets: []
      activeRevisionsMode: 'Single'
    }
    template: {
      containers: [
        {
          name: 'photo-uploader'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          env: [
            {
              name: 'AZURE_STORAGE_ACCOUNT_NAME'
              value: storageAccount.name
            }
            {
              name: 'AZURE_PHOTO_CONTAINER_NAME'
              value: photoContainer.name
            }
            {
              name: 'AZURE_USER_ASSIGNED_IDENTITY_CLIENT_ID'
              value: userAssignedIdentity.properties.clientId
            }
            {
              name: 'APP_HOST'
              value: '0.0.0.0'
            }
            {
              name: 'APP_PORT'
              value: '8000'
            }
            {
              name: 'LOG_LEVEL'
              value: 'INFO'
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          probes: [
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 10
              periodSeconds: 10
            }
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 30
              periodSeconds: 30
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
        rules: [
          {
            name: 'http-scale'
            http: {
              metadata: {
                concurrentRequests: '10'
              }
            }
          }
        ]
      }
    }
  }
  dependsOn: [
    acrPullRoleAssignment
  ]
}

// Additional outputs for the container app
output AZURE_CONTAINER_REGISTRY_NAME string = containerRegistry.name
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.properties.loginServer
output AZURE_LOG_ANALYTICS_WORKSPACE_NAME string = logAnalyticsWorkspace.name
output AZURE_CONTAINER_APPS_ENVIRONMENT_NAME string = containerAppsEnvironment.name
output AZURE_CONTAINER_APP_NAME string = photoUploaderApp.name
output AZURE_CONTAINER_APP_FQDN string = photoUploaderApp.properties.configuration.ingress.fqdn
output SERVICE_WEB_ENDPOINT_URL string = 'https://${photoUploaderApp.properties.configuration.ingress.fqdn}'
