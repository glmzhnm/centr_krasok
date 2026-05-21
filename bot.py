#!/usr/bin/env python3
"""
Telegram AI-бот для Центр Красок #1
Работает на бесплатном и сверхбыстром API от Groq (модель Llama 3).
"""
import os
import logging
import asyncio
from groq import AsyncGroq
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
    CommandHandler
)
from telegram.constants import ChatAction

# Подключаем вашу базу знаний
from company_knowledge import COMPANY_KNOWLEDGE

# ─── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Config ────────────────────────────────────────────────────────────────────
# Вставьте сюда ваши ключи (ОБЯЗАТЕЛЬНО В КАВЫЧКАХ)
TELEGRAM_TOKEN = os.environ.get("8061527614:AAHtrJ40CPbawzK6bzTXhvPvsTOhPDmgCB8")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")  # Начинается на gsk_...

MAX_HISTORY = 10


groq_client = AsyncGroq(api_key=GROQ_API_KEY)
MODEL_NAME = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = f"""Ты — дружелюбный AI-ассистент интернет-магазина «Центр Красок #1» (centr-krasok.kz).

Твоя задача — отвечать на вопросы пользователей ИСКЛЮЧИТЕЛЬНО на основе предоставленной базы знаний о компании. 

СТРОГИЕ ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе информации из базы знаний ниже. Не выдумывай и не дополняй.
2. Если вопрос не связан с компанией или информации нет в базе — вежливо скажи об этом и предложи обратиться напрямую: +7 778 061 50 00 или info@centr-krasok.kz
3. Если вопрос касается цен — уточни, что цены могут меняться, и рекомендуй проверить актуальные цены на сайте.
4. Отвечай на языке, на котором написан вопрос (русский или казахский).
5. Будь лаконичным, но информативным. Используй эмодзи умеренно для удобства чтения.
6. Никогда не претендуй на знание информации, которой нет в базе.
7. При вопросах о вакансиях — направляй связаться напрямую с компанией.

═══════════════════════════════════════════════
БАЗА ЗНАНИЙ О КОМПАНИИ:
═══════════════════════════════════════════════
{COMPANY_KNOWLEDGE}
═══════════════════════════════════════════════

Помни: ты представляешь бренд «Центр Красок #1» и должен быть профессиональным, дружелюбным и полезным.
"""

conversations: dict[int, list[dict]] = {}


def get_history(chat_id: int) -> list[dict]:
    return conversations.get(chat_id, [])


def add_to_history(chat_id: int, role: str, content: str) -> None:
    if chat_id not in conversations:
        conversations[chat_id] = []

    conversations[chat_id].append({"role": role, "content": content})

    if len(conversations[chat_id]) > MAX_HISTORY:
        conversations[chat_id] = conversations[chat_id][-MAX_HISTORY:]


BLOCKED_TOPICS = [
    "политик", "война", "оружи", "наркот", "секс", "порно",
    "убийств", "террор", "взлом", "хакер",
]


def is_off_topic(text: str) -> bool:
    text_lower = text.lower()
    return any(topic in text_lower for topic in BLOCKED_TOPICS)


async def get_ai_response(chat_id: int, user_message: str) -> str:
    if is_off_topic(user_message):
        return (
            "Извините, я могу отвечать только на вопросы, связанные с "
            "магазином «Центр Красок #1» и нашей продукцией. 🎨\n\n"
            "Если у вас есть вопросы о красках, доставке или услугах — "
            "я готов помочь!"
        )

    add_to_history(chat_id, "user", user_message)

    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + get_history(chat_id)

        response = await groq_client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=1000,
            temperature=0.3
        )

        assistant_text = response.choices[0].message.content
        add_to_history(chat_id, "assistant", assistant_text)
        return assistant_text

    except Exception as e:
        logger.error(f"Ошибка Groq API для chat_id={chat_id}: {e}")
        if conversations.get(chat_id):
            conversations[chat_id].pop()  # Удаляем вопрос, если ответ не получен
        return (
            "⚠️ Произошла техническая ошибка. Пожалуйста, попробуйте ещё раз.\n\n"
            "Если проблема повторяется, свяжитесь с нами напрямую:\n"
            "📞 +7 778 061 50 00\n"
            "📧 info@centr-krasok.kz"
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.text:
        return

    chat_id = message.chat_id
    user_text = message.text.strip()

    logger.info(f"Сообщение от chat_id={chat_id}: {user_text[:80]}")
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    response = await get_ai_response(chat_id, user_text)
    await message.reply_text(response, parse_mode=None)


async def handle_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    user_name = update.message.from_user.first_name or "Гость"

    conversations.pop(chat_id, None)

    welcome_text = (
        f"Привет, {user_name}! 👋\n\n"
        "🎨 Я AI-ассистент магазина **Центр Красок #1**.\n\n"
        "Я помогу вам узнать:\n"
        "• О нашей продукции и брендах\n"
        "• Контакты и адреса магазинов\n"
        "• Услуги (колеровка, доставка, консультации)\n"
        "• Условия для дизайнеров и строителей\n"
        "• И многое другое!\n\n"
        "Просто напишите ваш вопрос — и я отвечу 😊\n\n"
        "🌐 centr-krasok.kz"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")


def main() -> None:
    logger.info("Запуск Telegram-бота (Groq) Центр Красок #1...")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", handle_welcome))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен. Ожидание сообщений...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()