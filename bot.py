# =================================================================
# 🎬 TAM OTOMONOM FİKİRDEN VİDEOYA BOTU (RENDER SÜRÜMÜ) 🎬
# =================================================================
import os
import json
import asyncio
import logging
import requests
import tempfile
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

# --- HİKAYE VE ANAHTAR KELİME ÜRETİMİ (GEMINI) ---
def get_story_and_keywords(topic: str):
    logging.info(f"🧠 Gemini'den '{topic}' için hikaye ve anahtar kelimeler isteniyor...")
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
    prompt = f'Verilen konu hakkında, 3 cümleden oluşan kısa bir hikaye ve bu hikayeyi görselleştirmek için 3 anahtar kelime belirle. Cevabını SADECE şu JSON formatında ver: {{"hikaye": "...", "anahtar_kelimeler": ["kelime1", "kelime2", "kelime3"]}}\nKonu: {topic}'
    try:
        response = model.generate_content(prompt)
        data = json.loads(response.text)
        logging.info(f"✅ Hikaye ve anahtar kelimeler üretildi: {data['anahtar_kelimeler']}")
        return data['hikaye'], data['anahtar_kelimeler']
    except Exception as e:
        logging.error(f"❌ HATA: Gemini hikaye üretimi başarısız. Detaylar: {e}")
        return None, None

# --- ÇOKLU KAYNAKLI MEDYA AVCISI ---
def search_pexels(keyword: str):
    logging.info(f"📹 Pexels'te aranıyor: '{keyword}'")
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/videos/search?query={keyword}&per_page=5&orientation=portrait"
    try:
        r = requests.get(url, headers=headers, timeout=10); r.raise_for_status()
        videos = r.json().get('videos', [])
        return [{'url': v['video_files'][0]['link'], 'type': 'video'} for v in videos]
    except Exception as e:
        logging.error(f"❌ HATA: Pexels araması başarısız. Detaylar: {e}"); return []

def search_pixabay(keyword: str):
    logging.info(f"🖼️ Pixabay'de aranıyor: '{keyword}'")
    url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={keyword}&per_page=5&orientation=vertical"
    try:
        r = requests.get(url, timeout=10); r.raise_for_status()
        videos = r.json().get('hits', [])
        return [{'url': v['videos']['large']['url'], 'type': 'video'} for v in videos]
    except Exception as e:
        logging.error(f"❌ HATA: Pixabay araması başarısız. Detaylar: {e}"); return []

def search_unsplash(keyword: str):
    logging.info(f"📸 Unsplash'ta aranıyor: '{keyword}'")
    headers = {"Authorization": f"Client-ID {UNSPLASH_API_KEY}"}
    url = f"https://api.unsplash.com/search/photos?query={keyword}&per_page=5&orientation=portrait"
    try:
        r = requests.get(url, headers=headers, timeout=10); r.raise_for_status()
        photos = r.json().get('results', [])
        return [{'url': p['urls']['regular'], 'type': 'image'} for p in photos]
    except Exception as e:
        logging.error(f"❌ HATA: Unsplash araması başarısız. Detaylar: {e}"); return []

# --- YAPAY ZEKA VİDEO ELEŞTİRMENİ (GEMINI) ---
def critique_and_select_media(keyword: str, media_list: list):
    logging.info(f"🧐 Gemini, '{keyword}' için en iyi medyayı seçiyor...")
    if not media_list: return None
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
    prompt = f'Sen bir video editörüsün. Anahtar kelime: "{keyword}". Medya Adayları: {json.dumps(media_list, indent=2)}. Bu adaylar arasından anahtar kelimeye en uygun SADECE BİR tanesini seç. Cevabını SADECE seçtiğin adayın tam bilgilerini içeren bir JSON formatında ver. Örnek: {{"secilen_medya": {{"url": "...", "type": "video"}}}}'
    try:
        response = model.generate_content(prompt, request_options={"timeout": 60})
        data = json.loads(response.text)
        selected_media = data.get("secilen_medya")
        logging.info(f"✅ En iyi medya seçildi: {selected_media['url']}")
        return selected_media
    except Exception as e:
        logging.error(f"❌ HATA: Gemini medya seçimi başarısız. Detaylar: {e}"); return media_list[0]

# --- OTOMATİK KURGU OPERATÖRÜ (MOVIEPY) ---
def create_video_from_media(media_files: list, story: str):
    if not MOVIEPY_AVAILABLE: return None
    logging.info("🎬 Kurgu işlemi başlıyor..."); clips = []
    total_duration = 0
    for media_info in media_files:
        try:
            file_path = media_info['path']; media_type = media_info['type']
            clip_duration = 4
            if media_type == 'video':
                clip = VideoFileClip(file_path, target_resolution=(1080, 1920)).subclip(0, clip_duration)
            else:
                clip = ImageClip(file_path, duration=clip_duration).set_fps(24)
            clips.append(clip)
            total_duration += clip_duration
        except Exception as e:
            logging.error(f"Klip oluşturma hatası: {e}")
    if not clips: return None
    final_clip = concatenate_videoclips(clips, method="compose").resize((1080, 1920)).set_position(('center', 'center'))
    sentences = [s.strip() for s in story.split('.') if s.strip()]; text_clips = []; current_time = 0
    sentence_duration = final_clip.duration / len(sentences) if sentences else 0
    for sentence in sentences:
        txt_clip = TextClip(sentence, fontsize=80, color='white', font='Arial-Bold', stroke_color='black', stroke_width=3).set_position(('center', 'bottom')).set_duration(sentence_duration).set_start(current_time)
        text_clips.append(txt_clip); current_time += sentence_duration
    final_video = CompositeVideoClip([final_clip] + text_clips); output_path = tempfile.mktemp(suffix=".mp4")
    final_video.write_videofile(output_path, codec="libx24", audio_codec="aac", fps=24)
    logging.info(f"✅ Video başarıyla oluşturuldu: {output_path}"); return output_path

# --- TELEGRAM BOT KOMUTLARI ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Merhaba! 'Video oluştur [konu]' yazarak başlayabilirsin.")

async def run_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str):
    """Tüm ağır işlemleri arka planda yürüten fonksiyon."""
    chat_id = update.message.chat_id
    try:
        story, keywords = await asyncio.to_thread(get_story_and_keywords, topic)
        if not story:
            await context.bot.send_message(chat_id, "❌ Fikir üretme aşamasında sorun oluştu."); return
        await context.bot.send_message(chat_id, f"📝 Senaryo ve anahtar kelimeler hazır: {keywords}")

        selected_media_info = []
        for kw in keywords:
            candidates = await asyncio.to_thread(lambda: search_pexels(kw) + search_pixabay(kw) + search_unsplash(kw))
            if not candidates:
                await context.bot.send_message(chat_id, f"⚠️ '{kw}' için medya bulunamadı."); continue

            best_media = await asyncio.to_thread(critique_and_select_media, kw, candidates)
            if best_media:
                selected_media_info.append(best_media)
            await asyncio.sleep(1)

        if not selected_media_info:
            await context.bot.send_message(chat_id, "❌ Video için uygun medya bulunamadı."); return
        await context.bot.send_message(chat_id, f"📥 En iyi {len(selected_media_info)} medya dosyası indiriliyor...")

        downloaded_files = []
        for media in selected_media_info:
            try:
                r = requests.get(media['url'], stream=True, timeout=30); r.raise_for_status()
                suffix = ".mp4" if media['type'] == 'video' else ".jpg"
                fp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix); fp.write(r.content); fp.close()
                downloaded_files.append({'path': fp.name, 'type': media['type']})
            except Exception as e:
                logging.error(f"❌ HATA: Medya indirilemedi ({media['url']}). Detaylar: {e}")

        if not downloaded_files:
            await context.bot.send_message(chat_id, "❌ Medya dosyaları indirilemedi."); return

        await context.bot.send_message(chat_id, f"🎬 Medyalar birleştiriliyor...")
        final_video_path = await asyncio.to_thread(create_video_from_media, downloaded_files, story)

        if final_video_path:
            await context.bot.send_video(chat_id, video=open(final_video_path, 'rb'), caption=f"✨ İşte '{topic}' konulu videonuz!")
            os.remove(final_video_path)
        else:
            await context.bot.send_message(chat_id, "❌ Nihai video oluşturulamadı.")

        for f_info in downloaded_files:
            os.remove(f_info['path'])

    except Exception as e:
        logging.error(f"Ana işlem hatası: {e}")
        await context.bot.send_message(chat_id, f"❌ Genel bir hata oluştu: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if user_text.lower().startswith("video oluştur"):
        topic = user_text.replace("video oluştur", "", 1).strip()
        if not topic:
            await update.message.reply_text("Lütfen bir konu belirtin."); return

        await update.message.reply_text(f"✅ Anlaşıldı. '{topic}' konusu işleme alınıyor. Bu işlem arka planda devam edecek...")
        context.application.create_task(run_analysis(update, context, topic))
    else:
        await update.message.reply_text("Lütfen 'Video oluştur [konu]' formatını kullanın.")

# --- BOTU BAŞLATMA ---
def main():
    if not TELEGRAM_BOT_TOKEN:
        logging.error("TELEGRAM_BOT_TOKEN eksik!")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("--- BOT BAŞLATILIYOR... ---")
    application.run_polling()
    logging.info("--- BOT DURDU ---")

if __name__ == "__main__":
    main()
