# --- Stage 1: base image ---
    FROM python:3.11-slim AS base

    # Set working directory
    WORKDIR /app
    
    # Copy requirements first (để cache layer pip)
    COPY requirements.txt .
    COPY models /app/models
    
    # Cài dependencies
    RUN pip install --no-cache-dir -r requirements.txt
    
    # Copy toàn bộ project
    COPY . .
    
    # Nếu có model nặng tải ngoài (ví dụ S3 / Supabase) thì bạn có thể thêm script download tại đây
    # RUN python scripts/download_model.py
    
    # Expose port FastAPI
    EXPOSE 8000
    
    # Lệnh khởi động
    CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

    