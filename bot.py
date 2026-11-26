import asyncio
import logging
import os
import re
import sqlite3
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "9214809528"))
DB_PATH = Path(os.getenv("BOT_DB_PATH", "china_store.sqlite3"))
dp = Dispatcher()

# These are short-lived interaction states, keyed by Telegram user ID.
awaiting_product: set[int] = set()
user_languages: dict[int, str] = {}
handled_messages: set[tuple[int, int]] = set()
reply_map: dict[int, int] = {}

TEXTS = {
    "en": {
        "welcome": "🇨🇳 Welcome to China Store!\n\nShop from China with delivery across Europe.",
        "catalog": "🛍 Catalog", "orders": "📦 My orders", "support": "💬 Support", "language": "🌐 Language",
        "send_link": "🔗 Send a product link from Taobao, 1688 or Yupoo, or send a product photo.",
        "received": "Your request №{order} has been received. Our manager will check the product and contact you.",
        "no_orders": "📦 You haven't submitted any requests yet.",
        "support_info": "💬 Write your message here and our manager will receive it. You can send text, photos, videos, voice messages, documents, and other common message types.",
        "support_sent": "✅ Your message has been sent to our manager.", "language_info": "🌐 Choose your language:",
        "changed": "✅ Language changed!", "invalid_link": "That doesn't look like a product link. Please send a valid link or a product photo.",
        "send_failed": "We couldn't send your message right now. Please try again shortly.",
        "choose_language": "Please choose your language first:", "admin_sent": "✅ Reply sent to the customer.",
        "customer_unavailable": "I couldn't deliver the reply. The customer may have blocked the bot or deleted their account.",
    },
    "ru": {
        "welcome": "🇨🇳 Добро пожаловать в China Store!\n\nЗаказывайте товары из Китая с доставкой по Европе.",
        "catalog": "🛍 Каталог", "orders": "📦 Мои заявки", "support": "💬 Поддержка", "language": "🌐 Язык",
        "send_link": "🔗 Отправьте ссылку на товар с Taobao, 1688 или Yupoo либо фотографию товара.",
        "received": "Ваша заявка №{order} принята. Менеджер проверит товар и свяжется с вами.",
        "no_orders": "📦 У вас пока нет заявок.",
        "support_info": "💬 Напишите сообщение здесь — его получит наш менеджер. Можно отправлять текст, фото, видео, голосовые сообщения, документы и другие распространённые типы сообщений.",
        "support_sent": "✅ Ваше сообщение отправлено менеджеру.", "language_info": "🌐 Выберите язык:",
        "changed": "✅ Язык изменён!", "invalid_link": "Это не похоже на ссылку на товар. Отправьте корректную ссылку или фотографию товара.",
        "send_failed": "Не удалось отправить сообщение. Пожалуйста, попробуйте ещё раз позже.",
        "choose_language": "Сначала выберите язык:", "admin_sent": "✅ Ответ отправлен клиенту.",
        "customer_unavailable": "Не удалось доставить ответ. Возможно, клиент заблокировал бота или удалил аккаунт.",
    },
    "it": {
        "welcome": "🇨🇳 Benvenuto su China Store!\n\nAcquista prodotti dalla Cina con consegna in Europa.",
        "catalog": "🛍 Catalogo", "orders": "📦 I miei ordini", "support": "💬 Assistenza", "language": "🌐 Lingua",
        "send_link": "🔗 Inviaci un link Taobao, 1688 o Yupoo oppure una foto del prodotto.",
        "received": "La tua richiesta n. {order} è stata ricevuta. Il nostro manager controllerà il prodotto e ti contatterà.",
        "no_orders": "📦 Non hai ancora inviato richieste.",
        "support_info": "💬 Scrivi qui il tuo messaggio e il nostro manager lo riceverà. Puoi inviare testo, foto, video, messaggi vocali, documenti e altri tipi di messaggi comuni.",
        "support_sent": "✅ Il messaggio è stato inviato al nostro manager.", "language_info": "🌐 Scegli la tua lingua:",
        "changed": "✅ Lingua modificata!", "invalid_link": "Questo non sembra un link al prodotto. Invia un link valido o una foto del prodotto.",
        "send_failed": "Non siamo riusciti a inviare il messaggio. Riprova tra poco.",
        "choose_language": "Scegli prima la lingua:", "admin_sent": "✅ Risposta inviata al cliente.",
        "customer_unavailable": "Impossibile consegnare la risposta. Il cliente potrebbe aver bloccato il bot o eliminato l'account.",
    },
}


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS counters (name TEXT PRIMARY KEY, value INTEGER NOT NULL)")
        conn.execute("INSERT OR IGNORE INTO counters(name, value) VALUES ('order', 1000)")
        conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, language TEXT NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS reply_map (admin_message_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL)")
        conn.commit()
        user_languages.update(dict(conn.execute("SELECT user_id, language FROM users")))
        reply_map.update(dict(conn.execute("SELECT admin_message_id, customer_id FROM reply_map")))


def next_order_number() -> int:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE counters SET value = value + 1 WHERE name = 'order'")
        value = conn.execute("SELECT value FROM counters WHERE name = 'order'").fetchone()[0]
        conn.commit()
        return value


def save_language(user_id: int, lang: str) -> None:
    user_languages[user_id] = lang
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO users(user_id, language) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET language=excluded.language", (user_id, lang))
        conn.commit()


def save_reply(admin_message_id: int, customer_id: int) -> None:
    reply_map[admin_message_id] = customer_id
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR REPLACE INTO reply_map(admin_message_id, customer_id) VALUES (?, ?)", (admin_message_id, customer_id))
        conn.commit()


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"), InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru")],
        [InlineKeyboardButton(text="🇮🇹 Italiano", callback_data="lang:it")],
    ])


def main_menu(lang: str) -> ReplyKeyboardMarkup:
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=t["catalog"])], [KeyboardButton(text=t["orders"])], [KeyboardButton(text=t["support"])], [KeyboardButton(text=t["language"])]], resize_keyboard=True)


def customer_info(message: Message, order: int | None = None) -> str:
    user = message.from_user
    username = f"@{user.username}" if user.username else "—"
    order_line = f"\n📦 Request №{order}" if order is not None else "\n💬 Support message"
    return (f"{('🆕 NEW REQUEST' if order is not None else '💬 SUPPORT')}" + order_line +
            f"\n👤 Name: {user.full_name}\n🆔 Telegram ID: {user.id}\n🔗 Username: {username}\n🌐 Language: {user_languages.get(user.id, 'en')}")


async def forward_to_admin(message: Message, order: int | None = None) -> None:
    """Post a Reply-able copy to the admin and persist its customer mapping."""
    await message.bot.send_message(ADMIN_ID, customer_info(message, order))
    copied = await message.copy_to(chat_id=ADMIN_ID)
    save_reply(copied.message_id, message.from_user.id)


async def deliver_admin_reply(message: Message) -> bool:
    if not message.reply_to_message:
        return False
    customer_id = reply_map.get(message.reply_to_message.message_id)
    if not customer_id:
        return False
    lang = user_languages.get(message.from_user.id, "ru")
    try:
        await message.copy_to(chat_id=customer_id)
        await message.answer(TEXTS[lang]["admin_sent"])
    except (TelegramForbiddenError, TelegramBadRequest):
        await message.answer(TEXTS[lang]["customer_unavailable"])
    except TelegramAPIError:
        logging.exception("Telegram API error while delivering admin reply to %s", customer_id)
        await message.answer(TEXTS[lang]["customer_unavailable"])
    return True


def valid_product_url(text: str) -> bool:
    match = re.search(r"https?://[^\s]+", text, flags=re.IGNORECASE)
    if not match:
        return False
    from urllib.parse import urlparse
    parsed = urlparse(match.group(0).rstrip(".,);]"))
    return bool(parsed.netloc and "." in parsed.netloc and parsed.scheme in {"http", "https"})


@dp.message(CommandStart())
async def start(message: Message) -> None:
    lang = user_languages.get(message.from_user.id)
    if lang:
        await message.answer(TEXTS[lang]["welcome"], reply_markup=main_menu(lang))
    else:
        await message.answer("Welcome to China Store!\n\nChoose your language / Выберите язык / Scegli la lingua:", reply_markup=language_keyboard())


@dp.message(Command("help"))
async def help_command(message: Message) -> None:
    if message.from_user.id == ADMIN_ID:
        return
    lang = user_languages.get(message.from_user.id, "en")
    await message.answer(TEXTS[lang]["support_info"], reply_markup=main_menu(lang))


@dp.callback_query(F.data.startswith("lang:"))
async def choose_language(callback: CallbackQuery) -> None:
    lang = callback.data.split(":", 1)[1]
    if lang not in TEXTS:
        await callback.answer()
        return
    save_language(callback.from_user.id, lang)
    await callback.message.edit_text(TEXTS[lang]["changed"])
    await callback.message.answer(TEXTS[lang]["welcome"], reply_markup=main_menu(lang))
    await callback.answer()


@dp.message(F.from_user.id == ADMIN_ID)
async def admin_messages(message: Message) -> None:
    if await deliver_admin_reply(message):
        return
    # Ordinary admin messages and unrelated replies are ignored quietly.


@dp.message(F.text)
async def customer_text(message: Message) -> None:
    user_id = message.from_user.id
    lang = user_languages.get(user_id)
    if not lang:
        await message.answer(TEXTS["en"]["choose_language"], reply_markup=language_keyboard())
        return
    t = TEXTS[lang]
    if message.text == t["catalog"]:
        awaiting_product.add(user_id)
        await message.answer(t["send_link"])
        return
    if message.text == t["orders"]:
        await message.answer(t["no_orders"], reply_markup=main_menu(lang))
        return
    if message.text == t["support"]:
        awaiting_product.discard(user_id)
        await message.answer(t["support_info"], reply_markup=main_menu(lang))
        return
    if message.text == t["language"]:
        await message.answer(t["language_info"], reply_markup=language_keyboard())
        return

    key = (user_id, message.message_id)
    if key in handled_messages:
        return
    if valid_product_url(message.text):
        handled_messages.add(key)
        awaiting_product.discard(user_id)
        order = next_order_number()
        await message.answer(t["received"].format(order=order), reply_markup=main_menu(lang))
        try:
            await forward_to_admin(message, order)
        except TelegramAPIError:
            logging.exception("Failed forwarding product request %s to admin", order)
        return
    if user_id in awaiting_product:
        awaiting_product.discard(user_id)
        await message.answer(t["invalid_link"], reply_markup=main_menu(lang))
        return

    handled_messages.add(key)
    try:
        await forward_to_admin(message)
        await message.answer(t["support_sent"])
    except TelegramAPIError:
        logging.exception("Failed forwarding support message from %s", user_id)
        await message.answer(t["send_failed"])


@dp.message(F.photo)
async def customer_photo(message: Message) -> None:
    user_id = message.from_user.id
    if user_id not in user_languages:
        await message.answer(TEXTS["en"]["choose_language"], reply_markup=language_keyboard())
        return
    lang = user_languages[user_id]
    key = (user_id, message.message_id)
    if key in handled_messages:
        return
    handled_messages.add(key)
    if user_id in awaiting_product:
        awaiting_product.discard(user_id)
        order = next_order_number()
        await message.answer(TEXTS[lang]["received"].format(order=order), reply_markup=main_menu(lang))
        try:
            await forward_to_admin(message, order)
        except TelegramAPIError:
            logging.exception("Failed forwarding photo request %s to admin", order)
        return
    try:
        await forward_to_admin(message)
        await message.answer(TEXTS[lang]["support_sent"])
    except TelegramAPIError:
        logging.exception("Failed forwarding support photo from %s", user_id)
        await message.answer(TEXTS[lang]["send_failed"])


@dp.message()
async def customer_other_message(message: Message) -> None:
    """Forward other common media types as support; preserve catalog photo ordering."""
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        return
    lang = user_languages.get(user_id)
    if not lang:
        await message.answer(TEXTS["en"]["choose_language"], reply_markup=language_keyboard())
        return
    key = (user_id, message.message_id)
    if key in handled_messages:
        return
    handled_messages.add(key)
    try:
        await forward_to_admin(message)
        await message.answer(TEXTS[lang]["support_sent"])
    except TelegramAPIError:
        logging.exception("Failed forwarding support message from %s", user_id)
        await message.answer(TEXTS[lang]["send_failed"])


async def main() -> None:
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is missing; add it to the .env file")
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    init_db()
    async with Bot(token=TOKEN) as bot:
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
