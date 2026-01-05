import telebot
import sqlite3
import threading
import time
import schedule
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from flask import Flask

# --- СЕРВЕР ДЛЯ ПОДДЕРЖКИ ЖИЗНИ (KEEP ALIVE) ---
app = Flask('')

@app.route('/')
def home():
    return "OK"

def run_flask():
    # Порт 8080 для Render
    app.run(host='0.0.0.0', port=8080)

# --- НАСТРОЙКИ БОТА ---
TOKEN = "8538630326:AAF9z-OU-So_b4YCw3buiAKyFHK3A10aiP8"
bot = telebot.TeleBot(TOKEN)

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('life.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            birth_date TEXT,
            lifespan INTEGER
        )
    ''')
    conn.commit()
    conn.close()

# --- ГЕНЕРАЦИЯ КАРТИНКИ ---
def create_life_calendar(birth_date_str, lifespan_years):
    try:
        birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
        today = datetime.now()
        
        total_weeks = lifespan_years * 52
        weeks_lived = int((today - birth_date).days / 7)
        
        cols, rows = 52, lifespan_years
        box_size, padding, margin = 10, 2, 20
        width = (box_size + padding) * cols + margin * 2
        height = (box_size + padding) * rows + margin * 2 + 50
        
        img = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(img)
        
        for i in range(total_weeks):
            row, col = i // cols, i % cols
            x1 = margin + col * (box_size + padding)
            y1 = margin + row * (box_size + padding)
            x2, y2 = x1 + box_size, y1 + box_size
            
            if i < weeks_lived:
                color = 'black'
            elif i == weeks_lived:
                color = 'red' # Текущая неделя
            else:
                color = 'lightgray'
            draw.rectangle([x1, y1, x2, y2], fill=color)

        # Текст на русском для картинки
        text = f"Прожито: {weeks_lived} нед. | Осталось: {total_weeks - weeks_lived} нед."
        
        # Проверка наличия файла шрифта arial.ttf в папке проекта
        font_file = "arial.ttf"
        try:
            if os.path.exists(font_file):
                font = ImageFont.truetype(font_file, 16)
                draw.text((margin, height - 40), text, fill="black", font=font)
            else:
                # Если шрифта нет, используем стандартный (могут быть ромбики)
                draw.text((margin, height - 40), text, fill="black")
        except:
            draw.text((margin, height - 40), text, fill="black")
        
        filename = "calendar.png"
        img.save(filename)
        return filename
    except Exception as e:
        print(f"Ошибка отрисовки: {e}")
        return None

# --- ОБРАБОТКА КОМАНД ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Исправленное приветственное сообщение по твоей просьбе
    welcome_text = (
        "Привет! Я твой Календарь Жизни.\n"
        "Введи дату рождения и сколько лет планируешь прожить.\n"
        "Пример: /set 2000-01-01 80"
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['set'])
def set_user_data(message):
    try:
        # Разбиваем сообщение пользователя
        parts = message.text.split()
        if len(parts) < 3:
            raise ValueError("Недостаточно данных")
            
        date_str, lifespan = parts[1], int(parts[2])
        # Проверка формата даты
        datetime.strptime(date_str, "%Y-%m-%d")
        
        # Сохраняем в базу (чтобы бот помнил пользователя после перезагрузки)
        conn = sqlite3.connect('life.db')
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO users (user_id, birth_date, lifespan) VALUES (?, ?, ?)', 
                       (message.chat.id, date_str, lifespan))
        conn.commit()
        conn.close()
        
        # Создаем и отправляем календарь
        img_path = create_life_calendar(date_str, lifespan)
        if img_path:
            with open(img_path, 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption="Твой персональный календарь готов!")
        
    except Exception:
        bot.reply_to(message, "Ошибка! Пожалуйста, используй формат:\n/set ГГГГ-ММ-ДД ВОЗРАСТ\nПример: /set 2000-01-01 80")

# --- ПЛАНИРОВЩИК (РАССЫЛКА ПО ПОНЕДЕЛЬНИКАМ) ---
def send_weekly_notifications():
    conn = sqlite3.connect('life.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, birth_date, lifespan FROM users")
    users = cursor.fetchall()
    conn.close()
    
    for user_id, bdate, life in users:
        try:
            img_path = create_life_calendar(bdate, life)
            if img_path:
                with open(img_path, 'rb') as photo:
                    bot.send_photo(user_id, photo, caption="Началась новая неделя. Твой календарь обновился!")
        except Exception as e:
            print(f"Не удалось отправить уведомление {user_id}: {e}")

def run_scheduler():
    # Проверка каждую неделю в понедельник в 09:00
    schedule.every().monday.at("09:00").do(send_weekly_notifications)
    while True:
        schedule.run_pending()
        time.sleep(60)

# --- ЗАПУСК ВСЕХ ПРОЦЕССОВ ---
if __name__ == '__main__':
    init_db()
    
    # 1. Запуск планировщика в отдельном потоке
    threading.Thread(target=run_scheduler, daemon=True).start()
    
    # 2. Запуск самого бота
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    
    # 3. Запуск Flask-сервера для Render (в основном потоке)
    run_flask()
