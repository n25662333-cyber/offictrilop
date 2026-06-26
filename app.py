import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import datetime
import sqlite3
import time

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = -1003897540369

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ============= БАННЕР ПРИВЕТСТВИЯ =============
WELCOME_BANNER = "AgACAgIAAxkBAAFNdChqPekBHYvV2ahngd5FDt-N3Xk0TAACChprG4Yi8Ukaooz0BzOwzwEAAwIAA3cAAzwE"

# ============= БАЗА ДАННЫХ =============
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            join_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_join_date(user_id: int, date: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, join_date)
        VALUES (?, ?)
    ''', (user_id, date))
    conn.commit()
    conn.close()

def get_join_date(user_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT join_date FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

init_db()

# ============= КНОПКИ =============
PROFILE_BUTTON = "Профиль"
DESIGN_BUTTON = "Получить дизайн"
ABOUT_BUTTON = "О нас"
PORTFOLIO_BUTTON = "Портфолио"
REVIEWS_BUTTON = "Отзывы"
CONTACT_BUTTON = "Связь с Trilop"
SPAM_BUTTON = "Обход спам-блока"
SUPPORT_BUTTON = "Техподдержка"

def get_main_menu():
    kb = [
        [types.KeyboardButton(text=PROFILE_BUTTON)],
        [types.KeyboardButton(text=DESIGN_BUTTON)],
        [types.KeyboardButton(text=ABOUT_BUTTON), types.KeyboardButton(text=PORTFOLIO_BUTTON)],
        [types.KeyboardButton(text=REVIEWS_BUTTON), types.KeyboardButton(text=CONTACT_BUTTON)],
        [types.KeyboardButton(text=SPAM_BUTTON)],
        [types.KeyboardButton(text=SUPPORT_BUTTON)]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False

async def get_profile_photo(user_id: int):
    try:
        user_photos = await bot.get_user_profile_photos(user_id, limit=1)
        if user_photos.total_count > 0:
            return user_photos.photos[0][-1].file_id
        return None
    except Exception:
        return None

async def show_profile(message: types.Message):
    user_id = message.from_user.id
    user = message.from_user
    
    is_subscribed = await check_subscription(user_id)
    
    if not is_subscribed:
        await message.answer(
            "Вы не подписаны на канал! Используйте /start для подписки.",
            reply_markup=get_main_menu()
        )
        return
    
    # Получаем дату регистрации в Telegram
    try:
        tg_user = await bot.get_chat(user_id)
        if tg_user.date:
            join_date = datetime.datetime.fromtimestamp(tg_user.date).strftime("%d.%m.%Y в %H:%M")
        else:
            join_date = "Не удалось получить дату"
    except:
        join_date = "Не удалось получить дату"
    
    first_name = user.first_name or "Не указано"
    last_name = user.last_name or ""
    full_name = f"{first_name} {last_name}".strip()
    
    username = user.username
    username_display = f"@{username}" if username else "Не указан"
    
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        status_map = {
            'creator': 'Создатель',
            'administrator': 'Админ',
            'member': 'Подписан',
            'left': 'Не подписан',
            'kicked': 'Заблокирован',
            'restricted': 'Ограничен'
        }
        sub_status = status_map.get(member.status, member.status)
    except Exception:
        sub_status = 'Ошибка'
    
    profile_text = f"""
Профиль

Имя: {full_name}
Telegram ID: {user_id}
Никнейм: {username_display}
Дата регистрации в Telegram: {join_date}
Статус в канале: {sub_status}
    """
    
    photo = await get_profile_photo(user_id)
    
    if photo:
        await message.answer_photo(
            photo=photo,
            caption=profile_text,
            reply_markup=get_main_menu()
        )
    else:
        await message.answer(
            profile_text,
            reply_markup=get_main_menu()
        )

@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    await show_profile(message)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    is_subscribed = await check_subscription(user_id)
    
    if is_subscribed:
        await message.answer_photo(
            photo=WELCOME_BANNER,
            caption=f"Привет, {message.from_user.full_name}!\nДоступ открыт. Выберите нужный раздел в меню ниже:",
            reply_markup=get_main_menu()
        )
    else:
        link_btn = types.InlineKeyboardButton(text="Подписаться на канал", url="https://t.me/tripooldes")
        check_btn = types.InlineKeyboardButton(text="Я подписался", callback_data="check_sub")
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[link_btn], [check_btn]])
        
        await message.answer_photo(
            photo=WELCOME_BANNER,
            caption=f"Привет, {message.from_user.full_name}!\n\nДля использования бота подпишитесь на канал.",
            reply_markup=keyboard
        )

@dp.message()
async def handle_all_buttons(message: types.Message):
    if not message.text:
        return
    
    text = message.text.strip()
    print(f"Получено: '{text}'")
    
    if text == PROFILE_BUTTON:
        await show_profile(message)
    elif text == DESIGN_BUTTON:
        await message.answer(
            "Мои услуги дизайна:\n\n"
            "Логотипы - уникальные, запоминающиеся и отражающие суть вашего дела.\n"
            "Аватарки - стильное оформление для профилей в соцсетях и мессенджерах.\n"
            "Баннеры - рекламные, для сайтов, каналов или оформления сообществ.\n\n"
            "Каждый заказ обсуждается индивидуально, учитывая все ваши пожелания.\n\n"
            "Чтобы сделать заказ, нажмите кнопку Связь с Trilop и напишите мне в ЛС"
        )
    elif text == ABOUT_BUTTON:
        await message.answer(
            "Привет! Я ваш персональный графический дизайнер.\n\n"
            "Помогаю брендам, блогерам и бизнесу выделяться с помощью стильного визуала. "
            "Создаю уникальный дизайн, который привлекает клиентов и радует глаз!"
        )
    elif text == PORTFOLIO_BUTTON:
        btn = types.InlineKeyboardButton(text="Посмотреть портфолио", url="https://t.me/triloppo")
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[btn]])
        await message.answer(
            "Тут вы можете ознакомиться с примерами моих работ",
            reply_markup=keyboard
        )
    elif text == REVIEWS_BUTTON:
        btn = types.InlineKeyboardButton(text="Читать отзывы", url="https://t.me/TRILOOPOT")
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[btn]])
        await message.answer(
            "Отзывы моих клиентов!\n\nЗдесь вы можете прочитать, что говорят люди о моей работе. Нажмите на кнопку ниже",
            reply_markup=keyboard
        )
    elif text == CONTACT_BUTTON:
        support_link = "https://t.me/Trilop_01?text=%D0%9F%D1%80%D0%B8%D0%B2%D0%B5%D1%82%D1%81%D1%82%D0%B2%D1%83%D1%8E%2C%20%D1%85%D0%BE%D1%87%D1%83%20%D0%B7%D0%B0%D0%BA%D0%B0%D0%B7%D0%B0%D1%82%D1%8C%20%D1%83%20%D0%B2%D0%B0%D1%81%20%D0%B4%D0%B8%D0%B7%D0%B0%D0%B9%D0%BD"
        support_btn = types.InlineKeyboardButton(text="Написать Trilop", url=support_link)
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[support_btn]])
        await message.answer(
            "Нажмите на кнопку ниже, чтобы написать мне в личные сообщения.",
            reply_markup=keyboard
        )
    elif text == SPAM_BUTTON:
        backup_bot_btn = types.InlineKeyboardButton(text="Перейти в @Trilopsbot", url="https://t.me/Trilopsbot")
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[backup_bot_btn]])
        await message.answer(
            "У вас спам-блок и вы не можете связаться со мной!\n\n"
            "Вы можете связаться с Trilop через резервного бота:\n\n"
            "@Trilopsbot - бот для обхода спам-блока\n\n"
            "Оставьте ваше сообщение в этом боте, Trilop ответит вам в ближайшее время.",
            reply_markup=keyboard
        )
    elif text == SUPPORT_BUTTON:
        btn = types.InlineKeyboardButton(text="Написать в техподдержку", url="https://t.me/TRILOP_01")
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[btn]])
        await message.answer(
            "Техподдержка:\n\nЕсли у вас возникли проблемы, напишите нам.",
            reply_markup=keyboard
        )
    elif not text.startswith('/'):
        ADMIN_ID = 7968320360
        try:
            username = f"@{message.from_user.username}" if message.from_user.username else "нет"
            await bot.send_message(
                ADMIN_ID,
                f"Новое сообщение\n\n"
                f"Имя: {message.from_user.full_name}\n"
                f"ID: {message.from_user.id}\n"
                f"Сообщение: {message.text}\n"
                f"Username: {username}"
            )
            await message.answer("Ваше сообщение отправлено! Trilop свяжется с вами в ближайшее время.")
        except Exception as e:
            print(f"Ошибка: {e}")
            await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже или свяжитесь напрямую: @Trilop_01")

@dp.callback_query(lambda c: c.data == "check_sub")
async def process_check_sub(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    is_subscribed = await check_subscription(user_id)
    
    if is_subscribed:
        await callback_query.message.edit_text("Спасибо за подписку! Доступ открыт.")
        await callback_query.message.answer("Добро пожаловать в главное меню:", reply_markup=get_main_menu())
    else:
        await callback_query.answer("Вы всё еще не подписались на канал!", show_alert=True)

async def main():
    print("Бот запущен")
    print(f"ID канала: {CHANNEL_ID}")
    
    try:
        chat = await bot.get_chat(CHANNEL_ID)
        print(f"Канал: {chat.title}")
        bot_user = await bot.get_me()
        bot_member = await bot.get_chat_member(CHANNEL_ID, bot_user.id)
        print(f"Статус бота: {bot_member.status}")
    except Exception as e:
        print(f"Ошибка: {e}")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
