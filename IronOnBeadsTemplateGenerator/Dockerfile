FROM python:3.12-slim AS build-stage

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir --prefix=/install -r requirements.txt


FROM python:3.12-slim AS runtime

# Non-root user — required for hardened containers
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgeos-c1v5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build-stage /install /usr/local

# Copy application source
COPY IronOnBeadsTemplateGenerator/ .

# Azure App Service writes to /home; use that for uploads so the directory
# survives container restarts when persistent storage is mounted.
ENV UPLOADS_ROOT=/home/uploads
RUN mkdir -p /home/uploads && chown -R appuser:appgroup /home/uploads /app

USER appuser

# Gunicorn: production WSGI server
# - 2 workers per CPU core is standard for I/O-bound Flask apps
# - Timeout raised because mesh generation can take several seconds
# - Access log to stdout so log stream can work with it
EXPOSE 8000
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "IronOnBeadsTemplateGenerator:app"]