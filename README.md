# 🌐 Telegram Translator Bot

Telegram-бот, который переводит любое текстовое сообщение на русский язык. Просто перешлите боту сообщение на любом языке — и получите перевод.

## ✨ Возможности

- 🔄 **Автоматическое определение языка** — не нужно указывать исходный язык
- 🇷🇺 **Перевод на русский** — поддержка 100+ языков через Google Translate
- 🐳 **Docker-контейнер** — изолированная среда, простой запуск
- ⚡ **Мгновенный ответ** — перевод за секунды
- 🔄 **Автоматический перезапуск** — бот не падает, работает 24/7

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

# 2. Создайте .env с токеном бота
echo "TELEGRAM_TOKEN=ваш_токен" > .env

# 3. Соберите и запустите
docker build -t translator-bot .
docker run --name translator-bot --env-file .env -d --restart unless-stopped translator-bot
```

## 📝 Как получить токен

1. Откройте Telegram и найдите [@BotFather](https://t.me/BotFather)
2. Отправьте команду `/newbot`
3. Следуйте инструкциям — получите токен вида `123456:ABC-DEF1234gh...`
4. Вставьте токен в файл `.env`

## 🎯 Как использовать

1. Добавьте бота в чат или начните личный диалог
2. Перешлите любое сообщение на любом языке
3. Бот ответит переводом на русский 🇷🇺

## 📁 Структура проекта

```
translator_bot/
├── bot.py              # Основной код бота
├── Dockerfile          # Docker-образ
├── requirements.txt    # Python-зависимости
├── install.sh          # Скрипт установки
└── README.md           # Документация
```

## 🛠️ Команды управления

```bash
# Запуск
docker start translator-bot

# Остановка
docker stop translator-bot

# Логи
docker logs -f translator-bot

# Перезапуск
docker restart translator-bot

# Обновление
docker build -t translator-bot . && docker restart translator-bot
```

## 📦 Зависимости

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) — работа с Telegram API
- [deep-translator](https://github.com/nidhaloff/deep-translator) — перевод через Google Translate

## 📄 Лицензия

MIT License — свободное использование и модификация.

---

Сделано с ❤️ для сообщества [GeekHippo](https://geekhippo.ru)
