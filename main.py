import telebot
import sqlite3
import threading
import time
import schedule
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from flask import Flask

app = Flask('')
@app.route('/')
def home(): return "OK"
def run_flask(): app.run(host='0.0.0.0', port=8080)

TOKEN = "8538630326:AAF9z-OU-So_b4YCw3buiAKyFHK3A10aiP8"
bot = telebot.TeleBot(TOKEN)

def init_db():
    conn = sqlite3.connect('life.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, birth_date TEXT, lifespan INTEGER)')
    conn.commit()
    conn.close()

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
            x, y = margin + col*(box_size+padding), margin + row*(box_size+padding)
            color = 'black' if i < weeks_lived else ('red' if i == weeks_lived else 'lightgray')
            draw.rectangle([x, y, x + box_size, y + box_size], fill=color)

        # ТЕКСТ НА РУССКОМ
        text = f"Прожито: {weeks_lived} нед. | Осталось: {total_weeks - weeks_lived} нед."
        
        # ПРОВЕРКА ШРИФТА (ищем загруженный arial.ttf)
        font_file = "arial.ttf"
        try:
            if os.path.exists(font_file):
                font = ImageFont.truetype(font_file, 16)
                draw.text((margin, height - 40), text, fill="black", font=font)
            else:
                # Если файла нет, пишем стандартным (могут быть ромбики)
                draw.text((margin, height - 40), text, fill="black")
        except:
            draw.text((margin, height - 40), text, fill="black")
        
        img.save("calendar.png")
        return "calendar.png"
    except Exception as e:
        print(f"Error: {e}")
        return None

@bot.message_handler(commands=['start'])
def start(m): bot.reply_to(m, "Привет! Введи дату рождения: /set ГГГГ-ММ-ДД ВОЗРАСТ")

@bot.message_handler(commands=['set'])
def set_data(m):
    try:
        _, date_str, life = m.text.split()
        conn = sqlite3.connect('life.db')
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO users VALUES (?, ?, ?)', (m.chat.id, date_str, int(life)))
        conn.commit()
        conn.close()
        path = create_life_calendar(date_str, int(life))
        with open(path, 'rb') as f: bot.send_photo(m.chat.id, f, caption="Календарь обновлен!")
    except: bot.reply_to(m, "Ошибка! Формат: /set 2000-01-01 80")

def run_scheduler():
    schedule.every().monday.at("09:00").do(lambda: print("Рассылка..."))
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    init_db()
    threading.Thread(target=run_scheduler, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    run_flask()
