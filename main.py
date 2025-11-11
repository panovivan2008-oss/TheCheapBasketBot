# main.py
import os
import sqlite3
import datetime
import time
import logging
from flask import Flask, request
import telebot
from telebot import types
from dotenv import load_dotenv

load_dotenv()

# ===== Logging =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ===== Настройки =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # https://your-service.onrender.com/<BOT_TOKEN>

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в окружении!")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ===== Database path =====
DB_PATH = os.path.join(os.path.dirname(__file__), "subscribers.db")

# ===== Broadcast lock =====
is_broadcasting = False

# ===== Database helpers =====
def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id INTEGER PRIMARY KEY,
            language TEXT DEFAULT '',
            marketing_consent INTEGER DEFAULT 0,
            consent_ts TEXT
        )
        """)
        conn.commit()
        conn.close()
        logging.info("init_db: база инициализирована")
    except Exception as e:
        logging.exception(f"init_db: ошибка при инициализации базы: {e}")
        raise

def is_subscribed(user_id: int) -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM subscribers WHERE user_id = ?", (user_id,))
        res = cur.fetchone()
        conn.close()
        return res is not None
    except Exception as e:
        logging.exception(f"is_subscribed: ошибка DB для user {user_id}: {e}")
        return False

def add_subscriber(user_id: int):
    now = datetime.datetime.utcnow().isoformat()
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO subscribers (user_id, language, marketing_consent, consent_ts)
            VALUES (?, '', 0, ?)
            ON CONFLICT(user_id) DO NOTHING
        """, (user_id, now))
        conn.commit()
        conn.close()
        logging.info(f"add_subscriber: добавлен подписчик {user_id}")
    except Exception as e:
        logging.exception(f"add_subscriber: ошибка при добавлении {user_id}: {e}")

def set_language(user_id: int, language: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE subscribers SET language=? WHERE user_id=?", (language, user_id))
        conn.commit()
        conn.close()
        logging.info(f"set_language: user={user_id} language={language}")
    except Exception as e:
        logging.exception(f"set_language: ошибка для user={user_id}: {e}")

def get_user_language(user_id: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT language FROM subscribers WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row and row[0] else ""
    except Exception as e:
        logging.exception(f"get_user_language: ошибка для user={user_id}: {e}")
        return ""

def set_marketing_consent(user_id: int, consent: int):
    now = datetime.datetime.utcnow().isoformat()
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE subscribers SET marketing_consent=?, consent_ts=? WHERE user_id=?", (consent, now, user_id))
        conn.commit()
        conn.close()
        logging.info(f"set_marketing_consent: user={user_id} consent={consent}")
    except Exception as e:
        logging.exception(f"set_marketing_consent: ошибка для user={user_id}: {e}")

def remove_subscriber(user_id: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM subscribers WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()
        logging.info(f"remove_subscriber: удалён user={user_id}")
    except Exception as e:
        logging.exception(f"remove_subscriber: ошибка при удалении user={user_id}: {e}")

def get_all_subscribers(marketing_only=False):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        if marketing_only:
            cur.execute("SELECT user_id FROM subscribers WHERE marketing_consent=1")
        else:
            cur.execute("SELECT user_id FROM subscribers")
        rows = cur.fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        logging.exception(f"get_all_subscribers: ошибка при чтении базы: {e}")
        return []

# ===== Keyboards =====
def kb_main(lang=""):
    """Главное меню с кнопкой подписки/отписки и кнопкой маркетинга"""
    _, kb_after = get_keyboards_by_lang(lang)
    return kb_after

def kb_languages_markup():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🇷🇺 Русский", "🇬🇧 Английский")
    kb.add("🇵🇱 Польский", "🇪🇸 Испанский")
    kb.add("🇩🇪 Немецкий", "🇫🇷 Французский")
    kb.add("🇰🇿 Казахский", "🇺🇦 Украинский")
    return kb

def kb_marketing_bottom():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add("✅ Разрешаю рассылку", "❌ Не хочу рассылку")
    kb.add("Изменить позже")
    return kb

def get_keyboards_by_lang(lang_code):
    before = types.ReplyKeyboardMarkup(resize_keyboard=True)
    after = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang_code == "🇬🇧 Английский":
        before.add("✅ Subscribe"); after.add("❌ Unsubscribe")
    elif lang_code == "🇵🇱 Польский":
        before.add("✅ Subskrybuj"); after.add("❌ Anuluj subskrypcję")
    elif lang_code == "🇪🇸 Испанский":
        before.add("✅ Suscribirse"); after.add("❌ Cancelar suscripción")
    elif lang_code == "🇩🇪 Немецкий":
        before.add("✅ Abonnieren"); after.add("❌ Abbestellen")
    elif lang_code == "🇫🇷 Французский":
        before.add("✅ S’abonner"); after.add("❌ Se désabonner")
    elif lang_code == "🇰🇿 Казахский":
        before.add("✅ Жазылу"); after.add("❌ Жазылымнан бас тарту")
    elif lang_code == "🇺🇦 Украинский":
        before.add("✅ Підписатися"); after.add("❌ Відписатися")
    else:
        before.add("✅ Подписаться"); after.add("❌ Отписаться")
    return before, after

# ===== Presentations =====
PRESENTATIONS = {
    "🇷🇺 Русский": "🇷🇺 Вы выбрали русский язык!\n\n📦 Отправьте мне ссылку на товар — я буду отслеживать его цену и сообщу, когда она упадёт 💰\n🕵️ Также проверю этот товар на других сайтах, чтобы найти где дешевле!\n\nПоддерживаемые сайты:\n• Allegro\n• Temu\n• AliExpress\n• Banggood\n• Alibaba\n\nКогда найду дешевле или цена упадёт — сразу уведомлю вас 📲",
    "🇬🇧 Английский": "🇬🇧 You selected English!\n\n📦 Send me a product link — I’ll track its price and notify you when it drops 💰\n🕵️ I’ll also check this product on other sites to find where it’s cheaper!\n\nSupported sites:\n• Allegro\n• Temu\n• AliExpress\n• Banggood\n• Alibaba\n\nWhen I find a lower price or a drop — I’ll let you know 📲",
    # добавь остальные языки аналогично
}

# ===== Handlers =====
@bot.message_handler(commands=["start"])
def handle_start(message):
    uid = message.from_user.id
    if is_subscribed(uid):
        lang = get_user_language(uid) or "🇷🇺 Русский"
        bot.send_message(uid, "Вы уже подписаны ✅", reply_markup=kb_main(lang))
    else:
        bot.send_message(uid, "Привет! Нажмите кнопку ниже, чтобы подписаться на уведомления о товарах.", reply_markup=kb_main())

@bot.message_handler(func=lambda m: m.text in list(PRESENTATIONS.keys()))
def handle_language(message):
    uid = message.from_user.id
    lang = message.text
    if not is_subscribed(uid):
        add_subscriber(uid)
    set_language(uid, lang)
    bot.send_message(uid, PRESENTATIONS.get(lang, "Язык сохранён."), reply_markup=kb_main(lang))
    time.sleep(0.2)
    bot.send_message(uid, "Хотите получать рекламные уведомления? (можно изменить позже)", reply_markup=kb_marketing_bottom())

@bot.message_handler(func=lambda m: m.text in [
    "✅ Подписаться", "✅ Subscribe", "✅ Subskrybuj", "✅ Suscribirse",
    "✅ Abonnieren", "✅ S’abonner", "✅ Жазылу", "✅ Підписатися"
])
def handle_subscribe(message):
    uid = message.from_user.id
    if not is_subscribed(uid):
        add_subscriber(uid)
    lang = get_user_language(uid) or ""
    bot.send_message(uid, "Вы подписаны ✅", reply_markup=kb_main(lang))

@bot.message_handler(func=lambda m: m.text in [
    "❌ Отписаться", "❌ Unsubscribe", "❌ Anuluj subskrypcję", "❌ Cancelar suscripción",
    "❌ Abbestellen", "❌ Se désabonner", "❌ Жазылымнан бас тарту", "❌ Відписатися"
])
def handle_unsubscribe(message):
    uid = message.from_user.id
    remove_subscriber(uid)
    bot.send_message(uid, "Вы отписались 🔕", reply_markup=kb_main())

@bot.message_handler(func=lambda m: m.text in ["✅ Разрешаю рассылку", "❌ Не хочу рассылку", "Изменить позже"])
def handle_marketing_choice(message):
    uid = message.from_user.id
    lang = get_user_language(uid)
    if message.text == "✅ Разрешаю рассылку":
        set_marketing_consent(uid, 1)
        bot.send_message(uid, "Вы согласились на рассылку ✅", reply_markup=kb_main(lang))
    elif message.text == "❌ Не хочу рассылку":
        set_marketing_consent(uid, 0)
        bot.send_message(uid, "Вы отказались от рассылки ❌", reply_markup=kb_main(lang))
    else:
        bot.send_message(uid, "Ок — вы можете изменить своё решение о рассылке в любое время:", reply_markup=kb_marketing_bottom())

# ===== Admin commands =====
@bot.message_handler(commands=["count"])
def cmd_count(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ У вас нет доступа")
        return
    bot.reply_to(message, f"📊 Подписчиков: {len(get_all_subscribers())}")

@bot.message_handler(commands=["subscribers"])
def cmd_subscribers(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ У вас нет доступа")
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id, language, marketing_consent FROM subscribers")
    rows = cur.fetchall()
    conn.close()
    text = "Список подписчиков:\n\n" + "\n".join(f"{r[0]} | {r[1] or '—'} | consent={r[2]}" for r in rows)
    bot.reply_to(message, text)

@bot.message_handler(commands=["broadcast"])
def safe_broadcast(message):
    global is_broadcasting
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ У вас нет доступа")
        return
    if is_broadcasting:
        bot.reply_to(message, "⛔ Рассылка уже выполняется. Подождите.")
        return

    text = message.text.replace("/broadcast", "", 1).strip()
    if not text:
        bot.reply_to(message, "Укажите текст после /broadcast")
        return

    users = get_all_subscribers(marketing_only=True)
    failed = []
    removed_count = 0
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    batch_size = 50
    pause = 1
    is_broadcasting = True
    try:
        for i in range(0, len(users), batch_size):
            batch = users[i:i+batch_size]
            for uid in batch:
                for chunk in chunks:
                    try:
                        bot.send_message(uid, chunk)
                    except Exception as e:
                        logging.warning(f"safe_broadcast: ошибка отправки user={uid}: {e}")
                        failed.append({"user_id": uid, "error": str(e)})
                        try:
                            remove_subscriber(uid)
                            removed_count += 1
                        except Exception:
                            logging.exception(f"safe_broadcast: ошибка удаления user={uid}")
            time.sleep(pause)
        bot.reply_to(message, f"✅ Рассылка завершена. Не дошло: {len(failed)}\n🗑 Удалено: {removed_count}")
    finally:
        is_broadcasting = False

@bot.message_handler(commands=["status"])
def cmd_status(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ У вас нет доступа")
        return
    bot.reply_to(message, f"Бот живой. Подписчиков: {len(get_all_subscribers())}")

# ===== Flask webhook =====
@app.route("/", methods=["GET"])
def index():
    return "OK", 200

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        json_str = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
    except Exception as e:
        logging.exception(f"webhook: ошибка при обработке update: {e}")
        return "Error", 500
    return "OK", 200

# ===== Startup =====
if __name__ == "__main__":
    init_db()
    if WEBHOOK_URL:
        try:
            bot.remove_webhook()
        except Exception:
            pass
        ok = bot.set_webhook(url=WEBHOOK_URL)
        logging.info(f"set_webhook -> {ok} WEBHOOK_URL: {WEBHOOK_URL}")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
