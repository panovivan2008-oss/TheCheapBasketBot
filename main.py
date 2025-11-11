# main.py
import os
import sqlite3
import datetime
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
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в окружении!")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
DB_PATH = os.path.join("/tmp", "subscribers.db")
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

def get_all_subscribers():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM subscribers")
        rows = cur.fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        logging.exception(f"get_all_subscribers: ошибка при чтении базы: {e}")
        return []

# ===== Keyboards =====
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
    return kb

def get_main_panel(user_id, lang_code=None):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("❌ Отписаться")
    kb.add("Изменить рассылку")
    return kb

def get_main_keyboard(user_id: int):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if is_subscribed(user_id):
        kb.add("❌ Отписаться")
    else:
        kb.add("✅ Подписаться")
    return kb

# ===== Presentations =====
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
    "🇵🇱 Польский": (
        "🇵🇱 Wybrałeś język polski!\n\n"
        "📦 Wyślij mi link do produktu — będę śledzić jego cenę i powiadomię Cię, gdy spadnie 💰\n"
        "🕵️ Sprawdzę też ten produkt na innych stronach, aby znaleźć lepszą cenę!\n\n"
        "Obsługiwane strony:\n• Allegro\n• Temu\n• AliExpress\n• Banggood\n• Alibaba\n\n"
        "Gdy znajdę niższą cenę lub spadek — od razu Cię powiadomię 📲"
    ),
    "🇪🇸 Испанский": (
        "🇪🇸 ¡Has seleccionado español!\n\n"
        "📦 Envíame un enlace de producto — rastrearé su precio y te avisaré cuando baje 💰\n"
        "🕵️ También comprobaré este producto en otros sitios para encontrarlo más barato!\n\n"
        "Sitios compatibles:\n• Allegro\n• Temu\n• AliExpress\n• Banggood\n• Alibaba\n\n"
        "Cuando encuentre un precio más bajo o una caída, te lo notificaré 📲"
    ),
    "🇩🇪 Немецкий": (
        "🇩🇪 Sie haben Deutsch gewählt!\n\n"
        "📦 Senden Sie mir einen Produktlink — ich werde den Preis verfolgen und Sie benachrichtigen, wenn er fällt 💰\n"
        "🕵️ Ich überprüfe auch dieses Produkt auf anderen Seiten, um es günstiger zu finden!\n\n"
        "Unterstützte Seiten:\n• Allegro\n• Temu\n• AliExpress\n• Banggood\n• Alibaba\n\n"
        "Wenn ich einen niedrigeren Preis oder Rabatt finde — werde ich Sie sofort informieren 📲"
    ),
    "🇫🇷 Французский": (
        "🇫🇷 Vous avez choisi le français!\n\n"
        "📦 Envoyez-moi un lien de produit — je suivrai son prix et vous informerai lorsqu'il baissera 💰\n"
        "🕵️ Je vérifierai également ce produit sur d'autres sites pour trouver moins cher!\n\n"
        "Sites pris en charge:\n• Allegro\n• Temu\n• AliExpress\n• Banggood\n• Alibaba\n\n"
        "Quand je trouve un prix plus bas ou une baisse — je vous préviendrai immédiatement 📲"
    ),
    "🇰🇿 Казахский": (
        "🇰🇿 Қазақ тілін таңдадыңыз!\n\n"
        "📦 Өнімге сілтемені жіберіңіз — мен оның бағасын қадағалаймын және ол төмендегенде хабарлаймын 💰\n"
        "🕵️ Сондай-ақ өнімді басқа сайттардан тексеріп, қайда арзан екенін табамын!\n\n"
        "Қолдау көрсетілетін сайттар:\n• Allegro\n• Temu\n• AliExpress\n• Banggood\n• Alibaba\n\n"
        "Төмен баға немесе жеңілдік тапсам — дереу хабарлаймын 📲"
    ),
    "🇺🇦 Украинский": (
        "🇺🇦 Ви обрали українську мову!\n\n"
        "📦 Надішліть мені посилання на товар — я відстежуватиму його ціну та повідомлю, коли вона впаде 💰\n"
        "🕵️ Також перевірю цей товар на інших сайтах, щоб знайти, де дешевше!\n\n"
        "Підтримувані сайти:\n• Allegro\n• Temu\n• AliExpress\n• Banggood\n• Alibaba\n\n"
        "Коли знайду дешевше або ціна впаде — відразу повідомлю вас 📲"
    )
}


# ===== Handlers =====
@bot.message_handler(commands=["start"])
def handle_start(message):
    uid = message.from_user.id
    bot.send_message(uid, "Привет! Используй кнопки ниже.", reply_markup=get_main_keyboard(uid))

@bot.message_handler(func=lambda m: m.text == "✅ Подписаться")
def subscribe_user(message):
    uid = message.from_user.id
    if not is_subscribed(uid):
        add_subscriber(uid)
    bot.send_message(uid, "Вы подписались ✅", reply_markup=get_main_keyboard(uid))
    bot.send_message(uid, "Выберите язык:", reply_markup=kb_languages_markup())

@bot.message_handler(func=lambda m: m.text == "❌ Отписаться")
def unsubscribe_user(message):
    uid = message.from_user.id
    if is_subscribed(uid):
        remove_subscriber(uid)
        bot.send_message(uid, "Вы отписались 🔕", reply_markup=get_main_keyboard(uid))
    else:
        bot.send_message(uid, "Вы уже отписаны ❌", reply_markup=get_main_keyboard(uid))

@bot.message_handler(func=lambda m: m.text in PRESENTATIONS.keys())
def set_user_language(message):
    uid = message.from_user.id
    lang = message.text
    if not is_subscribed(uid):
        add_subscriber(uid)
    set_language(uid, lang)
    bot.send_message(uid, PRESENTATIONS.get(lang), reply_markup=get_main_panel(uid))
    bot.send_message(uid, "Хотите получать рекламные уведомления?", reply_markup=kb_marketing_bottom())

@bot.message_handler(func=lambda m: m.text in ["✅ Разрешаю рассылку", "❌ Не хочу рассылку", "Изменить рассылку"])
def marketing_choice(message):
    uid = message.from_user.id
    if message.text == "✅ Разрешаю рассылку":
        set_marketing_consent(uid, 1)
        bot.send_message(uid, "Вы согласились на рассылку ✅", reply_markup=get_main_panel(uid))
    elif message.text == "❌ Не хочу рассылку":
        set_marketing_consent(uid, 0)
        bot.send_message(uid, "Вы отказались от рассылки ❌", reply_markup=get_main_panel(uid))
    elif message.text == "Изменить рассылку":
        bot.send_message(uid, "Выберите новое решение о рассылке:", reply_markup=kb_marketing_bottom())

# ===== Admin commands =====
@bot.message_handler(commands=["count"])
def cmd_count(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ У вас нет доступа")
        return
    bot.reply_to(message, f"📊 Подписчиков: {len(get_all_subscribers())}")

@bot.message_handler(commands=["help"])
def handle_help(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ У вас нет доступа")
        return

    text = (
        "📌 Админские команды:\n"
        "/start - старт\n"
        "/count - количество подписчиков\n"
        "/subscribers - список подписчиков\n"
        "/broadcast <текст> - рассылка всем подписчикам\n"
        "/status - диагностика\n"
        "/debug - подробная информация о подписчиках\n"
    )
    bot.send_message(message.from_user.id, text)

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
        bot.set_webhook(url=WEBHOOK_URL)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
