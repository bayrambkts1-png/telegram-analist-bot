import sqlite3
import os
import logging
import asyncio
import json
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- API Anahtarlarını ve Konfigürasyonu Çekme ---
# Render, gizli anahtarları "Environment Variables" olarak yönetir.
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# --- Diğer Kurulumlar ---
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
DB_FILE = "akilli_onay_merkezi.db"

# --- Veritabanı Fonksiyonları ---
def setup_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS proposals (id INTEGER PRIMARY KEY, oneri_tipi TEXT, icerik TEXT, puan INTEGER, durum TEXT DEFAULT 'bekliyor')")
    conn.commit()
    conn.close()

def add_proposal(oneri_tipi: str, icerik: str, puan: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM proposals WHERE icerik = ? AND durum = 'bekliyor'", (icerik,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO proposals (oneri_tipi, icerik, puan) VALUES (?, ?, ?)", (oneri_tipi, icerik, puan))
    conn.commit()
    conn.close()

# --- Akıllı Fırsat Avcısı Modülü ---
def ham_fikirleri_getir():
    return [
        "AI Productivity Hacks", "Sustainable Living Gadgets", "Forgotten Civilizations", "DIY Smart Home",
        "Biohacking for Beginners", "Science of Sleep", "Luxury Tech on a Budget", "Unusual Historical Events",
        "Future of Transportation", "Debunking Common Myths"
    ]

def analiz_et(nis_fikri: str):
    if not GEMINI_API_KEY: return None
    model = genai.GenerativeModel('gemini-1.0-pro')
    prompt = f'Analyze the niche idea: "{nis_fikri}". Return ONLY a JSON object with keys "kazanc", "izlenme", "rekabet", and "gerekce".'
    try:
        logging.info(f"'{nis_fikri}' için Gemini analizi başlatıldı...")
        response = model.generate_content(prompt)
        logging.info(f"'{nis_fikri}' için Gemini'den yanıt alındı.")
        json_text = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(json_text)
    except Exception as e:
        logging.error(f"HATA: '{nis_fikri}' analizi başarısız. Detaylar: {e}")
        return None

# --- Ana Komutlar ve Butonlar ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🧠 Akıllı Fırsat Avcısı", callback_data="akilli_firsat_avcisi_baslat")], [InlineKeyboardButton("📬 Onay Bekleyenler", callback_data="onay_bekleyenler_goster")]]
    await update.message.reply_text("🤖 CEO Kontrol Paneli (v_PRO)\n\nSistem 7/24 aktif ve çalışıyor.", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "akilli_firsat_avcisi_baslat":
        await query.edit_message_text(text="✅ Analiz başlıyor... Bu işlem yaklaşık 15 saniye sürecektir.")
        
        # Analizi arka planda çalıştırarak botun donmasını engelle
        context.application.create_task(run_analysis(query))

    elif data == "onay_bekleyenler_goster":
        # ... (Bu kısım aynı, değişiklik yok)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, icerik FROM proposals WHERE durum = 'bekliyor' ORDER BY puan DESC")
        bekleyen_nisler = cursor.fetchall()
        conn.close()
        if not bekleyen_nisler:
            await query.edit_message_text("📬 Onay bekleyen yeni öneri yok.")
            return
        proposal_id, icerik = bekleyen_nisler[0]
        keyboard = [[InlineKeyboardButton("✅ Onayla", callback_data=f"onayla_nis_{proposal_id}")], [InlineKeyboardButton("❌ Reddet", callback_data=f"reddet_nis_{proposal_id}")], [InlineKeyboardButton("➡️ Sonraki", callback_data="onay_bekleyenler_goster")]]
        await query.edit_message_text(text=f"ONAY BEKLEYEN RAPOR ({len(bekleyen_nisler)} adet):\n\n{icerik}", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("onayla_nis_") or data.startswith("reddet_nis_"):
        # ... (Bu kısım aynı, değişiklik yok)
        is_approved = data.startswith("onayla_nis_")
        new_status = "onaylandi" if is_approved else "reddedildi"
        proposal_id = data.split("_")[-1]
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE proposals SET durum = ? WHERE id = ?", (new_status, proposal_id))
        conn.commit()
        conn.close()
        await query.edit_message_text(text=f"✅ Rapor #{proposal_id} {new_status}.")

async def run_analysis(query):
    """Analiz sürecini arka planda yürüten ve sonunda kullanıcıya mesaj atan fonksiyon."""
    fikirler = ham_fikirleri_getir()
    analiz_edilen_nisler = []
    for fikir in fikirler:
        analiz = await asyncio.to_thread(analiz_et, fikir) # Senkron fonksiyonu asenkron çalıştır
        if analiz:
            genel_puan = int(analiz['kazanc'] * 0.4 + analiz['izlenme'] * 0.4 + analiz['rekabet'] * 0.2)
            rapor = (f"🏆 Puan: {genel_puan} | Niş: '{fikir}'\n🧐 Gerekçe: {analiz['gerekce']}")
            analiz_edilen_nisler.append({"rapor": rapor, "puan": genel_puan})
        await asyncio.sleep(1)
    
    if analiz_edilen_nisler:
        analiz_edilen_nisler.sort(key=lambda x: x['puan'], reverse=True)
        for nis in analiz_edilen_nisler:
            add_proposal("nis_oneri", nis['rapor'], nis['puan'])
        await query.message.reply_text(f"🔔 Analiz tamamlandı! {len(analiz_edilen_nisler)} niş bulundu. 'Onay Bekleyenler'i kontrol edin.")
    else:
        await query.message.reply_text("🔔 Analiz sırasında bir sorun oluştu.")

def main():
    """Botu başlatır."""
    if not (TELEGRAM_BOT_TOKEN and GEMINI_API_KEY):
        logging.error("API Anahtarları bulunamadı. Lütfen ortam değişkenlerini ayarlayın.")
        return
    if not os.path.exists(DB_FILE):
        setup_database()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    logging.info("Bot başlatılıyor...")
    application.run_polling()

if __name__ == "__main__":
    main()