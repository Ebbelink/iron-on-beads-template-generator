@description('Name of the Container App')
param containerAppName string

@description('Azure region')
param location string = resourceGroup().location

@description('Docker image to deploy')
param containerImage string

@description('Container CPU cores (e.g. "0.25", "0.5", "1.0")')
param cpu string = '0.25'

@description('Container memory')
param memory string = '0.5Gi'

@description('Container port')
param targetPort int = 8000

@description('Container App Environment name')
param environmentName string = 'containerapp-env'

@description('Application Insights name')
param appInsightsName string = 'ai-${uniqueString(resourceGroup().id)}'

@description('Minimum replicas')
param minReplicas int = 0

@description('Maximum replicas')
param maxReplicas int = 1

// Classic Application Insights — uses Microsoft.Insights
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    // Classic mode: no workspace resource id supplied
    IngestionMode: 'ApplicationInsights'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// Container Apps Environment
resource managedEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'none'
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
output appInsightsConnectionString string = appInsights.properties.ConnectionString