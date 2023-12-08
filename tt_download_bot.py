import logging
import os
import time

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import InlineQuery, InputTextMessageContent, InlineQueryResultArticle, InlineQueryResultVideo, InlineQueryResultAudio

from re import findall
from httpx import AsyncClient
from hashlib import md5

from tt_video import tt_videos_or_images, convert_image, divide_chunks, yt_dlp, get_url_of_yt_dlp
from settings import languages, API_TOKEN

storage = MemoryStorage()
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)

# File to store user IDs
USERS_FILE = "users.txt"

# Admin user ID
ADMIN_USER_ID = 5259818746

def is_tool(name):
    from shutil import which

    return which(name) is not None

def get_user_lang(locale):
    user_lang = locale.language
    if user_lang not in languages:
        user_lang = "en"
    return user_lang

async def notify_new_user(user_id, username, first_name):
    channel_id = -1002074238489
    await bot.send_message(channel_id, f"Nuevo usuario en tiktok bot:\nUsuario: @{username}\nNombre: {first_name}")

async def save_user_id(user_id):
    with open(USERS_FILE, 'a+') as file:
        file.seek(0)
        users = file.read().splitlines()
        if str(user_id) not in users:
            file.write(str(user_id) + '\n')

async def get_total_users():
    with open(USERS_FILE, 'r') as file:
        users = file.read().splitlines()
        return len(users)

@dp.message_handler(commands=['start', 'help'])
@dp.throttled(rate=2)
async def send_welcome(message: types.Message):
    user_lang = get_user_lang(message.from_user.locale)
    
    await save_user_id(message.from_user.id)  # Save user ID
    await notify_new_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.reply(languages[user_lang]["help"])

@dp.message_handler(content_types=types.ContentType.NEW_CHAT_MEMBERS)
async def new_chat_members_handler(message: types.Message):
    for member in message.new_chat_members:
        await notify_new_user(member.id, member.username, member.first_name)

@dp.message_handler(commands=['miembros'])
async def get_total_members(message: types.Message):
    if message.from_user.id == ADMIN_USER_ID:
        total_users = await get_total_users()
        await message.reply(f"Total de usuarios: {total_users}")
    else:
        await message.reply("Este comando solo puede ser utilizado por el administrador.")

@dp.message_handler(regexp='https://\w{1,3}?\.?\w+\.\w{1,3}/')
@dp.throttled(rate=3)
async def tt_download2(message: types.Message):
    user_lang = get_user_lang(message.from_user.locale)

    await message.reply(languages[user_lang]["wait"])
    link = findall(r'\bhttps?://.*\w{1,30}\S+', message.text)[0]

    try:
        response = await yt_dlp(link)
        if response.endswith(".mp3"):
            await message.reply_audio(open(response, 'rb'), caption='@monoloc00', title=link)
        # video
        else:
            logging.info(f"VIDEO: {response}")
            await message.reply_video(open(response, 'rb'), caption='@monoloc00',)
        os.remove(response)

    except Exception as e:
        logging.error(e)
        await message.reply(f"error: {e}")
        os.remove(response)
        
@dp.message_handler(commands=['ad'])
async def send_ad_to_users(message: types.Message):
    if message.from_user.id != ADMIN_USER_ID:
        await message.reply("Este comando solo puede ser utilizado por el administrador.")
        return

    # Check if the command includes a message
    if len(message.text.split()) > 1:
        ad_message = " ".join(message.text.split()[1:])
        total_users = await get_total_users()

        if total_users == 0:
            await message.reply("No hay usuarios registrados.")
            return

        with open(USERS_FILE, 'r') as file:
            updated_user_ids = []
            for user_id in file.read().splitlines():
                try:
                    await bot.send_message(int(user_id), ad_message)
                    updated_user_ids.append(user_id)
                except Exception as e:
                    logging.error(f"Error sending message to user {user_id}: {e}")
                    # Remove the user from the list if an error occurs
                    await message.reply(f"Error sending message to user {user_id}: {e}")
            
            # Update the users.txt file with the remaining user IDs
            with open(USERS_FILE, 'w') as file:
                file.write("\n".join(updated_user_ids))

        await message.reply(f"Mensaje enviado a {len(updated_user_ids)} usuario(s).")
    else:
        await message.reply("Por favor, incluye un mensaje para enviar con el comando /ad.")

@dp.message_handler()
@dp.throttled(rate=3)
async def echo(message: types.Message):
    user_lang = get_user_lang(message.from_user.locale)

    await message.answer(languages[user_lang]["invalid_link"])

if __name__ == '__main__':
    if is_tool("yt-dlp"):
        logging.info("yt-dlp installed")
        executor.start_polling(dp, skip_updates=True)
    else:
        logging.error("yt-dlp not installed! Run: sudo apt install yt-dlp")
