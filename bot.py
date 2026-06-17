import os
import logging
import subprocess
import tempfile
import re
import json
import time
from urllib.parse import urlparse
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from deep_translator import GoogleTranslator
import pytesseract
from PIL import Image
import io
import httpx

STATS_FILE = "/app/data/stats.json"

try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logging.warning("PyMuPDF не установлен, поддержка PDF отключена")

try:
    from docx import Document
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False
    logging.warning("python-docx не установлен, поддержка DOCX отключена")

try:
    from trafilatura import extract as trafilatura_extract
    from trafilatura.settings import use_config
    LINK_SUPPORT = True
    _trafilatura_config = use_config()
    _trafilatura_config.set("DEFAULT", "EXTRACTION_TIMEOUT", "10")
except ImportError:
    LINK_SUPPORT = False
    logging.warning("trafilatura не установлен, поддержка ссылок отключена")

TOKEN = os.environ.get("BOT_TOKEN")
GROQ_API_KEYS = os.getenv("GROQ_API_KEYS", "").split(",")
current_key_index = 0

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def get_next_key():
    global current_key_index
    key = GROQ_API_KEYS[current_key_index].strip()
    current_key_index = (current_key_index + 1) % len(GROQ_API_KEYS)
    return key

MAX_CHUNK_SIZE = 4500  # Лимит Google Translate ~5000 символов, берём с запасом
TELEGRAM_MSG_LIMIT = 4096  # Лимит Telegram на длину сообщения

async def send_long_message(message, text, prefix=""):
    """Отправляет длинное сообщение, разбивая на части если нужно."""
    full_text = prefix + text if prefix else text
    if len(full_text) <= TELEGRAM_MSG_LIMIT:
        await message.reply_text(full_text)
        return
    # Разбиваем на части по границам строк
    lines = full_text.split('\n')
    chunk = ""
    for line in lines:
        # Если одна строка длиннее лимита — разбиваем её
        while len(line) > TELEGRAM_MSG_LIMIT:
            if chunk:
                await message.reply_text(chunk)
                chunk = ""
            await message.reply_text(line[:TELEGRAM_MSG_LIMIT])
            line = line[TELEGRAM_MSG_LIMIT:]
        # Проверяем не превысит ли лимит с новой строкой
        if len(chunk) + len(line) + 1 > TELEGRAM_MSG_LIMIT:
            if chunk:
                await message.reply_text(chunk)
            chunk = line + '\n'
        else:
            chunk += line + '\n'
    if chunk and len(chunk.strip()) > 0:
        await message.reply_text(chunk.strip())

def split_text(text: str, max_size: int = MAX_CHUNK_SIZE) -> list:
    """Разбивает длинный текст на куски по предложениям."""
    chunks = []
    while len(text) > max_size:
        # Ищем ближайшую точку/перенос строки в пределах лимита
        split_pos = max(
            text.rfind('. ', 0, max_size),
            text.rfind('\n', 0, max_size),
            text.rfind('! ', 0, max_size),
            text.rfind('? ', 0, max_size),
        )
        if split_pos <= 0:
            split_pos = max_size
        chunks.append(text[:split_pos + 1])
        text = text[split_pos + 1:]
    if text.strip():
        chunks.append(text)
    return chunks

async def translate_text(text: str) -> str:
    """Переводит текст, разбивая на куски при необходимости."""
    if not text.strip():
        return ""
    chunks = split_text(text)
    results = []
    for chunk in chunks:
        try:
            translated = GoogleTranslator(source='auto', target='ru').translate(chunk)
            results.append(translated)
        except Exception as e:
            logging.error(f"Ошибка перевода куска: {e}")
            results.append(chunk)
    return '\n'.join(results)

async def extract_text_from_pdf(file_path: str) -> str:
    if not PDF_SUPPORT:
        return ""
    try:
        doc = fitz.open(file_path)
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return '\n'.join(text_parts)
    except Exception as e:
        logging.error(f"Ошибка PDF: {e}")
        return ""

async def extract_text_from_docx(file_path: str) -> str:
    if not DOCX_SUPPORT:
        return ""
    try:
        doc = Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return '\n'.join(paragraphs)
    except Exception as e:
        logging.error(f"Ошибка DOCX: {e}")
        return ""

async def extract_text_from_txt(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        logging.error(f"Ошибка TXT: {e}")
        return ""

async def fetch_webpage_text(url: str) -> str:
    """Извлекает основной текст с веб-страницы."""
    if not LINK_SUPPORT:
        return ""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            html = response.text
            text = trafilatura_extract(html, config=_trafilatura_config)
            if text:
                return text
            # Fallback: простой извлечения текста
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            for script in soup(["script", "style", "header", "footer", "nav"]):
                script.decompose()
            body = soup.find('body')
            return body.get_text(separator='\n', strip=True) if body else ""
    except Exception as e:
        logging.error(f"Ошибка парсинга URL {url}: {e}")
        return ""

def is_url(text: str) -> bool:
    """Проверяет, является ли текст URL."""
    try:
        result = urlparse(text)
        return all([result.scheme, result.netloc])
    except:
        return False

async def transcribe_audio(file_path: str) -> str:
    """Отправляет аудиофайл в Groq Whisper и возвращает распознанный текст."""
    for _ in range(len(GROQ_API_KEYS)):
        api_key = get_next_key()
        if not api_key:
            continue
        try:
            async with httpx.AsyncClient() as client:
                with open(file_path, "rb") as f:
                    response = await client.post(
                        "https://api.groq.com/openai/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        files={"file": (os.path.basename(file_path), f, "audio/ogg")},
                        data={"model": "whisper-large-v3"},
                        timeout=120.0
                    )
            result = response.json()
            text = result.get("text", "")
            if text:
                return text
        except Exception as e:
            logging.error(f"Ошибка Groq с ключом: {e}")
            continue
    return ""

async def extract_audio_from_video(input_path: str) -> str:
    """Извлекает аудиодорожку из видео через ffmpeg, возвращает путь к .ogg файлу."""
    output_path = input_path + ".ogg"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", input_path, "-vn", "-acodec", "libopus", "-b:a", "64k", output_path],
            check=True, capture_output=True, timeout=60
        )
        return output_path
    except Exception as e:
        logging.error(f"Ошибка ffmpeg: {e}")
        return ""

def _load_stats() -> dict:
    """Загружает статистику из файла."""
    try:
        os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
        with open(STATS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"total_requests": 0, "users": {}}

def _save_stats(stats: dict):
    """Сохраняет статистику в файл."""
    os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

def _record_usage(user_id: int, username: str = None):
    """Записывает использование бота пользователем."""
    stats = _load_stats()
    stats["total_requests"] = stats.get("total_requests", 0) + 1
    uid = str(user_id)
    if uid not in stats.get("users", {}):
        stats["users"][uid] = {"count": 0, "username": username or "unknown"}
    stats["users"][uid]["count"] = stats["users"][uid].get("count", 0) + 1
    stats["users"][uid]["username"] = username or stats["users"][uid].get("username", "unknown")
    stats["users"][uid]["last_used"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save_stats(stats)

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /stats."""
    stats = _load_stats()
    total = stats.get("total_requests", 0)
    users = stats.get("users", {})
    unique_users = len(users)
    
    # Топ-5 активных пользователей
    sorted_users = sorted(users.values(), key=lambda u: u.get("count", 0), reverse=True)[:5]
    top_lines = []
    for i, u in enumerate(sorted_users, 1):
        name = u.get("username", "unknown")
        count = u.get("count", 0)
        top_lines.append(f"  {i}. @{name} — {count} раз")
    top_text = "\n".join(top_lines) if top_lines else "  пока нет данных"
    
    text = (
        f"📊 **Статистика бота**\n\n"
        f"👥 Уникальных пользователей: **{unique_users}**\n"
        f"📝 Всего запросов: **{total}**\n\n"
        f"🏆 Топ-5 активных:\n{top_text}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    # Записываем статистику
    user = msg.from_user
    _record_usage(user.id, user.username or user.first_name)

    # --- Текст ---
    if msg.text:
        text = msg.text
        try:
            result = await translate_text(text)
            await msg.reply_text(f"🇷🇺 {result}")
        except Exception as e:
            await msg.reply_text(f"Ошибка перевода: {e}")
        return

    # --- Фото (OCR) ---
    if msg.photo:
        file = await msg.photo[-1].get_file()
        file_bytes = await file.download_as_bytearray()
        try:
            image = Image.open(io.BytesIO(file_bytes))
            text = pytesseract.image_to_string(image)
            if not text.strip():
                await msg.reply_text("Не удалось распознать текст на изображении.")
                return
            result = await translate_text(text)
            await msg.reply_text(f"📝 Распознанный текст:\n{text}\n\n🇷🇺 Перевод:\n{result}")
        except Exception as e:
            await msg.reply_text(f"Ошибка при обработке изображения: {e}")
        return

    # --- Голосовое сообщение / Аудио ---
    if msg.voice or msg.audio:
        file_obj = msg.voice or msg.audio
        file = await file_obj.get_file()
        suffix = ".ogg"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
        await file.download_to_drive(tmp_path)
        try:
            text = await transcribe_audio(tmp_path)
            if not text:
                await msg.reply_text("Не удалось распознать речь.")
                return
            result = await translate_text(text)
            full_text = f"🎤 Распознанный текст:\n{text}\n\n🇷🇺 Перевод:\n{result}"
            await send_long_message(msg, full_text)
        except Exception as e:
            await msg.reply_text(f"Ошибка при обработке аудио: {e}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        return

    # --- Кружочек (video_note) ---
    if msg.video_note:
        file = await msg.video_note.get_file()
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name
        await file.download_to_drive(tmp_path)
        audio_path = ""
        try:
            audio_path = await extract_audio_from_video(tmp_path)
            if not audio_path:
                await msg.reply_text("Не удалось извлечь аудио из кружочка.")
                return
            text = await transcribe_audio(audio_path)
            if not text:
                await msg.reply_text("Не удалось распознать речь в кружочке.")
                return
            result = await translate_text(text)
            full_text = f"🎥 Распознанный текст:\n{text}\n\n🇷🇺 Перевод:\n{result}"
            await send_long_message(msg, full_text)
        except Exception as e:
            await msg.reply_text(f"Ошибка при обработке кружочка: {e}")
        finally:
            for p in [tmp_path, audio_path]:
                if p and os.path.exists(p):
                    os.remove(p)
        return

    # --- Документы (PDF, DOCX, TXT) ---
    if msg.document:
        file = await msg.document.get_file()
        file_name = msg.document.file_name or "document"
        suffix = os.path.splitext(file_name)[1].lower()
        
        if suffix not in ('.pdf', '.docx', '.txt'):
            await msg.reply_text(f"Формат {suffix} не поддерживается. Отправьте PDF, DOCX или TXT.")
            return
        
        # Проверяем размер файла (лимит Telegram ~20MB)
        if msg.document.file_size and msg.document.file_size > 20 * 1024 * 1024:
            await msg.reply_text("Файл слишком большой (максимум 20 МБ).")
            return
        
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
        await file.download_to_drive(tmp_path)
        try:
            await msg.reply_text("📄 Извлекаю текст из документа...")
            if suffix == '.pdf':
                if not PDF_SUPPORT:
                    await msg.reply_text("Поддержка PDF не установлена.")
                    return
                text = await extract_text_from_pdf(tmp_path)
            elif suffix == '.docx':
                if not DOCX_SUPPORT:
                    await msg.reply_text("Поддержка DOCX не установлена.")
                    return
                text = await extract_text_from_docx(tmp_path)
            elif suffix == '.txt':
                text = await extract_text_from_txt(tmp_path)
            else:
                text = ""
            
            if not text.strip():
                await msg.reply_text("Не удалось извлечь текст из документа.")
                return
            
            # Обрезаем очень длинный текст для предпросмотра
            preview = text[:1000] + "..." if len(text) > 1000 else text
            result = await translate_text(text)
            result_preview = result[:3000] + "\n\n(перевод обрезан, полный текст слишком длинный)" if len(result) > 3000 else result
            
            await msg.reply_text(
                f"📄 Документ: {file_name}\n"
                f"📝 Извлечённый текст ({len(text)} символов):\n{preview}\n\n"
                f"🇷🇺 Перевод:\n{result_preview}"
            )
        except Exception as e:
            await msg.reply_text(f"Ошибка при обработке документа: {e}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        return

    # --- Ссылка (URL в тексте) ---
    if msg.text and is_url(msg.text.strip()):
        url = msg.text.strip()
        await msg.reply_text(f"🔗 Загружаю страницу: {url[:50]}...")
        try:
            text = await fetch_webpage_text(url)
            if not text.strip():
                await msg.reply_text("Не удалось извлечь текст со страницы.")
                return
            
            preview = text[:1500] + "..." if len(text) > 1500 else text
            result = await translate_text(text)
            result_preview = result[:3000] + "\n\n(перевод обрезан)" if len(result) > 3000 else result
            
            await msg.reply_text(
                f"🔗 Ссылка: {url}\n"
                f"📝 Извлечённый текст ({len(text)} символов):\n{preview}\n\n"
                f"🇷🇺 Перевод:\n{result_preview}"
            )
        except Exception as e:
            await msg.reply_text(f"Ошибка при обработке ссылки: {e}")
        return

    # --- Видео ---
    if msg.video:
        file = await msg.video.get_file()
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name
        await file.download_to_drive(tmp_path)
        audio_path = ""
        try:
            audio_path = await extract_audio_from_video(tmp_path)
            if not audio_path:
                await msg.reply_text("Не удалось извлечь аудио из видео.")
                return
            text = await transcribe_audio(audio_path)
            if not text:
                await msg.reply_text("Не удалось распознать речь в видео.")
                return
            result = await translate_text(text)
            full_text = f"🎬 Распознанный текст:\n{text}\n\n🇷🇺 Перевод:\n{result}"
            await send_long_message(msg, full_text)
        except Exception as e:
            await msg.reply_text(f"Ошибка при обработке видео: {e}")
        finally:
            for p in [tmp_path, audio_path]:
                if p and os.path.exists(p):
                    os.remove(p)
        return

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.VOICE | filters.AUDIO |
         filters.VIDEO | filters.VIDEO_NOTE | filters.Document.ALL) & ~filters.COMMAND,
        handle_message
    ))
    print("Бот-переводчик с OCR и STT запущен...")
    app.run_polling()
