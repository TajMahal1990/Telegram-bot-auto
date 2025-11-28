

import os
import csv
from datetime import datetime
import telebot
from telebot import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ===============================
# Настройки
# ===============================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8590896819:AAFBqrBzbUwKQMSxyORJ1omPOmlWEeZg0QM")
ADMIN_ID = 5991920990

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}

# ===============================
# Google Sheets (опционально)
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
    print("Подключение к Google Sheets — УСПЕШНО")
except Exception as e:
    print("Google Sheets недоступен:", e)
    sheet = None
    connected_to_sheets = False

# ===============================
# /start
# ===============================
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Оставить заявку"))

    text = (
        "Привет!\n\n"
        "Мы команда *FlowPro* — создаём **Telegram-ботов на заказ** для бизнеса.\n\n"
        "Приём заявок · Автоматизация продаж · Запись клиентов · Интеграция с CRM\n\n"
        "Нажми кнопку ниже и расскажи, какой бот тебе нужен"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)


# ===============================
# Заявка — пошагово
# ===============================
@bot.message_handler(func=lambda m: m.text == "Оставить заявку")
def ask_description(message):
    user_data[message.from_user.id] = {}
    bot.send_message(message.chat.id, "Коротко опиши, какой бот тебе нужен:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, get_description)

def get_description(message):
    user_data[message.from_user.id]['desc'] = message.text.strip() or "Не указано"
    bot.send_message(message.chat.id, "Как тебя зовут?")
    bot.register_next_step_handler(message, get_name)

def get_name(message):
    user_data[message.from_user.id]['name'] = message.text.strip() or "Не указано"

    if message.from_user.username:
        user_data[message.from_user.id]['contact'] = f"@{message.from_user.username}"
        finalize_request(message)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton("Отправить контакт", request_contact=True))
        bot.send_message(message.chat.id, "Отправь свой контакт, чтобы мы могли написать:", reply_markup=markup)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    phone = message.contact.phone_number if message.contact else "Не указан"
    user_data[message.from_user.id]['contact'] = phone
    finalize_request(message)


# ===============================
# Финализация и запись
# ===============================
def finalize_request(message):
    uid = message.from_user.id
    data = user_data[uid]

    # Сообщение админу
    admin_text = (
        f"Новая заявка на бота\n\n"
        f"Имя: {data.get('name')}\n"
        f"Контакт: {data.get('contact')}\n"
        f"Задача: {data.get('desc')}"
    )
    bot.send_message(ADMIN_ID, admin_text)

    # Запись в CSV
    try:
        with open("leads.csv", "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                data.get('name'),
                data.get('contact'),
                data.get('desc')
            ])
    except Exception as e:
        print("Ошибка CSV:", e)

    # Запись в Google Sheets
    if sheet:
        try:
            sheet.append_row([
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                data.get('name'),
                data.get('contact'),
                data.get('desc')
            ])
        except Exception as e:
            print("Ошибка Google Sheets:", e)

    # Ответ пользователю
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Оставить заявку"))
    bot.send_message(
        message.chat.id,
        "Спасибо! Заявка принята.\nСкоро напишу тебе в личку и обсудим твой бот",
        reply_markup=markup
    )

    user_data.pop(uid, None)


# ===============================
# ЗАПУСК — РАБОТАЕТ НА RAILWAY, Render, VPS, Heroku
# ===============================
if __name__ == "__main__":
    # Уведомление админу при старте
    status = "и подключён к Google Sheets" if connected_to_sheets else ""
    try:
        bot.send_message(ADMIN_ID, f"FlowProBot запущен {status}")
    except:
        pass

    print("Бот запущен — работаем на вебхуках")

    # Полностью совместим с Railway / Render / любой хостинг
    port = int(os.environ.get("PORT", 10000))
    bot.remove_webhook()                    # на всякий случай
    bot.run_webhook(
        listen="0.0.0.0",
        port=port,
        webhook_url=""                      # можно оставить пустым
    )