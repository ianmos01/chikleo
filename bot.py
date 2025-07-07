import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import F

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()


class BuyVPN(StatesGroup):
    waiting_tariff = State()
    waiting_method = State()


TARIFFS = {
    "\U0001F7E1 1 мес — 200\u20BD": {"amount": 200, "code": "1m"},
    "\U0001F7E2 3 мес — 550\u20BD": {"amount": 550, "code": "3m"},
    "\U0001F7E2 6 мес — 1000\u20BD": {"amount": 1000, "code": "6m"},
    "\U0001F7E3 12 мес — 1900\u20BD": {"amount": 1900, "code": "12m"},
}

PAY_METHODS = {
    "\U0001F4B0 СБП": ("sbp", "СБП"),
    "\U0001F4B3 Карта РФ": ("card", "Карта РФ"),
    "\U0001F3E6 Ю.Касса": ("yookassa", "Ю.Касса"),
}


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


@dp.message(Command("buy"))
async def cmd_buy(message: types.Message):
    await menu_buy(message)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await menu_help(message)


@dp.message(F.text == "\U0001F6D2 Купить VPN | \U0001F4C5 Продлить")
async def menu_buy(message: types.Message, state: FSMContext):
    text = (
        "\U0001F525 Оформляя подписку на Premium VPN от Мировые анекдоты — вы получаете: \uD83D\uDC47\n\n"
        "└ 🚀 Максимальную скорость и стабильное соединение  \n"
        "└ 👥 Оперативную поддержку в чате — @andekdot_support  \n"
        "└ 🖥 Доступ с любых устройств — iOS, Android, Windows, MacOS, Android TV  \n"
        "└ 🔑 Один ключ — одно устройство (всё прозрачно)  \n"
        "└ 🛠 Подробная инструкция + видео — запустите VPN за 2 минуты  \n"
        "└ ✅ Безлимитный трафик — никаких ограничений  \n"
        "└ 🔕 Без рекламы — ничто не мешает  \n"
        "└ ⛔️ Без автосписаний — всё под вашим контролем\n\n"
        "🎥 Как оплатить подписку?  \n"
        "👉 Смотрите видео: тык сюда\n\n"
        "💡 Совет: чем дольше срок, тем ниже цена за месяц 😉  \n"
        "▶️ Выберите нужный тариф ниже и подключайтесь уже сегодня!"
    )

    tariff_kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="\U0001F7E1 1 мес — 200\u20BD"),
                KeyboardButton(text="\U0001F7E2 3 мес — 550\u20BD"),
                KeyboardButton(text="\U0001F7E2 6 мес — 1000\u20BD"),
            ],
            [KeyboardButton(text="\U0001F7E3 12 мес — 1900\u20BD")],
            [KeyboardButton(text="\U0001F4A0 Главное меню")],
        ],
        resize_keyboard=True,
    )

    await message.answer(text, reply_markup=tariff_kb)
    await state.set_state(BuyVPN.waiting_tariff)


@dp.message(BuyVPN.waiting_tariff, F.text.in_(TARIFFS.keys()))
async def select_tariff(message: types.Message, state: FSMContext):
    await state.update_data(tariff=message.text)
    pay_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="\U0001F4B0 СБП")],
            [KeyboardButton(text="\U0001F4B3 Карта РФ")],
            [KeyboardButton(text="\U0001F3E6 Ю.Касса")],
        ],
        resize_keyboard=True,
    )
    await state.set_state(BuyVPN.waiting_method)
    await message.answer("\U0001F4AC Выберите способ оплаты:", reply_markup=pay_kb)


@dp.message(BuyVPN.waiting_tariff, F.text == "\U0001F4A0 Главное меню")
async def tariff_back_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await cmd_start(message)


@dp.message(BuyVPN.waiting_method, F.text.in_(PAY_METHODS.keys()))
async def select_method(message: types.Message, state: FSMContext):
    data = await state.get_data()
    tariff_button = data.get("tariff")
    tariff = TARIFFS.get(tariff_button)
    method_code, method_name = PAY_METHODS[message.text]
    url = f"https://ваш-домен.ру/pay?tariff={tariff['code']}&method={method_code}"
    await message.answer(
        f"Вы выбрали оплату через {method_name}.\n"
        f"Для оплаты используйте следующую ссылку:\n{url}\n"
        f"После оплаты напишите менеджеру: @andekdot_support"
    )

    pay_url = f"https://ваш-сайт.ру/pay?amount={tariff['amount']}&method={method_code}"
    inline_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"\U0001F3E6 Оплатить {tariff['amount']} \u20BD", url=pay_url)]
        ]
    )
    await message.answer(
        "\u2611\uFE0F Создали запрос на покупку.\nНажмите на кнопку: «\U0001F3E6 Оплатить»",
        reply_markup=inline_kb,
    )
    await state.clear()


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
