# ── Stage 1: Build React Frontend ─────────────────────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --prefer-offline

COPY frontend/ ./
RUN npm run build


# ── Stage 2: Python Runtime ────────────────────────────────────────────────────
FROM python:3.11-slim

# System deps for OpenCV headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
     libgl1 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer cache)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY backend/ ./backend/
COPY ml/ ./ml/
COPY run_local.py ./

# Copy pre-built frontend
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Runtime data directory — mount as a Railway volume in production
RUN mkdir -p data/keys data/evidence data/frames data/reports data/raw

# Railway injects $PORT; default to 8000 for local docker run
ENV PORT=8000
EXPOSE $PORT

# Health check (uses $PORT via shell form)
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD curl -sf http://localhost:${PORT}/health || exit 1

CMD ["python", "run_local.py"]
