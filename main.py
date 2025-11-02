import telebot
from telebot import types
import sqlite3, os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(BOT_TOKEN)

# --- БАЗА ДАННЫХ ---
conn = sqlite3.connect("subscribers.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS subscribers (
    user_id INTEGER PRIMARY KEY,
    language TEXT
)
""")
conn.commit()

# --- КЛАВИАТУРЫ ---
kb_before_subscribe = types.ReplyKeyboardMarkup(resize_keyboard=True)
kb_before_subscribe.add("✅ Подписаться")

kb_after_subscribe = types.ReplyKeyboardMarkup(resize_keyboard=True)
kb_after_subscribe.add("❌ Отписаться")

kb_languages = types.ReplyKeyboardMarkup(resize_keyboard=True)
kb_languages.add("🇷🇺 Русский", "🇬🇧 Английский", "🇵🇱 Польский", "🇪🇸 Испанский")
kb_languages.add("🇩🇪 Немецкий", "🇫🇷 Французский", "🇰🇿 Казахский", "🇺🇦 Украинский")

# --- ПРОВЕРКА ПОДПИСКИ ---
def is_subscribed(user_id):
    cursor.execute("SELECT 1 FROM subscribers WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None

# --- СТАРТ ---
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    if is_subscribed(user_id):
        bot.send_message(user_id, "Вы уже подписаны ✅", reply_markup=kb_after_subscribe)
    else:
        bot.send_message(user_id, "Привет! Нажмите кнопку ниже, чтобы подписаться.", reply_markup=kb_before_subscribe)

# --- ПОДПИСКА ---
@bot.message_handler(func=lambda m: m.text == "✅ Подписаться")
def subscribe(message):
    user_id = message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO subscribers (user_id) VALUES (?)", (user_id,))
    conn.commit()
    bot.send_message(user_id, "Вы подписались! Выберите язык:", reply_markup=kb_languages)

# --- ВЫБОР ЯЗЫКА ---
@bot.message_handler(func=lambda m: m.text in [
    "🇷🇺 Русский","🇬🇧 Английский","🇵🇱 Польский","🇪🇸 Испанский",
    "🇩🇪 Немецкий","🇫🇷 Французский","🇰🇿 Казахский","🇺🇦 Украинский"
])
def choose_language(message):
    user_id = message.from_user.id
    language = message.text
    cursor.execute("UPDATE subscribers SET language = ? WHERE user_id = ?", (language, user_id))
    conn.commit()
    bot.send_message(user_id, f"Вы выбрали {language}", reply_markup=kb_after_subscribe)

# --- ОТПИСКА ---
@bot.message_handler(func=lambda m: m.text == "❌ Отписаться")
def unsubscribe(message):
    user_id = message.from_user.id
    cursor.execute("DELETE FROM subscribers WHERE user_id = ?", (user_id,))
    conn.commit()
    bot.send_message(user_id, "Вы отписались 🔕", reply_markup=kb_before_subscribe)

# --- РАССЫЛКА АДМИНОМ ---
@bot.message_handler(commands=["broadcast"])
def broadcast(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ У вас нет доступа")
        return
    text = message.text.replace("/broadcast ", "")
    cursor.execute("SELECT user_id FROM subscribers")
    users = cursor.fetchall()
    for (uid,) in users:
        try:
            bot.send_message(uid, text)
        except:
            pass

# --- ЗАПУСК ---
bot.infinity_polling()
