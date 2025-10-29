# GitLab Secrets Manager Dockerfile
# Use Python 3.12 slim image for smaller size
FROM python:3.12-slim

# Set metadata
LABEL maintainer="Nathaniel Koranteng <kora.nathaniel@gmail.com>"
LABEL description="CLI tool for managing GitLab CI/CD variables (secrets)"
LABEL version="1.0.0"

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy requirements and setup files first (for better layer caching)
COPY requirements.txt setup.py ./

# Copy application files
COPY config.py gitlab_client.py gitlab_secrets.py ./

# Install dependencies and package in development mode (as root)
# This allows using 'gitlab-secrets' command or 'python gitlab_secrets.py'
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -e .

# Create a non-root user for security
RUN useradd -m -u 1000 appuser

# Change ownership of application files to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set the entrypoint - allows both 'gitlab-secrets' and 'python gitlab_secrets.py'
ENTRYPOINT ["python", "gitlab_secrets.py"]

# Default command (can be overridden when running the container)
CMD ["--help"]
