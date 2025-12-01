# --- Stage 1: base image ---
FROM python:3.11-slim AS base

# Set working directory
WORKDIR /app

# Copy requirements first (để cache layer pip)
COPY requirements.txt .

# Cài dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code (không copy models và data)
COPY src/ /app/src/

# Expose port FastAPI (port 3000)
EXPOSE 3000

# Lệnh khởi động (sử dụng biến PORT hoặc mặc định 3000)
CMD sh -c "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-3000}"

    