"""
The flask application package.
"""

from azure.identity import DefaultAzureCredential
from azure.mgmt.applicationinsights import ApplicationInsightsManagementClient
import os

sub_id = os.getenv("AZURE_SUBSCRIPTION_ID")
client = ApplicationInsightsManagementClient(credential=DefaultAzureCredential(), subscription_id=sub_id)

from flask import Flask
app = Flask(__name__)

import IronOnBeadsTemplateGenerator.views
