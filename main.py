"""
🔥 Ultimate Free ChatGPT-like Bot — Hugging Face Router v2
----------------------------------------------------------
• Работает бесплатно на open-source моделях
• Использует новый endpoint https://router.huggingface.co/hf-inference/v1/chat/completions
• Полностью асинхронный, с мультичатами, очисткой и rate-limit
"""

import os, time, asyncio, logging, httpx
from collections import defaultdict, deque
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

# ---------- CONFIG ----------
load_dotenv()
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
log = logging.getLogger("RouterChatBot")

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
HF_API_KEY = os.getenv("HF_API_KEY", "")
if not TG_BOT_TOKEN:
    raise SystemExit("❌ TG_BOT_TOKEN отсутствует")

bot = Bot(token=TG_BOT_TOKEN)
dp = Dispatcher()

# ---------- HUGGING FACE ----------
HF_MODELS = [
    "meta-llama/Llama-3-8b-chat-hf",
    "HuggingFaceH4/zephyr-7b-beta",
    "mistralai/Mistral-7B-Instruct-v0.3",
]
HF_URL = "https://router.huggingface.co/hf-inference/v1/chat/completions"
HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"} if HF_API_KEY else {}

SYSTEM_PROMPT = (
    "Ты — дружелюбный профессиональный ассистент. Отвечай кратко и по существу. "
    "Если не уверен — честно скажи."
)

# ---------- MEMORY ----------
user_chats: dict[int, dict[str, deque[str]]] = {}
MAX_TURNS = 20

def get_or_create(uid, name):
    user_chats.setdefault(uid, {})
    user_chats[uid].setdefault(name, deque(maxlen=MAX_TURNS))
    return user_chats[uid][name]

def active_chat(uid):
    chats = user_chats.get(uid, {})
    if not chats:
        user_chats[uid] = {"Чат 1": deque(maxlen=MAX_TURNS)}
        return "Чат 1"
    return chats.get("_active", sorted([k for k in chats if k != "_active"]) or ["Чат 1"])[0]

def set_active(uid, name):
    user_chats.setdefault(uid, {})
    user_chats[uid]["_active"] = name

# ---------- RATE LIMIT ----------
USER_DELAY = 2.0
GLOBAL_LIMIT = 10
_last = defaultdict(lambda: 0.0)
_events = deque()

def allow(uid):
    now = time.time()
    if now - _last[uid] < USER_DELAY:
        return False, f"⏳ Подожди {USER_DELAY - (now - _last[uid]):.1f} с"
    while _events and now - _events[0] > 60:
        _events.popleft()
    if len(_events) >= GLOBAL_LIMIT:
        return False, "⚡ Перегруз. Попробуй через минуту."
    _last[uid] = now
    _events.append(now)
    return True, None

# ---------- CHAT COMPLETION ----------
async def hf_chat(prompt: str) -> str:
    payload = {
        "model": HF_MODELS[0],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 400,
        "temperature": 0.7,
    }
    async with httpx.AsyncClient(timeout=90) as client:
        for model in HF_MODELS:
            payload["model"] = model
            try:
                r = await client.post(HF_URL, headers=HEADERS, json=payload)
                if r.status_code == 200:
                    data = r.json()
                    text = data["choices"][0]["message"]["content"].strip()
                    log.info(f"✅ Модель: {model}")
                    return text
                else:
                    log.warning(f"❌ {model}: {r.status_code} {r.text[:80]}")
            except Exception as e:
                log.warning(f"⚠️ Ошибка {model}: {e}")
    return "😔 Все бесплатные модели временно недоступны."

# ---------- UI ----------
def kb_controls():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 Очистить чат", callback_data="clr")],
        [InlineKeyboardButton(text="📋 Мои чаты", callback_data="list")]
    ])

def kb_chats(uid):
    names = [k for k in user_chats.get(uid, {}) if k != "_active"]
    btns = [[InlineKeyboardButton(text=n, callback_data=f"sel:{n}")] for n in names]
    btns.append([InlineKeyboardButton(text="➕ Новый чат", callback_data="new")])
    return InlineKeyboardMarkup(inline_keyboard=btns)

# ---------- TELEGRAM ----------
@dp.message(CommandStart())
async def start(msg: types.Message):
    user_chats[msg.from_user.id] = {"Чат 1": deque(maxlen=MAX_TURNS)}
    await msg.answer(
        "👋 Привет! Я ChatGPT-бот на бесплатных моделях Hugging Face Router.\nПиши — отвечу 🤖",
        reply_markup=kb_controls()
    )

@dp.callback_query()
async def cb(cbq: types.CallbackQuery):
    uid, data = cbq.from_user.id, cbq.data
    if data == "clr":
        n = active_chat(uid); user_chats[uid][n].clear()
        await cbq.message.answer(f"{n} очищен ✅", reply_markup=kb_controls()); return await cbq.answer()
    if data == "new":
        i = len([k for k in user_chats.get(uid, {}) if k != "_active"]) + 1
        n = f"Чат {i}"; user_chats.setdefault(uid,{})[n] = deque(maxlen=MAX_TURNS); set_active(uid,n)
        await cbq.message.answer(f"Создан {n} 💬", reply_markup=kb_controls()); return await cbq.answer()
    if data == "list":
        await cbq.message.answer("📋 Выбери чат:", reply_markup=kb_chats(uid)); return await cbq.answer()
    if data.startswith("sel:"):
        n = data.split(":",1)[1]; set_active(uid,n)
        await cbq.message.answer(f"✅ Активен {n}", reply_markup=kb_controls()); return await cbq.answer()

@dp.message()
async def chat(msg: types.Message):
    uid, text = msg.from_user.id, msg.text.strip()
    ok, warn = allow(uid)
    if not ok:
        return await msg.answer(warn, reply_markup=kb_controls())
    n = active_chat(uid)
    hist = get_or_create(uid,n)
    hist.append(f"Пользователь: {text}")
    prompt = "\n".join(hist)[-4000:]
    await msg.chat.do("typing")
    reply = await hf_chat(prompt)
    hist.append(f"ИИ: {reply}")
    await msg.answer(reply, reply_markup=kb_controls())

# ---------- RUN ----------
async def main():
    log.info("🚀 Free ChatGPT-like Bot запущен (HF Router v2)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
