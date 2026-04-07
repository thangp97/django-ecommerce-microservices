FROM python:3.10-slim
WORKDIR /app

# Cài locale UTF-8 để tránh lỗi encoding tiếng Việt
RUN apt-get update && apt-get install -y \
    libpq-dev gcc g++ curl locales \
    && locale-gen C.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUTF8=1

COPY requirements.txt .
# Cài torch CPU-only trước (tránh xung đột index URL)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Tạo thư mục lưu model và vector DB
RUN mkdir -p /app/ai_models /app/chroma_db

# Pre-download embedding model để tránh timeout lúc runtime
# Model all-MiniLM-L6-v2 (~90MB) được cache vào image, không cần download khi sync
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('all-MiniLM-L6-v2'); \
print('Embedding model cached OK')"

COPY . .
EXPOSE 8000
