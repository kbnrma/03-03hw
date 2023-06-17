from aiogram import Bot, Dispatcher, types, executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.storage import FSMContext
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from dotenv import load_dotenv
from pytube import YouTube
import sqlite3, time, logging, os

load_dotenv('.env')

bot = Bot(os.environ.get('token'))
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
logging.basicConfig(level=logging.INFO)

database = sqlite3.connect('youtube.db')
cursor = database.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS users(
    user_id INT,
    chat_id INT,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    created VARCHAR(100)
);
""")
cursor.connection.commit()

@dp.message_handler(commands='start')
async def start(message:types.Message):
    cursor.execute(f"SELECT * FROM users WHERE user_id = {message.from_user.id};")
    result = cursor.fetchall()
    if result == []:
        cursor.execute(f"""INSERT INTO users VALUES ({message.from_user.id},
                    {message.chat.id}, '{message.from_user.username}',
                    '{message.from_user.first_name}', 
                    '{message.from_user.last_name}',
                    '{time.ctime()}');
                    """)
    cursor.connection.commit()
    await message.answer(f"Привет {message.from_user.full_name}!\nЯ помогу тебе скачать видео или же аудио с ютуба. Просто отправь ссылку из ютуба )")

format_buttons = [
    KeyboardButton('Mp3'),
    KeyboardButton('Mp4')
]

format_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(*format_buttons)

class FormatState(StatesGroup):
    url = State()
    format_url = State()

@dp.message_handler()
async def get_youtube_url(message:types.Message, state:FSMContext):
    if 'https://youtu.be/' in message.text:
        await message.reply("В каком формате вы хотите получить результат?", reply_markup=format_keyboard)
        await state.update_data(url=message.text)
        await FormatState.format_url.set()
    else:
        await message.reply("Неправильный формат ссылки")

@dp.message_handler(state=FormatState.format_url)
async def download(message:types.Message, state:FSMContext):
    url = await storage.get_data(user=message.from_user.id)
    yt = YouTube(url['url'], use_oauth=True)
    if message.text == 'Mp3':
        await message.answer("Скачиваем аудио, ожидайте...")
        yt.streams.filter(only_audio=True).first().download('audio', f'{yt.title}.mp3')
        await message.answer("Скачалось, отправляю...")
        with open(f'audio/{yt.title}.mp3', 'rb') as audio:
            await bot.send_audio(message.chat.id, audio)
        os.remove(f'audio/{yt.title}.mp3')

    elif message.text == 'Mp4':
        await message.answer("Скачиваем видео...")
        yt.streams.filter(file_extension='mp4').first().download('video', f'{yt.title}.mp4')
        await message.answer("Скачалось, отправляю...")
        with open(f'video/{yt.title}.mp4', 'rb') as video:
            await bot.send_video(message.chat.id, video)
        os.remove(f'video/{yt.title}.mp4')

executor.start_polling(dp)