import telebot
import requests
import sqlite3
import os
from groq import Groq


BOT_TOKEN = ""
GROQ_API_KEY = ""

# База данных
conn = sqlite3.connect('weather_bot.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, city TEXT)''')
conn.commit()

def save_city(user_id, city):
    cursor.execute('INSERT OR REPLACE INTO users (user_id, city) VALUES (?, ?)', (user_id, city))
    conn.commit()

def get_user_city(user_id):
    cursor.execute('SELECT city FROM users WHERE user_id = ?', (user_id,))
    res = cursor.fetchone()
    return res[0] if res else None

# Инициализация клиента Groq и бота
client = Groq(api_key=GROQ_API_KEY)
bot = telebot.TeleBot(BOT_TOKEN)

def get_ai_quote(temp):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": f"Придумай одну короткую мемную цитату на русском для погоды {temp}°C. Только цитату, без лишних слов!"
            }
        ]
    )
    return response.choices[0].message.content

def get_forecast(city):
    response = requests.get(f"https://wttr.in/{city}?format=j1")
    data = response.json()
    forecast_text = f"📅 Прогноз для {city}:\n\n"

    for day in data["weather"][:3]:
        date = day["date"]
        max_temp = day["maxtempC"]
        min_temp = day["mintempC"]
        avg_temp = day["avgtempC"]

        desc = day["hourly"][4]["lang_ru"][0]["value"] if "lang_ru" in day["hourly"][4] else \
        day["hourly"][4]["weatherDesc"][0]["value"]

        forecast_text += f"🔹 {date}: {min_temp}°C...{max_temp}°C (в среднем {avg_temp}°C), {desc}\n"

    return forecast_text

@bot.message_handler(commands=["forecast"])
def forecast(message):
    user_id = message.from_user.id
    args = message.text.split()
    city = args[1] if len(args) > 1 else get_user_city(user_id)

    if not city:
        bot.send_message(message.chat.id, "⚠ Напиши город! Например: /forecast Киев")
        return

    try:
        save_city(user_id, city)
        text = get_forecast(city)
        bot.send_message(message.chat.id, text)
    except Exception as e:
        bot.send_message(message.chat.id, "Не удалось получить прогноз.")

def get_weather(city):
    response = requests.get(f"https://wttr.in/{city}?format=j1")
    data = response.json()
    temp = data["current_condition"][0]["temp_C"]
    wind = data["current_condition"][0]["windspeedKmph"]
    return temp, wind

@bot.message_handler(commands=["start", "help"])
def start(message):
    bot.send_message(message.chat.id, "Привет!")
    text = (
        "Вот что я умею:\n"
        "/weather Киев — погода в городе\n"
        "/wind Киев — ветер в городе\n"
        "/help — список команд\n"
        "/forecast — прогноз погоды наперед "
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=["weather"])
def weather(message):
    user_id = message.from_user.id
    args = message.text.split()
    city = args[1] if len(args) > 1 else get_user_city(user_id)

    if not city:
        bot.send_message(message.chat.id, "⚠ Напиши город! Например: /weather Киев")
        return

    try:
        save_city(user_id, city)
        temp, wind = get_weather(city)
        quote = get_ai_quote(temp)
        bot.send_message(message.chat.id, f"Сейчас в {city}: {temp}°C 🌡️\n\n{quote}")
    except Exception:
        bot.send_message(message.chat.id, "Город не найден!")

@bot.message_handler(commands=["wind"])
def wind(message):
    user_id = message.from_user.id
    args = message.text.split()
    city = args[1] if len(args) > 1 else get_user_city(user_id)

    if not city:
        bot.send_message(message.chat.id, "⚠ Напиши город! Например: /wind Киев")
        return

    try:
        save_city(user_id, city)
        temp, wind_speed = get_weather(city)
        bot.send_message(message.chat.id, f'Сейчас ветер в {city}: {wind_speed} km/h ')
    except Exception:
        bot.send_message(message.chat.id, "Город не найден!")

@bot.message_handler(func=lambda message: True)
def unknown(message):
    bot.send_message(message.chat.id, "Увы такой команды нет! Напиши /help")

bot.polling(none_stop=True)