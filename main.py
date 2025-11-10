# main.py
import os
import sqlite3
import datetime
import time
from flask import Flask, request
import telebot
from telebot import types
from dotenv import load_dotenv

load_dotenv()

# ===== Настройки =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # https://your-service.onrender.com/<BOT_TOKEN>

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в окружении!")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

DB_PATH = "/mnt/data/subscribers.db"

# ===== Database helpers =====
def init_db():
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

def is_subscribed(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM subscribers WHERE user_id = ?", (user_id,))
    res = cur.fetchone()
    conn.close()
    return res is not None
    
def add_subscriber(user_id: int):
    """Добавляем пользователя в базу (язык пустой до выбора) и логируем."""
    now = datetime.datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO subscribers (user_id, language, marketing_consent, consent_ts)
        VALUES (?, '', 0, ?)
        ON CONFLICT(user_id) DO NOTHING
    """, (user_id, now))
    conn.commit()
    conn.close()
    print(f"Добавлен подписчик: {user_id} в {now}")


def set_language(user_id: int, language: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE subscribers SET language=? WHERE user_id=?", (language, user_id))
    conn.commit()
    conn.close()

def get_user_language(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT language FROM subscribers WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row and row[0] else ""

def set_marketing_consent(user_id: int, consent: int):
    now = datetime.datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE subscribers SET marketing_consent=?, consent_ts=? WHERE user_id=?", (consent, now, user_id))
    conn.commit()
    conn.close()

def remove_subscriber(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM subscribers WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_all_subscribers():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM subscribers")
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]

# ===== Keyboards =====
def kb_subscribe_default():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("✅ Подписаться"))
    return kb

def kb_unsubscribe_default():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("❌ Отписаться"))
    return kb

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
    """Возвращает before/after клавиатуры с переводом кнопок"""
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

# ===== Presentations (all languages) =====
PRESENTATIONS = {
    "🇷🇺 Русский": (
        "🇷🇺 Вы выбрали русский язык!\n\n"
        "📦 Отправьте мне ссылку на товар — я буду отслеживать его цену и сообщу, когда она упадёт 💰\n"
        "🕵️ Также проверю этот товар на других сайтах, чтобы найти где дешевле!\n\n"
        "Поддерживаемые сайты:\n• Allegro\n• Temu\n• AliExpress\n• Banggood\n• Alibaba\n\n"
        "Когда найду дешевле или цена упадёт — сразу уведомлю вас 📲"
    ),
    "🇬🇧 Английский": (
        "🇬🇧 You selected English!\n\n"
        "📦 Send me a product link — I’ll track its price and notify you when it drops 💰\n"
        "🕵️ I’ll also check this product on other sites to find where it’s cheaper!\n\n"
        "Supported sites:\n• Allegro\n• Temu\n• AliExpress\n• Banggood\n• Alibaba\n\n"
        "When I find a lower price or a drop — I’ll let you know 📲"
    ),
    # ... остальные языки (тот же код, что у тебя)
}

# ===== Handlers =====
@bot.message_handler(commands=["start"])
def handle_start(message):
    uid = message.from_user.id
    if is_subscribed(uid):
        lang = get_user_language(uid) or "🇷🇺 Русский"
        _, kb_after = get_keyboards_by_lang(lang)
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
        bot.send_message(uid, greetings.get(lang, "Вы уже подписаны ✅"), reply_markup=kb_after)
    else:
        bot.send_message(uid, "Привет! Нажмите кнопку ниже, чтобы подписаться на уведомления о товарах.", reply_markup=kb_subscribe_default())

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
        lang = get_user_language(uid) or "🇷🇺 Русский"
        before, _ = get_keyboards_by_lang(lang)
        bot.send_message(uid, "Вы уже подписаны ✅", reply_markup=before)
        return

    add_subscriber(uid)
    bot.send_message(uid, "Выберите язык:", reply_markup=kb_languages_markup())

@bot.message_handler(func=lambda m: m.text in list(PRESENTATIONS.keys()))
def handle_language(message):
    uid = message.from_user.id
    lang = message.text
    if not is_subscribed(uid):
        add_subscriber(uid)
    set_language(uid, lang)
    presentation = PRESENTATIONS.get(lang, "Язык сохранён.")
    _, kb_after = get_keyboards_by_lang(lang)
    bot.send_message(uid, presentation, reply_markup=kb_after)
    time.sleep(0.2)
    bot.send_message(uid, "Хотите получать рекламные уведомления? (можно изменить позже)", reply_markup=kb_marketing_bottom())

@bot.message_handler(func=lambda m: m.text in ["✅ Разрешаю рассылку", "❌ Не хочу рассылку", "Изменить позже"])
def handle_marketing_choice(message):
    uid = message.from_user.id
    lang = get_user_language(uid)
    if not lang:
        bot.send_message(uid, "Сначала выберите язык, пожалуйста.", reply_markup=kb_languages_markup())
        return
    if message.text == "✅ Разрешаю рассылку":
        set_marketing_consent(uid, 1)
        _, kb_after = get_keyboards_by_lang(lang)
        bot.send_message(uid, "Вы согласились на рассылку ✅", reply_markup=kb_after)
    elif message.text == "❌ Не хочу рассылку":
        set_marketing_consent(uid, 0)
        _, kb_after = get_keyboards_by_lang(lang)
        bot.send_message(uid, "Вы отказались от рассылки ❌", reply_markup=kb_after)
    else:
        bot.send_message(uid, "Ок — вы можете изменить своё решение о рассылке в любое время:", reply_markup=kb_marketing_bottom())

@bot.message_handler(func=lambda m: m.text == "❌ Отписаться")
def handle_unsubscribe(message):
    uid = message.from_user.id
    remove_subscriber(uid)
    bot.send_message(uid, "Вы отписались 🔕", reply_markup=kb_subscribe_default())

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
    if not rows:
        bot.reply_to(message, "Пока нет подписчиков.")
        return
    text = "Список подписчиков:\n\n" + "\n".join(f"{r[0]} | {r[1] or '—'} | consent={r[2]}" for r in rows)
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
    bot.reply_to(message, f"✅ Рассылка завершена. Не дошло: {len(failed)}\n🗑 Удалено: {removed_count}")

@bot.message_handler(commands=["status"])
def cmd_status(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ У вас нет доступа")
        return
    bot.reply_to(message, f"Бот живой. Подписчиков: {len(get_all_subscribers())}")

# ===== Admin debug command =====
@bot.message_handler(commands=["debug"])
def cmd_debug(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ У вас нет доступа")
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id, language, marketing_consent, consent_ts FROM subscribers")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        bot.reply_to(message, "База пустая")
        return
    text = "DEBUG: все подписчики:\n\n" + "\n".join(
        f"{r[0]} | {r[1] or '—'} | consent={r[2]} | {r[3]}" for r in rows
    )
    bot.reply_to(message, text)

# ===== Flask webhook =====
@app.route("/", methods=["GET"])
def index():
    return "OK", 200

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
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
        print("set_webhook ->", ok, "WEBHOOK_URL:", WEBHOOK_URL)
    else:
        print("WEBHOOK_URL не задан — укажи его в переменных окружения")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
