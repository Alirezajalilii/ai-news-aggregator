# =============================================================================
# AI News Aggregator - Multi-stage Production Dockerfile
# =============================================================================
# Build:   docker build -t ai-news-aggregator:latest .
# Run:     docker compose up -d
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system deps needed for building Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create venv and install Python deps
COPY requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: Runtime - Minimal production image
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

LABEL maintainer="Alireza Jalili" \
      org.opencontainers.image.title="AI News Aggregator" \
      org.opencontainers.image.description="AI news aggregation and distribution system" \
      org.opencontainers.image.version="1.0.0"

# Install runtime system deps (libpq for asyncpg, curl for healthcheck)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && \
    useradd -r -g appuser -d /app -s /sbin/nologin -c "Application user" appuser

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY src/ ./src/
COPY config.yaml ./config.yaml
COPY migrations/ ./migrations/

# Copy entrypoint and healthcheck scripts
COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/healthcheck.py /healthcheck.py

RUN chmod +x /entrypoint.sh && \
    chmod +x /healthcheck.py

# Create log directory with proper ownership
RUN mkdir -p /app/logs && \
    chown -R appuser:appuser /app

# Environment defaults (override via .env or docker-compose)
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CONFIG_PATH=/app/config.yaml

# Expose healthcheck port
EXPOSE 8080

# Volume for logs
VOLUME ["/app/logs"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python /healthcheck.py || exit 1

# Run as non-root user
USER appuser

# Entrypoint handles DB migration + app start
ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["python", "-m", "src.main", "scheduler"]