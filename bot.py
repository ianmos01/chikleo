import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           ReplyKeyboardMarkup, KeyboardButton)
from aiogram import F

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    text = (
        "\U0001F44B Привет! Мы — Мировые анекдоты, и да, у нас есть свой VPN, который работает так же надёжно, "
        "как хорошая шутка заходит в пятницу вечером \U0001F60F\n\n"
        "Почему выбирают Мировые анекдоты?\n\n"
        "\u2705 Приватный сервер — вас никто не увидит и не заблокирует\n"
        "\U0001F680 Скорость до 1 Гбит/сек — летает, как смех в хорошей компании\n"
        "\U0001F4F5 Без рекламы и вылетов — ничего не раздражает\n"
        "\U0001F4CA Безлимитный трафик — никаких ограничений, хоть сутки напролёт\n"
        "\U0001F6E1 100% защита данных — всё по-взрослому, только безопасность\n"
        "\U0001F4F1 Поддержка: iOS, Android, Windows, MacOS, Android TV\n\n"
        "Мировые анекдоты — это не только про весёлое настроение,\n"
        "а ещё и про свободу доступа в интернете \U0001F680"
    )

    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001F511 Пробный период", callback_data="trial")],
        [InlineKeyboardButton(text="\U0001F6D2 Купить VPN | \U0001F4C5 Продлить", callback_data="buy_extend")]
    ])

    reply_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="\U0001F6D2 Купить VPN | \U0001F4C5 Продлить"),
             KeyboardButton(text="\U0001F511 Мои активные ключи")],
            [KeyboardButton(text="\U0001F9D1\u200D\U0001F4AC Отзывы"),
             KeyboardButton(text="\U0001F381 Пригласить")],
            [KeyboardButton(text="\U0001F198 Помощь")]
        ],
        resize_keyboard=True
    )

    await message.answer(text, reply_markup=inline_kb)
    await message.answer("Выберите действие:", reply_markup=reply_kb)


@dp.callback_query(F.data == "trial")
async def callback_trial(callback: types.CallbackQuery):
    await callback.message.answer('Вы нажали "Пробный период"')
    await callback.answer()


@dp.callback_query(F.data == "buy_extend")
async def callback_buy(callback: types.CallbackQuery):
    await callback.message.answer('Вы нажали "Купить VPN | Продлить"')
    await callback.answer()


@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    await cmd_start(message)


@dp.message(F.text == "\U0001F6D2 Купить VPN | \U0001F4C5 Продлить")
async def menu_buy(message: types.Message):
    await message.answer('Раздел "Купить VPN | Продлить" пока в разработке')


@dp.message(F.text == "\U0001F511 Мои активные ключи")
async def menu_keys(message: types.Message):
    await message.answer('Вот ваши активные ключи: ...')


@dp.message(F.text == "\U0001F9D1\u200D\U0001F4AC Отзывы")
async def menu_reviews(message: types.Message):
    await message.answer('Раздел "Отзывы" пока в разработке')


@dp.message(F.text == "\U0001F381 Пригласить")
async def menu_invite(message: types.Message):
    await message.answer('Раздел "Пригласить" пока в разработке')


@dp.message(F.text == "\U0001F198 Помощь")
async def menu_help(message: types.Message):
    await message.answer('Раздел "Помощь" пока в разработке')


async def main() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
