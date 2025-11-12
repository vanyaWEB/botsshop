"""
🔥 Ultimate Free ChatGPT-like Bot (Hugging Face Official)
---------------------------------------------------------
• HuggingFace Hub InferenceClient
• Бесплатные open-source модели (Zephyr, Mistral, Llama-3)
• Мультичаты, очистка, rate-limit
• Полностью асинхронный, без OpenAI
"""

import os
import time
import asyncio
import logging
from collections import defaultdict, deque
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

# -------------------- SETUP --------------------
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s"
)
log = logging.getLogger("FreeHFChatBot")

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
HF_API_KEY = os.getenv("HF_API_KEY", "")  # можно пустым

if not TG_BOT_TOKEN:
    raise SystemExit("❌ TG_BOT_TOKEN не найден в .env")

bot = Bot(token=TG_BOT_TOKEN)
dp = Dispatcher()

# -------------------- HF CLIENT --------------------
client = InferenceClient(token=HF_API_KEY or None)
HF_MODELS = [
    "mistralai/Mistral-7B-Instruct-v0.3",
    "HuggingFaceH4/zephyr-7b-beta",
    "meta-llama/Llama-3-8b-chat-hf",
]
SYSTEM_PROMPT = (
    "Ты — дружелюбный, профессиональный ассистент. "
    "Отвечай кратко, чётко и по существу. "
    "Если не уверен — скажи честно."
)

# -------------------- МЕМОРИ --------------------
MAX_TURNS = 20
user_chats: dict[int, dict[str, deque[str]]] = {}

def get_or_create_chat(uid: int, name: str) -> deque[str]:
    user_chats.setdefault(uid, {})
    user_chats[uid].setdefault(name, deque(maxlen=MAX_TURNS))
    return user_chats[uid][name]

def get_active_chat(uid: int) -> str:
    chats = user_chats.get(uid, {})
    if not chats:
        user_chats[uid] = {"Чат 1": deque(maxlen=MAX_TURNS)}
        return "Чат 1"
    return chats.get("_active", sorted([k for k in chats if k != "_active"]) or ["Чат 1"])[0]

def set_active_chat(uid: int, name: str):
    user_chats.setdefault(uid, {})
    user_chats[uid]["_active"] = name

def clear_chat(uid: int, name: str):
    if uid in user_chats and name in user_chats[uid]:
        user_chats[uid][name].clear()

def kb_controls():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧠 Очистить чат", callback_data="clear")],
            [InlineKeyboardButton(text="📋 Мои чаты", callback_data="show")]
        ]
    )

def kb_chats(uid: int):
    names = [k for k in user_chats.get(uid, {}) if k != "_active"]
    buttons = [[InlineKeyboardButton(text=n, callback_data=f"sel:{n}")] for n in names]
    buttons.append([InlineKeyboardButton(text="➕ Новый чат", callback_data="new")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# -------------------- RATE LIMIT --------------------
USER_DELAY = 2.0
GLOBAL_LIMIT = 10
_last_user = defaultdict(lambda: 0.0)
_events = deque()

def check_limit(uid: int):
    now = time.time()
    if now - _last_user[uid] < USER_DELAY:
        return False, f"⏳ Подожди {USER_DELAY - (now - _last_user[uid]):.1f} с"
    while _events and now - _events[0] > 60:
        _events.popleft()
    if len(_events) >= GLOBAL_LIMIT:
        return False, "⚡ Много запросов. Попробуй через минуту."
    _last_user[uid] = now
    _events.append(now)
    return True, None

# -------------------- HF CHAT --------------------
_cached = {"name": None, "ts": 0.0}
CACHE_TTL = 600.0

async def hf_chat(prompt: str) -> str:
    """Асинхронный вызов чата через huggingface_hub"""
    now = time.time()

    async def _call(model: str) -> str:
        resp = await asyncio.to_thread(
            client.chat_completion,
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.7,
        )
        return resp.choices[0].message["content"].strip()

    if _cached["name"] and now - _cached["ts"] < CACHE_TTL:
        try:
            return await _call(_cached["name"])
        except Exception as e:
            log.warning(f"⚠️ Кэш-модель {_cached['name']} отвалилась: {e}")
            _cached["name"] = None

    for m in HF_MODELS:
        try:
            txt = await _call(m)
            log.info(f"✅ Используется модель: {m}")
            _cached.update({"name": m, "ts": now})
            return txt
        except Exception as e:
            log.warning(f"❌ {m}: {e}")
    return "😔 Сейчас нет доступных моделей HF. Попробуй позже."

# -------------------- TELEGRAM --------------------
@dp.message(CommandStart())
async def start(msg: types.Message):
    user_chats[msg.from_user.id] = {"Чат 1": deque(maxlen=MAX_TURNS)}
    await msg.answer(
        "👋 Привет! Я ChatGPT-бот на бесплатных моделях Hugging Face.\n"
        "Пиши сообщение — я отвечу 🤖",
        reply_markup=kb_controls()
    )

@dp.callback_query()
async def callbacks(cb: types.CallbackQuery):
    uid = cb.from_user.id
    data = cb.data

    if data == "clear":
        n = get_active_chat(uid)
        clear_chat(uid, n)
        await cb.message.answer(f"{n} очищен ✅", reply_markup=kb_controls())
        return await cb.answer()

    if data == "new":
        chats = user_chats.get(uid, {})
        i = len([k for k in chats if k != "_active"]) + 1
        n = f"Чат {i}"
        user_chats.setdefault(uid, {})[n] = deque(maxlen=MAX_TURNS)
        set_active_chat(uid, n)
        await cb.message.answer(f"Создан {n} 💬", reply_markup=kb_controls())
        return await cb.answer()

    if data == "show":
        await cb.message.answer("📋 Выбери чат:", reply_markup=kb_chats(uid))
        return await cb.answer()

    if data.startswith("sel:"):
        n = data.split(":", 1)[1]
        if uid in user_chats and n in user_chats[uid]:
            set_active_chat(uid, n)
            await cb.message.answer(f"✅ Активен {n}", reply_markup=kb_controls())
        else:
            await cb.message.answer("❌ Чат не найден.")
        return await cb.answer()

@dp.message()
async def handle_chat(msg: types.Message):
    uid = msg.from_user.id
    txt = msg.text.strip()
    ok, warn = check_limit(uid)
    if not ok:
        return await msg.answer(warn, reply_markup=kb_controls())

    name = get_active_chat(uid)
    hist = get_or_create_chat(uid, name)
    hist.append(f"Пользователь: {txt}")
    prompt = "\n".join(hist)[-4000:]

    await msg.chat.do("typing")
    reply = await hf_chat(prompt)
    hist.append(f"ИИ: {reply}")
    await msg.answer(reply, reply_markup=kb_controls())

# -------------------- RUN --------------------
async def main():
    log.info("🚀 Free ChatGPT-like Bot (Hugging Face) запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
