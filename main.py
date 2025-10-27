import telebot
import os

# Берём токен из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("Не найден BOT_TOKEN! Проверь Environment Variables на Render.")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "Привет! Бот работает 🎉")

@bot.message_handler(func=lambda m: True)
def echo_all(message):
    bot.reply_to(message, f"Ты написал: {message.text}")

# Запуск бота
bot.infinity_polling()
