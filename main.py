import os
import csv
from datetime import datetime
from urllib import request

import telebot
from flask import Flask
from telebot import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ===============================
# Настройки
# ===============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ADMIN_ID = 5991920990

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
user_data = {}

# ===============================
# Google Sheets
# ===============================
try:
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("telegram bot").sheet1
    connected_to_sheets = True
    print("Sheets OK")
except Exception as e:
    print("Sheets ERROR:", e)
    sheet = None
    connected_to_sheets = False

# ===============================
# /start
# ===============================
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Оставить заявку"))
    bot.send_message(
        message.chat.id,
        "Привет! Я — FlowPro Bot.\nНажми кнопку ниже, чтобы оставить заявку.",
        reply_markup=markup
    )

# ===============================
# Заявка — шаги
# ===============================
@bot.message_handler(func=lambda m: m.text == "Оставить заявку")
def ask_description(message):
    user_data[message.from_user.id] = {}
    bot.send_message(message.chat.id, "Опиши, какой бот нужен:")
    bot.register_next_step_handler(message, get_description)

def get_description(message):
    user_data[message.from_user.id]['desc'] = message.text
    bot.send_message(message.chat.id, "Как тебя зовут?")
    bot.register_next_step_handler(message, get_name)

def get_name(message):
    user_data[message.from_user.id]['name'] = message.text
    if message.from_user.username:
        user_data[message.from_user.id]['contact'] = f"@{message.from_user.username}"
        finalize(message)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton("Отправить контакт", request_contact=True))
        bot.send_message(message.chat.id, "Отправь свой номер:", reply_markup=markup)

@bot.message_handler(content_types=['contact'])
def save_contact(message):
    user_data[message.from_user.id]['contact'] = message.contact.phone_number
    finalize(message)

# ===============================
# Финализация
# ===============================
def finalize(message):
    uid = message.from_user.id
    data = user_data[uid]

    # сообщение админу
    bot.send_message(
        ADMIN_ID,
        f"Новая заявка\n\nИмя: {data['name']}\nКонтакт: {data['contact']}\nОписание: {data['desc']}"
    )

    # запись в CSV
    with open("leads.csv", "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            data['name'], data['contact'], data['desc']
        ])

    # Google Sheets
    if sheet:
        try:
            sheet.append_row([
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                data['name'], data['contact'], data['desc']
            ])
        except Exception as e:
            print("Sheets Append ERROR:", e)

    # ответ пользователю
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Оставить заявку"))
    bot.send_message(message.chat.id, "Заявка принята!", reply_markup=markup)

    user_data.pop(uid, None)

# ===============================
# Webhook (Render)
# ===============================
@app.route("/webhook", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.data.decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

# ===============================
# Запуск
# ===============================
if __name__ == "__main__":
    try:
        bot.send_message(ADMIN_ID, "FlowPro Bot запущен!")
    except:
        pass

    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")

    port = int(os.environ.get("PORT", 10000))
    print(f"Запущено на порту {port}")
    app.run(host="0.0.0.0", port=port)
