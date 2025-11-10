# main.py
import os
import sqlite3
import datetime
import time
from flask import Flask, request
import telebot
from telebot import types
from dotenv import load_dotenv

# ===== Настройки =====
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден!")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
DB_PATH = "subscribers.db"

# ===== Инициализация базы =====
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS subscribers (
        user_id INTEGER PRIMARY KEY,
        language TEXT,
        marketing_consent INTEGER DEFAULT 0,
        consent_ts TEXT
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
        INSERT INTO subscribers (user_id, language, marketing_consent, consent_ts)
        VALUES (?, '', ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            marketing_consent=excluded.marketing_consent,
            consent_ts=excluded.consent_ts
    """, (user_id, 1 if marketing_consent else 0, now))
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

# ===== Клавиатуры =====
def get_keyboards(language):
    before = types.ReplyKeyboardMarkup(resize_keyboard=True)
    after = types.ReplyKeyboardMarkup(resize_keyboard=True)

    if language == "🇬🇧 Английский":
        before.add("✅ Subscribe")
        after.add("❌ Unsubscribe")
    elif language == "🇵🇱 Польский":
        before.add("✅ Subskrybuj")
        after.add("❌ Anuluj subskrypcję")
    elif language == "🇪🇸 Испанский":
        before.add("✅ Suscribirse")
        after.add("❌ Cancelar suscripción")
    elif language == "🇩🇪 Немецкий":
        before.add("✅ Abonnieren")
        after.add("❌ Abbestellen")
    elif language == "🇫🇷 Французский":
        before.add("✅ S’abonner")
        after.add("❌ Se désabonner")
    elif language == "🇰🇿 Казахский":
        before.add("✅ Жазылу")
        after.add("❌ Жазылымнан бас тарту")
    elif language == "🇺🇦 Украинский":
        before.add("✅ Підписатися")
        after.add("❌ Відписатися")
    else:
        before.add("✅ Подписаться")
        after.add("❌ Отписаться")
    return before, after

# ===== Обработчики =====
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
        _, kb_after = get_keyboards(user_lang)
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
        bot.send_message(uid, greetings.get(user_lang, "Вы уже подписаны ✅"), reply_markup=kb_after)
    else:
        kb_before, _ = get_keyboards("🇷🇺 Русский")
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

# ===== Подписка с выбором согласия и языка =====
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
        kb_before, _ = get_keyboards(user_lang)
        bot.send_message(uid, "Вы уже подписаны ✅", reply_markup=kb_before)
        return

    add_subscriber(uid)

    # Кнопки согласия на маркетинг
    kb_consent = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb_consent.add("✅ Согласен на рассылку", "❌ Не согласен на рассылку")
    bot.send_message(uid, "Хотите получать рекламные уведомления?", reply_markup=kb_consent)

    # Кнопки выбора языка
    kb_languages, _ = get_keyboards("🇷🇺 Русский")
    bot.send_message(uid, "Выберите язык:", reply_markup=kb_languages)

@bot.message_handler(func=lambda m: m.text in ["✅ Согласен на рассылку", "❌ Не согласен на рассылку"])
def handle_marketing_consent(message):
    uid = message.from_user.id
    consent = 1 if message.text == "✅ Согласен на рассылку" else 0
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE subscribers SET marketing_consent = ? WHERE user_id = ?", (consent, uid))
    conn.commit()
    conn.close()
    bot.send_message(uid, "Ваш выбор сохранён ✅")

@bot.message_handler(func=lambda m: m.text in [
    "🇷🇺 Русский","🇬🇧 Английский","🇵🇱 Польский","🇪🇸 Испанский",
    "🇩🇪 Немецкий","🇫🇷 Французский","🇰🇿 Казахский","🇺🇦 Украинский"
])
def handle_language(message):
    uid = message.from_user.id
    lang = message.text
    set_language(uid, lang)
    _, kb_after = get_keyboards(lang)
    bot.send_message(uid, f"Вы выбрали язык: {lang}", reply_markup=kb_after)

@bot.message_handler(func=lambda m: m.text == "❌ Отписаться")
def handle_unsubscribe(message):
    uid = message.from_user.id
    remove_subscriber(uid)
    kb_before, _ = get_keyboards("🇷🇺 Русский")
    bot.send_message(uid, "Вы отписались 🔕", reply_markup=kb_before)

# ===== Админ команды =====
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
                except:
                    failed.append(uid)
                    remove_subscriber(uid)
                    removed_count += 1
        time.sleep(pause)
    bot.reply_to(message, f"✅ Рассылка завершена. Не дошло: {len(failed)}. Удалено: {removed_count}")

@bot.message_handler(commands=["status"])
def cmd_status(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ У вас нет доступа")
        return
    users = get_all_subscribers()
    bot.reply_to(message, f"Бот живой. Подписчиков: {len(users)}")

# ===== Flask маршруты =====
@app.route("/", methods=["GET"])
def index():
    return "OK", 200

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

# ===== Запуск =====
init_db()
if WEBHOOK_URL:
    try: bot.remove_webhook()
    except: pass
    bot.set_webhook(url=WEBHOOK_URL)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
