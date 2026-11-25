import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛍 Каталог")],
        [KeyboardButton(text="📦 Мои заказы")],
        [KeyboardButton(text="💬 Поддержка")],
        [KeyboardButton(text="🌍 Язык")]
    ],
    resize_keyboard=True
)


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🇨🇳 Добро пожаловать в China Store!\n\n"
        "Покупай товары из Китая с доставкой в Европу.",
        reply_markup=main_menu
    )


@dp.message(lambda message: message.text == "🛍 Каталог")
async def catalog(message: Message):
    await message.answer(
        "🛍 Каталог\n\n"
        "Отправь ссылку на товар с китайского маркетплейса, "
        "и мы рассчитаем стоимость."
    )


@dp.message(lambda message: message.text == "📦 Мои заказы")
async def orders(message: Message):
    await message.answer("📦 У тебя пока нет заказов.")


@dp.message(lambda message: message.text == "💬 Поддержка")
async def support(message: Message):
    await message.answer("💬 Напиши свой вопрос, и наш менеджер тебе поможет.")


async def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN is missing in .env")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
