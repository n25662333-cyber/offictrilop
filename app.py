import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.functions.channels import GetParticipantRequest, GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch
import datetime
import sqlite3
import time

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = -1003897540369

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
PHONE = os.getenv("PHONE", "")

bot = Bot(token=TOKEN)
dp = Dispatcher()
telethon_client = TelegramClient('session', API_ID, API_HASH)

def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            subscribe_date TEXT,
            last_update INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def save_subscribe_date(user_id: int, date: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, subscribe_date, last_update)
        VALUES (?, ?, ?)
    ''', (user_id, date, int(time.time())))
    conn.commit()
    conn.close()

def get_cached_date(user_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT subscribe_date, last_update FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        date, last_update = result
        if int(time.time()) - last_update < 7 * 24 * 60 * 60:
            return date
    return None

init_db()

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

async def get_subscription_date_telethon(user_id: int):
    try:
        cached = get_cached_date(user_id)
        if cached:
            return cached
    except:
        pass
    
    try:
        channel = await telethon_client.get_entity(CHANNEL_ID)
        
        # Пытаемся получить участника напрямую
        try:
            result = await telethon_client(GetParticipantRequest(
                channel=channel,
                participant=user_id
            ))
            participant = result.participant
            
            if hasattr(participant, 'date') and participant.date:
                join_date = participant.date.strftime("%d.%m.%Y в %H:%M")
                try:
                    save_subscribe_date(user_id, join_date)
                except:
                    pass
                return join_date
            else:
                return None
                
        except Exception as e:
            print(f"Не удалось получить участника напрямую: {e}")
            
            # Получаем всех участников
            offset = 0
            limit = 100
            all_participants = []
            
            while True:
                participants = await telethon_client(GetParticipantsRequest(
                    channel=channel,
                    filter=ChannelParticipantsSearch(''),
                    offset=offset,
                    limit=limit,
                    hash=0
                ))
                all_participants.extend(participants.users)
                if len(participants.users) < limit:
                    break
                offset += limit
            
            # Ищем нужного пользователя
            target_user = None
            for user in all_participants:
                if user.id == user_id:
                    target_user = user
                    break
            
            if not target_user:
                print(f"Пользователь {user_id} не найден в канале")
                return None
            
            # Получаем участника с датой
            result = await telethon_client(GetParticipantRequest(
                channel=channel,
                participant=target_user
            ))
            participant = result.participant
            
            if hasattr(participant, 'date') and participant.date:
                join_date = participant.date.strftime("%d.%m.%Y в %H:%M")
                try:
                    save_subscribe_date(user_id, join_date)
                except:
                    pass
                return join_date
            else:
                return None
            
    except FloodWaitError as e:
        print(f"FloodWait: ждем {e.seconds} секунд")
        await asyncio.sleep(e.seconds)
        return await get_subscription_date_telethon(user_id)
    except Exception as e:
        print(f"Ошибка получения даты через Telethon: {e}")
        return None

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
    
    join_date = await get_subscription_date_telethon(user_id)
    
    if not join_date:
        try:
            tg_user = await bot.get_chat(user_id)
            if tg_user.date:
                join_date = datetime.datetime.fromtimestamp(tg_user.date).strftime("%d.%m.%Y в %H:%M")
                join_date = f"{join_date} (дата регистрации в Telegram)"
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
Дата: {join_date}
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
        await message.answer(
            f"Привет, {message.from_user.full_name}!\nДоступ открыт.",
            reply_markup=get_main_menu()
        )
    else:
        link_btn = types.InlineKeyboardButton(text="Подписаться на канал", url="https://t.me/tripooldes")
        check_btn = types.InlineKeyboardButton(text="Я подписался", callback_data="check_sub")
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[link_btn], [check_btn]])
        
        await message.answer(
            f"Привет, {message.from_user.full_name}!\n\nДля использования бота подпишитесь на канал.",
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
            "Логотипы - уникальные, запоминающиеся.\n"
            "Аватарки - стильное оформление.\n"
            "Баннеры - для сайтов и каналов.\n\n"
            "Чтобы сделать заказ, нажмите Связь с Trilop"
        )
    elif text == ABOUT_BUTTON:
        await message.answer(
            "Привет! Я графический дизайнер.\n\n"
            "Помогаю брендам и бизнесу выделяться."
        )
    elif text == PORTFOLIO_BUTTON:
        btn = types.InlineKeyboardButton(text="Посмотреть портфолио", url="https://t.me/triloppo")
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[btn]])
        await message.answer("Мои работы:", reply_markup=keyboard)
    elif text == REVIEWS_BUTTON:
        btn = types.InlineKeyboardButton(text="Читать отзывы", url="https://t.me/TRILOOPOT")
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[btn]])
        await message.answer("Отзывы клиентов:", reply_markup=keyboard)
    elif text == CONTACT_BUTTON:
        btn = types.InlineKeyboardButton(text="Написать Trilop", url="https://t.me/Trilop_01")
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[btn]])
        await message.answer("Связь со мной:", reply_markup=keyboard)
    elif text == SPAM_BUTTON:
        btn = types.InlineKeyboardButton(text="Перейти в @Trilopsbot", url="https://t.me/Trilopsbot")
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[btn]])
        await message.answer(
            "Обход спам-блока:\n\n@Trilopsbot",
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
            await message.answer("Сообщение отправлено!")
        except Exception as e:
            print(f"Ошибка: {e}")

@dp.callback_query(lambda c: c.data == "check_sub")
async def process_check_sub(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    is_subscribed = await check_subscription(user_id)
    
    if is_subscribed:
        await callback_query.message.edit_text("Спасибо за подписку!")
        await callback_query.message.answer("Главное меню:", reply_markup=get_main_menu())
    else:
        await callback_query.answer("Вы не подписались!", show_alert=True)

async def main():
    print("Бот запущен")
    print(f"ID канала: {CHANNEL_ID}")
    
    if not API_ID or not API_HASH or not PHONE:
        print("ВНИМАНИЕ: Не указаны API_ID, API_HASH или PHONE для Telethon!")
        print("Дата подписки работать НЕ будет!")
    else:
        try:
            await telethon_client.start(phone=PHONE)
            print("Telethon подключен")
            try:
                channel = await telethon_client.get_entity(CHANNEL_ID)
                print(f"Канал найден: {channel.title}")
            except Exception as e:
                print(f"Ошибка получения канала: {e}")
        except Exception as e:
            print(f"Ошибка подключения Telethon: {e}")
    
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
