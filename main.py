from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Вызови это перед bot.infinity_polling()
keep_alive()




import telebot
import sqlite3
import threading
import time
import schedule
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

# --- НАСТРОЙКИ ---
TOKEN = "8538630326:AAF9z-OU-So_b4YCw3buiAKyFHK3A10aiP8" # Вставь токен сюда
bot = telebot.TeleBot(TOKEN)

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('life.db')
    cursor = conn.cursor()
    # Создаем таблицу: ID, дата рождения, желаемый возраст
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            birth_date TEXT,
            lifespan INTEGER
        )
    ''')
    conn.commit()
    conn.close()

# --- ГЕНЕРАЦИЯ КАРТИНКИ (САМОЕ ИНТЕРЕСНОЕ) ---
def create_life_calendar(birth_date_str, lifespan_years):
    birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
    today = datetime.now()
    
    # Расчеты
    total_weeks = lifespan_years * 52
    weeks_lived = int((today - birth_date).days / 7)
    
    # Настройки рисования
    cols = 52  # 52 недели в строке (один год)
    rows = lifespan_years
    box_size = 10 # Размер квадратика
    padding = 2   # Отступ между квадратиками
    margin = 20   # Отступ от краев картинки
    
    # Размер итоговой картинки
    width = (box_size + padding) * cols + margin * 2
    height = (box_size + padding) * rows + margin * 2 + 50 # +50 для текста снизу
    
    # Создаем белый фон
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # Рисуем квадратики
    for i in range(total_weeks):
        row = i // cols
        col = i % cols
        
        x1 = margin + col * (box_size + padding)
        y1 = margin + row * (box_size + padding)
        x2 = x1 + box_size
        y2 = y1 + box_size
        
        if i < weeks_lived:
            color = 'black' # Прожитая неделя
        elif i == weeks_lived:
            color = 'red'   # Текущая неделя
        else:
            color = 'lightgray' # Будущее
            
        draw.rectangle([x1, y1, x2, y2], fill=color)

    # Добавляем текст снизу
    weeks_left = total_weeks - weeks_lived
    text = f"Прожито: {weeks_lived} | Осталось: {weeks_left} недель"
    # Пытаемся использовать стандартный шрифт, если нет - по умолчанию
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()
        
    draw.text((margin, height - 40), text, fill="black", font=font)
    
    # Сохраняем во временный файл
    filename = f"calendar_{weeks_lived}.png"
    img.save(filename)
    return filename

# --- КОМАНДЫ БОТА ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, 
                 "Привет! Я Календарь Жизни.\n"
                 "Давай настроим твой календарь.\n"
                 "Введи команду в формате:\n"
                 "/set ГГГГ-ММ-ДД ВОЗРАСТ\n\n"
                 "Пример (родился 2 мая 2009, хочет прожить 80):\n"
                 "/set 2009-05-02 80")

@bot.message_handler(commands=['set'])
def set_user_data(message):
    try:
        # Разбираем сообщение: /set 2009-05-02 80
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "Ошибка формата. Пиши так: /set 2009-05-02 80")
            return
            
        date_str = parts[1]
        lifespan = int(parts[2])
        
        # Проверяем, что дата правильная
        datetime.strptime(date_str, "%Y-%m-%d")
        
        # Сохраняем в базу
        conn = sqlite3.connect('life.db')
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO users (user_id, birth_date, lifespan) VALUES (?, ?, ?)', 
                       (message.chat.id, date_str, lifespan))
        conn.commit()
        conn.close()
        
        bot.reply_to(message, "Данные сохранены! Сейчас сгенерирую твой календарь...")
        
        # Сразу отправляем картинку для теста
        img_path = create_life_calendar(date_str, lifespan)
        with open(img_path, 'rb') as photo:
            bot.send_photo(message.chat.id, photo, caption="Вот твоя жизнь. Черное — прошлое, серое — будущее.")
            
    except ValueError:
        bot.reply_to(message, "Неверный формат даты или числа. Проверь пример: /set 2009-05-02 80")

# --- РАССЫЛКА (РАЗ В НЕДЕЛЮ) ---
def send_weekly_notifications():
    conn = sqlite3.connect('life.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, birth_date, lifespan FROM users")
    users = cursor.fetchall()
    conn.close()
    
    for user in users:
        user_id, bdate, life = user
        try:
            img_path = create_life_calendar(bdate, life)
            with open(img_path, 'rb') as photo:
                bot.send_photo(user_id, photo, caption="Неделя прошла. Время не вернуть. Действуй.")
        except Exception as e:
            print(f"Не удалось отправить пользователю {user_id}: {e}")

# Функция запуска планировщика
def run_scheduler():
    # Ставим рассылку, например, на понедельник в 09:00 утра
    schedule.every().monday.at("09:00").do(send_weekly_notifications)
    
    # Для ТЕСТА (раскомментируй строку ниже, чтобы проверить работу каждую минуту)
    # schedule.every(1).minutes.do(send_weekly_notifications)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# --- ЗАПУСК ---
if __name__ == '__main__':
    init_db()
    
    # Запускаем планировщик в отдельном потоке
    thread = threading.Thread(target=run_scheduler)
    thread.start()
    
    print("Бот запущен...")
    bot.infinity_polling()