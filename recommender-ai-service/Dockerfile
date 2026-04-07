FROM python:3.10-slim
WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Cài torch CPU-only trước (tránh xung đột index URL)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Tạo thư mục lưu model và vector DB
RUN mkdir -p /app/ai_models /app/chroma_db

COPY . .
EXPOSE 8000
