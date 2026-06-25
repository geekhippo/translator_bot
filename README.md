# 🌐 Telegram Translator Bot

Универсальный Telegram-бот для перевода текста, речи, изображений и документов на русский язык.

🤖 **Попробовать бота:** [@hippotranslator_bot](https://t.me/hippotranslator_bot)
Поддерживает текст, картинки, голосовые сообщения, кружочки, видео, документы и веб-страницы.

## ✨ Возможности

- 📝 **Перевод текста** — отправьте текст на любом языке, получите перевод на русский
- 🖼️ **Распознавание текста на фото** — OCR с помощью Tesseract + перевод через Google Translate
- 🎤 **Перевод голосовых сообщений** — распознавание речи через Groq Whisper + перевод
- 🎥 **Перевод кружочков** — извлечение аудио + распознавание + перевод
- 🎬 **Перевод видео** — извлечение аудиодорожки + распознавание + перевод
- 📄 **Перевод документов** — поддержка PDF, DOCX, TXT с извлечением текста
- 🔗 **Перевод веб-страниц** — отправьте URL, бот извлечёт и переведёт контент
- 🔄 **Автоматическое определение языка** — не нужно указывать исходный язык
- 🇷🇺 **Поддержка 100+ языков** через Google Translate
- 🐳 **Docker-контейнер** — изолированная среда, простой запуск
- ⚡ **Мгновенный ответ** — перевод за секунды
- 🔄 **Автоматический перезапуск** — бот не падает, работает 24/7
- 🔑 **Ротация API-ключей Groq** — автоматическое переключение между ключами при лимите
- 📊 **Статистика** — команда `/stats` показывает топ пользователей

## 🚀 Быстрый старт

### Одной командой

```bash
curl -fsSL https://raw.githubusercontent.com/geekhippo/translator_bot/master/install.sh | bash
```

### Или вручную

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/geekhippo/translator_bot.git
cd translator_bot

# 2. Создайте .env с токенами
echo "TELEGRAM_TOKEN=***" > .env
echo "GROQ_API_KEYS=твой_ключ_groq" >> .env

# 3. Соберите и запустите
docker build -t translator-bot .
docker run --name translator-bot-container \
  --env-file .env \
  -v translator-bot-data:/app/data \
  -d --restart unless-stopped translator-bot
```

## 📝 Как получить ключи

### Telegram Token

1. Откройте Telegram и найдите [@BotFather](https://t.me/BotFather)
2. Отправьте команду `/newbot`
3. Следуйте инструкциям — получите токен вида `123456:ABC-DEF1234gh...`
4. Вставьте токен в файл `.env`

### Groq API Key (для распознавания речи)

1. Перейдите на [console.groq.com](https://console.groq.com/keys)
2. Создайте бесплатный аккаунт
3. Создайте API-ключ
4. Вставьте ключ в файл `.env`
5. Можно указать несколько ключей через запятую для обхода лимитов

## 🎯 Как использовать

1. Добавьте бота в чат или начните личный диалог
2. Отправьте любое из поддерживаемых сообщений:

   | Тип | Что делает бот |
   |-----|----------------|
   | 📝 Текст | Переводит на русский |
   | 🔗 Ссылка (URL) | Парсит страницу и переводит контент |
   | 🖼️ Фото | Распознаёт текст (OCR) и переводит |
   | 🎤 Голосовое | Распознаёт речь и переводит |
   | 🎥 Кружочек | Извлекает аудио, распознаёт и переводит |
   | 🎬 Видео | Извлекает аудио, распознаёт и переводит |
   | 📄 PDF/DOCX/TXT | Извлекает текст из документа и переводит |

3. Бот ответит распознанным текстом и переводом на русский 🇷🇺
4. Команда `/stats` покажет статистику использования

## 📁 Структура проекта

```
translator_bot/
├── bot.py              # Основной код бота
├── Dockerfile          # Docker-образ (Python + Tesseract + FFmpeg)
├── requirements.txt    # Python-зависимости
├── install.sh          # Скрипт установки
├── LICENSE             # MIT License
├── .gitignore          # Игнорируемые файлы
├── .dockerignore       # Игнорируемые файлы при сборке Docker
└── README.md           # Документация
```

## 🛠️ Команды управления

```bash
# Запуск
docker start translator-bot-container

# Остановка
docker stop translator-bot-container

# Логи
docker logs -f translator-bot-container

# Перезапуск
docker restart translator-bot-container

# Обновление
cd translator_bot && git pull && docker build -t translator-bot . && docker stop translator-bot-container && docker rm translator-bot-container && docker run --name translator-bot-container --env-file .env -v translator-bot-data:/app/data -d --restart unless-stopped translator-bot
```

## 📦 Зависимости

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) — работа с Telegram API
- [deep-translator](https://github.com/nidhaloff/deep-translator) — перевод через Google Translate
- [pytesseract](https://github.com/madmaze/pytesseract) — распознавание текста (OCR)
- [Pillow](https://python-pillow.org/) — обработка изображений
- [httpx](https://github.com/encode/httpx) — HTTP-клиент для запросов к Groq API
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) — движок OCR (системная зависимость)
- [FFmpeg](https://ffmpeg.org/) — извлечение аудио из видео (системная зависимость)
- [Groq API](https://console.groq.com) — распознавание речи (Whisper Large V3)
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) — извлечение текста из PDF
- [python-docx](https://github.com/python-openxml/python-docx) — извлечение текста из DOCX
- [trafilatura](https://github.com/adbar/trafilatura) — извлечение контента с веб-страниц

## 📄 Лицензия

MIT License — свободное использование и модификация.

---

Сделано с ❤️ для сообщества [GeekHippo](https://geekhippo.ru)
