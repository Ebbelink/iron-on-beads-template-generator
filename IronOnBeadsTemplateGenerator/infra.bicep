@description('Name of the Container App')
param containerAppName string

@description('Azure region')
param location string = resourceGroup().location

@description('Docker image to deploy')
param containerImage string

@description('Container CPU cores (e.g. "0.25", "0.5", "1.0")')
param cpu string = '1.0'

@description('Container memory (needs to be 2x cpu)')
param memory string = '2.0Gi'

@description('Container port')
param targetPort int = 8000

@description('Container App Environment name')
param environmentName string = 'containerapp-env'

@description('Minimum replicas')
param minReplicas int = 0

@description('Maximum replicas')
param maxReplicas int = 1

var lowerContainerAppName = toLower(containerAppName)
var appInsightsName = 'ai-${lowerContainerAppName}'
var logAnalyticsName = 'log-${lowerContainerAppName}'

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

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    IngestionMode: 'LogAnalytics'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

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

@description('GitHub username for GHCR authentication')
param ghcrUsername string

@description('GitHub PAT with read:packages scope for pulling from GHCR')
@secure()
param ghcrToken string

resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: lowerContainerAppName
  location: location
  properties: {
    managedEnvironmentId: managedEnvironment.id

    configuration: {
      // Store the PAT as a Container App secret
      secrets: [
        {
          name: 'ghcr-token'
          value: ghcrToken
        }
      ]

      registries: [
        {
          server: 'ghcr.io'
          username: ghcrUsername
          passwordSecretRef: 'ghcr-token'
        }
      ]

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
            cpu: json(cpu)
            memory: memory
          }
          // Inject App Insights connection string so the app/SDK can use it
          env: [
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: appInsights.properties.ConnectionString
            }
            {
              name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
              value: appInsights.properties.InstrumentationKey
            }
          ]
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
