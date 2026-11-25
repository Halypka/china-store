

import asyncio
import os
from itertools import count

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 9214809528

bot = Bot(token=TOKEN)
dp = Dispatcher()

user_languages = {}
awaiting_link = set()
active_orders = set()
order_numbers = count(1001)

# ID of a copied customer message -> customer Telegram ID
reply_map = {}

TEXTS = {
    "en": {
        "welcome": "🇨🇳 Welcome to China Store!\n\nShop from China with delivery across Europe.",
        "catalog": "🛍 Catalog",
        "orders": "📦 My orders",
        "support": "💬 Support",
        "language": "🌍 Language",
        "send_link": "🔗 Send your product link from Taobao, 1688 or Yupoo. You can also send a product photo.",
        "received": "✅ Your request #{order} has been received!\n\nOur manager will check your product and contact you shortly.",
        "no_orders": "📦 You haven't submitted any requests yet.",
        "support_info": "💬 Send your message here. Our manager will receive it.",
        "language_info": "🌍 Choose your language:",
        "changed": "✅ Language changed!"
    },
    "ru": {
        "welcome": "🇨🇳 Добро пожаловать в China Store!\n\nЗаказывай товары из Китая с доставкой по Европе.",
        "catalog": "🛍 Каталог",
        "orders": "📦 Мои заказы",
        "support": "💬 Поддержка",
        "language": "🌍 Язык",
        "send_link": "🔗 Отправь ссылку на товар с Taobao, 1688 или Yupoo. Также можешь отправить фотографию товара.",
        "received": "✅ Твоя заявка №{order} принята!\n\nМенеджер проверит товар и свяжется с тобой в ближайшее время.",
        "no_orders": "📦 У тебя пока нет заявок.",
        "support_info": "💬 Напиши сообщение здесь. Его получит наш менеджер.",
        "language_info": "🌍 Выбери язык:",
        "changed": "✅ Язык изменён!"
    },
    "it": {
        "welcome": "🇨🇳 Benvenuto su China Store!\n\nAcquista prodotti dalla Cina con consegna in Europa.",
        "catalog": "🛍 Catalogo",
        "orders": "📦 I miei ordini",
        "support": "💬 Assistenza",
        "language": "🌍 Lingua",
        "send_link": "🔗 Inviaci un link Taobao, 1688 o Yupoo. Puoi anche inviare una foto del prodotto.",
        "received": "✅ La tua richiesta #{order} è stata ricevuta!\n\nIl nostro manager controllerà il prodotto e ti contatterà al più presto.",
        "no_orders": "📦 Non hai ancora inviato richieste.",
        "support_info": "💬 Scrivi qui il tuo messaggio. Il nostro manager lo riceverà.",
        "language_info": "🌍 Scegli la lingua:",
        "changed": "✅ Lingua modificata!"
    }
}


def language_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru")
        ],
        [
            InlineKeyboardButton(text="🇮🇹 Italiano", callback_data="lang:it")
        ]
    ])


def main_menu(lang):
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t["catalog"])],
            [KeyboardButton(text=t["orders"])],
            [KeyboardButton(text=t["support"])],
            [KeyboardButton(text=t["language"])]
        ],
        resize_keyboard=True
    )


@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id

    if user_id not in user_languages:
        await message.answer(
            "🇨🇳 Welcome to China Store!\n\n"
            "Choose your language / Выберите язык / Scegli la lingua:",
            reply_markup=language_keyboard()
        )
        return

    lang = user_languages[user_id]
    await message.answer(
        TEXTS[lang]["welcome"],
        reply_markup=main_menu(lang)
    )


@dp.callback_query(F.data.startswith("lang:"))
async def choose_language(callback: CallbackQuery):
    lang = callback.data.split(":")[1]

    if lang not in TEXTS:
        await callback.answer()
        return

    user_languages[callback.from_user.id] = lang

    await callback.message.edit_text(TEXTS[lang]["changed"])
    await callback.message.answer(
        TEXTS[lang]["welcome"],
        reply_markup=main_menu(lang)
    )
    await callback.answer()


@dp.message(F.text)
async def handle_text(message: Message):
    user_id = message.from_user.id

    # Admin replies to a customer's copied message
    if user_id == ADMIN_ID:
        if message.reply_to_message:
            customer_id = reply_map.get(
                message.reply_to_message.message_id
            )
            if customer_id:
                try:
                    await message.copy_to(chat_id=customer_id)
                    await message.answer("✅ Сообщение отправлено клиенту.")
                except Exception as e:
                    await message.answer(f"Не удалось отправить: {e}")
                return

        await message.answer(
            "Чтобы ответить клиенту, нажми Reply на его сообщении."
        )
        return

    lang = user_languages.get(user_id)

    if not lang:
        await message.answer(
            "Please choose your language first:",
            reply_markup=language_keyboard()
        )
        return

    t = TEXTS[lang]

    if message.text == t["catalog"]:
        awaiting_link.add(user_id)
        await message.answer(t["send_link"])
        return

    if message.text == t["orders"]:
        await message.answer(
            t["no_orders"],
            reply_markup=main_menu(lang)
        )
        return

    if message.text == t["support"]:
        await message.answer(t["support_info"])
        return

    if message.text == t["language"]:
        await message.answer(
            t["language_info"],
            reply_markup=language_keyboard()
        )
        return

    # A new product request
    if user_id in awaiting_link:
        awaiting_link.discard(user_id)
        order_id = next(order_numbers)
        active_orders.add(user_id)

        username = (
            f"@{message.from_user.username}"
            if message.from_user.username else "No username"
        )

        await message.answer(
            t["received"].format(order=order_id),
            reply_markup=main_menu(lang)
        )

        await bot.send_message(
            ADMIN_ID,
            f"🆕 NEW REQUEST #{order_id}\n\n"
            f"👤 Client: {message.from_user.full_name}\n"
            f"🔗 Username: {username}\n"
            f"🆔 Telegram ID: {user_id}\n"
            f"🌍 Language: {lang}\n\n"
            f"Reply to the copied message below to contact the client."
        )

        copied = await message.copy_to(chat_id=ADMIN_ID)
        reply_map[copied.message_id] = user_id
        return

    # Other customer messages are sent to admin as support messages
    if user_id in active_orders:
        copied = await message.copy_to(chat_id=ADMIN_ID)
        reply_map[copied.message_id] = user_id

        await message.answer("✅ Сообщение отправлено менеджеру.")
        return

    await message.answer(t["send_link"])


# Handle customer photos, videos, voice messages and documents
@dp.message()
async def handle_media(message: Message):
    user_id = message.from_user.id

    if user_id == ADMIN_ID:
        if message.reply_to_message:
            customer_id = reply_map.get(
                message.reply_to_message.message_id
            )
            if customer_id:
                await message.copy_to(chat_id=customer_id)
                await message.answer("✅ Отправлено клиенту.")
        return

    lang = user_languages.get(user_id)

    if not lang:
        await message.answer(
            "Choose your language / Выберите язык:",
            reply_markup=language_keyboard()
        )
        return

    if user_id in awaiting_link:
        awaiting_link.discard(user_id)
        order_id = next(order_numbers)
        active_orders.add(user_id)

        await message.answer(
            TEXTS[lang]["received"].format(order=order_id)
        )

        await bot.send_message(
            ADMIN_ID,
            f"🆕 NEW REQUEST #{order_id}\n"
            f"👤 {message.from_user.full_name}\n"
            f"🆔 Telegram ID: {user_id}\n"
            f"🌍 Language: {lang}\n\n"
            f"Reply to the copied message to contact the client."
        )

        copied = await message.copy_to(chat_id=ADMIN_ID)
        reply_map[copied.message_id] = user_id
        return

    if user_id in active_orders:
        copied = await message.copy_to(chat_id=ADMIN_ID)
        reply_map[copied.message_id] = user_id
        await message.answer("✅ Сообщение отправлено менеджеру.")


async def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN is missing")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
