import telebot
import time

import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Бот запущен и работает 24/7!")

while True:
    try:
        bot.polling(none_stop=True, interval=0)
    except Exception as e:
        print("Ошибка:", e)
        time.sleep(5)
