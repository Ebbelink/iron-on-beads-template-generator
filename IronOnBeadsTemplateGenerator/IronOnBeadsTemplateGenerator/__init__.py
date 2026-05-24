"""
The flask application package.
"""

import logging
import sys
import os

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    from azure.monitor.opentelemetry import configure_azure_monitor
    configure_azure_monitor()

from flask import Flask
app = Flask(__name__)
app.logger.setLevel(logging.INFO)

_EXCLUDED_PREFIXES = ("opentelemetry", "azure.monitor", "azure.core")

class _ExcludeInternalLogsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= logging.ERROR or not any(record.name.startswith(p) for p in _EXCLUDED_PREFIXES)

for _handler in logging.getLogger().handlers:
    _handler.addFilter(_ExcludeInternalLogsFilter())

for _prefix in _EXCLUDED_PREFIXES:
    logging.getLogger(_prefix).addFilter(_ExcludeInternalLogsFilter())

import IronOnBeadsTemplateGenerator.views