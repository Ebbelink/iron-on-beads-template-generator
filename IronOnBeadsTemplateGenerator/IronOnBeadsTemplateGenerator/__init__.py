"""
The flask application package.
"""

import logging
import sys

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from flask import Flask
app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# Wire up Azure Monitor telemetry if the connection string is present.
# APPLICATIONINSIGHTS_CONNECTION_STRING is injected by infra.bicep as an env var.
import os
if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    from azure.monitor.opentelemetry import configure_azure_monitor
    configure_azure_monitor()  # picks up APPLICATIONINSIGHTS_CONNECTION_STRING automatically

# Filter out internal noise from OpenTelemetry and Azure Monitor exporters.
# Applied after configure_azure_monitor() because it adds handlers directly to
# these child loggers; a root-level filter would not intercept those.
_EXCLUDED_PREFIXES = ("opentelemetry", "azure.monitor", "azure.core")

class _ExcludeInternalLogsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= logging.ERROR or not any(record.name.startswith(p) for p in _EXCLUDED_PREFIXES)

for _prefix in _EXCLUDED_PREFIXES:
    logging.getLogger(_prefix).addFilter(_ExcludeInternalLogsFilter())

import IronOnBeadsTemplateGenerator.views