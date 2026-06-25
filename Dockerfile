FROM python:3.12-slim

WORKDIR /app

# Системные зависимости: Tesseract (с русским языком) + FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-rus \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python-зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код бота
COPY bot.py .

CMD ["python3", "bot.py"]
