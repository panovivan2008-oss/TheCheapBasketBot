# main.py
import os
import sqlite3
from flask import Flask, request
import telebot
from telebot import types
from dotenv import load_dotenv
import datetime
import time
import json

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # https://your-service.onrender.com/<BOT_TOKEN>

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в окружении!")

bot = telebot.TeleBot(BOT_TOKEN)

# ---------- Database helpers ----------
DB_PATH = "subscribers.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS subscribers (
        user_id INTEGER PRIMARY KEY,
        language TEXT,
        marketing_consent INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()

def is_subscribed(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM subscribers WHERE user_id = ?", (user_id,))
    res = cur.fetchone()
    conn.close()
    return res is not None

def add_subscriber(user_id: int, marketing_consent: bool = False):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    cur.execute("""
        INSERT INTO subscribers (user_id, language, marketing_consent)
        VALUES (?, '', ?)
        ON CONFLICT(user_id) DO UPDATE SET marketing_consent=excluded.marketing_consent
    """, (user_id, 1 if marketing_consent else 0))
    conn.commit()
    conn.close()

def set_language(user_id: int, language: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE subscribers SET language = ? WHERE user_id = ?", (language, user_id))
    conn.commit()
    conn.close()

def set_marketing_consent(user_id: int, consent: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE subscribers SET marketing_consent = ? WHERE user_id = ?", (consent, user_id))
    conn.commit()
    conn.close()

def remove_subscriber(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM subscribers WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_all_subscribers():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers")
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]

# ---------- Keyboards ----------
kb_before = types.ReplyKeyboardMarkup(resize_keyboard=True)
kb_before.add(types.KeyboardButton("✅ Подписаться"))

kb_after = types.ReplyKeyboardMarkup(resize_keyboard=True)
kb_after.add(types.KeyboardButton("❌ Отписаться"))

kb_languages = types.ReplyKeyboardMarkup(resize_keyboard=True)
kb_languages.add("🇷🇺 Русский", "🇬🇧 Английский")
kb_languages.add("🇵🇱 Польский", "🇪🇸 Испанский")
kb_languages.add("🇩🇪 Немецкий", "🇫🇷 Французский")
kb_languages.add("🇰🇿 Казахский", "🇺🇦 Украинский")

# ---------- Dynamic Keyboards ----------
def get_keyboards(language):
    if language == "🇬🇧 Английский":
        before = types.ReplyKeyboardMarkup(resize_keyboard=True); before.add("✅ Subscribe")
        after = types.ReplyKeyboardMarkup(resize_keyboard=True); after.add("❌ Unsubscribe")
    elif language == "🇵🇱 Польский":
        before = types.ReplyKeyboardMarkup(resize_keyboard=True); before.add("✅ Subskrybuj")
        after = types.ReplyKeyboardMarkup(resize_keyboard=True); after.add("❌ Anuluj subskrypcję")
    elif language == "🇪🇸 Испанский":
        before = types.ReplyKeyboardMarkup(resize_keyboard=True); before.add("✅ Suscribirse")
        after = types.ReplyKeyboardMarkup(resize_keyboard=True); after.add("❌ Cancelar suscripción")
    elif language == "🇩🇪 Немецкий":
        before = types.ReplyKeyboardMarkup(resize_keyboard=True); before.add("✅ Abonnieren")
        after = types.ReplyKeyboardMarkup(resize_keyboard=True); after.add("❌ Abbestellen")
    elif language == "🇫🇷 Французский":
        before = types.ReplyKeyboardMarkup(resize_keyboard=True); before.add("✅ S’abonner")
        after = types.ReplyKeyboardMarkup(resize_keyboard=True); after.add("❌ Se désabonner")
    elif language == "🇰🇿 Казахский":
        before = types.ReplyKeyboardMarkup(resize_keyboard=True); before.add("✅ Жазылу")
        after = types.ReplyKeyboardMarkup(resize_keyboard=True); after.add("❌ Жазылымнан бас тарту")
    elif language == "🇺🇦 Украинский":
        before = types.ReplyKeyboardMarkup(resize_keyboard=True); before.add("✅ Підписатися")
        after = types.ReplyKeyboardMarkup(resize_keyboard=True); after.add("❌ Відписатися")
    else:
        before = types.ReplyKeyboardMarkup(resize_keyboard=True); before.add("✅ Подписаться")
        after = types.ReplyKeyboardMarkup(resize_keyboard=True); after.add("❌ Отписаться")
    return before, after

# ---------- Handlers ----------
@bot.message_handler(commands=["start"])
def handle_start(message):
    uid = message.from_user.id
    if is_subscribed(uid):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT language FROM subscribers WHERE user_id = ?", (uid,))
        row = cur.fetchone()
        conn.close()
        user_lang = row[0] if row and row[0] else "🇷🇺 Русский"
        _, kb_after_lang = get_keyboards(user_lang)
        greetings = {
            "🇷🇺 Русский": "Вы уже подписаны ✅",
            "🇬🇧 Английский": "You are already subscribed ✅",
            "🇵🇱 Польский": "Już jesteś zapisany ✅",
            "🇪🇸 Испанский": "Ya estás suscrito ✅",
            "🇩🇪 Немецкий": "Du bist bereits abonniert ✅",
            "🇫🇷 Французский": "Vous êtes déjà abonné ✅",
            "🇰🇿 Казахский": "Сіз бұрыннан жазылдыңыз ✅",
            "🇺🇦 Украинский": "Ви вже підписані ✅"
        }
        bot.send_message(uid, greetings.get(user_lang, "Вы уже подписаны ✅"), reply_markup=kb_after_lang)
    else:
        kb_before_lang, _ = get_keyboards("🇷🇺 Русский")
        bot.send_message(uid, "Привет! Нажмите кнопку ниже, чтобы подписаться на уведомления о товарах.", reply_markup=kb_before_lang)

@bot.message_handler(commands=["help"])
def handle_help(message):
    text = (
        "📌 Команды:\n"
        "/start - старт\n"
        "✅ Подписаться - подписаться\n"
        "❌ Отписаться - отписаться\n"
        "Выбор языка — нажать флаг\n"
        "/count - количество подписчиков (только админ)\n"
        "/subscribers - список подписчиков (только админ)\n"
        "/broadcast <текст> - рассылка всем подписчикам (только админ)\n"
        "/status - диагностика (только админ)\n"
    )
    bot.send_message(message.from_user.id, text)

@bot.message_handler(func=lambda m: m.text == "✅ Подписаться")
def handle_subscribe(message):
    uid = message.from_user.id
    if is_subscribed(uid):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT language FROM subscribers WHERE user_id = ?", (uid,))
        row = cur.fetchone()
        conn.close()
        user_lang = row[0] if row and row[0] else "🇷🇺 Русский"
        kb_before_lang, _ = get_keyboards(user_lang)
        bot.send_message(uid, "Вы уже подписаны ✅", reply_markup=kb_before_lang)
        return

    add_subscriber(uid)

    # Inline кнопки согласия на маркетинг
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ Да, хочу рекламу", callback_data=f"marketing_yes:{uid}"),
        types.InlineKeyboardButton("❌ Нет, только уведомления", callback_data=f"marketing_no:{uid}")
    )
    bot.send_message(uid, "Хотите получать рекламные уведомления? (можно изменить позже)", reply_markup=kb)

    # Кнопки выбора языка
    kb_langs = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb_langs.add("🇷🇺 Русский", "🇬🇧 Английский")
    kb_langs.add("🇵🇱 Польский", "🇪🇸 Испанский")
    kb_langs.add("🇩🇪 Немецкий", "🇫🇷 Французский")
    kb_langs.add("🇰🇿 Казахский", "🇺🇦 Украинский")
    bot.send_message(uid, "Выберите язык:", reply_markup=kb_langs)

# Выбор языка
@bot.message_handler(func=lambda m: m.text in [
    "🇷🇺 Русский","🇬🇧 Английский","🇵🇱 Польский","🇪🇸 Испанский",
    "🇩🇪 Немецкий","🇫🇷 Французский","🇰🇿 Казахский","🇺🇦 Украинский"
])
def handle_language(message):
    uid = message.from_user.id
    lang = message.text
    set_language(uid, lang)

    greetings_map = {
       "🇷🇺 Русский": (
        "🇷🇺 Вы выбрали русский язык!\n\n"
        "📦 Отправьте мне ссылку на товар — я буду отслеживать его цену и сообщу, когда она упадёт 💰\n"
        "🕵️ Также я проверю этот товар на других сайтах, чтобы найти где дешевле!\n\n"
        "Поддерживаемые сайты:\n"
        "• Allegro\n• Temu\n• AliExpress\n• Banggood\n• Alibaba\n\n"
        "Когда найду дешевле или цена упадёт — сразу уведомлю вас 📲"
    ),
    "🇬🇧 Английский": (
        "🇬🇧 You selected English!\n\n"
        "📦 Send me a product link — I’ll track its price and notify you when it drops 💰\n"
        "🕵️ I’ll also check this product on other sites to find where it’s cheaper!\n\n"
        "Supported sites:\n• Allegro\n• Temu\n• AliExpress\n• Banggood\n• Alibaba\n\n"
        "When I find a lower price or a drop — I’ll let you know 📲"
    ),
    # ... аналогично для остальных языков
    }
    _, kb_after_lang = get_keyboards(lang)
    bot.send_message(uid, greetings_map.get(lang, "Язык сохранён."), reply_markup=kb_after_lang)

# Отписка
@bot.message_handler(func=lambda m: m.text == "❌ Отписаться")
def handle_unsubscribe(message):
    uid = message.from_user.id
    remove_subscriber(uid)
    bot.send_message(uid, "Вы отписались 🔕", reply_markup=kb_before)

# --- Admin commands ---
@bot.message_handler(commands=["count"])
def cmd_count(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ У вас нет доступа")
        return
    n = len(get_all_subscribers())
    bot.reply_to(message, f"📊 Подписчиков: {n}")

@bot.message_handler(commands=["subscribers"])
def cmd_subscribers(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ У вас нет доступа")
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id, language FROM subscribers")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        bot.reply_to(message, "Пока нет подписчиков.")
        return
    text = "Список подписчиков:\n\n" + "\n".join(f"{r[0]} | {r[1] or '—'}" for r in rows)
    bot.reply_to(message, text)

@bot.message_handler(commands=["broadcast"])
def safe_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ У вас нет доступа")
        return
    text = message.text.replace("/broadcast", "", 1).strip()
    if not text:
        bot.reply_to(message, "Укажите текст после /broadcast")
        return
    users = get_all_subscribers()
    failed = []
    removed_count = 0
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    batch_size = 50
    pause = 1
    for i in range(0, len(users), batch_size):
        batch = users[i:i+batch_size]
        for uid in batch:
            for chunk in chunks:
                try:
                    bot.send_message(uid, chunk)
                except Exception as e:
                    failed.append({"user_id": uid, "error": str(e)})
                    remove_subscriber(uid)
                    removed_count += 1
        time.sleep(pause)
    bot.reply_to(
        message,
        f"✅ Рассылка завершена. Не дошло: {len(failed)} пользователей\n🗑 Автоматически удалено: {removed_count}"
    )
    if failed:
        with open("broadcast_errors.log", "w", encoding="utf-8") as f:
            json.dump(failed, f, ensure_ascii=False, indent=2)

@bot.message_handler(commands=["status"])
def cmd_status(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ У вас нет доступа")
        return
    users = get_all_subscribers()
    bot.reply_to(message, f"Бот живой. Подписчиков: {len(users)}")

# ---------- Flask app ----------
app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "OK", 200

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

# ---------- Startup ----------
init_db()

if WEBHOOK_URL:
    try: bot.remove_webhook()
    except: pass
    ok = bot.set_webhook(url=WEBHOOK_URL)
    print("set_webhook ->", ok, "WEBHOOK_URL:", WEBHOOK_URL)
else:
    print("WEBHOOK_URL не задан — установите переменную окружения WEBHOOK_URL на Render")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
