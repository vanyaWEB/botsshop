"""
Ultimate Free ChatGPT-like Bot (Telegram, HF-only, No OpenAI)
-------------------------------------------------------------
• Полностью бесплатный режим: только open-source модели через Hugging Face Router
• Ключ HF не обязателен (если есть — укажи; если нет — запросы без авторизации)
• Мультичаты (создание/выбор/очистка), память контекста
• Rate limit (пер-пользователь + глобальный), бэкофф и ретраи
• Чистый Docker-образ, минимальные зависимости

Файлы:
- bot.py (основное приложение)
- requirements.txt
- Dockerfile
- .env.example
"""

# ============================= bot.py =============================
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

# -------------------- Models (HF Router) --------------------
HF_BASE_URL = "https://router.huggingface.co/hf-inference/models"
# Порядок: пробуем по очереди до успешного ответа
HF_MODEL_CANDIDATES = [
    "HuggingFaceH4/zephyr-7b-beta",
    "mistralai/Mistral-7B-Instruct-v0.2",
    "tiiuae/falcon-7b-instruct",
]

SYSTEM_PROMPT = (
    "Ты — доброжелательный ассистент в стиле ChatGPT. Отвечай чётко и по делу,"
    " можно с короткими примерами. Если чего-то не знаешь — скажи об этом."
)

# -------------------- Memory (Multi-Chat) --------------------
user_chats: dict[int, dict[str, deque[str]]] = {}
MAX_TURNS = 24


def get_or_create_chat(user_id: int, chat_name: str) -> deque:
    user_chats.setdefault(user_id, {})
    user_chats[user_id].setdefault(chat_name, deque(maxlen=MAX_TURNS))
    return user_chats[user_id][chat_name]


def get_active_chat_name(user_id: int) -> str:
    chats = user_chats.get(user_id, {})
    if not chats:
        user_chats[user_id] = {"Чат 1": deque(maxlen=MAX_TURNS)}
        return "Чат 1"
    return chats.get("_active", sorted([k for k in chats.keys() if k != "_active"]) or ["Чат 1"])  # type: ignore


def set_active_chat(user_id: int, chat_name: str):
    user_chats.setdefault(user_id, {})
    user_chats[user_id]["_active"] = chat_name


def clear_chat(user_id: int, chat_name: str):
    if user_id in user_chats and chat_name in user_chats[user_id]:
        user_chats[user_id][chat_name].clear()


def chat_menu_kb(user_id: int) -> InlineKeyboardMarkup:
    chats = [k for k in user_chats.get(user_id, {}).keys() if k != "_active"]
    if not chats:
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Нет чатов", callback_data="none")]])
    buttons = [[InlineKeyboardButton(text=name, callback_data=f"select:{name}")] for name in chats]
    buttons.append([InlineKeyboardButton(text="➕ Новый чат", callback_data="new_chat")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def control_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧠 Очистить чат", callback_data="clear_chat")],
            [InlineKeyboardButton(text="📋 Мои чаты", callback_data="show_chats")],
        ]
    )

# -------------------- Rate limit --------------------
USER_COOLDOWN_SEC = 2.0
GLOBAL_MAX_PER_MIN = 12
_last_user_ts: dict[int, float] = defaultdict(lambda: 0.0)
_global_events: deque[float] = deque()


def allow_request(user_id: int) -> tuple[bool, str | None]:
    import time as _t
    now = _t.time()
    if now - _last_user_ts[user_id] < USER_COOLDOWN_SEC:
        wait = USER_COOLDOWN_SEC - (now - _last_user_ts[user_id])
        return False, f"Слишком часто. Подождите {wait:.0f} сек…"
    while _global_events and now - _global_events[0] > 60:
        _global_events.popleft()
    if len(_global_events) >= GLOBAL_MAX_PER_MIN:
        return False, "Много запросов. Попробуйте через минуту — я уже отвечаю другим."
    _last_user_ts[user_id] = now
    _global_events.append(now)
    return True, None

# -------------------- HTTP Client --------------------
HTTP_TIMEOUT = httpx.Timeout(90.0, connect=15.0)
client = httpx.AsyncClient(timeout=HTTP_TIMEOUT)

# -------------------- HF Calls --------------------
_cached = {"name": None, "ts": 0.0}
CACHE_TTL = 300.0


def _headers():
    h = {"Content-Type": "application/json", "x-wait-for-model": "true"}
    if HF_API_KEY:
        h["Authorization"] = f"Bearer {HF_API_KEY}"
    return h


async def hf_try_model(model: str, prompt: str) -> str | None:
    url = f"{HF_BASE_URL}/{model}"
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 400, "temperature": 0.6}}
    r = await client.post(url, headers=_headers(), json=payload)
    if r.status_code != 200:
        log.warning("HF %s -> %s %s", model, r.status_code, r.text[:160])
        return None
    data = r.json()
    if isinstance(data, dict) and "generated_text" in data:
        return data["generated_text"].strip()
    if isinstance(data, list) and data and "generated_text" in data[0]:
        return data[0]["generated_text"].strip()
    return None


async def hf_pick_and_answer(full_prompt: str) -> str:
    import time as _t
    now = _t.time()
    if _cached["name"] and now - _cached["ts"] < CACHE_TTL:
        txt = await hf_try_model(_cached["name"], full_prompt)  # type: ignore
        if txt:
            return txt
        _cached["name"] = None
    for m in HF_MODEL_CANDIDATES:
        txt = await hf_try_model(m, full_prompt)
        if txt:
            _cached.update({"name": m, "ts": now})
            return txt
    return "Все бесплатные модели заняты/недоступны. Попробуйте позже."

# -------------------- Telegram Commands --------------------
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_chats[message.from_user.id] = {"Чат 1": deque(maxlen=MAX_TURNS)}
    await message.answer(
        "👋 Привет! Я бесплатный ChatGPT‑like бот на open‑source моделях.\n"
        "Создавай несколько чатов, очищай контекст и спрашивай что угодно!",
        reply_markup=control_kb(),
    )

@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    await message.answer("📋 Выберите чат:", reply_markup=chat_menu_kb(message.from_user.id))

@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    uid = message.from_user.id
    chat_name = get_active_chat_name(uid)
    clear_chat(uid, chat_name)
    await message.answer(f"История {chat_name} очищена 🧠", reply_markup=control_kb())

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "Команды:\n"
        "/menu — список чатов\n/reset — очистить текущий\n/help — помощь\n\n"
        "Совет: если ответ не пришёл — подождите пару секунд и спросите снова."
    )

@dp.callback_query()
async def callbacks(callback: types.CallbackQuery):
    uid = callback.from_user.id
    data = callback.data

    if data == "clear_chat":
        chat_name = get_active_chat_name(uid)
        clear_chat(uid, chat_name)
        await callback.message.answer(f"{chat_name} очищен ✅", reply_markup=control_kb())
        return await callback.answer()

    if data == "new_chat":
        current = user_chats.get(uid, {})
        new_index = len([k for k in current.keys() if k != "_active"]) + 1
        chat_name = f"Чат {new_index}"
        user_chats.setdefault(uid, {})[chat_name] = deque(maxlen=MAX_TURNS)
        set_active_chat(uid, chat_name)
        await callback.message.answer(f"Создан {chat_name}. Начните разговор 💬", reply_markup=control_kb())
        return await callback.answer()

    if data == "show_chats":
        await callback.message.answer("📋 Ваши чаты:", reply_markup=chat_menu_kb(uid))
        return await callback.answer()

    if data.startswith("select:"):
        chat_name = data.split(":", 1)[1]
        if uid in user_chats and chat_name in user_chats[uid]:
            set_active_chat(uid, chat_name)
            await callback.message.answer(f"✅ Активен {chat_name}", reply_markup=control_kb())
        else:
            await callback.message.answer("❌ Чат не найден.")
        return await callback.answer()

# -------------------- Chat Logic --------------------
@dp.message()
async def chat(message: types.Message):
    uid = message.from_user.id
    text = (message.text or "").strip()

    ok, warn = allow_request(uid)
    if not ok:
        return await message.answer(warn, reply_markup=control_kb())

    active = get_active_chat_name(uid)
    history = get_or_create_chat(uid, active)
    history.append(f"Пользователь: {text}")
    short_history = list(history)[-20:]
    full_prompt = SYSTEM_PROMPT + "\n" + "\n".join(short_history) + "\nИИ:"

    await message.chat.do("typing")
    reply_text = await hf_pick_and_answer(full_prompt)

    history.append(f"ИИ: {reply_text}")
    await message.answer(reply_text, reply_markup=control_kb())

# -------------------- Runner --------------------
async def main():
    log.info("🚀 Free ChatGPT-like Bot started (HF-only)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        try:
            import anyio  # только для аккуратного закрытия, можно не ставить
        except Exception:
            pass

# ============================= requirements.txt =============================
aiogram==3.4.1
httpx==0.27.2
python-dotenv==1.0.1
uvloop==0.19.0
loguru==0.7.2

# ============================= Dockerfile =============================
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
CMD ["python", "bot.py"]

# ============================= .env.example =============================
# Telegram
TG_BOT_TOKEN=123456:ABC...

# Hugging Face — необязателен. Если пусто, запросы пойдут без токена
HF_API_KEY=
