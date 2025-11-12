"""
Ultimate AI Chat Bot (OpenAI + Hugging Face Fallback)
----------------------------------------------------
Профессиональный мультичат-бот для Telegram.
Использует OpenAI GPT-4 для ответов и Hugging Face как резервный источник.
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
log = logging.getLogger("UltimateAIChatBot")

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
HF_API_KEY = os.getenv("HF_API_KEY", "")

if not TG_BOT_TOKEN:
    raise SystemExit("❌ Missing TG_BOT_TOKEN in .env")

bot = Bot(token=TG_BOT_TOKEN)
dp = Dispatcher()

# -------------------- Model Config --------------------
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
HF_BASE_URL = "https://router.huggingface.co/hf-inference/models"
PRIMARY_MODEL = "gpt-4o-mini"
FALLBACK_MODEL = "mistralai/Mixtral-8x7B-Instruct-v0.1"

SYSTEM_PROMPT = (
    "Ты — профессиональный ассистент. Отвечай умно, кратко и по делу. "
    "Поддерживай дружелюбный тон и всегда помогай пользователю найти решение."
)

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

# -------------------- AI Handlers --------------------
async def openai_reply(prompt: str) -> str:
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": PRIMARY_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        "temperature": 0.6,
        "max_tokens": 400
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(OPENAI_URL, headers=headers, json=payload)
            if r.status_code == 200:
                data = r.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                log.error("OpenAI error %s: %s", r.status_code, r.text)
                raise Exception("OpenAI error")
    except Exception as e:
        log.warning("OpenAI недоступен: %s", e)
        return await hf_fallback(prompt)

async def hf_fallback(prompt: str) -> str:
    if not HF_API_KEY:
        return "Извини, OpenAI временно недоступен, а резерв не настроен."

    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json",
        "x-wait-for-model": "true"
    }
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 400, "temperature": 0.6}}
    url = f"{HF_BASE_URL}/{FALLBACK_MODEL}"

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict) and "generated_text" in data:
                    return data["generated_text"].strip()
                elif isinstance(data, list) and data and "generated_text" in data[0]:
                    return data[0]["generated_text"].strip()
            log.error("HF fallback error %s: %s", r.status_code, r.text)
            return "Извини, ни одна модель сейчас не отвечает."
    except Exception as e:
        log.error("HF fallback exception: %s", e)
        return "Все нейросети временно недоступны."

# -------------------- Telegram Commands --------------------
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_chats[message.from_user.id] = {"Чат 1": []}
    await message.answer(
        "👋 Привет! Я интеллектуальный AI-ассистент.\n"
        "Использую OpenAI GPT-4 для ответов и Hugging Face в резерве.\n\n"
        "💡 Начни писать вопрос — я помогу!",
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
        await callback.message.answer(f"Создан {chat_name}. Начни разговор 💬", reply_markup=control_kb())
        await callback.answer()

    elif data == "show_chats":
        await callback.message.answer("📋 Выбери чат:", reply_markup=chat_menu_kb(uid))
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
    prompt = "\n".join(short_history)

    await message.chat.do("typing")
    reply = await openai_reply(prompt)

    history.append(f"ИИ: {reply}")
    user_chats[uid][current_chat] = history[-20:]

    await message.answer(reply, reply_markup=control_kb())

# -------------------- Runner --------------------
async def main():
    log.info("🚀 Ultimate AI Bot (OpenAI + HF Fallback) started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
