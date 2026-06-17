import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator
import pytesseract
from PIL import Image
import io

TOKEN = os.environ.get("BOT_TOKEN")

async def translate_text(text: str) -> str:
    return GoogleTranslator(source='auto', target='ru').translate(text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Если это текст
    if update.message.text:
        text = update.message.text
        try:
            result = await translate_text(text)
            await update.message.reply_text(f"🇷🇺 {result}")
        except Exception as e:
            await update.message.reply_text(f"Ошибка перевода: {e}")
            
    # Если это фото
    elif update.message.photo:
        file = await update.message.photo[-1].get_file()
        file_bytes = await file.download_as_bytearray()
        
        try:
            image = Image.open(io.BytesIO(file_bytes))
            text = pytesseract.image_to_string(image)
            
            if not text.strip():
                await update.message.reply_text("Не удалось распознать текст на изображении.")
                return
            
            result = await translate_text(text)
            await update.message.reply_text(f"Распознанный текст:\n{text}\n\nПеревод:\n🇷🇺 {result}")
        except Exception as e:
            await update.message.reply_text(f"Ошибка при обработке изображения: {e}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_message))
    print("Бот-переводчик с OCR запущен...")
    app.run_polling()
