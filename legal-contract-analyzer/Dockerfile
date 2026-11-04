# ==============================================================================
# Multi-Stage Production Dockerfile for ContractIQ Full-Stack Application
# Stage 1: Build React 19 + TypeScript + Vite Frontend
# Stage 2: Production Python 3.11 Backend Serving API & Built Static Assets
# ==============================================================================

# Stage 1: Frontend Build
FROM node:20-alpine AS frontend-builder
WORKDIR /build

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# Stage 2: Production Backend & Full-Stack Container
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ /app/backend/

# Copy built frontend assets from Stage 1 into frontend dist
COPY --from=frontend-builder /build/dist /app/frontend/dist

# Create uploads directory
RUN mkdir -p /app/backend/uploads /app/uploads

ENV PYTHONPATH=/app/backend
ENV PORT=8000
EXPOSE 8000

WORKDIR /app/backend
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-2}"]
