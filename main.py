"""
🔥 Ultimate Hermes AI Chat Bot (Router v2)
-----------------------------------------
• Модель: NousResearch/Hermes-2-Pro-Mistral-7B
• Fallback: tiiuae/falcon-7b-instruct
• Работает бесплатно через Hugging Face Router v2
• Мультичаты, очистка, история, rate-limit
"""

import os, time, asyncio, httpx, logging
from collections import defaultdict, deque
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

# -------------------- SETUP --------------------
load_dotenv()
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
log = logging.getLogger("HermesChatBot")

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
HF_API_KEY = os.getenv("HF_API_KEY", "")
if not TG_BOT_TOKEN:
    raise SystemExit("❌ TG_BOT_TOKEN отсутствует в .env")

bot = Bot(token=TG_BOT_TOKEN)
dp = Dispatcher()

# -------------------- HUGGING FACE --------------------
HF_URL = "https://router.huggingface.co/hf-inference/v1/chat/completions"
PRIMARY_MODEL = "NousResearch/Hermes-2-Pro-Mistral-7B"
FALLBACK_MODEL = "tiiuae/falcon-7b-instruct"
HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"} if HF_API_KEY else {}

SYSTEM_PROMPT = (
    "Ты — умный, уверенный, позитивный ассистент. "
    "Отвечай по делу, вежливо и с лёгким дружелюбным тоном. "
    "Если вопрос непонятен — уточни. Не извиняйся без причины."
)

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

# -------------------- HF CHAT --------------------
async def hf_chat(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=90) as client:
        for model in [PRIMARY_MODEL, FALLBACK_MODEL]:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 400,
                "temperature": 0.7,
            }
            try:
                r = await client.post(HF_URL, headers=HEADERS, json=payload)
                if r.status_code == 200:
                    data = r.json()
                    text = data["choices"][0]["message"]["content"].strip()
                    log.info(f"✅ Модель: {model}")
                    return text
                else:
                    log.warning(f"⚠️ {model}: {r.status_code} {r.text[:120]}")
            except Exception as e:
                log.warning(f"❌ Ошибка {model}: {e}")
    return "😔 Все модели временно недоступны. Попробуй чуть позже."

# -------------------- TELEGRAM --------------------
@dp.message(CommandStart())
async def start(msg: types.Message):
    user_chats[msg.from_user.id] = {"Чат 1": deque(maxlen=MAX_TURNS)}
    await msg.answer(
        "👋 Привет! Я бот на базе **Hermes-2-Pro-Mistral-7B** 🧠\n"
        "Создавай новые чаты, очищай историю и общайся как с ChatGPT!",
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
    reply = await hf_chat(prompt)
    hist.append(f"ИИ: {reply}")
    await msg.answer(reply, reply_markup=kb_controls())

# -------------------- RUN --------------------
async def main():
    log.info("🚀 Hermes Chat Bot запущен (Router v2)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
