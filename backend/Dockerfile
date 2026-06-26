###############################################################################
# ResearchOS Backend — Production Dockerfile (multi-stage)
###############################################################################

# ========================== Stage 1: Builder ==========================
FROM python:3.12-slim AS builder

# Prevent Python from writing .pyc and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps required to compile binary wheels (psycopg, numpy, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual-env so we can copy it cleanly into the runtime stage
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies (layer cached until requirements.txt changes)
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir gunicorn && \
    pip install --no-cache-dir -r /tmp/requirements.txt


# ========================== Stage 2: Runtime ==========================
FROM python:3.12-slim AS runtime

LABEL maintainer="ResearchOS Team" \
    description="ResearchOS FastAPI backend — production image"

# Runtime ENV
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    APP_PORT=8000 \
    PATH="/opt/venv/bin:$PATH"

# Install only the minimal runtime libraries (libpq for asyncpg)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Copy the virtual-env from builder
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /home/appuser/backend

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Pre-download the embedding model so it is cached in the image
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-large-en-v1.5')"

EXPOSE 8000

# Health check — hit the /health endpoint every 30 s
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["curl", "-f", "http://localhost:8000/health"]

# Launch with Gunicorn + Uvicorn workers (config file baked in)
CMD ["gunicorn", "app.main:app", "-c", "gunicorn.conf.py"]
