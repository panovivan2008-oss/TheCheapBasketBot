import sqlite3
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

# Загружаем токен и ID админа из .env или Render Environment
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# --- БАЗА ДАННЫХ ---
conn = sqlite3.connect("subscribers.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS subscribers (
    user_id INTEGER PRIMARY KEY,
    language TEXT
)
""")
conn.commit()

# --- КЛАВИАТУРЫ ---
kb_before_subscribe = ReplyKeyboardMarkup(resize_keyboard=True)
kb_before_subscribe.add(KeyboardButton("✅ Подписаться"))

kb_after_subscribe = ReplyKeyboardMarkup(resize_keyboard=True)
kb_after_subscribe.add(KeyboardButton("❌ Отписаться"))

kb_languages = ReplyKeyboardMarkup(resize_keyboard=True)
kb_languages.add("🇷🇺 Русский", "🇬🇧 Английский")
kb_languages.add("🇵🇱 Польский", "🇪🇸 Испанский")
kb_languages.add("🇩🇪 Немецкий", "🇫🇷 Французский")
kb_languages.add("🇰🇿 Казахский", "🇺🇦 Украинский")

# --- ПРОВЕРКА ПОДПИСКИ ---
def is_subscribed(user_id: int) -> bool:
    cursor.execute("SELECT 1 FROM subscribers WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None

# --- /START ---
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = message.from_user.id
    if is_subscribed(user_id):
        await message.answer("Вы уже подписаны ✅", reply_markup=kb_after_subscribe)
    else:
        await message.answer("Привет! Нажмите кнопку ниже, чтобы подписаться на уведомления о товарах.", reply_markup=kb_before_subscribe)

# --- ПОДПИСКА ---
@dp.message_handler(lambda m: m.text == "✅ Подписаться")
async def subscribe(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO subscribers (user_id) VALUES (?)", (user_id,))
    conn.commit()
    await message.answer("Вы подписались ✅\nТеперь выберите язык:", reply_markup=kb_languages)

# --- ВЫБОР ЯЗЫКА ---
@dp.message_handler(lambda m: m.text in [
    "🇷🇺 Русский","🇬🇧 Английский","🇵🇱 Польский","🇪🇸 Испанский",
    "🇩🇪 Немецкий","🇫🇷 Французский","🇰🇿 Казахский","🇺🇦 Украинский"
])
async def choose_language(message: types.Message):
    user_id = message.from_user.id
    language = message.text
    cursor.execute("UPDATE subscribers SET language = ? WHERE user_id = ?", (language, user_id))
    conn.commit()

    await message.answer(f"Язык выбран: {language}\nТеперь просто отправьте ссылку на товар — я помогу найти дешевле!", reply_markup=kb_after_subscribe)

# --- ОТПИСКА ---
@dp.message_handler(lambda m: m.text == "❌ Отписаться")
async def unsubscribe(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("DELETE FROM subscribers WHERE user_id = ?", (user_id,))
    conn.commit()
    await message.answer("Вы отписались 🔕", reply_markup=kb_before_subscribe)

# --- АДМИН-КОМАНДЫ ---
@dp.message_handler(commands=["count"])
async def count_subscribers(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔ Нет доступа.")
    cursor.execute("SELECT COUNT(*) FROM subscribers")
    count = cursor.fetchone()[0]
    await message.answer(f"📊 Подписчиков: {count}")

@dp.message_handler(commands=["subscribers"])
async def show_subscribers(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔ Нет доступа.")
    cursor.execute("SELECT user_id, language FROM subscribers")
    subs = cursor.fetchall()
    if not subs:
        return await message.answer("Подписчиков пока нет 😢")
    text = "\n".join([f"👤 {uid} | {lang}" for uid, lang in subs])
    await message.answer(text[:4000])

# --- Рассылка от админа ---
@dp.message_handler(commands=["send"])
async def admin_send(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔ Нет доступа.")
    text = message.text.replace("/send", "").strip()
    if not text:
        return await message.answer("⚠ Используй так:\n`/send текст или ссылка`", parse_mode="Markdown")

    cursor.execute("SELECT user_id FROM subscribers")
    users = [u[0] for u in cursor.fetchall()]
    sent = 0
    for uid in users:
        try:
            await bot.send_message(uid, text)
            sent += 1
        except:
            pass
    await message.answer(f"✅ Рассылка отправлена {sent} пользователям.")

# --- ЗАПУСК ---
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
