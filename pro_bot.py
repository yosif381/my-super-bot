import telebot
from telebot import types, apihelper
import yt_dlp
import os
import json
import time
import hashlib
import threading
import socket
import re
import shutil
import logging
from concurrent.futures import ThreadPoolExecutor
import http.server
import socketserver
from flask import Flask
from threading import Thread

# ==========================================
# 🌐 سيرفر Flask المتطور (لإبقاء البوت حياً)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "<b>Telegram Bot is Running by Your Name! 🚀</b>"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run, daemon=True)
    t.start()

# ==========================================
# 🍪 منطقة الكوكيز
# ==========================================
COOKIES_DATA = [
    {
        "name": "VISITOR_PRIVACY_METADATA",
        "value": "CgJZRRIEGgAgJQ%3D%3D",
        "domain": ".youtube.com",
        "hostOnly": False,
        "path": "/",
        "secure": True,
        "httpOnly": True,
        "sameSite": "no_restriction",
        "session": False,
        "firstPartyDomain": "",
        "partitionKey": None,
        "expirationDate": 1785932125,
        "storeId": None
    },
    {
        "name": "GPS",
        "value": "1",
        "domain": ".youtube.com",
        "hostOnly": False,
        "path": "/",
        "secure": True,
        "httpOnly": True,
        "sameSite": "no_restriction",
        "session": False,
        "firstPartyDomain": "",
        "partitionKey": None,
        "expirationDate": 1770381848,
        "storeId": None
    },
    {
        "name": "YSC",
        "value": "NDZ09HNf8Kg",
        "domain": ".youtube.com",
        "hostOnly": False,
        "path": "/",
        "secure": True,
        "httpOnly": True,
        "sameSite": "no_restriction",
        "session": True,
        "firstPartyDomain": "",
        "partitionKey": None,
        "storeId": None
    },
    {
        "name": "__Secure-ROLLOUT_TOKEN",
        "value": "COnK6O6f7cK9JRC8lYek5MSSAxjrk9a_5MSSAw%3D%3D",
        "domain": ".youtube.com",
        "hostOnly": False,
        "path": "/",
        "secure": True,
        "httpOnly": True,
        "sameSite": "no_restriction",
        "session": False,
        "firstPartyDomain": "",
        "partitionKey": None,
        "expirationDate": 1785930136,
        "storeId": None
    },
    {
        "name": "__Secure-YNID",
        "value": "15.YT=Jq1aQ5gbCJDDUQ6NA7dCg-tTeTPtARQt1B_Zz98gSG8fGhjOUaGhaaYNuHbT1VQqRobY3mWXuxFAaVlxSaTzfKBz9D4VK9DYMbT131aeW8NBLz7A6D35OdfCorf_LnB6ccejYBooMJw0Q_qD-CRvj8eQbMSLniCzzdRnTUA7MM77ie-YdLGOcjCQaTagizMiqHOB4DTsip2S5zfHmJMt-c7R_21aT9nsLSwEU5EZC0nP0UDu1bh54iXZHmTTAvteowISu_yugDDA4KzVGhiGXTWu0GdHPs2S3Hguj3uWh1HruH1cbPQuigOVNAWk7E2lTJhrQUni1YsR0ZtWicfhHQ",
        "domain": ".youtube.com",
        "hostOnly": False,
        "path": "/",
        "secure": True,
        "httpOnly": True,
        "sameSite": "no_restriction",
        "session": False,
        "firstPartyDomain": "",
        "partitionKey": None,
        "expirationDate": 1785930078,
        "storeId": None
    },
    {
        "name": "PREF",
        "value": "tz=Asia.Aden",
        "domain": ".youtube.com",
        "hostOnly": False,
        "path": "/",
        "secure": True,
        "httpOnly": False,
        "sameSite": "no_restriction",
        "session": False,
        "firstPartyDomain": "",
        "partitionKey": None,
        "expirationDate": 1833452131,
        "storeId": None
    },
    {
        "name": "VISITOR_INFO1_LIVE",
        "value": "lIdCxdnbrsM",
        "domain": ".youtube.com",
        "hostOnly": False,
        "path": "/",
        "secure": True,
        "httpOnly": True,
        "sameSite": "no_restriction",
        "session": False,
        "firstPartyDomain": "",
        "partitionKey": None,
        "expirationDate": 1785932125,
        "storeId": None
    }
]

def setup_cookies_file():
    if not COOKIES_DATA:
        return
    with open('cookies.txt', 'w') as f:
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# This is a generated file!  Do not edit.\n\n")
        for c in COOKIES_DATA:
            domain = c.get('domain', '')
            flag = 'TRUE' if c.get('hostOnly') == True else 'FALSE'
            path = c.get('path', '/')
            secure = 'TRUE' if c.get('secure', False) else 'FALSE'
            expiration = int(c.get('expirationDate', 0)) if c.get('expirationDate') is not None else 0
            name = c.get('name', '')
            value = c.get('value', '')
            f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}\n")

setup_cookies_file()

# ==========================================
# ⚙️ الإعدادات المتقدمة (Config)
# ==========================================
TOKEN = "8298277087:AAEv36igY-juy9TAIJHDvXwqx4k7pMF3qPM"
VERIFICATION_CODE = "4415"
QURAN_VIDEO_URL = "https://www.instagram.com/reel/DUYAQBaihUg/?igsh=Y2dhNDNuMGRiYWp3"

apihelper.CONNECT_TIMEOUT = 1000
apihelper.READ_TIMEOUT = 1000
apihelper.RETRY_ON_ERROR = True

BASE_DIR = "downloads"
DB_FILE = "system_db.json"
LOG_FILE = "bot_log.txt"
os.makedirs(BASE_DIR, exist_ok=True)

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(message)s')

bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=40)
executor = ThreadPoolExecutor(max_workers=20)

# ==========================================
# 📊 نظام إدارة البيانات
# ==========================================
class Database:
    @staticmethod
    def load():
        if not os.path.exists(DB_FILE):
            return {"users": {}, "verified": [], "stats": {"total_dl": 0}}
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            return {"users": {}, "verified": [], "stats": {"total_dl": 0}}

    @staticmethod
    def save(data):
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def is_verified(user_id):
        return str(user_id) in Database.load().get("verified", [])

    @staticmethod
    def verify_user(user_id):
        data = Database.load()
        if str(user_id) not in data["verified"]:
            data["verified"].append(str(user_id))
            Database.save(data)

# ==========================================
# 🛡️ الحماية وعزل المستخدمين
# ==========================================
def is_owner(call, owner_id):
    if call.from_user.id != int(owner_id):
        bot.answer_callback_query(call.id, "⚠️ عذراً! هذا الطلب يخص مستخدماً آخر.", show_alert=True)
        return False
    return True

# ==========================================
# 🚀 محرك التحميل الذكي
# ==========================================
class SmartDownloader:
    def __init__(self, chat_id, message_id, user_id):
        self.chat_id = chat_id
        self.msg_id = message_id
        self.user_id = user_id
        self.last_update_time = 0

    def progress_hook(self, d):
        if d.get('status') == 'downloading':
            now = time.time()
            if now - self.last_update_time < 10:
                return
            self.last_update_time = now
            p = d.get('_percent_str', '0%')
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            bar = self.create_progress_bar(d.get('downloaded_bytes', 0), d.get('total_bytes') or 1)
            text = f"📥 تحميل ذكي\n📊 {p}\n⚡ {speed}\n⏳ {eta}\n{bar}"
            try:
                bot.edit_message_text(text, self.chat_id, self.msg_id)
            except:
                pass

    def create_progress_bar(self, current, total):
        total = total or 1
        filled = int(10 * current / total)
        return '🟢' * filled + '⚪' * (10 - filled)

    def download(self, url, quality, file_path):
        ydl_opts = {
            'outtmpl': file_path,
            'continuedl': True,
            'retries': 50,
            'fragment_retries': 50,
            'socket_timeout': 30,
            'progress_hooks': [self.progress_hook],
            'quiet': True,
            'no_warnings': True,
            'geo_bypass': True,
            'geo_bypass_country': 'US',
            'force_ipv4': True,
            'merge_output_format': 'mp4',
            'cookiefile': 'cookies.txt',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web', 'tv_embedded'],
                    'skip': ['hls', 'dash'],
                    'player_skip': ['configs'],
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        }
        if quality == 'audio':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'
            }]
        else:
            try:
                h = int(quality)
            except:
                h = 720
            ydl_opts['format'] = f'bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/best[height<={h}][ext=mp4]/best'
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return True
        except Exception as e:
            return str(e)

# ==========================================
# 🔍 محرك البحث عبر الإنترنت
# ==========================================
class InternetSearch:
    @staticmethod
    def search(query, limit=5):
        results = []
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'force_ipv4': True,
            'cookiefile': 'cookies.txt'
        }
        search_query = f"ytsearch{limit}:{query}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(search_query, download=False)
                for e in info.get('entries', []):
                    results.append({
                        "title": e.get("title", "بدون عنوان"),
                        "url": e.get("url"),
                        "thumb": e.get("thumbnail"),
                        "duration": e.get("duration", 0),
                        "uploader": e.get("uploader", "غير معروف")
                    })
            except:
                pass
        return results

# ==========================================
# 🤖 معالجة الأوامر والرسائل
# ==========================================
@bot.message_handler(commands=['start'])
def welcome(message):
    text = (
        "🌟 **مرحباً بك في نظام التحميل الاحترافي V2**\n\n"
        "🚀 أرسل رابط الفيديو للبدء."
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['search'])
def search_command(message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        bot.reply_to(message, "🔎 اكتب اسم الفيديو بعد الأمر")
        return
    query = parts[1]
    limit = 5
    if len(parts) == 3 and parts[2].isdigit():
        limit = min(10, int(parts[2]))
    msg = bot.reply_to(message, "🔍 جاري البحث...")
    results = InternetSearch.search(query, limit=limit)
    if not results:
        bot.edit_message_text("❌ لا نتائج.", msg.chat.id, msg.message_id)
        return
    for r in results:
        url_hash = hashlib.md5(r["url"].encode()).hexdigest()[:10]
        data = Database.load()
        data["users"][str(message.from_user.id)] = {"url": r["url"], "file_id": f"{message.from_user.id}_{url_hash}"}
        Database.save(data)
        markup = types.InlineKeyboardMarkup(row_width=4)
        markup.add(
            types.InlineKeyboardButton("1080p", callback_data=f"get_{message.from_user.id}_{url_hash}_1080"),
            types.InlineKeyboardButton("720p", callback_data=f"get_{message.from_user.id}_{url_hash}_720"),
            types.InlineKeyboardButton("480p", callback_data=f"get_{message.from_user.id}_{url_hash}_480"),
            types.InlineKeyboardButton("🎵 MP3", callback_data=f"get_{message.from_user.id}_{url_hash}_audio")
        )
        caption = f"🎬 {r['title']}\n⏱ {r['duration']} ثانية\n📺 {r['uploader']}"
        if r.get("thumb"):
            bot.send_photo(message.chat.id, r["thumb"], caption=caption, reply_markup=markup)
        else:
            bot.send_message(message.chat.id, caption, reply_markup=markup)
    bot.delete_message(msg.chat.id, msg.message_id)

@bot.message_handler(func=lambda m: m.text and "http" in m.text)
def handle_links(message):
    user_id = message.from_user.id
    m = re.search(r'(https?://\S+)', message.text)
    if not m:
        return
    url = m.group(1)
    if not Database.is_verified(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📖 شاهد المقطع", url=QURAN_VIDEO_URL))
        markup.add(types.InlineKeyboardButton("🔑 إدخال الكود", callback_data=f"verify_{user_id}"))
        bot.reply_to(message, "⛔ وصول محدود!", reply_markup=markup)
        return
    url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
    file_id = f"{user_id}_{url_hash}"
    data = Database.load()
    data["users"][str(user_id)] = {"url": url, "file_id": file_id}
    Database.save(data)
    partial_path = f"{BASE_DIR}/{file_id}.mp4.part"
    if os.path.exists(partial_path):
        size = os.path.getsize(partial_path) / (1024*1024)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"✅ إكمال ({size:.1f}MB)", callback_data=f"resume_{user_id}_{file_id}"))
        markup.add(types.InlineKeyboardButton("❌ حذف والبدء", callback_data=f"restart_{user_id}_{file_id}"))
        bot.reply_to(message, "🔍 تم العثور على جزء سابق.", reply_markup=markup)
    else:
        show_quality_options(message.chat.id, user_id, file_id)

def show_quality_options(chat_id, user_id, file_id):
    markup = types.InlineKeyboardMarkup(row_width=3)
    btns = [
        types.InlineKeyboardButton("1080p", callback_data=f"get_{user_id}_{file_id}_1080"),
        types.InlineKeyboardButton("720p", callback_data=f"get_{user_id}_{file_id}_720"),
        types.InlineKeyboardButton("480p", callback_data=f"get_{user_id}_{file_id}_480"),
        types.InlineKeyboardButton("360p", callback_data=f"get_{user_id}_{file_id}_360"),
        types.InlineKeyboardButton("144p", callback_data=f"get_{user_id}_{file_id}_144"),
        types.InlineKeyboardButton("🎵 MP3", callback_data=f"get_{user_id}_{file_id}_audio"),
        types.InlineKeyboardButton("⌨️ دقة يدوية", callback_data=f"manual_{user_id}_{file_id}")
    ]
    markup.add(*btns)
    bot.send_message(chat_id, "🎬 اختر الدقة:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    data = call.data.split('_')
    action = data[0]
    owner_id = data[1]
    if not is_owner(call, owner_id):
        return
    if action == "verify":
        msg = bot.send_message(call.message.chat.id, "🔢 أدخل الكود:")
        bot.register_next_step_handler(msg, check_verification_code)
    elif action == "get":
        file_id, quality = data[2], data[3]
        initiate_download(call.message, owner_id, file_id, quality)
    elif action == "manual":
        file_id = data[2]
        msg = bot.send_message(call.message.chat.id, "🔢 اكتب الدقة:")
        bot.register_next_step_handler(msg, lambda m: manual_dl_step(m, owner_id, file_id))
    elif action == "resume":
        file_id = data[2]
        initiate_download(call.message, owner_id, file_id, "720")
    elif action == "restart":
        file_id = data[2]
        for f in os.listdir(BASE_DIR):
            if file_id in f:
                os.remove(os.path.join(BASE_DIR, f))
        show_quality_options(call.message.chat.id, owner_id, file_id)

def check_verification_code(message):
    if message.text == VERIFICATION_CODE:
        Database.verify_user(message.from_user.id)
        bot.reply_to(message, "✅ تم التحقق.")
    else:
        bot.reply_to(message, "❌ كود خاطئ.")

def manual_dl_step(message, user_id, file_id):
    if message.text.isdigit():
        initiate_download(message, user_id, file_id, message.text)
    else:
        bot.reply_to(message, "⚠️ أرقام فقط.")

def initiate_download(message, user_id, file_id, quality):
    task_data = Database.load()["users"].get(str(user_id))
    if not task_data:
        return
    url = task_data["url"]
    ext = "mp3" if quality == "audio" else "mp4"
    file_path = f"{BASE_DIR}/{file_id}.{ext}"
    prog_msg = bot.send_message(message.chat.id, "⏳ جاري التحضير...")
    executor.submit(run_task, prog_msg, user_id, url, quality, file_path)

def run_task(prog_msg, user_id, url, quality, file_path):
    dl = SmartDownloader(prog_msg.chat.id, prog_msg.message_id, user_id)
    success = dl.download(url, quality, file_path)
    if success is True:
        try:
            bot.edit_message_text("📤 اكتمل التحميل، جارٍ الرفع...", prog_msg.chat.id, prog_msg.message_id)
            with open(file_path, 'rb') as f:
                if quality == "audio":
                    bot.send_audio(prog_msg.chat.id, f, caption="🎵 تم التحميل", timeout=1000)
                else:
                    bot.send_video(prog_msg.chat.id, f, caption="🎬 تم التحميل", timeout=2000)
            if os.path.exists(file_path):
                os.remove(file_path)
            bot.delete_message(prog_msg.chat.id, prog_msg.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ خطأ أثناء الرفع:\n{e}", prog_msg.chat.id, prog_msg.message_id)
    else:
        bot.edit_message_text(f"❌ فشل التحميل:\n{success}", prog_msg.chat.id, prog_msg.message_id)

keep_alive()
bot.infinity_polling(skip_pending=True)
