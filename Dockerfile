# Multi-stage Dockerfile for Glassdome

# Stage 1: Build Frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python Backend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy package files
COPY pyproject.toml setup.py MANIFEST.in ./
COPY requirements.txt .

# Copy glassdome package (main Python package)
COPY glassdome/ ./glassdome/

# Install package
RUN pip install --no-cache-dir -e .

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose port
EXPOSE 8001

# Run the application
CMD ["glassdome", "serve", "--host", "0.0.0.0", "--port", "8001"]

