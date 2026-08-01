# ─── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.10-slim AS builder

WORKDIR /app

# Install build dependencies & OpenCV system libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt


# ─── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.10-slim AS runtime

WORKDIR /app

# Runtime OS dependencies for OpenCV, PyTorch & FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/queue/status || exit 1

# Entry point
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
