# ShopSmart AI - Backend Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # Proxies whose X-Forwarded-For uvicorn trusts (read by uvicorn itself). Set to the
    # proxy's address, or "*" only when the container is reachable solely through a proxy.
    FORWARDED_ALLOW_IPS=127.0.0.1 \
    # Listening port; Cloud Run sets PORT itself.
    PORT=8000

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Default port (see PORT)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f "http://localhost:${PORT}/health" || exit 1

# Run the application
# Shell form so $PORT is expanded; exec keeps uvicorn as PID 1 to receive SIGTERM.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --proxy-headers
