"""
Ultimate Pro AI Chat Bot (Multi-Chat + Stable Model Fallback)
-------------------------------------------------------------
Исправлено подключение к модели Hugging Face Router. Добавлено автоопределение рабочей модели.
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

# -------------------- Hugging Face Models --------------------
# Если Phi-3 недоступна, бот автоматически переключится на Mixtral
PRIMARY_MODEL = "microsoft/Phi-3-mini-4k-instruct"
FALLBACK_MODEL = "mistralai/Mixtral-8x7B-Instruct-v0.1"
HF_BASE_URL = "https://router.huggingface.co/hf-inference/models"

SYSTEM_PROMPT = (
    """
Ты — профессиональный и дружелюбный ассистент. Общайся естественно, кратко и по существу.
Помогай пользователю с любыми вопросами. Если не уверен — честно скажи и предложи помощь.
"""
).strip()

async def query_hf_model(model: str, prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json",
        "x-wait-for-model": "true"
    }
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 400, "temperature": 0.6}}

    async with httpx.AsyncClient(timeout=90) as client:
        url = f"{HF_BASE_URL}/{model}"
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and "generated_text" in data:
                return data["generated_text"].strip()
            elif isinstance(data, list) and data and "generated_text" in data[0]:
                return data[0]["generated_text"].strip()
        log.error("HF API error %s %s", r.status_code, r.text)
        raise Exception(f"HF API error {r.status_code}")

async def hf_reply(prompt: str) -> str:
    if not HF_API_KEY:
        return "(Демо) Укажи HF_API_KEY, чтобы активировать нейросеть."

    try:
        return await query_hf_model(PRIMARY_MODEL, prompt)
    except Exception:
        log.warning("⚠️ Основная модель недоступна, переключение на Mixtral...")
        try:
            return await query_hf_model(FALLBACK_MODEL, prompt)
        except Exception as e:
            log.error("Обе модели недоступны: %s", e)
            return "Все нейросети временно недоступны. Попробуйте позже."

# -------------------- Multi-Chat Memory --------------------
user_chats = {}

def get_or_create_chat(user_id: int, chat_name: str):
    user_chats.setdefault(user_id, {}).setdefault(chat_name, [])
    return user_chats[user_id][chat_name]

def clear_chat(user_id: int, chat_name: str):
    if user_id in user_chats and chat_name in user_chats[user_id]:
        user_chats[user_id][chat_name] = []

def chat_menu_kb(user_id: int):
    chats = list(user_chats.get(user_id, {}).keys())
    if not chats:
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Нет чатов", callback_data="none")]])
    buttons = [[InlineKeyboardButton(text=name, callback_data=f"select:{name}")] for name in chats]
    buttons.append([InlineKeyboardButton(text="➕ Новый чат", callback_data="new_chat")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def control_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧠 Очистить чат", callback_data="clear_chat")],
            [InlineKeyboardButton(text="📋 Мои чаты", callback_data="show_chats")]
        ]
    )

# -------------------- Commands --------------------

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_chats[message.from_user.id] = {"Чат 1": []}
    await message.answer(
        "👋 Привет! Я обновлённый AI-бот с fallback на Mixtral, если Phi-3 недоступна!",
        reply_markup=control_kb()
    )

@dp.callback_query()
async def callbacks(callback: types.CallbackQuery):
    uid = callback.from_user.id
    data = callback.data

    if data == "clear_chat":
        chats = user_chats.get(uid, {"Чат 1": []})
        current_chat = sorted(chats.keys())[-1]
        clear_chat(uid, current_chat)
        await callback.message.answer(f"{current_chat} очищен ✅", reply_markup=control_kb())
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
    short_history = history[-20:]
    prompt = SYSTEM_PROMPT + "\n" + "\n".join(short_history) + "\nИИ:"

    await message.chat.do("typing")
    reply = await hf_reply(prompt)

    history.append(f"ИИ: {reply}")
    user_chats[uid][current_chat] = history[-20:]

    await message.answer(reply, reply_markup=control_kb())

# -------------------- Runner --------------------
async def main():
    log.info("🚀 Ultimate Pro AI Chat Bot (Phi-3 + Mixtral fallback) started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
