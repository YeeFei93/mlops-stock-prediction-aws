# MLOps Stock Prediction - Production API Server
# Multi-stage build for optimized production image

# Stage 1: Build environment
FROM python:3.10-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Set environment variables for build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Stage 2: Runtime environment
FROM python:3.10-slim as runtime

# Add metadata labels
LABEL maintainer="MLOps Team" \
      org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.version=$VERSION \
      org.label-schema.name="MLOps Stock Prediction API" \
      org.label-schema.description="Production-ready stock prediction API server" \
      org.label-schema.schema-version="1.0"

# Set runtime environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    FLASK_APP=src/inference/predict_api.py \
    FLASK_ENV=production \
    PORT=8080

# Create non-root user for security
RUN groupadd --gid 1000 mlops && \
    useradd --uid 1000 --gid mlops --shell /bin/bash --create-home mlops

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create application directories
WORKDIR /app
RUN chown -R mlops:mlops /app

# Copy application code
COPY --chown=mlops:mlops src/ ./src/
COPY --chown=mlops:mlops lambda_simple.py ./
COPY --chown=mlops:mlops requirements.txt ./

# Create directory for MLflow artifacts and logs
RUN mkdir -p /app/mlruns /app/logs && \
    chown -R mlops:mlops /app/mlruns /app/logs

# Switch to non-root user
USER mlops

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Expose port
EXPOSE $PORT

# Default command
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=8080"]
