# ============================================================
# RAG Knowledge Base - Multi-Stage Production Dockerfile
# Supports both Basic (Ollama) and Premium (OpenAI) modes
# ============================================================

# ---- Stage 1: Builder ----
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (wheel for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir wheel \
    && pip install --no-cache-dir -r requirements.txt

# ---- Stage 2: Runtime ----
FROM python:3.11-slim AS runtime

# Security: run as non-root user
RUN groupadd --gid 1000 raguser \
    && useradd --uid 1000 --gid raguser --shell /bin/bash --create-home raguser

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=raguser:raguser . .

# Create data directories
RUN mkdir -p /app/data /app/chroma_db /app/logs \
    && chown -R raguser:raguser /app

USER raguser

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV CHROMA_PERSIST_DIR=/app/chroma_db
ENV PYTHONUNBUFFERED=x

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Ports
EXPOSE 8000 7860

# Default: start API server
# Override with --target=gradio for Gradio UI
CMD ["python", "run.py"]
