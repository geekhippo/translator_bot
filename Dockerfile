FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y tesseract-ocr
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py .
CMD ["python3", "bot.py"]
