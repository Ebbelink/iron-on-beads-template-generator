"""
The flask application package.
"""

from flask import Flask
app = Flask(__name__)

# Wire up Azure Monitor telemetry if the connection string is present.
# APPLICATIONINSIGHTS_CONNECTION_STRING is injected by infra.bicep as an env var.
import os
if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    from azure.monitor.opentelemetry import configure_azure_monitor
    configure_azure_monitor()  # picks up APPLICATIONINSIGHTS_CONNECTION_STRING automatically

import IronOnBeadsTemplateGenerator.views