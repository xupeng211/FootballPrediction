# Base image
FROM python:3.11-slim

# Set environment variables
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing pyc files to disc
# PYTHONUNBUFFERED: Prevents Python from buffering stdout and stderr
# PYTHONPATH: Adds the src directory to the Python path
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    TZ=UTC

# Set working directory
WORKDIR /app

# Install system dependencies
# libpq-dev and gcc for building Python extensions
# curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies using pyproject.toml
# First copy pyproject.toml and src directory (required for editable install)
COPY pyproject.toml .
COPY src/ ./src/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .[all]

# Copy remaining project files
COPY . .

# Create a non-root user for security BEFORE creating directories
RUN useradd -m appuser

# Create necessary directories and set ownership
RUN mkdir -p logs data models && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check - probes the /health endpoint
# Interval: 30s, Timeout: 10s, Retries: 3, Start period: 40s
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/quick || exit 1

# Default command - production FastAPI server
# Can be overridden in docker-compose for development
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
