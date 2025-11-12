"""
✅ Free ChatGPT-like Bot — Hugging Face Official Inference API (v1)
------------------------------------------------------------------
• Работает без OpenAI, бесплатно через router.huggingface.co/v1
• Поддерживает: mistralai/Mistral-7B-Instruct, HuggingFaceH4/zephyr-7b-beta, meta-llama/Llama-3-8b-chat-hf
• Мультичаты, очистка, rate-limit, кэширование модели.
"""

import os
import time
import asyncio
import logging
from collections import defaultdict, deque
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

# -------------------- Setup --------------------
load_dotenv()
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
log = logging.getLogger("FreeChatBot")

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
HF_API_KEY = os.getenv("HF_API_KEY", "")  # можно пустым

if not TG_BOT_TOKEN:
    raise SystemExit("❌ Missing TG_BOT_TOKEN in .env")

bot = Bot(token=TG_BOT_TOKEN)
dp = Dispatcher()

# -------------------- HF Router Config --------------------
HF_BASE_URL = "https://router.huggingface.co/v1/chat/completions"
HF_MODEL_CANDIDATES = [
    "mistralai/Mistral-7B-Instruct-v0.2",
    "HuggingFaceH4/zephyr-7b-beta",
    "meta-llama/Llama-3-8b-chat-hf",
]

SYSTEM_PROMPT = (
    "Ты — дружелюбный AI-ассистент в стиле ChatGPT. "
    "Отвечай чётко, по делу, без воды. Если не уверен — честно скажи."
)

# -------------------- Memory --------------------
user_chats: dict[int, dict[str, deque[str]]] = {}
MAX_TURNS = 20

def get_or_create_chat(user_id: int, chat_name: str) -> deque:
    user_chats.setdefault(user_id, {})
    user_chats[user_id].setdefault(chat_name, deque(maxlen=MAX_TURNS))
    return user_chats[user_id][chat_name]

def get_active_chat(user_id: int) -> str:
    chats = user_chats.get(user_id, {})
    if not chats:
        user_chats[user_id] = {"Чат 1": deque(maxlen=MAX_TURNS)}
        return "Чат 1"
    return chats.get("_active", sorted([k for k in chats.keys() if k != "_active"]) or ["Чат 1"])[0]

def set_active_chat(user_id: int, chat_name: str):
    user_chats.setdefault(user_id, {})
    user_chats[user_id]["_active"] = chat_name

def clear_chat(user_id: int, chat_name: str):
    if user_id in user_chats and chat_name in user_chats[user_id]:
        user_chats[user_id][chat_name].clear()

def chat_menu_kb(user_id: int):
    chats = [k for k in user_chats.get(user_id, {}).keys() if k != "_active"]
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

# -------------------- Rate-limit --------------------
USER_COOLDOWN_SEC = 2.0
GLOBAL_MAX_PER_MIN = 10
_last_user_ts: dict[int, float] = defaultdict(lambda: 0.0)
_global_events: deque[float] = deque()

def allow_request(uid: int) -> tuple[bool, str | None]:
    now = time.time()
    if now - _last_user_ts[uid] < USER_COOLDOWN_SEC:
        wait = USER_COOLDOWN_SEC - (now - _last_user_ts[uid])
        return False, f"Слишком часто. Подожди {wait:.0f} сек."
    while _global_events and now - _global_events[0] > 60:
        _global_events.popleft()
    if len(_global_events) >= GLOBAL_MAX_PER_MIN:
        return False, "Я сейчас отвечаю другим. Попробуй через минуту."
    _last_user_ts[uid] = now
    _global_events.append(now)
    return True, None

# -------------------- Inference --------------------
_cached_model = {"name": None, "ts": 0.0}
CACHE_TTL = 600.0

async def hf_chat(model: str, messages: list[dict]) -> str | None:
    headers = {"Content-Type": "application/json"}
    if HF_API_KEY:
        headers["Authorization"] = f"Bearer {HF_API_KEY}"
    payload = {"model": model, "messages": messages, "max_tokens": 400, "temperature": 0.7}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(HF_BASE_URL, headers=headers, json=payload)
        if r.status_code == 200:
            data = r.json()
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"].strip()
        log.warning(f"HF {model} -> {r.status_code} {r.text[:150]}")
        return None

async def hf_pick_and_answer(prompt: str) -> str:
    now = time.time()
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
    # try cached model first
    if _cached_model["name"] and now - _cached_model["ts"] < CACHE_TTL:
        txt = await hf_chat(_cached_model["name"], msgs)
        if txt:
            return txt
        _cached_model["name"] = None
    # try all
    for m in HF_MODEL_CANDIDATES:
        txt = await hf_chat(m, msgs)
        if txt:
            _cached_model.update({"name": m, "ts": now})
            return txt
    return "Все бесплатные модели заняты. Попробуй чуть позже."

# -------------------- Telegram --------------------
@dp.message(CommandStart())
async def start(message: types.Message):
    user_chats[message.from_user.id] = {"Чат 1": deque(maxlen=MAX_TURNS)}
    await message.answer("👋 Привет! Я бесплатный ChatGPT-бот на Hugging Face.", reply_markup=control_kb())

@dp.callback_query()
async def callbacks(callback: types.CallbackQuery):
    uid = callback.from_user.id
    data = callback.data
    if data == "clear_chat":
        chat_name = get_active_chat(uid)
        clear_chat(uid, chat_name)
        await callback.message.answer(f"{chat_name} очищен ✅", reply_markup=control_kb())
        return await callback.answer()
    if data == "new_chat":
        current = user_chats.get(uid, {})
        idx = len([k for k in current.keys() if k != "_active"]) + 1
        chat_name = f"Чат {idx}"
        user_chats.setdefault(uid, {})[chat_name] = deque(maxlen=MAX_TURNS)
        set_active_chat(uid, chat_name)
        await callback.message.answer(f"Создан {chat_name}. Начни разговор 💬", reply_markup=control_kb())
        return await callback.answer()
    if data == "show_chats":
        await callback.message.answer("📋 Твои чаты:", reply_markup=chat_menu_kb(uid))
        return await callback.answer()
    if data.startswith("select:"):
        chat_name = data.split(":", 1)[1]
        if uid in user_chats and chat_name in user_chats[uid]:
            set_active_chat(uid, chat_name)
            await callback.message.answer(f"✅ Активен {chat_name}", reply_markup=control_kb())
        else:
            await callback.message.answer("❌ Чат не найден.")
        return await callback.answer()

@dp.message()
async def chat(message: types.Message):
    uid = message.from_user.id
    text = message.text.strip()
    ok, warn = allow_request(uid)
    if not ok:
        return await message.answer(warn, reply_markup=control_kb())
    chat_name = get_active_chat(uid)
    history = get_or_create_chat(uid, chat_name)
    history.append(f"Пользователь: {text}")
    short_history = list(history)[-20:]
    prompt = "\n".join(short_history)
    await message.chat.do("typing")
    reply = await hf_pick_and_answer(prompt)
    history.append(f"ИИ: {reply}")
    await message.answer(reply, reply_markup=control_kb())

# -------------------- Runner --------------------
async def main():
    log.info("🚀 Free ChatGPT-like Bot running via HF v1 API")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
