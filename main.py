"""
💡 Free Mistral AI Chat Bot (Router v2)
--------------------------------------
• Использует Mistral-7B-Instruct-v0.3
• Абсолютно бесплатный, без OpenAI
• Поддержка очистки чата и rate-limit
"""

import os, time, asyncio, httpx, logging
from collections import deque, defaultdict
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

# --- Setup ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
log = logging.getLogger("MistralBot")

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
HF_API_KEY = os.getenv("HF_API_KEY", "")
if not TG_BOT_TOKEN:
    raise SystemExit("❌ TG_BOT_TOKEN отсутствует в .env")

bot = Bot(token=TG_BOT_TOKEN)
dp = Dispatcher()

# --- HF Endpoint ---
HF_URL = "https://router.huggingface.co/hf-inference/v1/chat/completions"
MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"} if HF_API_KEY else {}

SYSTEM_PROMPT = (
    "Ты — умный, уверенный и дружелюбный ассистент. "
    "Отвечай по делу, вежливо и максимально полезно."
)

# --- Memory & Rate limit ---
user_chats = defaultdict(lambda: deque(maxlen=20))
user_last = defaultdict(float)
COOLDOWN = 2.0

def control_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 Очистить чат", callback_data="clr")]
    ])

# --- Hugging Face call ---
async def mistral_chat(prompt: str) -> str:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 400,
        "temperature": 0.7
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(HF_URL, headers=HEADERS, json=payload)
        if r.status_code == 200:
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()
        else:
            log.error(f"HF {r.status_code}: {r.text}")
            return "🤖 Ошибка соединения с Mistral AI."

# --- Telegram ---
@dp.message(CommandStart())
async def start(msg: types.Message):
    user_chats[msg.from_user.id].clear()
    await msg.answer(
        "👋 Привет! Я бот на модели **Mistral-7B-Instruct-v0.3**.\n"
        "Задавай вопросы — отвечу бесплатно 🤖",
        reply_markup=control_kb()
    )

@dp.callback_query()
async def callbacks(cb: types.CallbackQuery):
    if cb.data == "clr":
        user_chats[cb.from_user.id].clear()
        await cb.message.answer("🧠 Чат очищен!", reply_markup=control_kb())
        await cb.answer()

@dp.message()
async def chat(msg: types.Message):
    uid, text = msg.from_user.id, msg.text.strip()
    if time.time() - user_last[uid] < COOLDOWN:
        return await msg.answer("⏳ Подожди пару секунд...", reply_markup=control_kb())
    user_last[uid] = time.time()

    hist = user_chats[uid]
    hist.append(f"Пользователь: {text}")
    prompt = "\n".join(hist)[-4000:]

    await msg.chat.do("typing")
    reply = await mistral_chat(prompt)
    hist.append(f"ИИ: {reply}")
    await msg.answer(reply, reply_markup=control_kb())

# --- Runner ---
async def main():
    log.info("🚀 Запуск Mistral Chat Bot (Router v2)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
