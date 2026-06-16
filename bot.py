import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from deep_translator import GoogleTranslator

TOKEN = os.environ.get("BOT_TOKEN")

async def translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text:
        return
    try:
        result = GoogleTranslator(source='auto', target='ru').translate(text)
        await update.message.reply_text(f"🇷🇺 {result}")
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate))
    print("Бот-переводчик запущен...")
    app.run_polling()
