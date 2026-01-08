import asyncio
import random
import logging
import sqlite3
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

API_TOKEN = os.getenv("API_TOKEN")

# ----------------- DB -----------------
conn = sqlite3.connect("bot.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    style TEXT,
    streak INTEGER DEFAULT 0,
    last_done TEXT,
    last_motivation TEXT
)
""")
conn.commit()

# ----------------- TEXTS -----------------
MOTIVATION = {
    "hard": [
        "Ніхто не зобовʼязаний робити це за тебе. Вставай і працюй.",
        "Ти втомився? А результатам байдуже.",
        "Дисципліна — це робити, навіть коли не хочеться.",
        "Ще один день або ще одна відмазка?",
        "Поки ти думаєш — хтось уже робить.",
    ],
    "soft": [
        "Один маленький крок сьогодні — велика різниця завтра 💙",
        "Ти не повинен бути ідеальним. Просто будь наполегливим.",
        "Навіть 10 хвилин — це вже прогрес.",
        "Дихай. Зберися. Зроби один крок.",
    ]
}

IGNORE_TEXT = {
    "hard": [
        "Другий день тиші. Це і є твій максимум?",
        "Ти зупинився. Чому?",
        "Ніхто не прийде і не змусить. Або ти, або ніхто.",
        "Ти обіцяв собі більше, ніж це.",
        "Пропуск — це теж вибір."
    ],
    "soft": [
        "Я помітив паузу. Можемо спробувати сьогодні 💙",
        "Нічого страшного. Повернемося до руху?",
        "Навіть після паузи можна продовжити.",
        "Ти не зламався. Просто зроби маленький крок.",
        "Я тут, коли будеш готовий."
    ]
}

# ----------------- QUOTES -----------------
QUOTES = [
    "Успіх приходить до тих, хто щодня робить маленькі кроки.",
    "Не чекай натхнення — створюй його сам.",
    "Кожен день — нова можливість стати кращим.",
    "Дисципліна сильніше мотивації.",
    "Помилки — це сходинки до успіху.",
    "Великі зміни починаються з маленьких кроків.",
    "Ти сильніший, ніж думаєш.",
    "Сьогоднішня праця — завтрашній результат."
]

# ----------------- BOT -----------------
bot = Bot(API_TOKEN)
dp = Dispatcher()

# ----------------- KEYBOARDS -----------------
style_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="💪 Жорстко"), KeyboardButton(text="😌 Підтримка")]],
    resize_keyboard=True
)

menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔥 Мотивація")],
        [KeyboardButton(text="✅ Зробив"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="⚙️ Стиль"), KeyboardButton(text="📜 Цитата дня")]
    ],
    resize_keyboard=True
)

# ----------------- HANDLERS -----------------
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("Привіт! Я мотиваційний бот 💪\nОбери стиль мотивації:", reply_markup=style_kb)

@dp.message(F.text.in_(["💪 Жорстко", "😌 Підтримка"]))
async def choose_style(message: Message):
    style = "hard" if "Жорстко" in message.text else "soft"
    cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, style, streak, last_done)
        VALUES (?, ?, COALESCE((SELECT streak FROM users WHERE user_id=?),0), NULL)
    """, (message.from_user.id, style, message.from_user.id))
    conn.commit()
    await message.answer("Стиль збережено ✅ Ось твоє меню 👇", reply_markup=menu_kb)

# ----------------- MENU BUTTONS -----------------
@dp.message(F.text.in_(["🔥 Мотивація"]))
async def manual_motivation(message: Message):
    cursor.execute("SELECT style FROM users WHERE user_id=?", (message.from_user.id,))
    row = cursor.fetchone()
    if not row:
        await message.answer("Спочатку /start")
        return
    style = row[0]
    await message.answer(random.choice(MOTIVATION[style]), reply_markup=menu_kb)

@dp.message(F.text.in_(["✅ Зробив"]))
async def done_btn(message: Message):
    await done(message)

@dp.message(F.text.in_(["📊 Статистика"]))
async def stats_btn(message: Message):
    await stats(message)

@dp.message(F.text.in_(["⚙️ Стиль"]))
async def change_style_btn(message: Message):
    await message.answer("Обери новий стиль:", reply_markup=style_kb)

# ----------------- QUOTE BUTTON -----------------
@dp.message(F.text == "📜 Цитата дня")
async def send_quote(message: Message):
    quote = random.choice(QUOTES)
    await message.answer(f"📜 Цитата дня:\n\n{quote}", reply_markup=menu_kb)

# ----------------- COMMANDS -----------------
@dp.message(Command("done"))
async def done(message: Message):
    today = datetime.utcnow().date().isoformat()
    cursor.execute("SELECT last_done, streak FROM users WHERE user_id=?", (message.from_user.id,))
    row = cursor.fetchone()
    if not row:
        await message.answer("Спочатку /start")
        return
    last_done, streak = row
    yesterday = (datetime.utcnow().date() - timedelta(days=1)).isoformat()
    streak = streak + 1 if last_done == yesterday else 1
    cursor.execute("UPDATE users SET streak=?, last_done=? WHERE user_id=?", (streak, today, message.from_user.id))
    conn.commit()
    await message.answer(f"Зараховано ✅\n🔥 Серія: {streak}", reply_markup=menu_kb)

@dp.message(Command("stats"))
async def stats(message: Message):
    cursor.execute("SELECT style, streak, last_done FROM users WHERE user_id=?", (message.from_user.id,))
    row = cursor.fetchone()
    if not row:
        await message.answer("Немає даних. Натисни /start")
        return
    style, streak, last_done = row
    style_name = "💪 Жорстко" if style == "hard" else "😌 Підтримка"
    await message.answer(f"🧠 Стиль: {style_name}\n🔥 Серія: {streak}\n📆 Остання дія: {last_done or 'ще не було'}", reply_markup=menu_kb)

# ----------------- DAILY MOTIVATION -----------------
async def daily_motivation():
    while True:
        now = datetime.utcnow()
        target = now.replace(hour=7, minute=0, second=0, microsecond=0)
        if now > target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())

        cursor.execute("SELECT user_id, style, last_done FROM users")
        users = cursor.fetchall()
        today = datetime.utcnow().date()
        for user_id, style, last_done in users:
            if last_done != today.isoformat():
                if last_done and datetime.fromisoformat(last_done).date() < today - timedelta(days=1):
                    text = random.choice(IGNORE_TEXT[style])
                else:
                    text = random.choice(MOTIVATION[style])
            else:
                text = random.choice(MOTIVATION[style])
            try:
                await bot.send_message(user_id, text, reply_markup=menu_kb)
            except Exception:
                pass

# ----------------- MAIN -----------------
async def main():
    logging.basicConfig(level=logging.INFO)
    asyncio.create_task(daily_motivation())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
