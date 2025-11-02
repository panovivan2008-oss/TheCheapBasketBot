from telebot import TeleBot, types
import sqlite3
import os
from dotenv import load_dotenv

# ----------------- ЗАГРУЗКА ПЕРЕМЕННЫХ -----------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = TeleBot(BOT_TOKEN)

# ----------------- КНОПКИ -----------------
kb_before_subscribe = types.ReplyKeyboardMarkup(resize_keyboard=True)
kb_before_subscribe.add(types.KeyboardButton("✅ Подписаться"))

kb_after_subscribe = types.ReplyKeyboardMarkup(resize_keyboard=True)
kb_after_subscribe.add(types.KeyboardButton("❌ Отписаться"))

kb_languages = types.ReplyKeyboardMarkup(resize_keyboard=True)
kb_languages.add("🇷🇺 Русский", "🇬🇧 Английский")
kb_languages.add("🇵🇱 Польский", "🇪🇸 Испанский")
kb_languages.add("🇩🇪 Немецкий", "🇫🇷 Французский")
kb_languages.add("🇰🇿 Казахский", "🇺🇦 Украинский")

# ----------------- ФУНКЦИИ ДЛЯ БАЗЫ -----------------
def is_subscribed(user_id):
    conn = sqlite3.connect("subscribers.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM subscribers WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def add_subscriber(user_id):
    conn = sqlite3.connect("subscribers.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO subscribers (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def set_language(user_id, language):
    conn = sqlite3.connect("subscribers.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE subscribers SET language = ? WHERE user_id = ?", (language, user_id))
    conn.commit()
    conn.close()

def remove_subscriber(user_id):
    conn = sqlite3.connect("subscribers.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subscribers WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_all_subscribers():
    conn = sqlite3.connect("subscribers.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM subscribers")
    users = cursor.fetchall()
    conn.close()
    return [uid for (uid,) in users]

# ----------------- ИНИЦИАЛИЗАЦИЯ БАЗЫ -----------------
conn = sqlite3.connect("subscribers.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS subscribers (
    user_id INTEGER PRIMARY KEY,
    language TEXT
)
""")
conn.commit()
conn.close()

# ----------------- КОМАНДЫ -----------------
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    if is_subscribed(user_id):
        bot.send_message(user_id, "Вы уже подписаны ✅", reply_markup=kb_after_subscribe)
    else:
        bot.send_message(user_id, "Привет! Нажмите кнопку ниже, чтобы подписаться на уведомления о товарах.", reply_markup=kb_before_subscribe)

@bot.message_handler(commands=["help"])
def help_command(message):
    text = (
        "📌 Команды бота:\n\n"
        "/start - Начало работы\n"
        "✅ Подписаться - Подписаться на рассылку\n"
        "❌ Отписаться - Отписаться\n"
        "🇷🇺🇬🇧🇵🇱... - Выбор языка\n"
        "/broadcast <текст> - Рассылка всем подписчикам (только для админа)\n"
    )
    bot.send_message(message.from_user.id, text)

# ----------------- ПОДПИСКА -----------------
@bot.message_handler(lambda m: m.text == "✅ Подписаться")
def subscribe(message):
    user_id = message.from_user.id
    add_subscriber(user_id)
    bot.send_message(user_id, "Вы подписались! Выберите язык:", reply_markup=kb_languages)

# ----------------- ВЫБОР ЯЗЫКА -----------------
@bot.message_handler(lambda m: m.text in [
    "🇷🇺 Русский","🇬🇧 Английский","🇵🇱 Польский","🇪🇸 Испанский",
    "🇩🇪 Немецкий","🇫🇷 Французский","🇰🇿 Казахский","🇺🇦 Украинский"
])
def choose_language(message):
    user_id = message.from_user.id
    language = message.text
    set_language(user_id, language)
    greetings = {
        "🇷🇺 Русский": "Вы выбрали русский 🇷🇺\nБот отслеживает цены на AliExpress, Allegro, Temu, Alibaba, Banggood.\nПросто отправьте ссылку!",
        "🇬🇧 Английский": "You selected English 🌐\nThe bot can track prices on AliExpress, Allegro, Temu, Alibaba, Banggood.\nSend a link!",
        "🇵🇱 Польский": "Wybrałeś język polski 🇵🇱\nŚledzę ceny na AliExpress, Allegro, Temu, Alibaba, Banggood.",
        "🇪🇸 Испанский": "Has seleccionado Español 🇪🇸\nRastreo precios en AliExpress, Allegro, Temu, Alibaba, Banggood.",
        "🇩🇪 Немецкий": "Du hast Deutsch 🇩🇪 gewählt\nIch verfolge Preise auf AliExpress, Allegro, Temu, Alibaba, Banggood.",
        "🇫🇷 Французский": "Vous avez choisi Français 🇫🇷\nJe suis un bot qui suit les prix sur AliExpress, Allegro, Temu, Alibaba, Banggood.",
        "🇰🇿 Казахский": "Сіз қазақ тілін таңдадыңыз 🇰🇿\nМен AliExpress, Allegro, Temu, Alibaba, Banggood бағаларын бақылаймын.",
        "🇺🇦 Украинский": "Ви обрали українську 🇺🇦\nЯ відслідковую ціни на AliExpress, Allegro, Temu, Alibaba, Banggood."
    }
    bot.send_message(user_id, greetings.get(language, "Язык не поддерживается"), reply_markup=kb_after_subscribe)

# ----------------- ОТПИСКА -----------------
@bot.message_handler(lambda m: m.text == "❌ Отписаться")
def unsubscribe(message):
    user_id = message.from_user.id
    remove_subscriber(user_id)
    bot.send_message(user_id, "Вы отписались 🔕", reply_markup=kb_before_subscribe)

# ----------------- АДМИН: РАССЫЛКА -----------------
@bot.message_handler(commands=["broadcast"])
def broadcast(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ У вас нет доступа")
        return
    text = message.text.replace("/broadcast ", "")
    users = get_all_subscribers()
    for uid in users:
        try:
            bot.send_message(uid, text)
        except:
            pass
    bot.reply_to(message, f"✅ Рассылка отправлена {len(users)} пользователям")

# ----------------- ЗАПУСК БОТА -----------------
if __name__ == "__main__":
    bot.infinity_polling()
