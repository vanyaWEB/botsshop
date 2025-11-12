"""
Ultimate Pro AI Chat Bot (bot.py)
---------------------------------
Основной файл для запуска Telegram-бота.
"""

import os
import asyncio
import logging
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

# -------------------- Setup --------------------
load_dotenv()
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
log = logging.getLogger("UltimateProAIChatBot")

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
HF_API_KEY = os.getenv("HF_API_KEY", "")

if not TG_BOT_TOKEN:
    raise SystemExit("❌ Missing TG_BOT_TOKEN in .env")

bot = Bot(token=TG_BOT_TOKEN)
dp = Dispatcher()

# -------------------- Hugging Face API --------------------
MODEL_URL = "https://api-inference.huggingface.co/models/microsoft/Phi-3-mini-4k-instruct"
SYSTEM_PROMPT = (
    """
Ты — профессиональный и дружелюбный ассистент. Общайся естественно, кратко и по существу.
Помогай пользователю с любыми вопросами. Если не уверен — честно скажи и предложи помощь.
"""
).strip()

async def hf_reply(prompt: str) -> str:
    if not HF_API_KEY:
        return "(Демо) Укажи HF_API_KEY, чтобы активировать нейросеть."

    headers = {"Authorization": f"Bearer {HF_API_KEY}", "Content-Type": "application/json"}
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 400, "temperature": 0.6}}

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(MODEL_URL, headers=headers, json=payload)
            if r.status_code != 200:
                log.error("HF API error %s %s", r.status_code, r.text)
                return "Ошибка соединения с моделью. Попробуйте позже."
            data = r.json()
            if isinstance(data, list) and data and "generated_text" in data[0]:
                return data[0]["generated_text"].strip()
            elif isinstance(data, dict) and "generated_text" in data:
                return data["generated_text"].strip()
            return "Не удалось получить ответ от модели."
    except Exception as e:
        log.exception("HF API exception: %s", e)
        return "Произошла ошибка при обращении к модели."

# -------------------- Multi-Chat Memory --------------------
user_chats = {}  # {user_id: {chat_name: [history]}}

def get_or_create_chat(user_id: int, chat_name: str):
    user_chats.setdefault(user_id, {}).setdefault(chat_name, [])
    return user_chats[user_id][chat_name]

def clear_chat(user_id: int, chat_name: str):
    if user_id in user_chats and chat_name in user_chats[user_id]:
        user_chats[user_id][chat_name] = []

# -------------------- Keyboards --------------------

def control_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧠 Очистить чат", callback_data="clear_chat")],
            [InlineKeyboardButton(text="➕ Новый чат", callback_data="new_chat")],
            [InlineKeyboardButton(text="📋 Список чатов", callback_data="show_chats")]
        ]
    )

def chat_menu_kb(user_id: int):
    chats = list(user_chats.get(user_id, {}).keys())
    if not chats:
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Нет чатов", callback_data="none")]])
    buttons = [[InlineKeyboardButton(text=name, callback_data=f"select:{name}")] for name in chats]
    buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# -------------------- Commands --------------------

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_chats[message.from_user.id] = {"Чат 1": []}
    await message.answer(
        "👋 Привет! Я Ultimate AI-ассистент. Создай новый чат или выбери существующий.",
        reply_markup=control_kb()
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "ℹ️ Команды:\n/start — начать\n/reset — очистить текущий чат\n/menu — меню чатов\n/help — помощь\n\n"
        "Используй кнопки под сообщениями, чтобы управлять чатами."
    )

@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    uid = message.from_user.id
    await message.answer("📋 Ваши чаты:", reply_markup=chat_menu_kb(uid))

@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    uid = message.from_user.id
    if uid not in user_chats:
        await message.answer("Нет активных чатов для очистки.")
        return
    last_chat = sorted(user_chats[uid].keys())[-1]
    clear_chat(uid, last_chat)
    await message.answer(f"История {last_chat} очищена 🧠", reply_markup=control_kb())

# -------------------- Callbacks --------------------

@dp.callback_query()
async def callbacks(callback: types.CallbackQuery):
    uid = callback.from_user.id
    data = callback.data

    if data == "clear_chat":
        last_chat = sorted(user_chats.get(uid, {"Чат 1": []}).keys())[-1]
        clear_chat(uid, last_chat)
        await callback.message.answer(f"{last_chat} очищен ✅", reply_markup=control_kb())
        await callback.answer()

    elif data == "new_chat":
        current_chats = user_chats.get(uid, {})
        new_index = len(current_chats) + 1
        chat_name = f"Чат {new_index}"
        user_chats[uid][chat_name] = []
        await callback.message.answer(f"Создан {chat_name}. Начните разговор 💬", reply_markup=control_kb())
        await callback.answer()

    elif data == "show_chats":
        await callback.message.answer("📋 Выберите чат:", reply_markup=chat_menu_kb(uid))
        await callback.answer()

    elif data.startswith("select:"):
        chat_name = data.split(":", 1)[1]
        if uid in user_chats and chat_name in user_chats[uid]:
            user_chats[uid]["_active"] = chat_name
            await callback.message.answer(f"✅ Активен {chat_name}", reply_markup=control_kb())
        else:
            await callback.message.answer("❌ Чат не найден.")
        await callback.answer()

    elif data == "back":
        await callback.message.answer("Возврат в меню управления.", reply_markup=control_kb())
        await callback.answer()

# -------------------- Chat Logic --------------------

@dp.message()
async def chat(message: types.Message):
    uid = message.from_user.id
    text = message.text.strip()

    if uid not in user_chats:
        user_chats[uid] = {"Чат 1": []}

    chats = user_chats[uid]
    current_chat = chats.get("_active", sorted(chats.keys())[-1])
    history = get_or_create_chat(uid, current_chat)

    history.append(f"Пользователь: {text}")
    short_history = history[-30:]
    prompt = SYSTEM_PROMPT + "\n" + "\n".join(short_history) + "\nИИ:"

    await message.chat.do("typing")
    reply = await hf_reply(prompt)

    history.append(f"ИИ: {reply}")
    user_chats[uid][current_chat] = history[-30:]

    log.info(f"User {uid} ({current_chat}): {text}")
    log.info(f"Bot: {reply}")

    await message.answer(reply, reply_markup=control_kb())

# -------------------- Runner --------------------
async def main():
    log.info("🚀 Ultimate Pro AI Chat Bot started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
