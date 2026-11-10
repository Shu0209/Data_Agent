# Python base image
FROM python:3.12-slim

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
# Pin this to the uv version tested in your local environment for reproducible builds.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY uv.lock pyproject.toml ./

# Export locked dependencies and install them
RUN uv export \
    --locked \
    --no-dev \
    --no-emit-project \
    --format requirements.txt \
    --output-file /tmp/requirements.txt \
    && uv pip install --system --no-cache -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# Create non-root user
RUN useradd --create-home --uid 10001 app

# Copy application source code
COPY --chown=app:app src/ /app/src/



# Switch to non-root user
USER app

# Application port
EXPOSE 8000

# Start FastAPI
CMD ["uvicorn", "data_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]