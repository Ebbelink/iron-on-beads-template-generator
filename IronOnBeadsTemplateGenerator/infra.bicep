@description('Name of the Container App')
param containerAppName string

@description('Azure region')
param location string = resourceGroup().location

@description('Docker image to deploy')
param containerImage string

@description('Container CPU cores')
param cpu string = '0.25'

@description('Container memory')
param memory string = '0.5Gi'

@description('Container port')
param targetPort int = 8080

@description('Container App Environment name')
param environmentName string = 'containerapp-env'

@description('Log Analytics Workspace name')
param logAnalyticsName string = 'log-${uniqueString(resourceGroup().id)}'

@description('Minimum replicas')
param minReplicas int = 0

@description('Maximum replicas')
param maxReplicas int = 1

// Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// Container Apps Environment
resource managedEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// Container App
resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
  properties: {
    managedEnvironmentId: managedEnvironment.id

    configuration: {
      ingress: {
        external: true
        targetPort: targetPort
        transport: 'auto'
      }
    }

    template: {
      containers: [
        {
          name: 'app'
          image: containerImage

          resources: {
            cpu: cpu
            memory: memory
          }
        }
      ]

      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
      }
    }
  }
}

output containerAppUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'