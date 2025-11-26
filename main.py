import telebot
import csv
import time
from datetime import datetime
from telebot import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ===============================
# 🔧 Настройки
# ===============================
BOT_TOKEN = "8590896819:AAFBqrBzbUwKQMSxyORJ1omPOmlWEeZg0QM"
ADMIN_ID = 5991920990  # ID администратора

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}

# ===============================
# 📊 Подключение к Google Sheets
# ===============================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

try:
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("telegram bot").sheet1
    print("✅ Подключение к Google Sheets успешно")
    connected_to_sheets = True
except Exception as e:
    print("❌ Ошибка подключения к Google Sheets:", e)
    sheet = None
    connected_to_sheets = False

# ===============================
# 🚀 Команда /start
# ===============================
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("💬 Оставить заявку")
    markup.add(btn1)

    welcome_text = (
        "👋 Привет!\n\n"
        "Мы команда *FlowPro* — создаём **Telegram-ботов на заказ** для бизнеса.\n\n"
        "🤖 Разрабатываем ботов для приёма заявок, продаж, записи клиентов, "
        "уведомлений и интеграции с CRM.\n\n"
        "Нажмите кнопку ниже, чтобы оставить заявку 👇"
    )

    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=markup)

# ===============================
# 📝 Заполнение заявки
# ===============================
@bot.message_handler(func=lambda message: message.text == "💬 Оставить заявку")
def ask_description(message):
    user_id = message.from_user.id
    user_data[user_id] = {}

    hide_keyboard = types.ReplyKeyboardRemove()
    bot.send_message(
        message.chat.id,
        "Расскажите коротко, какого Telegram-бота вы хотите: "
        "для приёма заявок, продаж, записи клиентов или чего-то другого?",
        reply_markup=hide_keyboard
    )

    bot.register_next_step_handler(message, get_description)

def get_description(message):
    user_id = message.from_user.id
    user_data[user_id]['desc'] = message.text.strip() or "Не указано"
    bot.send_message(message.chat.id, "Как вас зовут?")
    bot.register_next_step_handler(message, get_name)

def get_name(message):
    user_id = message.from_user.id
    user_data[user_id]['name'] = message.text.strip() or "Не указано"

    username = message.from_user.username
    if username:
        user_data[user_id]['telegram'] = f"@{username}"
        finalize_request(message)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        contact_btn = types.KeyboardButton("📱 Отправить свой контакт", request_contact=True)
        markup.add(contact_btn)
        bot.send_message(
            message.chat.id,
            "У вас нет Telegram-username. Пожалуйста, отправьте контакт, чтобы мы могли связаться с вами:",
            reply_markup=markup
        )

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.from_user.id
    phone = message.contact.phone_number if message.contact else "Не указан"
    user_data[user_id]['telegram'] = phone
    finalize_request(message)

def finalize_request(message):
    user_id = message.from_user.id

    text = (
        f"🆕 Новая заявка на создание Telegram-бота\n\n"
        f"Имя: {user_data[user_id].get('name', 'Не указано')}\n"
        f"Контакт: {user_data[user_id].get('telegram', 'Не указан')}\n"
        f"Запрос: {user_data[user_id].get('desc', 'Не указано')}"
    )

    try:
        bot.send_message(ADMIN_ID, text)
        print("✅ Заявка отправлена админу.")
    except Exception as e:
        print("❌ Ошибка при отправке админу:", e)

    try:
        with open("leads.csv", "a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                user_data[user_id].get('name', 'Не указано'),
                user_data[user_id].get('telegram', 'Не указан'),
                user_data[user_id].get('desc', 'Не указано')
            ])
        print("✅ Заявка записана в leads.csv")
    except Exception as e:
        print("❌ Ошибка при записи в CSV:", e)

    if sheet:
        try:
            sheet.append_row([
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                user_data[user_id].get('name', 'Не указано'),
                user_data[user_id].get('telegram', 'Не указан'),
                user_data[user_id].get('desc', 'Не указано')
            ])
            print("✅ Заявка добавлена в Google Sheets")
        except Exception as e:
            print("❌ Ошибка при записи в Google Sheets:", e)
    else:
        print("⚠️ Google Sheets недоступен, заявка сохранена только в CSV")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("💬 Оставить заявку"))

    bot.send_message(
        message.chat.id,
        "✅ Спасибо! Ваша заявка отправлена. Мы свяжемся с вами в Telegram и обсудим создание вашего бота.",
        reply_markup=markup
    )

    user_data.pop(user_id, None)

# ===============================
# 🧠 Запуск бота
# ===============================
if __name__ == "__main__":
    try:
        if connected_to_sheets:
            bot.send_message(ADMIN_ID, "✅ FlowProBot запущен и подключён к Google Sheets.")
        else:
            bot.send_message(ADMIN_ID, "⚠️ FlowProBot запущен, но Sheets недоступен.")
        print("Бот запущен ✅")

        while (True):
            try:
                bot.polling(none_stop = True)
            except Exception as e:
                print("⚠️ Ошибка соединения, перезапуск через 5 секунд:", e)
                time.sleep(5)
    except Exception as e:
        print("❌ Ошибка запуска бота:", e)
