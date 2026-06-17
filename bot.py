import os
import logging
import subprocess
import tempfile
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator
import pytesseract
from PIL import Image
import io
import httpx

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

async def translate_text(text: str) -> str:
    return GoogleTranslator(source='auto', target='ru').translate(text)

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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

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
            await msg.reply_text(f"🎤 Распознанный текст:\n{text}\n\n🇷🇺 Перевод:\n{result}")
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
            await msg.reply_text(f"🎥 Распознанный текст:\n{text}\n\n🇷🇺 Перевод:\n{result}")
        except Exception as e:
            await msg.reply_text(f"Ошибка при обработке кружочка: {e}")
        finally:
            for p in [tmp_path, audio_path]:
                if p and os.path.exists(p):
                    os.remove(p)
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
            await msg.reply_text(f"🎬 Распознанный текст:\n{text}\n\n🇷🇺 Перевод:\n{result}")
        except Exception as e:
            await msg.reply_text(f"Ошибка при обработке видео: {e}")
        finally:
            for p in [tmp_path, audio_path]:
                if p and os.path.exists(p):
                    os.remove(p)
        return

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.VOICE | filters.AUDIO |
         filters.VIDEO | filters.VIDEO_NOTE) & ~filters.COMMAND,
        handle_message
    ))
    print("Бот-переводчик с OCR и STT запущен...")
    app.run_polling()
