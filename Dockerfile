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

# Expose port FastAPI
EXPOSE 8000

# Lệnh khởi động
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

    