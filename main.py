from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import sqlite3, os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

conn = sqlite3.connect("subscribers.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS subscribers (
    user_id INTEGER PRIMARY KEY,
    language TEXT
)
""")
conn.commit()

kb_before_subscribe = ReplyKeyboardMarkup(resize_keyboard=True)
kb_before_subscribe.add(KeyboardButton("✅ Подписаться"))

kb_after_subscribe = ReplyKeyboardMarkup(resize_keyboard=True)
kb_after_subscribe.add(KeyboardButton("❌ Отписаться"))

kb_languages = ReplyKeyboardMarkup(resize_keyboard=True)
kb_languages.add("🇷🇺 Русский", "🇬🇧 Английский", "🇵🇱 Польский", "🇪🇸 Испанский")
kb_languages.add("🇩🇪 Немецкий", "🇫🇷 Французский", "🇰🇿 Казахский", "🇺🇦 Украинский")

def is_subscribed(user_id: int) -> bool:
    cursor.execute("SELECT 1 FROM subscribers WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = message.from_user.id
    if is_subscribed(user_id):
        await message.answer("Вы уже подписаны ✅", reply_markup=kb_after_subscribe)
    else:
        await message.answer("Привет! Нажмите кнопку ниже, чтобы подписаться на уведомления.", reply_markup=kb_before_subscribe)

@dp.message_handler(lambda m: m.text == "✅ Подписаться")
async def subscribe(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO subscribers (user_id) VALUES (?)", (user_id,))
    conn.commit()
    await message.answer("Вы подписались ✅\nВыберите язык:", reply_markup=kb_languages)

@dp.message_handler(lambda m: m.text in [
    "🇷🇺 Русский","🇬🇧 Английский","🇵🇱 Польский","🇪🇸 Испанский",
    "🇩🇪 Немецкий","🇫🇷 Французский","🇰🇿 Казахский","🇺🇦 Украинский"
])
async def choose_language(message: types.Message):
    user_id = message.from_user.id
    language = message.text
    cursor.execute("UPDATE subscribers SET language = ? WHERE user_id = ?", (language, user_id))
    conn.commit()
    await message.answer(f"Вы выбрали язык {language} 🌍", reply_markup=kb_after_subscribe)

@dp.message_handler(lambda m: m.text == "❌ Отписаться")
async def unsubscribe(message: types.Message):
    cursor.execute("DELETE FROM subscribers WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    await message.answer("Вы отписались 🔕", reply_markup=kb_before_subscribe)

# Команда для админа: отправить сообщение всем
@dp.message_handler(commands=["broadcast"])
async def broadcast(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        await message.answer("✍️ Введите текст после команды /broadcast")
        return
    cursor.execute("SELECT user_id FROM subscribers")
    users = cursor.fetchall()
    sent = 0
    for (uid,) in users:
        try:
            await bot.send_message(uid, text)
            sent += 1
        except:
            pass
    await message.answer(f"📢 Рассылка завершена. Отправлено {sent} пользователям.")

@dp.message_handler(commands=["count"])
async def count_subscribers(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        cursor.execute("SELECT COUNT(*) FROM subscribers")
        count = cursor.fetchone()[0]
        await message.answer(f"👥 Подписчиков: {count}")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
