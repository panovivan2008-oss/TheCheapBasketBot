import telebot
import time

TOKEN = "7082898376:AAHbxzKe4HlQMMQMxv31J_lo9olKDoU9MH8"

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
