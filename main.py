# main.py
import os
import sqlite3
from flask import Flask, request
import telebot
from telebot import types
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # https://your-service.onrender.com/<BOT_TOKEN>

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в окружении!")

bot = telebot.TeleBot(BOT_TOKEN)

# ---------- Database helpers (open/close per operation) ----------
DB_PATH = "subscribers.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS subscribers (
        user_id INTEGER PRIMARY KEY,
        language TEXT
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

def add_subscriber(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO subscribers (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def set_language(user_id: int, language: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE subscribers SET language = ? WHERE user_id = ?", (language, user_id))
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

# ---------- Handlers ----------
@bot.message_handler(commands=["start"])
def handle_start(message):
    uid = message.from_user.id
    if is_subscribed(uid):
        bot.send_message(uid, "Вы уже подписаны ✅", reply_markup=kb_after)
    else:
        bot.send_message(uid, "Привет! Нажмите кнопку ниже, чтобы подписаться на уведомления о товарах.", reply_markup=kb_before)

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
    add_subscriber(uid)
    bot.send_message(uid, "Вы подписались! Выберите язык:", reply_markup=kb_languages)

@bot.message_handler(func=lambda m: m.text in [
    "🇷🇺 Русский","🇬🇧 Английский","🇵🇱 Польский","🇪🇸 Испанский",
    "🇩🇪 Немецкий","🇫🇷 Французский","🇰🇿 Казахский","🇺🇦 Украинский"
])
def handle_language(message):
    uid = message.from_user.id
    lang = message.text
    set_language(uid, lang)
    greetings_map = {
        "🇷🇺 Русский": "Вы выбрали русский 🇷🇺\nЯ буду отслеживать цены — пришлите ссылку.",
        "🇬🇧 Английский": "You selected English 🌐\nI will track prices — send a link.",
        "🇵🇱 Польский": "Wybrałeś język polski 🇵🇱\nWyślij link — powiadomię o zmianie ceny!",
        "🇪🇸 Испанский": "Has seleccionado Español 🇪🇸\nEnvía un enlace — te avisaré si baja el precio!",
        "🇩🇪 Немецкий": "Du hast Deutsch 🇩🇪 gewählt\nSende einen Link — ich informiere dich bei Preisänderungen!",
        "🇫🇷 Французский": "Vous avez choisi Français 🇫🇷\nEnvoyez un lien — je vous avertirai si le prix baisse!",
        "🇰🇿 Казахский": "Сіз қазақ тілін таңдадыңыз 🇰🇿\nСілтемені жіберіңіз — баға төмендесе хабарлаймын!",
        "🇺🇦 Украинский": "Ви обрали українську 🇺🇦\nНадішліть посилання — повідомлю, якщо ціна знизиться!"
    }
    bot.send_message(uid, greetings_map.get(lang, "Язык сохранён."), reply_markup=kb_after)

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
def cmd_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ У вас нет доступа")
        return
    text = message.text.replace("/broadcast", "", 1).strip()
    if not text:
        bot.reply_to(message, "Укажите текст после /broadcast")
        return
    users = get_all_subscribers()
    sent = 0
    for uid in users:
        try:
            bot.send_message(uid, text)
            sent += 1
        except Exception:
            continue
    bot.reply_to(message, f"✅ Рассылка отправлена {sent} пользователям")

@bot.message_handler(commands=["status"])
def cmd_status(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ У вас нет доступа")
        return
    users = get_all_subscribers()
    bot.reply_to(message, f"Бот живой. Подписчиков: {len(users)}")

# ---------- Flask app to accept updates ----------
app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "OK", 200

# Telegram will POST updates to /<BOT_TOKEN>
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

# ---------- Startup: init DB and set webhook ----------
init_db()

# Remove previous webhook and set new one (WEBHOOK_URL must be https://.../<BOT_TOKEN>)
if WEBHOOK_URL:
    try:
        bot.remove_webhook()
    except Exception:
        pass
    ok = bot.set_webhook(url=WEBHOOK_URL)
    print("set_webhook ->", ok, "WEBHOOK_URL:", WEBHOOK_URL)
else:
    print("WEBHOOK_URL не задан — установите переменную окружения WEBHOOK_URL на Render")

# ---------- If run directly (development) ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# main.py
from flask import Flask, request
import telebot
import os

# ===== Настройки =====
TOKEN = os.getenv("BOT_TOKEN")  # Твой токен бота из Render Environment
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # URL твоего сайта Render

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ===== Обработчики команд =====
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "👋 Привет! Бот успешно запущен и работает через Render!")

@bot.message_handler(commands=['help'])
def help_message(message):
    bot.reply_to(message, "🛠 Команды:\n/start — запустить бота\n/help — помощь")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.send_message(message.chat.id, f"Ты написал: {message.text}")

# ===== Flask маршруты =====
@app.route("/", methods=["GET"])
def index():
    return "✅ Bot is running via Render!", 200

@app.route("/", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_str = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return "", 200
    else:
        return "Unsupported Media Type", 415

# ===== Запуск приложения =====
if __name__ == "__main__":
    if WEBHOOK_URL:
        bot.remove_webhook()
        bot.set_webhook(url=WEBHOOK_URL)
        print(f"✅ set_webhook -> True WEBHOOK_URL: {WEBHOOK_URL}")
    else:
        print("⚠️ WEBHOOK_URL не задан! Укажи его в Render Environment Variables.")
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)



