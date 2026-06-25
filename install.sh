#!/bin/bash
set -e

echo "🚀 Запуск установки @hippotranslator_bot..."

# 1. Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "📦 Docker не найден. Устанавливаю..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
fi

# 2. Создание директории
mkdir -p translator_bot
cd translator_bot

# 3. Запрос данных
echo "📝 Нам понадобятся ключи для работы бота."
read -p "Введите TELEGRAM_TOKEN: " TELEGRAM_TOKEN < /dev/tty
echo "🔑 Для распознавания голосовых и видео нужен Groq API Key."
echo "   Получить бесплатно: https://console.groq.com/keys"
read -p "Введите GROQ_API_KEYS (можно несколько через запятую): " GROQ_API_KEYS < /dev/tty

cat <<EOF > .env
TELEGRAM_TOKEN=$TELEGRAM_TOKEN
GROQ_API_KEYS=$GROQ_API_KEYS
EOF

# 4. Скачивание файлов
echo "📥 Скачиваю файлы бота..."
curl -fsSL https://raw.githubusercontent.com/geekhippo/translator_bot/master/bot.py -o bot.py
curl -fsSL https://raw.githubusercontent.com/geekhippo/translator_bot/master/Dockerfile -o Dockerfile
curl -fsSL https://raw.githubusercontent.com/geekhippo/translator_bot/master/requirements.txt -o requirements.txt

# 5. Сборка и запуск
echo "🏗️ Собираю и запускаю бота..."
docker build -t translator-bot .

# Останавливаем и удаляем старый контейнер, если есть
docker stop translator-bot-container 2>/dev/null || true
docker rm translator-bot-container 2>/dev/null || true

# Создаём volume для статистики
docker volume create translator-bot-data 2>/dev/null || true

docker run --name translator-bot-container \
    --env-file .env \
    -v translator-bot-data:/app/data \
    -d \
    --restart unless-stopped \
    translator-bot

echo "🎉 Готово! Бот @hippotranslator_bot запущен."
echo ""
echo "Возможности бота:"
echo "  📝 Перевод текста"
echo "  🖼️ Перевод текста с картинок (OCR)"
echo "  🎤 Перевод голосовых сообщений"
echo "  🎥 Перевод кружочков"
echo "  🎬 Перевод видео"
echo "  📄 Перевод документов (PDF, DOCX, TXT)"
echo "  🔗 Перевод веб-страниц (URL)"
echo "  📊 Статистика: /stats"
echo ""
echo "Логи: docker logs -f translator-bot-container"
