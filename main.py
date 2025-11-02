# main.py
from flask import Flask, request
import telebot
import os

# ===== Настройки =====
TOKEN = os.getenv("BOT_TOKEN")  # Твой токен бота из Render Environment
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # URL твоего сайта Render

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ===== Обработчики команд =====
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "👋 Привет! Бот успешно запущен и работает через Render!")

@bot.message_handler(commands=['help'])
def help_message(message):
    bot.reply_to(message, "🛠 Команды:\n/start — запустить бота\n/help — помощь")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.send_message(message.chat.id, f"Ты написал: {message.text}")

# ===== Flask маршруты =====
@app.route("/", methods=["GET"])
def index():
    return "✅ Bot is running via Render!", 200

@app.route("/", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_str = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return "", 200
    else:
        return "Unsupported Media Type", 415

# ===== Запуск приложения =====
if __name__ == "__main__":
    if WEBHOOK_URL:
        bot.remove_webhook()
        bot.set_webhook(url=WEBHOOK_URL)
        print(f"✅ set_webhook -> True WEBHOOK_URL: {WEBHOOK_URL}")
    else:
        print("⚠️ WEBHOOK_URL не задан! Укажи его в Render Environment Variables.")
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)



