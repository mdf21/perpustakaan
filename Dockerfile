FROM python:3.10-slim

WORKDIR /app

# Menginstal dependensi sistem yang mungkin dibutuhkan oleh library (misalnya untuk pengolahan gambar PIL/qrcode)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Menyalin requirements.txt dan menginstal library python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instal gunicorn untuk production server
RUN pip install --no-cache-dir gunicorn

# Menyalin seluruh kode aplikasi
COPY . .

# Membuat direktori data agar bisa di-mount sebagai volume
RUN mkdir -p /app/data

# Mengatur environment variables
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

# Script CMD menjalankan inisialisasi database lalu menjalankan gunicorn
CMD ["sh", "-c", "flask --app app init-db && gunicorn --workers 3 --bind 0.0.0.0:5000 app:app"]
