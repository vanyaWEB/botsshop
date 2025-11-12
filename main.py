"""
🚀 Ultimate AI Bot — OpenRouter Edition
---------------------------------------
• Работает через OpenRouter.ai (бесплатно)
• Совместим с OpenAI API
• Мультичаты, очистка, память
• Минимальная нагрузка на RAM
"""

import os, time, asyncio, logging, httpx
from collections import defaultdict, deque
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

# -------------------- SETUP --------------------
load_dotenv()
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
log = logging.getLogger("OpenRouterBot")

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

if not TG_BOT_TOKEN:
    raise SystemExit("❌ Нет TG_BOT_TOKEN в .env")

bot = Bot(token=TG_BOT_TOKEN)
dp = Dispatcher()

# -------------------- MEMORY --------------------
MAX_TURNS = 20
user_chats: dict[int, dict[str, deque[str]]] = defaultdict(dict)
_last_user: dict[int, float] = defaultdict(float)
COOLDOWN = 2.0

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

# -------------------- UI --------------------
def kb_controls():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧠 Очистить чат", callback_data="clear_chat")],
            [InlineKeyboardButton(text="📋 Мои чаты", callback_data="show_chats")],
        ]
    )

def kb_chats(uid: int):
    chats = [k for k in user_chats.get(uid, {}) if k != "_active"]
    buttons = [[InlineKeyboardButton(text=name, callback_data=f"sel:{name}")] for name in chats]
    buttons.append([InlineKeyboardButton(text="➕ Новый чат", callback_data="new_chat")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# -------------------- RATE LIMIT --------------------
def allow_request(uid: int) -> tuple[bool, str | None]:
    now = time.time()
    if now - _last_user[uid] < COOLDOWN:
        wait = COOLDOWN - (now - _last_user[uid])
        return False, f"⏳ Подожди {wait:.1f} сек."
    _last_user[uid] = now
    return True, None

# -------------------- CHAT COMPLETION --------------------
async def ai_reply(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "mistralai/mixtral-8x7b-instruct",  # бесплатная мощная модель
        "messages": [
            {"role": "system", "content": "Ты — умный и дружелюбный ассистент. Отвечай ясно и интересно."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 400,
        "temperature": 0.7,
    }

    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(OPENROUTER_URL, headers=headers, json=payload)
        if r.status_code == 200:
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()
        else:
            log.warning(f"⚠️ OpenRouter error {r.status_code}: {r.text[:100]}")
            return "😔 Нейросеть сейчас недоступна. Попробуй позже."

# -------------------- TELEGRAM --------------------
@dp.message(CommandStart())
async def start(msg: types.Message):
    user_chats[msg.from_user.id] = {"Чат 1": deque(maxlen=MAX_TURNS)}
    await msg.answer(
        "👋 Привет! Я AI-бот на базе **Mixtral 8x7B** (через OpenRouter.ai)\n"
        "Создавай чаты, очищай историю и задавай любые вопросы!",
        reply_markup=kb_controls(),
    )

@dp.callback_query()
async def callbacks(cb: types.CallbackQuery):
    uid, data = cb.from_user.id, cb.data
    if data == "clear_chat":
        name = get_active_chat(uid)
        clear_chat(uid, name)
        await cb.message.answer(f"{name} очищен ✅", reply_markup=kb_controls())
        return await cb.answer()

    if data == "new_chat":
        current = user_chats.get(uid, {})
        index = len([k for k in current if k != "_active"]) + 1
        name = f"Чат {index}"
        user_chats[uid][name] = deque(maxlen=MAX_TURNS)
        set_active_chat(uid, name)
        await cb.message.answer(f"Создан {name} 💬", reply_markup=kb_controls())
        return await cb.answer()

    if data == "show_chats":
        await cb.message.answer("📋 Выбери чат:", reply_markup=kb_chats(uid))
        return await cb.answer()

    if data.startswith("sel:"):
        name = data.split(":", 1)[1]
        if name in user_chats[uid]:
            set_active_chat(uid, name)
            await cb.message.answer(f"✅ Активен {name}", reply_markup=kb_controls())
        else:
            await cb.message.answer("❌ Чат не найден.")
        return await cb.answer()

@dp.message()
async def chat(msg: types.Message):
    uid, text = msg.from_user.id, msg.text.strip()
    ok, warn = allow_request(uid)
    if not ok:
        return await msg.answer(warn, reply_markup=kb_controls())

    name = get_active_chat(uid)
    hist = get_or_create_chat(uid, name)
    hist.append(f"Пользователь: {text}")
    prompt = "\n".join(hist)[-4000:]

    await msg.chat.do("typing")
    reply = await ai_reply(prompt)
    hist.append(f"ИИ: {reply}")
    await msg.answer(reply, reply_markup=kb_controls())

# -------------------- RUN --------------------
async def main():
    log.info("🚀 Ultimate OpenRouter Bot запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
