# Build stage
FROM python:3.13-slim AS builder

WORKDIR /app
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Runtime stage: keep compilers and audio conversion tools out of the final image.
FROM python:3.13-slim

WORKDIR /app/backend
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Copy Python packages from builder
COPY --from=builder /install/ /usr/local/
ENV PYTHONPATH=/app/backend

# Copy only runtime code and bundled scripts, not tests, build files, or local env files.
COPY backend/app ./app
COPY backend/roteiros ./roteiros

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app/backend
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f\"http://localhost:{os.getenv('PORT', '8000')}/healthz\")" || exit 1

# Run with gunicorn + eventlet for WebSocket support
# Single worker (-w 1) required: Vosk model (~1.5GB) loaded in-process.
# Multiple workers would multiply memory usage (OOM risk).
CMD ["sh", "-c", "exec gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:${PORT:-8000} --timeout 120 'app:create_app()'"]
