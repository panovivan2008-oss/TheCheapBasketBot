import os
from flask import Flask, request
import telebot

TOKEN = os.getenv("7082898376:AAHbxzKe4HlQMMQMxv31J_lo9olKDoU9MH8")
import os
import telebot

# Берём токен из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")

# Создаём бота
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route("/" + TOKEN, methods=["POST"])
def webhook():
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "OK", 200

# Установим webhook на Render
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
bot.remove_webhook()
bot.set_webhook(url=WEBHOOK_URL)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
