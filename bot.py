
import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
ADMIN_ID = 9214809528
dp = Dispatcher()

# Temporary language storage
user_languages = {}

TEXTS = {
    "en": {
        "welcome": "🇨🇳 Welcome to China Store!\n\nShop from China with delivery across Europe.",
        "catalog": "🛍 Catalog",
        "orders": "📦 My orders",
        "support": "💬 Support",
        "language": "🌍 Language",
        "catalog_info": "🛍 Send us a Taobao, 1688 or Yupoo product link. We will calculate the price.",
        "orders_info": "📦 You don't have any orders yet.",
        "support_info": "💬 Write your question. Our manager will help you.",
        "language_info": "🌍 Choose your language:",
        "changed": "✅ Language changed to English!"
    },
    "ru": {
        "welcome": "🇨🇳 Добро пожаловать в China Store!\n\nЗаказывай товары из Китая с доставкой по Европе.",
        "catalog": "🛍 Каталог",
        "orders": "📦 Мои заказы",
        "support": "💬 Поддержка",
        "language": "🌍 Язык",
        "catalog_info": "🛍 Отправь ссылку на товар с Taobao, 1688 или Yupoo. Мы рассчитаем стоимость.",
        "orders_info": "📦 У тебя пока нет заказов.",
        "support_info": "💬 Напиши свой вопрос. Наш менеджер тебе поможет.",
        "language_info": "🌍 Выбери язык:",
        "changed": "✅ Язык изменён на русский!"
    },
    "it": {
        "welcome": "🇨🇳 Benvenuto su China Store!\n\nAcquista prodotti dalla Cina con consegna in Europa.",
        "catalog": "🛍 Catalogo",
        "orders": "📦 I miei ordini",
        "support": "💬 Assistenza",
        "language": "🌍 Lingua",
        "catalog_info": "🛍 Inviaci un link Taobao, 1688 o Yupoo. Calcoleremo il prezzo.",
        "orders_info": "📦 Non hai ancora ordini.",
        "support_info": "💬 Scrivi la tua domanda. Il nostro manager ti aiuterà.",
        "language_info": "🌍 Scegli la lingua:",
        "changed": "✅ Lingua cambiata in italiano!"
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

    if user_id in user_languages:
        lang = user_languages[user_id]
        await message.answer(
            TEXTS[lang]["welcome"],
            reply_markup=main_menu(lang)
        )
    else:
        await message.answer(
            "🇨🇳 Welcome to China Store!\n\n"
            "Choose your language / Выберите язык / Scegli la lingua:",
            reply_markup=language_keyboard()
        )


@dp.callback_query(F.data.startswith("lang:"))
async def choose_language(callback: CallbackQuery):
    lang = callback.data.split(":")[1]

    if lang not in TEXTS:
        await callback.answer("Unknown language")
        return

    user_id = callback.from_user.id
    user_languages[user_id] = lang

    await callback.message.edit_text(TEXTS[lang]["changed"])
    await callback.message.answer(
        TEXTS[lang]["welcome"],
        reply_markup=main_menu(lang)
    )

    await callback.answer()


@dp.message(F.text)
async def handle_menu(message: Message):
    lang = user_languages.get(message.from_user.id)

    if not lang:
        await message.answer(
            "Please choose your language first:",
            reply_markup=language_keyboard()
        )
        return

    t = TEXTS[lang]

    if message.text == t["catalog"]:
        await message.answer(t["catalog_info"])

    elif message.text == t["orders"]:
        await message.answer(t["orders_info"])

    elif message.text == t["support"]:
        await message.answer(t["support_info"])

    elif message.text == t["language"]:
        await message.answer(
            t["language_info"],
            reply_markup=language_keyboard()
        )


async def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN is missing")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
