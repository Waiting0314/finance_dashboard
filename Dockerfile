# 使用 NVIDIA CUDA 基礎映像支援 GPU
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# 設定環境變數
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# 設定工作目錄
WORKDIR /app

# 安裝 Python 3.10（Ubuntu 22.04 預設版本）和系統依賴
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3 /usr/bin/python

# 安裝 Python 依賴
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案
COPY . /app/

# 收集靜態文件
RUN python manage.py collectstatic --noinput

# 開放埠號 8000
EXPOSE 8000

# 預設指令（docker-compose 會覆蓋 worker 的指令）
CMD ["gunicorn", "stock_dashboard.wsgi:application", "--bind", "0.0.0.0:8000"]
