import telebot
from telebot import types
import sqlite3
import os
from dotenv import load_dotenv

# --- Загрузка токена и ID администратора ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(BOT_TOKEN)

# --- Настройка базы данных ---
conn = sqlite3.connect("subscribers.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS subscribers (
    user_id INTEGER PRIMARY KEY,
    language TEXT
)
""")
conn.commit()

# --- Клавиатуры ---
kb_subscribe = types.ReplyKeyboardMarkup(resize_keyboard=True)
kb_subscribe.add(types.KeyboardButton("✅ Подписаться"))

kb_unsubscribe = types.ReplyKeyboardMarkup(resize_keyboard=True)
kb_unsubscribe.add(types.KeyboardButton("❌ Отписаться"))

kb_languages = types.ReplyKeyboardMarkup(resize_keyboard=True)
kb_languages.add("🇷🇺 Русский", "🇬🇧 Английский")
kb_languages.add("🇵🇱 Польский", "🇪🇸 Испанский")
kb_languages.add("🇩🇪 Немецкий", "🇫🇷 Французский")
kb_languages.add("🇰🇿 Казахский", "🇺🇦 Украинский")

# --- Проверка подписки ---
def is_subscribed(user_id: int) -> bool:
    cursor.execute("SELECT 1 FROM subscribers WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None

# --- /start ---
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    if is_subscribed(user_id):
        bot.send_message(user_id, "Вы уже подписаны ✅", reply_markup=kb_unsubscribe)
    else:
        bot.send_message(user_id, "Привет! Нажмите кнопку ниже, чтобы подписаться.", reply_markup=kb_subscribe)

# --- Подписка ---
@bot.message_handler(func=lambda m: m.text == "✅ Подписаться")
def subscribe(message):
    user_id = message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO subscribers (user_id) VALUES (?)", (user_id,))
    conn.commit()
    bot.send_message(user_id, "Вы подписались! Выберите язык:", reply_markup=kb_languages)

# --- Выбор языка ---
@bot.message_handler(func=lambda m: m.text in [
    "🇷🇺 Русский","🇬🇧 Английский","🇵🇱 Польский","🇪🇸 Испанский",
    "🇩🇪 Немецкий","🇫🇷 Французский","🇰🇿 Казахский","🇺🇦 Украинский"
])
def choose_language(message):
    user_id = message.from_user.id
    language = message.text
    cursor.execute("UPDATE subscribers SET language = ? WHERE user_id = ?", (language, user_id))
    conn.commit()

    greetings = {
        "🇷🇺 Русский": "Вы выбрали русский язык 🇷🇺\nЯ могу отслеживать цены на AliExpress, Allegro, Temu, Alibaba, Banggood. Отправьте ссылку — и я сообщу, если цена упадет!",
        "🇬🇧 Английский": "You selected English 🌐\nI can track prices on AliExpress, Allegro, Temu, Alibaba, Banggood. Send a link — and I will notify if the price drops!",
        "🇵🇱 Польский": "Wybrałeś język polski 🇵🇱\nŚledzę ceny na AliExpress, Allegro, Temu, Alibaba, Banggood. Wyślij link — powiadomię Cię o zmianie ceny!",
        "🇪🇸 Испанский": "Has seleccionado Español 🇪🇸\nPuedo rastrear precios en AliExpress, Allegro, Temu, Alibaba, Banggood. Envía un enlace y te avisaré si baja el precio!",
        "🇩🇪 Немецкий": "Du hast Deutsch 🇩🇪 gewählt\nIch verfolge Preise auf AliExpress, Allegro, Temu, Alibaba, Banggood. Sende einen Link — ich benachrichtige dich bei Preisänderungen!",
        "🇫🇷 Французский": "Vous avez choisi Français 🇫🇷\nJe peux suivre les prix sur AliExpress, Allegro, Temu, Alibaba, Banggood. Envoyez un lien — je vous avertirai si le prix baisse!",
        "🇰🇿 Казахский": "Сіз қазақ тілін таңдадыңыз 🇰🇿\nМен AliExpress, Allegro, Temu, Alibaba, Banggood сайттарындағы бағаларды бақылаймын. Сілтемені жіберіңіз — баға төмендесе хабарлаймын!",
        "🇺🇦 Украинский": "Ви обрали українську 🇺🇦\nЯ відслідковую ціни на AliExpress, Allegro, Temu, Alibaba, Banggood. Надішліть посилання — і я повідомлю, якщо ціна знизиться!"
    }

    bot.send_message(user_id, greetings[language], reply_markup=kb_unsubscribe)

# --- Отписка ---
@bot.message_handler(func=lambda m: m.text == "❌ Отписаться")
def unsubscribe(message):
    user_id = message.from_user.id
    cursor.execute("DELETE FROM subscribers WHERE user_id = ?", (user_id,))
    conn.commit()
    bot.send_message(user_id, "Вы отписались 🔕", reply_markup=kb_subscribe)

# --- Команды администратора ---
@bot.message_handler(commands=["count"])
def count_subscribers(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ У вас нет доступа")
        return
    cursor.execute("SELECT COUNT(*) FROM subscribers")
    count = cursor.fetchone()[0]
    bot.reply_to(message, f"📊 Подписано пользователей: {count}")

@bot.message_handler(commands=["subscribers"])
def list_subscribers(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ У вас нет доступа")
        return
    cursor.execute("SELECT user_id, language FROM subscribers")
    rows = cursor.fetchall()
    if not rows:
        bot.reply_to(message, "Пока нет подписчиков 😢")
        return
    text = "📋 Список подписчиков:\n\n"
    for user_id, lang in rows:
        text += f"👤 ID: {user_id} | Язык: {lang}\n"
    bot.reply_to(message, text)

# --- Рассылка (только админ) ---
@bot.message_handler(commands=["broadcast"])
def broadcast(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ У вас нет доступа")
        return
    msg = message.text.replace("/broadcast ", "", 1)
    cursor.execute("SELECT user_id FROM subscribers")
    users = cursor.fetchall()
    for (user_id,) in users:
        try:
            bot.send_message(user_id, msg)
        except Exception:
            continue
    bot.reply_to(message, "✅ Рассылка отправлена!")

# --- Запуск бота ---
print("Бот запущен...")
bot.infinity_polling()
