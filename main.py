import asyncio
import random
import logging
from os import getenv
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command

load_dotenv()
TOKEN = getenv("8005942747:AAG7UznaolAscG9b5lg30MPQIQCeXoRKTgc")

bot = Bot(token= 8005942747:AAG7UznaolAscG9b5lg30MPQIQCeXoRKTgc, parse_mode="HTML")
dp = Dispatcher()

# Хранилище данных (пока в памяти — для простоты)
games = {}          # chat_id -> game_data
player_numbers = {} # user_id -> (chat_id, number)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "🐍 <b>Заклинатель змей</b>\n\n"
        "Я помогу провести игру в твоём чате!\n\n"
        "Команды:\n"
        "/newgame — начать новую игру в этом чате\n"
        "/join — присоединиться к игре\n"
        "/begin — начать сбор фактов (только ведущий)"
    )

@dp.message(Command("newgame"))
async def cmd_newgame(message: Message):
    chat_id = message.chat.id
    if chat_id in games:
        await message.answer("Игра уже запущена в этом чате. Используй /join")
        return

    games[chat_id] = {
        "players": [],      # список user_id
        "numbers": {},      # user_id -> номер
        "facts": {},        # номер -> факт
        "phase": "joining", # joining / facts / guessing
        "host": message.from_user.id
    }
    await message.answer(
        "🎮 <b>Новая игра «Заклинатель змей» создана!</b>\n\n"
        "Участники — жмите /join\n"
        "Когда все готовы — ведущий жмёт /begin"
    )

@dp.message(Command("join"))
async def cmd_join(message: Message):
    chat_id = message.chat.id
    if chat_id not in games:
        await message.answer("Сначала создай игру командой /newgame")
        return
    game = games[chat_id]
    user_id = message.from_user.id
    if user_id in game["players"]:
        await message.answer("Ты уже в игре!")
        return

    game["players"].append(user_id)
    await message.answer(f"@{message.from_user.username or message.from_user.first_name} присоединился(ась) к игре! 🐍")

@dp.message(Command("begin"))
async def cmd_begin(message: Message):
    chat_id = message.chat.id
    if chat_id not in games:
        return
    game = games[chat_id]
    if message.from_user.id != game["host"]:
        await message.answer("Только ведущий может начать!")
        return
    if len(game["players"]) < 3:
        await message.answer("Нужно минимум 3 змеи!")
        return

    # Раздаём номера
    players = game["players"][:]
    random.shuffle(players)
    for i, user_id in enumerate(players, 1):
        game["numbers"][user_id] = i
        player_numbers[user_id] = (chat_id, i)

        try:
            await bot.send_message(
                user_id,
                f"🐍 <b>Ты — Змея №{i}</b>\n\n"
                "Скоро твоя очередь. Когда ведущий скажет «Змея №X, твоя очередь», напиши мне сюда один завуалированный факт о себе."
            )
        except:
            await message.answer(f"Не смог написать пользователю с id {user_id} (возможно, бот не добавлен в ЛС)")

    game["phase"] = "facts"
    game["current_fact"] = 1
    await message.answer(
        f"✅ Номера розданы ({len(game['players'])} змей)!\n\n"
        "Теперь по очереди будем собирать факты.\n"
        f"Змея №1 — твоя очередь! Напиши мне в ЛС завуалированный факт."
    )

# Обработка фактов в личных сообщениях
@dp.message(F.chat.type == "private")
async def handle_private_fact(message: Message):
    user_id = message.from_user.id
    if user_id not in player_numbers:
        await message.answer("Ты не участвуешь ни в одной игре.")
        return

    chat_id, number = player_numbers[user_id]
    if chat_id not in games:
        return
    game = games[chat_id]

    if game["phase"] != "facts" or game.get("current_fact") != number:
        await message.answer("Сейчас не твоя очередь или игра не в фазе сбора фактов.")
        return

    fact = message.text.strip()
    if len(fact) < 10:
        await message.answer("Факт слишком короткий. Напиши подробнее 😉")
        returngame["facts"][number] = fact

    await bot.send_message(
        chat_id,
        f"🐍 <b>Змея №{number} шепнула:</b>\n\n{i} {fact}"
    )

    # Переходим к следующей змее
    next_num = number + 1
    if next_num > len(game["players"]):
        game["phase"] = "guessing"
        await bot.send_message(
            chat_id,
            "✅ Все факты собраны!\n\n"
            "Теперь обсуждайте и угадывайте, кто какая змея!\n"
            "Пишите догадки в формате:\n"
            "<code>№3 — @username</code>"
        )
    else:
        game["current_fact"] = next_num
        await bot.send_message(
            chat_id,
            f"Следующая — Змея №{next_num}! Напиши факт в ЛС боту."
        )

    await message.answer("Факт принят! ✅")

# Для завершения игры (по желанию)
@dp.message(Command("reveal"))
async def cmd_reveal(message: Message):
    chat_id = message.chat.id
    if chat_id not in games or message.from_user.id != games[chat_id]["host"]:
        return
    game = games[chat_id]

    text = "🔥 <b>Раскрытие змей!</b>\n\n"
    for user_id, num in game["numbers"].items():
        try:
            user = await bot.get_chat(user_id)
            name = user.username or user.first_name
            text += f"Змея №{num} — @{name}\n"
        except:
            text += f"Змея №{num} — неизвестный пользователь\n"

    await message.answer(text)
    # Очистка
    for uid in game["numbers"]:
        player_numbers.pop(uid, None)
    games.pop(chat_id, None)

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if name == "main":
    asyncio.run(main())
