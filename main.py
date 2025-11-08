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
       "🇷🇺 Русский": (
        "🇷🇺 Вы выбрали русский язык!\n\n"
        "📦 Отправьте мне ссылку на товар — я буду отслеживать его цену и сообщу, когда она упадёт 💰\n"
        "🕵️ Также я проверю этот товар на других сайтах, чтобы найти где дешевле!\n\n"
        "Поддерживаемые сайты:\n"
        "• Allegro\n"
        "• Temu\n"
        "• AliExpress\n"
        "• Banggood\n"
        "• Alibaba\n\n"
        "Когда найду дешевле или цена упадёт — сразу уведомлю вас 📲"
    ),

    "🇬🇧 Английский": (
        "🇬🇧 You selected English!\n\n"
        "📦 Send me a product link — I’ll track its price and notify you when it drops 💰\n"
        "🕵️ I’ll also check this product on other sites to find where it’s cheaper!\n\n"
        "Supported sites:\n"
        "• Allegro\n"
        "• Temu\n"
        "• AliExpress\n"
        "• Banggood\n"
        "• Alibaba\n\n"
        "When I find a lower price or a drop — I’ll let you know 📲"
    ),

    "🇵🇱 Польский": (
        "🇵🇱 Wybrałeś język polski!\n\n"
        "📦 Wyślij mi link do produktu — będę śledzić jego cenę i dam znać, gdy spadnie 💰\n"
        "🕵️ Sprawdzę też ten produkt na innych stronach, aby znaleźć tańszą ofertę!\n\n"
        "Obsługiwane strony:\n"
        "• Allegro\n"
        "• Temu\n"
        "• AliExpress\n"
        "• Banggood\n"
        "• Alibaba\n\n"
        "Gdy znajdę niższą cenę lub spadek — natychmiast Cię powiadomię 📲"
    ),

    "🇪🇸 Испанский": (
        "🇪🇸 ¡Has seleccionado Español!\n\n"
        "📦 Envíame un enlace de producto — seguiré su precio y te avisaré cuando baje 💰\n"
        "🕵️ También comprobaré este producto en otros sitios para ver dónde es más barato.\n\n"
        "Sitios compatibles:\n"
        "• Allegro\n"
        "• Temu\n"
        "• AliExpress\n"
        "• Banggood\n"
        "• Alibaba\n\n"
        "Cuando encuentre un precio más bajo o una bajada — te lo notificaré 📲"
    ),

    "🇩🇪 Немецкий": (
        "🇩🇪 Du hast Deutsch gewählt!\n\n"
        "📦 Sende mir den Produktlink — ich verfolge den Preis und informiere dich, wenn er fällt 💰\n"
        "🕵️ Außerdem überprüfe ich das Produkt auf anderen Websites, um den günstigsten Preis zu finden!\n\n"
        "Unterstützte Seiten:\n"
        "• Allegro\n"
        "• Temu\n"
        "• AliExpress\n"
        "• Banggood\n"
        "• Alibaba\n\n"
        "Wenn ich einen besseren Preis finde oder der Preis sinkt — bekommst du sofort eine Benachrichtigung 📲"
    ),

    "🇫🇷 Французский": (
        "🇫🇷 Vous avez choisi Français !\n\n"
        "📦 Envoyez-moi un lien vers un produit — je suivrai son prix et vous informerai dès qu’il baisse 💰\n"
        "🕵️ Je vérifierai aussi ce produit sur d’autres sites pour voir où il est moins cher !\n\n"
        "Sites pris en charge :\n"
        "• Allegro\n"
        "• Temu\n"
        "• AliExpress\n"
        "• Banggood\n"
        "• Alibaba\n\n"
        "Dès que je trouve un meilleur prix ou une baisse — je vous le dirai 📲"
    ),

    "🇰🇿 Казахский": (
        "🇰🇿 Сіз қазақ тілін таңдадыңыз!\n\n"
        "📦 Маған тауардың сілтемесін жіберіңіз — мен оның бағасын бақылаймын және арзандағанда хабарлаймын 💰\n"
        "🕵️ Сондай-ақ мен бұл тауарды басқа сайттардан қарап, арзанырақ нұсқасын табуға тырысамын!\n\n"
        "Қолдау көрсетілетін сайттар:\n"
        "• Allegro\n"
        "• Temu\n"
        "• AliExpress\n"
        "• Banggood\n"
        "• Alibaba\n\n"
        "Баға түссе немесе арзанырақ табылса — бірден хабарлаймын 📲"
    ),

    "🇺🇦 Украинский": (
        "🇺🇦 Ви обрали українську мову!\n\n"
        "📦 Надішліть мені посилання на товар — я відстежуватиму його ціну та повідомлю, коли вона знизиться 💰\n"
        "🕵️ Також я перевірю цей товар на інших сайтах, щоб знайти, де він дешевше!\n\n"
        "Підтримувані сайти:\n"
        "• Allegro\n"
        "• Temu\n"
        "• AliExpress\n"
        "• Banggood\n"
        "• Alibaba\n\n"
        "Коли знайду нижчу ціну або зниження — одразу повідомлю 📲"
    ),
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

    # Разбиваем текст на куски <= 4000 символов
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]

    batch_size = 50   # количество пользователей в пакете
    pause = 1         # пауза между пакетами в секундах

    for i in range(0, len(users), batch_size):
        batch = users[i:i+batch_size]
        for uid in batch:
            for chunk in chunks:
                try:
                    bot.send_message(uid, chunk)
                except Exception as e:
                    failed.append({"user_id": uid, "error": str(e)})
        time.sleep(pause)  # пауза между пакетами

    bot.reply_to(message, f"✅ Рассылка завершена. Не дошло: {len(failed)} пользователей")
    
    # Сохраняем ошибки в файл
    if failed:
        import json
        with open("broadcast_errors.log", "w", encoding="utf-8") as f:
            json.dump(failed, f, ensure_ascii=False, indent=2)


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



