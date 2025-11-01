import os
import sqlite3
from aiogram import Bot, Dispatcher, types, executor

# --- Получаем токен и ID админа из .env ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

if not BOT_TOKEN:
    raise ValueError("Не найден BOT_TOKEN! Проверь .env и Environment Variables на Render.")

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

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

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
    await message.answer(
        "Вы подписались на уведомления ✅\n\nТеперь выберите язык:",
        reply_markup=kb_languages
    )

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

    greetings = {
        "🇷🇺 Русский": "Вы выбрали русский язык 🇷🇺\n\nЯ бот, который может отслеживать цены на товары на платформах: AliExpress, Allegro, Temu, Alibaba, Banggood.\nПросто отправьте ссылку — и я помогу найти товар дешевле или сообщу, если цена упадет!",
        "🇬🇧 Английский": "You selected English 🌐\n\nI am a bot that can track prices of products on: AliExpress, Allegro, Temu, Alibaba, Banggood.\nJust send me a link — and I will help find the product cheaper or notify if the price drops!",
        "🇵🇱 Польский": "Wybrałeś język polski 🇵🇱\n\nJestem botem, który może śledzić ceny produktów na platformach: AliExpress, Allegro, Temu, Alibaba, Banggood.\nPo prostu wyślij link — a ja pomogę znaleźć produkt taniej lub powiadomię, jeśli cena spadnie!",
        "🇪🇸 Испанский": "Has seleccionado Español 🇪🇸\n\nSoy un bot que puede rastrear los precios de productos en: AliExpress, Allegro, Temu, Alibaba, Banggood.\nSimplemente envía un enlace — y te ayudaré a encontrar el producto más barato o te avisaré si el precio baja!",
        "🇩🇪 Немецкий": "Du hast Deutsch 🇩🇪 gewählt\n\nIch bin ein Bot, der die Preise von Produkten auf Plattformen wie AliExpress, Allegro, Temu, Alibaba, Banggood verfolgen kann.\nSchicke einfach einen Link — ich helfe dir, das Produkt günstiger zu finden oder benachrichtige, wenn der Preis fällt!",
        "🇫🇷 Французский": "Vous avez choisi Français 🇫🇷\n\nJe suis un bot qui peut suivre les prix de produits sur : AliExpress, Allegro, Temu, Alibaba, Banggood.\nEnvoyez simplement un lien — et je vous aiderai à trouver le produit moins cher ou vous avertirai si le prix baisse !",
        "🇰🇿 Казахский": "Сіз қазақ тілін таңдадыңыз 🇰🇿\n\nМен — AliExpress, Allegro, Temu, Alibaba, Banggood платформаларындағы тауарлардың бағаларын бақылауға арналған ботпын.\nСілтемені жіберіңіз — мен тауарды арзан табуға көмектесемін немесе баға төмендесе хабарлаймын!",
        "🇺🇦 Украинский": "Ви обрали українську 🇺🇦\n\nЯ бот, який може відслідковувати ціни на товари на платформах: AliExpress, Allegro, Temu, Alibaba, Banggood.\nПросто надішліть посилання — і я допоможу знайти товар дешевше або повідомлю, якщо ціна впаде!"
    }

    await message.answer(greetings.get(language, "Язык не поддерживается"), reply_markup=kb_after_subscribe)

# --- ОТПИСКА ---
@dp.message_handler(lambda m: m.text == "❌ Отписаться")
async def unsubscribe(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("DELETE FROM subscribers WHERE user_id = ?", (user_id,))
    conn.commit()
    await message.answer(
        "Вы отписались от уведомлений 🔕\nВаши данные удалены из базы.",
        reply_markup=kb_before_subscribe
    )

# --- КОМАНДЫ АДМИНА ---
@dp.message_handler(commands=["count"])
async def count_subscribers(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    cursor.execute("SELECT COUNT(*) FROM subscribers")
    count = cursor.fetchone()[0]
    await message.answer(f"📊 Сейчас подписано пользователей: {count}")

@dp.message_handler(commands=["subscribers"])
async def show_subscribers(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    cursor.execute("SELECT user_id, language FROM subscribers")
    rows = cursor.fetchall()
    if not rows:
        await message.answer("Пока нет подписчиков 😢")
        return

    text = "📋 Список подписчиков:\n\n"
    for user_id, lang in rows:
        text += f"👤 ID: {user_id} | Язык: {lang}\n"

    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(text)

# --- РАССЫЛКА ДЛЯ АДМИНА ---
@dp.message_handler(commands=["broadcast"])
async def broadcast(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Только админ может отправлять рассылку.")
        return

    text = message.get_args()
    if not text:
        await message.answer("❗ Используйте команду: /broadcast ТЕКСТ_СООБЩЕНИЯ")
        return

    cursor.execute("SELECT user_id FROM subscribers")
    users = cursor.fetchall()
    for (user_id,) in users:
        try:
            await bot.send_message(user_id, text)
        except:
            continue

    await message.answer(f"✅ Сообщение отправлено {len(users)} подписчикам.")

# --- ЗАПУСК БОТА ---
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
