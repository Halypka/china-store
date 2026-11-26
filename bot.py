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
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "blastshop_manager").strip().lstrip("@")
DB_PATH = Path(os.getenv("BOT_DB_PATH", "china_store.sqlite3"))
dp = Dispatcher()

# Interaction states are short-lived; language, orders, and message claims are persistent.
awaiting_product: set[int] = set()
user_languages: dict[int, str] = {}
reply_map: dict[int, int] = {}

TEXTS = {
    "en": {
        "welcome": "🇨🇳 Welcome to China Store!\n\nShop from China with delivery across Europe.",
        "catalog": "🛍 Catalog", "orders": "📦 My orders", "support": "💬 Support", "language": "🌐 Language",
        "send_link": "🔗 Send a product link from Taobao, 1688 or Yupoo, or send a product photo.",
        "catalog_info": "Send a product link or photo here. Our manager will look for a similar item and contact you.",
        "received": "Your request №{order} has been received. Our manager will check the product and contact you.",
        "no_orders": "📦 You haven't submitted any requests yet.",
        "orders_list": "📦 Your requests:", "status_pending": "waiting for review", "status_approved": "approved", "status_rejected": "declined",
        "support_info": "💬 Write your message here and our manager will receive it. You can send text, photos, videos, voice messages, documents, and other common message types.",
        "support_contact": "Or message the manager directly: @{username}", "support_button": "✉️ Message the manager",
        "support_sent": "✅ Your message has been sent to our manager.", "language_info": "🌐 Choose your language:",
        "changed": "✅ Language changed!", "invalid_link": "That doesn't look like a product link. Please send a valid link or a product photo.",
        "send_failed": "We couldn't send your message right now. Please try again shortly.",
        "approved_notice": "✅ Your request №{order} has been approved. The manager will contact you with the next steps.",
        "rejected_notice": "Your request №{order} was not approved. Contact the manager if you have questions.",
        "admin_approve": "✅ Approve", "admin_reject": "✖️ Decline", "admin_done": "Request №{order}: {status}",
        "admin_already": "This request has already been reviewed.", "order_not_found": "Request not found.", "not_admin": "You are not allowed to manage requests.",
        "choose_language": "Please choose your language first:", "admin_sent": "✅ Reply sent to the customer.",
        "customer_unavailable": "I couldn't deliver the reply. The customer may have blocked the bot or deleted their account.",
    },
    "ru": {
        "welcome": "🇨🇳 Добро пожаловать в China Store!\n\nЗаказывайте товары из Китая с доставкой по Европе.",
        "catalog": "🛍 Каталог", "orders": "📦 Мои заявки", "support": "💬 Поддержка", "language": "🌐 Язык",
        "send_link": "🔗 Отправьте ссылку на товар с Taobao, 1688 или Yupoo либо фотографию товара.",
        "catalog_info": "Отправьте сюда ссылку или фото товара. Менеджер подберёт похожий товар и свяжется с вами.",
        "received": "Ваша заявка №{order} принята. Менеджер проверит товар и свяжется с вами.",
        "no_orders": "📦 У вас пока нет заявок.",
        "orders_list": "📦 Ваши заявки:", "status_pending": "на проверке", "status_approved": "согласована", "status_rejected": "отклонена",
        "support_info": "💬 Напишите сообщение здесь — его получит наш менеджер. Можно отправлять текст, фото, видео, голосовые сообщения, документы и другие распространённые типы сообщений.",
        "support_contact": "Или напишите менеджеру напрямую: @{username}", "support_button": "✉️ Написать менеджеру",
        "support_sent": "✅ Ваше сообщение отправлено менеджеру.", "language_info": "🌐 Выберите язык:",
        "changed": "✅ Язык изменён!", "invalid_link": "Это не похоже на ссылку на товар. Отправьте корректную ссылку или фотографию товара.",
        "send_failed": "Не удалось отправить сообщение. Пожалуйста, попробуйте ещё раз позже.",
        "approved_notice": "✅ Ваша заявка №{order} согласована. Менеджер свяжется с вами и сообщит дальнейшие шаги.",
        "rejected_notice": "Заявка №{order} не согласована. Если есть вопросы, напишите менеджеру.",
        "admin_approve": "✅ Согласовать", "admin_reject": "✖️ Отклонить", "admin_done": "Заявка №{order}: {status}",
        "admin_already": "Эта заявка уже обработана.", "order_not_found": "Заявка не найдена.", "not_admin": "У вас нет прав управлять заявками.",
        "choose_language": "Сначала выберите язык:", "admin_sent": "✅ Ответ отправлен клиенту.",
        "customer_unavailable": "Не удалось доставить ответ. Возможно, клиент заблокировал бота или удалил аккаунт.",
    },
    "it": {
        "welcome": "🇨🇳 Benvenuto su China Store!\n\nAcquista prodotti dalla Cina con consegna in Europa.",
        "catalog": "🛍 Catalogo", "orders": "📦 I miei ordini", "support": "💬 Assistenza", "language": "🌐 Lingua",
        "send_link": "🔗 Inviaci un link Taobao, 1688 o Yupoo oppure una foto del prodotto.",
        "catalog_info": "Invia qui un link o una foto del prodotto. Il manager cercherà un articolo simile e ti contatterà.",
        "received": "La tua richiesta n. {order} è stata ricevuta. Il nostro manager controllerà il prodotto e ti contatterà.",
        "no_orders": "📦 Non hai ancora inviato richieste.",
        "orders_list": "📦 Le tue richieste:", "status_pending": "in attesa di revisione", "status_approved": "approvata", "status_rejected": "rifiutata",
        "support_info": "💬 Scrivi qui il tuo messaggio e il nostro manager lo riceverà. Puoi inviare testo, foto, video, messaggi vocali, documenti e altri tipi di messaggi comuni.",
        "support_contact": "Oppure scrivi direttamente al manager: @{username}", "support_button": "✉️ Scrivi al manager",
        "support_sent": "✅ Il messaggio è stato inviato al nostro manager.", "language_info": "🌐 Scegli la tua lingua:",
        "changed": "✅ Lingua modificata!", "invalid_link": "Questo non sembra un link al prodotto. Invia un link valido o una foto del prodotto.",
        "send_failed": "Non siamo riusciti a inviare il messaggio. Riprova tra poco.",
        "approved_notice": "✅ La tua richiesta n. {order} è stata approvata. Il manager ti contatterà per i prossimi passi.",
        "rejected_notice": "La richiesta n. {order} non è stata approvata. Contatta il manager se hai domande.",
        "admin_approve": "✅ Approva", "admin_reject": "✖️ Rifiuta", "admin_done": "Richiesta n. {order}: {status}",
        "admin_already": "Questa richiesta è già stata gestita.", "order_not_found": "Richiesta non trovata.", "not_admin": "Non hai i permessi per gestire le richieste.",
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
        conn.execute("CREATE TABLE IF NOT EXISTS handled_messages (user_id INTEGER NOT NULL, message_id INTEGER NOT NULL, PRIMARY KEY(user_id, message_id))")
        conn.execute("""CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            product_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.commit()
        user_languages.update(dict(conn.execute("SELECT user_id, language FROM users")))
        reply_map.update(dict(conn.execute("SELECT admin_message_id, customer_id FROM reply_map")))


def create_order(customer_id: int, product_type: str) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("UPDATE counters SET value = value + 1 WHERE name = 'order'")
        value = conn.execute("SELECT value FROM counters WHERE name = 'order'").fetchone()[0]
        conn.execute("INSERT INTO orders(order_id, customer_id, product_type) VALUES (?, ?, ?)", (value, customer_id, product_type))
        conn.commit()
        return value


def list_orders(customer_id: int) -> list[tuple[int, str]]:
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute("SELECT order_id, status FROM orders WHERE customer_id = ? ORDER BY order_id DESC", (customer_id,)).fetchall()


def claim_message(user_id: int, message_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("INSERT OR IGNORE INTO handled_messages(user_id, message_id) VALUES (?, ?)", (user_id, message_id))
        conn.commit()
        return cursor.rowcount == 1


def update_order_status(order_id: int, status: str) -> tuple[int, bool] | None:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("UPDATE orders SET status = ? WHERE order_id = ? AND status = 'pending'", (status, order_id))
        row = conn.execute("SELECT customer_id FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        conn.commit()
    return (row[0], cursor.rowcount == 1) if row else None


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


def support_keyboard(lang: str) -> InlineKeyboardMarkup | None:
    if not SUPPORT_USERNAME:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=TEXTS[lang]["support_button"], url=f"https://t.me/{SUPPORT_USERNAME}")
    ]])


def order_review_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=TEXTS["ru"]["admin_approve"], callback_data=f"order:approve:{order_id}"),
        InlineKeyboardButton(text=TEXTS["ru"]["admin_reject"], callback_data=f"order:reject:{order_id}"),
    ]])


def orders_text(user_id: int, lang: str) -> str:
    orders = list_orders(user_id)
    if not orders:
        return TEXTS[lang]["no_orders"]
    lines = [TEXTS[lang]["orders_list"]]
    for order_id, status in orders:
        status_text = TEXTS[lang].get(f"status_{status}", status)
        lines.append(f"№{order_id} — {status_text}")
    return "\n".join(lines)


def main_menu(lang: str) -> ReplyKeyboardMarkup:
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=t["catalog"])], [KeyboardButton(text=t["orders"])], [KeyboardButton(text=t["support"])], [KeyboardButton(text=t["language"])]], resize_keyboard=True)


def customer_info(message: Message, order: int | None = None, product_type: str | None = None) -> str:
    user = message.from_user
    username = f"@{user.username}" if user.username else "—"
    order_line = f"\n📦 Request №{order}" if order is not None else "\n💬 Support message"
    product_line = f"\n🔎 Product submitted as: {product_type}" if product_type else ""
    return (f"{('🆕 NEW REQUEST' if order is not None else '💬 SUPPORT')}" + order_line + product_line +
            f"\n👤 Name: {user.full_name}\n🆔 Telegram ID: {user.id}\n🔗 Username: {username}\n🌐 Language: {user_languages.get(user.id, 'en')}")


async def forward_to_admin(message: Message, order: int | None = None, product_type: str | None = None) -> None:
    """Post a Reply-able copy to the admin and persist its customer mapping."""
    await message.bot.send_message(
        ADMIN_ID,
        customer_info(message, order, product_type),
        reply_markup=order_review_keyboard(order) if order is not None else None,
    )
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


async def show_support_info(message: Message, lang: str) -> None:
    t = TEXTS[lang]
    contact_line = t["support_contact"].format(username=SUPPORT_USERNAME) if SUPPORT_USERNAME else ""
    body = "\n\n".join(part for part in (t["support_info"], contact_line) if part)
    await message.answer(body, reply_markup=main_menu(lang))
    if SUPPORT_USERNAME:
        await message.answer(t["support_button"], reply_markup=support_keyboard(lang))


@dp.message(Command("help"))
async def help_command(message: Message) -> None:
    if message.from_user.id == ADMIN_ID:
        return
    lang = user_languages.get(message.from_user.id, "en")
    await show_support_info(message, lang)


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


@dp.callback_query(F.data.startswith("order:"))
async def review_order(callback: CallbackQuery) -> None:
    if callback.from_user.id != ADMIN_ID:
        await callback.answer(TEXTS["en"]["not_admin"], show_alert=True)
        return
    try:
        _, action, raw_order_id = callback.data.split(":", 2)
        order_id = int(raw_order_id)
        status = {"approve": "approved", "reject": "rejected"}[action]
    except (ValueError, KeyError):
        await callback.answer(TEXTS["ru"]["order_not_found"], show_alert=True)
        return

    result = update_order_status(order_id, status)
    if result is None:
        await callback.answer(TEXTS["ru"]["order_not_found"], show_alert=True)
        return
    customer_id, changed = result
    if not changed:
        await callback.answer(TEXTS["ru"]["admin_already"], show_alert=True)
        return

    customer_lang = user_languages.get(customer_id, "en")
    notice_key = "approved_notice" if status == "approved" else "rejected_notice"
    try:
        await callback.bot.send_message(customer_id, TEXTS[customer_lang][notice_key].format(order=order_id))
    except TelegramAPIError:
        logging.exception("Could not notify customer %s about request %s", customer_id, order_id)

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramAPIError:
        logging.exception("Could not remove review buttons for request %s", order_id)
    await callback.answer(TEXTS["ru"]["admin_done"].format(order=order_id, status=TEXTS["ru"][f"status_{status}"]))


@dp.message(F.from_user.id == ADMIN_ID)
async def admin_messages(message: Message) -> None:
    if await deliver_admin_reply(message):
        return
    # Let the manager use the customer menu while ignoring ordinary admin chat.
    if not message.text:
        if message.photo and message.from_user.id in awaiting_product:
            awaiting_product.discard(message.from_user.id)
            order = create_order(message.from_user.id, "photo")
            lang = user_languages.get(message.from_user.id, "ru")
            await message.answer(TEXTS[lang]["received"].format(order=order), reply_markup=main_menu(lang))
            try:
                await forward_to_admin(message, order, "photo")
            except TelegramAPIError:
                logging.exception("Failed forwarding admin test photo request %s", order)
        return
    lang = user_languages.get(message.from_user.id, "ru")
    t = TEXTS[lang]
    if message.text == t["catalog"]:
        awaiting_product.add(message.from_user.id)
        await message.answer(t["catalog_info"])
        return
    elif message.text == t["orders"]:
        await message.answer(orders_text(message.from_user.id, lang), reply_markup=main_menu(lang))
        return
    elif message.text == t["support"]:
        await show_support_info(message, lang)
        return
    elif message.text == t["language"]:
        await message.answer(t["language_info"], reply_markup=language_keyboard())
        return
    if message.from_user.id in awaiting_product:
        awaiting_product.discard(message.from_user.id)
        if not valid_product_url(message.text):
            await message.answer(t["invalid_link"], reply_markup=main_menu(lang))
            return
        order = create_order(message.from_user.id, "link")
        await message.answer(t["received"].format(order=order), reply_markup=main_menu(lang))
        try:
            await forward_to_admin(message, order, "link")
        except TelegramAPIError:
            logging.exception("Failed forwarding admin test link request %s", order)
    # Other admin messages without a mapped Reply are ignored quietly.


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
        await message.answer(t["catalog_info"])
        return
    if message.text == t["orders"]:
        await message.answer(orders_text(user_id, lang), reply_markup=main_menu(lang))
        return
    if message.text == t["support"]:
        awaiting_product.discard(user_id)
        await show_support_info(message, lang)
        return
    if message.text == t["language"]:
        await message.answer(t["language_info"], reply_markup=language_keyboard())
        return

    if not claim_message(user_id, message.message_id):
        return
    if valid_product_url(message.text):
        awaiting_product.discard(user_id)
        order = create_order(user_id, "link")
        await message.answer(t["received"].format(order=order), reply_markup=main_menu(lang))
        try:
            await forward_to_admin(message, order, "link")
        except TelegramAPIError:
            logging.exception("Failed forwarding product request %s to admin", order)
        return
    if user_id in awaiting_product:
        awaiting_product.discard(user_id)
        await message.answer(t["invalid_link"], reply_markup=main_menu(lang))
        return

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
    if not claim_message(user_id, message.message_id):
        return
    if user_id in awaiting_product:
        awaiting_product.discard(user_id)
        order = create_order(user_id, "photo")
        await message.answer(TEXTS[lang]["received"].format(order=order), reply_markup=main_menu(lang))
        try:
            await forward_to_admin(message, order, "photo")
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
    if not claim_message(user_id, message.message_id):
        return
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
