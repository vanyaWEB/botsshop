"""
Ultimate Pro AI Chat Bot (Updated for Hugging Face Router)
----------------------------------------------------------
Исправлено подключение к нейросети: используется новый endpoint Hugging Face.
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

# -------------------- Hugging Face Router --------------------
MODEL_URL = "https://router.huggingface.co/hf-inference/models/microsoft/Phi-3-mini-4k-instruct"
SYSTEM_PROMPT = (
    """
Ты — профессиональный и дружелюбный ассистент. Общайся естественно, кратко и по существу.
Помогай пользователю с любыми вопросами. Если не уверен — честно скажи и предложи помощь.
"""
).strip()

async def hf_reply(prompt: str) -> str:
    if not HF_API_KEY:
        return "(Демо) Укажи HF_API_KEY, чтобы активировать нейросеть."

    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json",
        "x-wait-for-model": "true"
    }
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 400, "temperature": 0.6}
    }

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(MODEL_URL, headers=headers, json=payload)
            if r.status_code != 200:
                log.error("HF API error %s %s", r.status_code, r.text)
                return "Ошибка соединения с моделью Hugging Face. Попробуйте позже."
            data = r.json()
            if isinstance(data, dict) and "generated_text" in data:
                return data["generated_text"].strip()
            elif isinstance(data, list) and data and "generated_text" in data[0]:
                return data[0]["generated_text"].strip()
            else:
                return "Ответ модели пуст. Попробуйте позже."
    except Exception as e:
        log.exception("HF API exception: %s", e)
        return "Произошла ошибка при подключении к нейросети."

# -------------------- Memory --------------------
user_chats = {}

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
            [InlineKeyboardButton(text="➕ Новый чат", callback_data="new_chat")]
        ]
    )

# -------------------- Commands --------------------

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_chats[message.from_user.id] = {"Чат 1": []}
    await message.answer(
        "👋 Привет! Я обновлённый AI-бот с подключением к новой Hugging Face API.\n"
        "Теперь я отвечаю стабильнее и быстрее!", reply_markup=control_kb()
    )

@dp.callback_query()
async def callbacks(callback: types.CallbackQuery):
    uid = callback.from_user.id
    data = callback.data
    if data == "clear_chat":
        clear_chat(uid, "Чат 1")
        await callback.message.answer("Чат очищен ✅", reply_markup=control_kb())
        await callback.answer()
    elif data == "new_chat":
        current_chats = user_chats.get(uid, {})
        new_index = len(current_chats) + 1
        chat_name = f"Чат {new_index}"
        user_chats[uid][chat_name] = []
        await callback.message.answer(f"Создан {chat_name}. Начните разговор 💬", reply_markup=control_kb())
        await callback.answer()

# -------------------- Chat Logic --------------------

@dp.message()
async def chat(message: types.Message):
    uid = message.from_user.id
    text = message.text.strip()

    chats = user_chats.setdefault(uid, {"Чат 1": []})
    current_chat = sorted(chats.keys())[-1]
    history = get_or_create_chat(uid, current_chat)

    history.append(f"Пользователь: {text}")
    short_history = history[-20:]
    prompt = SYSTEM_PROMPT + "\n" + "\n".join(short_history) + "\nИИ:"

    await message.chat.do("typing")
    reply = await hf_reply(prompt)

    history.append(f"ИИ: {reply}")
    user_chats[uid][current_chat] = history[-20:]

    await message.answer(reply, reply_markup=control_kb())

# -------------------- Runner --------------------
async def main():
    log.info("🚀 Ultimate Pro AI Chat Bot connected to new HF endpoint!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
