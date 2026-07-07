# Hocaya Sor backend - production Dockerfile
# Repo kökünde (hocaya_sor/) durmalı, src/ klasörünü çalışma dizinine kopyalar.
# Kendi requirements.txt konumun farklıysa COPY satırlarını ona göre düzelt.

FROM python:3.11-slim

WORKDIR /app

# Sistem bağımlılıkları (psycopg2 gibi paketler için gerekebilir)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Önce requirements'ı kopyala (Docker layer cache için)
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodu
COPY src/ .

EXPOSE 8000

# Render/Fly gibi platformlar PORT env değişkenini kendileri set eder.
# Container ayağa kalkarken önce migration'ları uygula, sonra API'yi başlat.
CMD alembic -c alembic.ini upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
