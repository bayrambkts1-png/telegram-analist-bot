# =================================================================
# 🎬 TAM OTOMONOM FİKİRDEN VİDEOYA BOTU (RENDER - UYANIK TUTMA SÜRÜMÜ) 🎬
# =================================================================
import os
import json
import asyncio
import logging
import requests
import tempfile
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# --- MoviePy Kütüphanesi ve Ayarları ---
try:
    from moviepy.editor import (VideoFileClip, ImageClip, TextClip,
                                CompositeVideoClip, concatenate_videoclips)
    MOVIEPY_AVAILABLE = True
    logging.info("✅ MoviePy başarıyla yüklendi.")
except ImportError:
    logging.warning("⚠️ UYARI: MoviePy yüklenemedi. Video işleme devre dışı.")
    MOVIEPY_AVAILABLE = False

# --- API ANAHTARLARINI ÇEKME (Render Ortam Değişkenleri) ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
PEXELS_API_KEY = os.environ.get('PEXELS_API_KEY')
PIXABAY_API_KEY = os.environ.get('PIXABAY_API_KEY')
UNSPLASH_API_KEY = os.environ.get('UNSPLASH_ACCESS_KEY')

# --- Diğer Kurulumlar ---
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# ... (Bir önceki cevaptaki get_story_and_keywords, search_pexels vb. tüm fonksiyonlar buraya gelecek) ...
# ... (Tüm analiz ve kurgu fonksiyonları aynı kalıyor, değişiklik yok) ...

# --- TELEGRAM BOT KOMUTLARI ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Merhaba! 'Video oluştur [konu]' yazarak başlayabilirsin.")

async def run_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str):
    # ... (Bu fonksiyon da aynı kalıyor, değişiklik yok) ...
    pass # Örnek olarak geçildi, tam kodu bir önceki cevaptan alabilirsiniz.

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (Bu fonksiyon da aynı kalıyor, değişiklik yok) ...
    pass # Örnek olarak geçildi, tam kodu bir önceki cevaptan alabilirsiniz.


# --- FLASK WEB SUNUCUSU (Uyanık Tutma Hilesi) ---
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is alive!"

def run_flask():
    # Render.com genellikle 10000 portunu kullanır
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# --- BOTU BAŞLATMA ---
def main():
    if not TELEGRAM_BOT_TOKEN:
        logging.error("TELEGRAM_BOT_TOKEN eksik!")
        return

    # Flask sunucusunu ayrı bir thread'de (arka planda) başlat
    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    # Telegram botunu başlat
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("--- BOT ve WEB SUNUCUSU BAŞLATILIYOR... ---")
    application.run_polling()
    logging.info("--- BOT DURDU ---")

if __name__ == "__main__":
    main()
