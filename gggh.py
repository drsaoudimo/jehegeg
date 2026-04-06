import sys
import telebot
from telebot import types
import time
import subprocess
import os
import tempfile
import re
import json
import threading
import signal
from datetime import datetime

# إعدادات البوت
BOT_TOKEN = '8621848439:AAG2BXhKw0xHwn7EtPAsIz_D6WzPMEzkX9M'
bot = telebot.TeleBot(BOT_TOKEN)

# معرف المطور
DEVELOPER_ID = 7032092360

# مجلد التحميل
uploaded_files_dir = "uploaded_files"
if not os.path.exists(uploaded_files_dir):
    os.makedirs(uploaded_files_dir)

# ملف لحفظ المكتبات المثبتة
LIBRARIES_FILE = "installed_libraries.json"

# تخزين عمليات البوتات النشطة
active_bots = {}  # {chat_id: [{id, process, file_name, bot_username, start_time}]}

# تحميل المكتبات المثبتة مسبقاً
def load_installed_libraries():
    if os.path.exists(LIBRARIES_FILE):
        with open(LIBRARIES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_installed_library(lib_name):
    libraries = load_installed_libraries()
    libraries[lib_name] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LIBRARIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(libraries, f, ensure_ascii=False, indent=2)

# قائمة المكتبات الأساسية المضمنة في بايثون
BUILTIN_LIBS = [
    # المكتبات القياسية
    'os', 'sys', 'time', 'datetime', 're', 'json', 'random', 'math', 
    'io', 'collections', 'functools', 'itertools', 'hashlib', 'base64',
    'types', 'typing', 'threading', 'subprocess', 'tempfile', 'pathlib',
    'string', 'decimal', 'fractions', 'statistics', 'copy', 'pprint',
    'inspect', 'argparse', 'csv', 'pickle', 'sqlite3', 'uuid', 'html',
    'queue', 'ssl', 'socket', 'logging', 'signal', 'atexit', 'gc',
    'weakref', 'abc', 'bisect', 'codecs', 'contextlib', 'difflib',
    'dis', 'doctest', 'enum', 'fileinput', 'getopt', 'glob', 'gzip',
    'importlib', 'keyword', 'linecache', 'locale', 'marshal', 'mimetypes',
    'operator', 'optparse', 'parser', 'pdb', 'pickletools', 'pkgutil',
    'platform', 'plistlib', 'posixpath', 'py_compile', 'pyclbr', 'pydoc',
    'quopri', 'reprlib', 'rlcompleter', 'runpy', 'sched', 'selectors',
    'shelve', 'shlex', 'shutil', 'site', 'smtplib', 'sndhdr', 'spwd',
    'sqlite3', 'stat', 'stringprep', 'struct', 'sunau', 'symbol',
    'symtable', 'sysconfig', 'tabnanny', 'tarfile', 'telnetlib',
    'textwrap', 'this', 'timeit', 'token', 'tokenize', 'traceback',
    'tty', 'turtle', 'unicodedata', 'unittest', 'urllib', 'uu',
    'warnings', 'wave', 'webbrowser', 'xml', 'zipapp', 'zipfile',
    'zlib', '__future__', '_thread', 'multiprocessing', 'select',
    'fcntl', 'msvcrt', 'winreg', 'winsound', 'asyncio', 'concurrent',
    
    # أنواع telebot (ليست مكتبات حقيقية)
    'InlineKeyboardMarkup', 'InlineKeyboardButton', 'types',
    'ReplyKeyboardMarkup', 'KeyboardButton', 'ForceReply',
    'ReplyKeyboardRemove', 'CallbackQuery', 'Message'
]

# كشف المكتبات المطلوبة (محسّن)
def detect_required_libraries(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        required_libs = []
        
        # أنماط البحث عن المكتبات الحقيقية فقط
        import_patterns = [
            r'^\s*import\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\s*,\s*[a-zA-Z_][a-zA-Z0-9_]*)*)\s*(?:#|$)',
            r'^\s*from\s+([a-zA-Z_][a-zA-Z0-9_]+)\s+import',
        ]
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            for pattern in import_patterns:
                match = re.search(pattern, line)
                if match:
                    libs_str = match.group(1)
                    # تقسيم المكتبات المتعددة
                    libs = [lib.strip() for lib in libs_str.split(',')]
                    
                    for lib in libs:
                        # تجاهل المكتبات المضمنة وأنواع telebot
                        if (lib and 
                            lib not in BUILTIN_LIBS and 
                            lib not in required_libs and
                            not lib.startswith('_') and
                            len(lib) > 1):
                            
                            # تحويل أسماء المكتبات إلى أسماء تثبيت صحيحة
                            lib = map_library_name(lib)
                            if lib:
                                required_libs.append(lib)
        
        # البحث عن المكتبات في المحتوى (للحالات الخاصة)
        content_lower = content.lower()
        
        # كشف المكتبات الشائعة
        common_libs_patterns = {
            'telebot': 'pyTelegramBotAPI',
            'pytelegrambotapi': 'pyTelegramBotAPI',
            'requests': 'requests',
            'aiohttp': 'aiohttp',
            'bs4': 'beautifulsoup4',
            'selenium': 'selenium',
            'pymongo': 'pymongo',
            'sqlalchemy': 'SQLAlchemy',
            'flask': 'Flask',
            'django': 'Django',
            'numpy': 'numpy',
            'pandas': 'pandas',
            'pillow': 'Pillow',
            'PIL': 'Pillow',
            'pyrogram': 'pyrogram',
            'telethon': 'telethon',
            'aiogram': 'aiogram',
            'discord': 'discord.py',
            'cv2': 'opencv-python',
            'opencv': 'opencv-python',
            'matplotlib': 'matplotlib',
            'scipy': 'scipy',
            'sklearn': 'scikit-learn',
            'tensorflow': 'tensorflow',
            'torch': 'torch',
            'qrcode': 'qrcode[pil]',
            'youtube_dl': 'youtube_dl',
            'yt_dlp': 'yt-dlp',
            'wget': 'wget',
            'pyautogui': 'pyautogui',
            'pyshorteners': 'pyshorteners',
            'pytz': 'pytz',
            'colorama': 'colorama',
            'pyfiglet': 'pyfiglet',
            'termcolor': 'termcolor',
            'tqdm': 'tqdm',
            'pyperclip': 'pyperclip',
            'cryptography': 'cryptography',
            'pycryptodome': 'pycryptodome',
            'psutil': 'psutil',
            'pyaes': 'pyaes',
            'rsa': 'rsa'
        }
        
        for keyword, lib_name in common_libs_patterns.items():
            if keyword in content_lower and lib_name not in required_libs:
                required_libs.append(lib_name)
        
        # إزالة التكرارات
        required_libs = list(set(required_libs))
        
        print(f"🔍 المكتبات المكتشفة: {required_libs}")
        return required_libs
        
    except Exception as e:
        print(f"خطأ في كشف المكتبات: {e}")
        return []

def map_library_name(lib_name):
    """تحويل اسم المكتبة إلى اسم التثبيت الصحيح"""
    lib_mapping = {
        'telebot': 'pyTelegramBotAPI',
        'telegram': 'python-telegram-bot',
        'requests': 'requests',
        'bs4': 'beautifulsoup4',
        'selenium': 'selenium',
        'pymongo': 'pymongo',
        'sqlalchemy': 'SQLAlchemy',
        'flask': 'Flask',
        'django': 'Django',
        'numpy': 'numpy',
        'pandas': 'pandas',
        'PIL': 'Pillow',
        'pillow': 'Pillow',
        'cv2': 'opencv-python',
        'matplotlib': 'matplotlib',
        'scipy': 'scipy',
        'sklearn': 'scikit-learn',
        'tensorflow': 'tensorflow',
        'torch': 'torch',
        'discord': 'discord.py',
        'telethon': 'telethon',
        'pyrogram': 'pyrogram',
        'aiogram': 'aiogram',
        'qrcode': 'qrcode[pil]',
        'youtube_dl': 'youtube_dl',
        'yt_dlp': 'yt-dlp',
        'wget': 'wget',
        'pyautogui': 'pyautogui',
        'pyshorteners': 'pyshorteners',
        'pytz': 'pytz',
        'colorama': 'colorama',
        'pyfiglet': 'pyfiglet',
        'termcolor': 'termcolor',
        'tqdm': 'tqdm',
        'pyperclip': 'pyperclip',
        'cryptography': 'cryptography',
        'pycryptodome': 'pycryptodome',
        'psutil': 'psutil',
        'pyaes': 'pyaes',
        'rsa': 'rsa',
        'aiohttp': 'aiohttp',
        'asyncio': 'asyncio'
    }
    
    # إذا كان الاسم موجود في التعيين، نرجع القيمة
    if lib_name in lib_mapping:
        return lib_mapping[lib_name]
    
    # إذا كان الاسم يحتوي على شرطة سفلية، قد يكون اسم تثبيت صحيح
    if '_' in lib_name and lib_name not in BUILTIN_LIBS:
        return lib_name
    
    return None

# استخراج التوكن من الملف
def extract_token_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # أنماط البحث عن التوكن
        token_patterns = [
            r'["\']?([0-9]{8,11}:[A-Za-z0-9_-]{34,36})["\']?',
            r'bot_token\s*=\s*["\']([^"\']+)["\']',
            r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'token\s*=\s*["\']([^"\']+)["\']',
            r'TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'TeleBot\(["\']([^"\']+)["\']\)',
        ]
        
        for pattern in token_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                token = matches[0].strip()
                if (token.startswith('"') and token.endswith('"')) or (token.startswith("'") and token.endswith("'")):
                    token = token[1:-1]
                
                if len(token) > 30 and ':' in token:
                    print(f"✅ تم العثور على توكن: {'*' * 20}{token[-10:]}")
                    return token
        
        return None
        
    except Exception as e:
        print(f"خطأ في استخراج التوكن: {e}")
        return None

# الحصول على معلومات البوت من التوكن
def get_bot_info_from_token(token):
    try:
        import requests
        url = f"https://api.telegram.org/bot{token}/getMe"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                username = data['result'].get('username')
                if username:
                    return f"@{username}"
        return None
    except:
        return None

# استخراج معلومات البوت
def extract_bot_info(file_path):
    try:
        token = extract_token_from_file(file_path)
        
        if not token:
            print("❌ لم يتم العثور على توكن في الملف")
            return None
        
        # محاولات متعددة
        for attempt in range(3):
            bot_username = get_bot_info_from_token(token)
            if bot_username:
                print(f"✅ تم الحصول على يوزر البوت: {bot_username}")
                return bot_username
            time.sleep(1)
        
        print("❌ فشل في الحصول على معلومات البوت")
        return None
        
    except Exception as e:
        print(f"خطأ في استخراج معلومات البوت: {e}")
        return None

# تثبيت المكتبات (محسّن)
def install_libraries(libraries, chat_id, message_id):
    installed_libs = load_installed_libraries()
    to_install = []
    already_installed = []
    
    # فلترة المكتبات الحقيقية فقط
    real_libraries = []
    for lib in libraries:
        if lib and lib.strip():
            real_libraries.append(lib.strip())
    
    libraries = real_libraries
    
    print(f"📚 المكتبات المطلوبة بعد الفلترة: {libraries}")
    
    # فصل المكتبات
    for lib in libraries:
        if lib in installed_libs:
            already_installed.append(lib)
        else:
            to_install.append(lib)
    
    print(f"📦 سيتم تثبيت: {to_install}")
    print(f"✅ مثبتة مسبقاً: {already_installed}")
    
    # تحديث الرسالة
    status_msg = "🔧 <b>جاري تثبيت المكتبات المطلوبة...</b>\n\n"
    
    if already_installed:
        status_msg += f"✅ <b>{len(already_installed)} مكتبة مثبتة مسبقاً</b>\n"
    
    if to_install:
        status_msg += f"📦 <b>{len(to_install)} مكتبة جديدة</b>\n"
    
    try:
        bot.edit_message_text(status_msg, chat_id, message_id, parse_mode='HTML')
    except:
        pass
    
    # تثبيت المكتبات الجديدة
    installed = []
    failed = []
    
    if to_install:
        # تحديث التقدم
        progress_msg = status_msg + f"\n<b>جاري التثبيت...</b>"
        try:
            bot.edit_message_text(progress_msg, chat_id, message_id, parse_mode='HTML')
        except:
            pass
        
        # تثبيت جميع المكتبات في مرة واحدة لتسريع العملية
        try:
            install_cmd = [sys.executable, "-m", "pip", "install"] + to_install + ["--quiet", "--no-warn-script-location"]
            
            result = subprocess.run(
                install_cmd,
                timeout=120,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                for lib in to_install:
                    installed.append(lib)
                    save_installed_library(lib)
                print(f"✅ تم تثبيت جميع المكتبات بنجاح")
            else:
                # إذا فشل التثبيت الجماعي، نجرب كل مكتبة على حدة
                for lib in to_install:
                    try:
                        subprocess.run([
                            sys.executable, "-m", "pip", "install", lib, 
                            "--quiet", "--no-warn-script-location"
                        ], timeout=30, capture_output=True)
                        installed.append(lib)
                        save_installed_library(lib)
                        print(f"✅ تم تثبيت: {lib}")
                    except:
                        failed.append(lib)
                        print(f"❌ فشل تثبيت: {lib}")
            
        except Exception as e:
            print(f"❌ خطأ في التثبيت السريع: {e}")
            failed = to_install
    
    return installed, failed, already_installed

# تشغيل ملف البوت
def start_bot_process(script_path, chat_id, bot_id):
    try:
        # الحفاظ على الاسم الأصلي للملف
        original_dir = os.path.dirname(script_path)
        original_name = os.path.basename(script_path)
        
        # إنشاء نسخة بالاسم الأصلي
        original_script_path = os.path.join(original_dir, original_name)
        
        # تشغيل البوت
        process = subprocess.Popen(
            [sys.executable, original_script_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.PIPE,
            start_new_session=True
        )
        
        print(f"⚡ تم تشغيل البوت {bot_id}")
        return process
        
    except Exception as e:
        print(f"❌ خطأ في تشغيل الملف: {e}")
        return None

# إيقاف العملية
def stop_process_tree(process):
    try:
        if os.name == 'posix':
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            time.sleep(2)
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except:
                pass
        else:
            process.terminate()
            time.sleep(2)
            if process.poll() is None:
                process.kill()
        
        process.wait(timeout=5)
        return True
    except:
        return False

# إرسال ملف للمطور
def send_to_developer(file_path, user_info):
    try:
        with open(file_path, 'rb') as f:
            bot.send_document(
                DEVELOPER_ID,
                f,
                caption=f"📤 ملف بايثون جديد\n\n👤 من: {user_info}\n⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
    except Exception as e:
        print(f"❌ خطأ في إرسال الملف للمطور: {e}")

# ======= Handlers ======= #
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    upload_button = types.InlineKeyboardButton("📥 رفع ملف بايثون", callback_data='upload_py')
    
    if message.from_user.id == DEVELOPER_ID:
        files_button = types.InlineKeyboardButton("📂 البوتات النشطة", callback_data='dev_files')
        markup.add(upload_button, files_button)
    else:
        markup.add(upload_button)
        
    my_bots_button = types.InlineKeyboardButton("🤖 بوتاتي النشطة", callback_data='my_bots')
    markup.add(my_bots_button)

    welcome_msg = "⚡ <b>بوت استضافة بايثون المتقدم</b>\n\n"
    welcome_msg += "• رفع وتشغيل أي بوت تليجرام\n"
    welcome_msg += "• تثبيت المكتبات المطلوبة تلقائياً\n"
    welcome_msg += "• استخراج يوزر البوت تلقائياً\n"
    welcome_msg += "• سيرفر سريع ومستقر\n\n"
    welcome_msg += "<b>يمكنك رفع أي عدد من البوتات!</b>"

    bot.send_message(message.chat.id, welcome_msg, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == 'upload_py')
def upload_py_callback(call):
    bot.answer_callback_query(call.id, "📤 أرسل ملف البايثون")
    msg = "⚡ <b>أرسل ملف البايثون الآن (.py)</b>\n\n"
    msg += "سأقوم بـ:\n"
    msg += "1️⃣ تثبيت المكتبات المطلوبة\n"
    msg += "2️⃣ استخراج يوزر البوت\n"
    msg += "3️⃣ تشغيل البوت في سيرفر سريع"
    bot.send_message(call.message.chat.id, msg, parse_mode='HTML')

@bot.message_handler(content_types=['document'])
def handle_file(message):
    try:
        file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        file_name = message.document.file_name
        
        if not file_name.lower().endswith('.py'):
            bot.reply_to(message, "❌ <b>فقط ملفات PY مسموحة</b>", parse_mode='HTML')
            return
        
        # إرسال رسالة البدء
        wait_msg = bot.send_message(message.chat.id, "📥 <b>جاري تحميل الملف...</b>", parse_mode='HTML')
        
        # تحميل الملف
        downloaded_file = bot.download_file(file_info.file_path)
        
        # حفظ الملف بالاسم الأصلي (باستبدال الأحرار غير الآمنة)
        safe_name = re.sub(r'[^\w\-_.]', '_', file_name)
        script_path = os.path.join(uploaded_files_dir, safe_name)
        
        with open(script_path, 'wb') as f:
            f.write(downloaded_file)
        
        bot.edit_message_text("✅ <b>تم تحميل الملف</b>\n🔍 <b>جاري التحليل...</b>", 
                            message.chat.id, wait_msg.message_id, parse_mode='HTML')
        
        # إرسال للمطور
        user_info = f"{message.from_user.first_name}"
        if message.from_user.username:
            user_info += f" (@{message.from_user.username})"
        send_to_developer(script_path, user_info)
        
        # بدء المعالجة
        process_file(message, script_path, file_name, wait_msg.message_id)
        
    except Exception as e:
        error_msg = f"❌ <b>حدث خطأ:</b>\n\n<code>{str(e)[:300]}</code>"
        bot.reply_to(message, error_msg, parse_mode='HTML')

def process_file(message, script_path, original_name, wait_msg_id):
    """معالجة الملف في thread منفصل"""
    
    def processing_thread():
        try:
            # إنشاء معرف فريد للبوت
            bot_id = f"{message.chat.id}_{int(time.time())}_{os.urandom(4).hex()}"
            
            # المرحلة 1: كشف المكتبات
            bot.edit_message_text("🔍 <b>جاري فحص المكتبات المطلوبة...</b>", 
                                message.chat.id, wait_msg_id, parse_mode='HTML')
            
            required_libs = detect_required_libraries(script_path)
            
            # المرحلة 2: تثبيت المكتبات
            if required_libs:
                libs_text = ", ".join(required_libs[:5])
                if len(required_libs) > 5:
                    libs_text += f" و{len(required_libs)-5} أخرى"
                
                progress_text = f"🔧 <b>تم اكتشاف {len(required_libs)} مكتبة مطلوبة</b>\n\n{libs_text}\n\n⚡ <b>جاري التثبيت...</b>"
                bot.edit_message_text(progress_text, message.chat.id, wait_msg_id, parse_mode='HTML')
                
                installed, failed, already_installed = install_libraries(
                    required_libs, message.chat.id, wait_msg_id
                )
                
                # عرض نتيجة التثبيت
                result_msg = "✅ <b>تم تثبيت المكتبات</b>\n\n"
                if already_installed:
                    result_msg += f"📚 <b>مثبتة مسبقاً:</b> {len(already_installed)}\n"
                if installed:
                    result_msg += f"📦 <b>مثبتة حديثاً:</b> {len(installed)}\n"
                if failed:
                    result_msg += f"⚠️ <b>فشل تثبيت:</b> {len(failed)}\n"
                
                bot.edit_message_text(
                    result_msg + "\n👤 <b>جاري استخراج يوزر البوت...</b>",
                    message.chat.id, wait_msg_id, parse_mode='HTML'
                )
            else:
                bot.edit_message_text(
                    "✅ <b>لا توجد مكتبات خارجية مطلوبة</b>\n👤 <b>جاري استخراج يوزر البوت...</b>",
                    message.chat.id, wait_msg_id, parse_mode='HTML'
                )
            
            time.sleep(1)
            
            # المرحلة 3: استخراج يوزر البوت
            bot.edit_message_text("🔐 <b>جاري استخراج يوزر البوت...</b>", 
                                message.chat.id, wait_msg_id, parse_mode='HTML')
            
            bot_username = extract_bot_info(script_path)
            
            if bot_username:
                success_text = f"✅ <b>تم استخراج معلومات البوت بنجاح!</b>\n\n👤 <b>يوزر البوت:</b> {bot_username}\n\n⚡ <b>جاري التشغيل...</b>"
                bot.edit_message_text(success_text, message.chat.id, wait_msg_id, parse_mode='HTML')
            else:
                bot.edit_message_text(
                    "⚠️ <b>يوزر البوت:</b> غير معروف\n\n⚡ <b>جاري التشغيل...</b>",
                    message.chat.id, wait_msg_id, parse_mode='HTML'
                )
            
            time.sleep(2)
            
            # المرحلة 4: تشغيل البوت
            bot.edit_message_text("🚀 <b>جاري تشغيل البوت في سيرفر سريع...</b>", 
                                message.chat.id, wait_msg_id, parse_mode='HTML')
            
            process = start_bot_process(script_path, message.chat.id, bot_id)
            
            if process:
                # الانتظار للتأكد من تشغيل البوت
                time.sleep(3)
                
                # التحقق إذا كانت العملية لا تزال تعمل
                if process.poll() is None:
                    # إضافة البوت إلى القائمة النشطة
                    if message.chat.id not in active_bots:
                        active_bots[message.chat.id] = []
                    
                    bot_info = {
                        'id': bot_id,
                        'process': process,
                        'file_path': script_path,
                        'original_name': original_name,
                        'bot_username': bot_username,
                        'start_time': datetime.now()
                    }
                    
                    active_bots[message.chat.id].append(bot_info)
                    
                    # مراقبة العملية في الخلفية
                    def monitor_process():
                        try:
                            process.wait(timeout=86400)
                        except:
                            pass
                        if message.chat.id in active_bots:
                            for i, b in enumerate(active_bots[message.chat.id]):
                                if b['id'] == bot_id:
                                    del active_bots[message.chat.id][i]
                                    if not active_bots[message.chat.id]:
                                        del active_bots[message.chat.id]
                                    break
                    
                    threading.Thread(target=monitor_process, daemon=True).start()
                    
                    # بناء رسالة النجاح النهائية
                    success_message = "✅ <b>تم تشغيل البوت بنجاح</b>\n\n"
                    
                    if bot_username:
                        success_message += f"👤 <b>يوزر البوت:</b> {bot_username}\n\n"
                    
                    success_message += f"📄 <b>الملف:</b> <code>{original_name}</code>\n\n"
                    success_message += "🚀 <b>البوت يعمل الآن في سيرفر سريع!</b>\n\n"
                    success_message += "🛑 <b>اضغط على زر إيقاف البوت إذا تريد</b>"
                    
                    # إضافة زر إيقاف البوت
                    markup = types.InlineKeyboardMarkup(row_width=1)
                    stop_button = types.InlineKeyboardButton("🛑 إيقاف هذا البوت", callback_data=f'stop_my_bot_{bot_id}')
                    markup.add(stop_button)
                    
                    # إرسال الرسالة النهائية
                    bot.delete_message(message.chat.id, wait_msg_id)
                    bot.send_message(message.chat.id, success_message, 
                                   reply_markup=markup, parse_mode='HTML')
                    
                    # إرسال إشعار للمطور
                    try:
                        if message.chat.id != DEVELOPER_ID:
                            notification = "🚀 <b>بوت جديد تم تشغيله</b>\n\n"
                            notification += f"👤 المستخدم: {message.from_user.first_name}\n"
                            notification += f"🆔 ID: {message.chat.id}\n"
                            notification += f"📄 الملف: {original_name}\n"
                            if bot_username:
                                notification += f"🔗 البوت: {bot_username}"
                            
                            bot.send_message(DEVELOPER_ID, notification, parse_mode='HTML')
                    except:
                        pass
                    
                else:
                    error_msg = "❌ <b>البوت توقف بعد التشغيل</b>\n\n"
                    error_msg += "<b>الأسباب المحتملة:</b>\n"
                    error_msg += "• أخطاء في الكود\n"
                    error_msg += "• التوكن غير صحيح\n"
                    error_msg += "• مكتبات مفقودة"
                    
                    bot.delete_message(message.chat.id, wait_msg_id)
                    bot.send_message(message.chat.id, error_msg, parse_mode='HTML')
                
            else:
                error_msg = "❌ <b>فشل في تشغيل البوت</b>\n\n"
                error_msg += "<b>الأسباب المحتملة:</b>\n"
                error_msg += "• أخطاء في الكود\n"
                error_msg += "• مسار ملف غير صحيح\n"
                error_msg += "• مشاكل في النظام"
                
                bot.delete_message(message.chat.id, wait_msg_id)
                bot.send_message(message.chat.id, error_msg, parse_mode='HTML')
                
        except Exception as e:
            error_msg = f"❌ <b>خطأ في المعالجة:</b>\n\n<code>{str(e)[:500]}</code>"
            try:
                bot.delete_message(message.chat.id, wait_msg_id)
                bot.send_message(message.chat.id, error_msg, parse_mode='HTML')
            except:
                pass
    
    # تشغيل thread المعالجة
    thread = threading.Thread(target=processing_thread)
    thread.daemon = True
    thread.start()

# باقي الhandlers (dev_files, my_bots, stop_specific_bot, stop_all_bots, stop_my_bot, stop_my_all)
# نستخدم نفس الhandlers من الكود السابق مع تعديل بسيط

@bot.callback_query_handler(func=lambda call: call.data == 'dev_files')
def dev_files_callback(call):
    if call.from_user.id != DEVELOPER_ID:
        bot.answer_callback_query(call.id, "❌ هذا الزر للمطور فقط")
        return
    
    bot.answer_callback_query(call.id, "📂 جاري جلب البوتات النشطة...")
    
    all_bots = []
    for chat_id, bots_list in active_bots.items():
        for bot_info in bots_list:
            all_bots.append((chat_id, bot_info))
    
    if not all_bots:
        bot.send_message(call.message.chat.id, "📭 <b>لا توجد بوتات نشطة حالياً</b>", parse_mode='HTML')
        return
    
    all_bots.sort(key=lambda x: x[1]['start_time'], reverse=True)
    
    active_list = "🤖 <b>البوتات النشطة:</b>\n\n"
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    for chat_id, bot_info in all_bots[:20]:
        file_name = bot_info['original_name'][:20]
        runtime = datetime.now() - bot_info['start_time']
        hours, remainder = divmod(int(runtime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        active_list += f"🆔 <b>ID:</b> {bot_info['id'][:8]}\n"
        active_list += f"👤 <b>المستخدم:</b> {chat_id}\n"
        active_list += f"📄 <b>الملف:</b> {file_name}\n"
        if bot_info.get('bot_username'):
            active_list += f"🔗 <b>البوت:</b> {bot_info['bot_username']}\n"
        active_list += f"⏱️ <b>المدة:</b> {hours}:{minutes:02d}:{seconds:02d}\n"
        active_list += "─" * 30 + "\n"
        
        stop_button = types.InlineKeyboardButton(
            f"🛑 {bot_info['id'][:8]}",
            callback_data=f'stop_specific_{chat_id}_{bot_info["id"]}'
        )
        markup.add(stop_button)
    
    if len(all_bots) > 20:
        active_list += f"\n<b>... و{len(all_bots) - 20} بوت آخر</b>"
    
    stop_all_button = types.InlineKeyboardButton("🛑 إيقاف جميع البوتات", callback_data='stop_all_bots')
    markup.add(stop_all_button)
    
    bot.send_message(call.message.chat.id, active_list, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == 'my_bots')
def my_bots_callback(call):
    chat_id = call.message.chat.id
    
    if chat_id not in active_bots or not active_bots[chat_id]:
        bot.answer_callback_query(call.id, "📭 لا توجد بوتات نشطة")
        return
    
    bots_list = active_bots[chat_id]
    
    my_bots_msg = f"🤖 <b>بوتاتك النشطة:</b> ({len(bots_list)})\n\n"
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    for i, bot_info in enumerate(bots_list, 1):
        file_name = bot_info['original_name'][:20]
        runtime = datetime.now() - bot_info['start_time']
        hours, remainder = divmod(int(runtime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        my_bots_msg += f"<b>{i}.</b> 📄 {file_name}\n"
        if bot_info.get('bot_username'):
            my_bots_msg += f"   👤 {bot_info['bot_username']}\n"
        my_bots_msg += f"   ⏱️ {hours}:{minutes:02d}:{seconds:02d}\n"
        
        stop_button = types.InlineKeyboardButton(
            f"🛑 إيقاف {i}",
            callback_data=f'stop_my_bot_{bot_info["id"]}'
        )
        markup.add(stop_button)
    
    stop_all_button = types.InlineKeyboardButton("🛑 إيقاف جميع بوتاتي", callback_data='stop_my_all')
    markup.add(stop_all_button)
    
    bot.answer_callback_query(call.id, f"📊 لديك {len(bots_list)} بوت نشط")
    bot.send_message(chat_id, my_bots_msg, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('stop_specific_'))
def stop_specific_bot(call):
    if call.from_user.id != DEVELOPER_ID:
        bot.answer_callback_query(call.id, "❌ هذا الزر للمطور فقط")
        return
    
    parts = call.data.split('_')
    chat_id = int(parts[2])
    bot_id = parts[3]
    
    if chat_id in active_bots:
        for i, bot_info in enumerate(active_bots[chat_id]):
            if bot_info['id'] == bot_id:
                process = bot_info['process']
                if stop_process_tree(process):
                    del active_bots[chat_id][i]
                    if not active_bots[chat_id]:
                        del active_bots[chat_id]
                    
                    bot.answer_callback_query(call.id, "✅ تم إيقاف البوت")
                    dev_files_callback(call)
                else:
                    bot.answer_callback_query(call.id, "❌ فشل في إيقاف البوت")
                return
    
    bot.answer_callback_query(call.id, "❌ البوت غير موجود")

@bot.callback_query_handler(func=lambda call: call.data == 'stop_all_bots')
def stop_all_bots_callback(call):
    if call.from_user.id != DEVELOPER_ID:
        bot.answer_callback_query(call.id, "❌ هذا الزر للمطور فقط")
        return
    
    stopped_count = 0
    for chat_id in list(active_bots.keys()):
        for bot_info in active_bots[chat_id]:
            try:
                process = bot_info['process']
                if process.poll() is None:
                    stop_process_tree(process)
                    stopped_count += 1
            except:
                pass
    
    active_bots.clear()
    bot.answer_callback_query(call.id, f"✅ تم إيقاف {stopped_count} بوت")
    
    bot.edit_message_text(
        f"✅ <b>تم إيقاف جميع البوتات ({stopped_count})</b>",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('stop_my_bot_'))
def stop_my_bot_callback(call):
    chat_id = call.message.chat.id
    bot_id = call.data.split('_')[3]
    
    if chat_id in active_bots:
        for i, bot_info in enumerate(active_bots[chat_id]):
            if bot_info['id'] == bot_id:
                process = bot_info['process']
                if stop_process_tree(process):
                    del active_bots[chat_id][i]
                    if not active_bots[chat_id]:
                        del active_bots[chat_id]
                    
                    bot.answer_callback_query(call.id, "✅ تم إيقاف البوت")
                    
                    bot.edit_message_text(
                        "✅ <b>تم إيقاف البوت بنجاح</b>",
                        chat_id,
                        call.message.message_id,
                        parse_mode='HTML'
                    )
                else:
                    bot.answer_callback_query(call.id, "❌ فشل في إيقاف البوت")
                return
    
    bot.answer_callback_query(call.id, "❌ البوت غير موجود")

@bot.callback_query_handler(func=lambda call: call.data == 'stop_my_all')
def stop_my_all_callback(call):
    chat_id = call.message.chat.id
    
    if chat_id in active_bots:
        stopped_count = 0
        for bot_info in active_bots[chat_id]:
            try:
                process = bot_info['process']
                if process.poll() is None:
                    stop_process_tree(process)
                    stopped_count += 1
            except:
                pass
        
        del active_bots[chat_id]
        bot.answer_callback_query(call.id, f"✅ تم إيقاف {stopped_count} بوت")
        
        bot.edit_message_text(
            f"✅ <b>تم إيقاف جميع بوتاتك ({stopped_count})</b>",
            chat_id,
            call.message.message_id,
            parse_mode='HTML'
        )
    else:
        bot.answer_callback_query(call.id, "❌ لا توجد بوتات نشطة")

@bot.message_handler(commands=['libraries'])
def show_libraries(message):
    libraries = load_installed_libraries()
    
    if not libraries:
        bot.reply_to(message, "📭 <b>لم يتم تثبيت أي مكتبات بعد</b>", parse_mode='HTML')
        return
    
    libs_list = "📚 <b>المكتبات المثبتة:</b>\n\n"
    count = 0
    for lib, install_time in libraries.items():
        count += 1
        libs_list += f"• <code>{lib}</code>\n"
        if count >= 30:
            break
    
    if len(libraries) > 30:
        libs_list += f"\n... و {len(libraries) - 30} مكتبة أخرى"
    
    libs_list += f"\n\n<b>الإجمالي:</b> {len(libraries)} مكتبة"
    
    bot.reply_to(message, libs_list, parse_mode='HTML')

@bot.message_handler(commands=['stats'])
def show_stats(message):
    total_bots = sum(len(bots) for bots in active_bots.values())
    total_users = len(active_bots)
    
    stats_msg = "📊 <b>إحصائيات البوت:</b>\n\n"
    stats_msg += f"👥 <b>المستخدمون النشطون:</b> {total_users}\n"
    stats_msg += f"🤖 <b>البوتات النشطة:</b> {total_bots}\n"
    stats_msg += f"📚 <b>المكتبات المثبتة:</b> {len(load_installed_libraries())}\n"
    stats_msg += "⚡ <b>الحالة:</b> تشغيل سريع"
    
    bot.reply_to(message, stats_msg, parse_mode='HTML')

@bot.message_handler(commands=['clean'])
def clean_files(message):
    try:
        count = 0
        for filename in os.listdir(uploaded_files_dir):
            file_path = os.path.join(uploaded_files_dir, filename)
            if os.path.isfile(file_path):
                if time.time() - os.path.getmtime(file_path) > 3600:
                    os.remove(file_path)
                    count += 1
        
        bot.reply_to(message, f"🧹 <b>تم تنظيف {count} ملف قديم</b>", parse_mode='HTML')
    except Exception as e:
        bot.reply_to(message, f"❌ <b>خطأ في التنظيف:</b>\n\n<code>{str(e)}</code>", parse_mode='HTML')

# ======= تشغيل البوت ======= #
if __name__ == '__main__':
    print("=" * 70)
    print("🚀 بوت استضافة بايثون المتقدم يعمل...")
    print(f"🔑 التوكن: {BOT_TOKEN[:10]}...{BOT_TOKEN[-10:]}")
    print(f"👑 المطور: {DEVELOPER_ID}")
    print("=" * 70)
    print("\n✅ الإصلاحات المطبقة:")
    print("   1. حفظ أسماء الملفات الأصلية (بدون تغيير)")
    print("   2. فلترة المكتبات الحقيقية فقط")
    print("   3. تنسيق رسالة النجاح الجديد")
    print("   4. إزالة اختبار البوت الإضافي")
    print("=" * 70)
    
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ خطأ: {e}")
        time.sleep(5)
