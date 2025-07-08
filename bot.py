import logging
import os
import asyncio

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
from outline_api import Manager
import time
from db import init_db, add_key, clear_key, has_used_trial, get_active_key

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

OUTLINE_API_URL = os.getenv("OUTLINE_API_URL")

DELETE_DELAY = int(os.getenv("DELETE_DELAY", "30"))


async def send_temporary(bot: Bot, chat_id: int, text: str, delay: int = DELETE_DELAY, **kwargs) -> types.Message:
    msg = await bot.send_message(chat_id, text, **kwargs)

    async def _remove() -> None:
        await asyncio.sleep(delay)
        try:
            await bot.delete_message(chat_id, msg.message_id)
        except Exception as exc:
            logging.error("Failed to delete message: %s", exc)

    asyncio.create_task(_remove())
    return msg


class BuyVPN(StatesGroup):
    waiting_tariff = State()
    waiting_method = State()


TARIFFS = {
    "\U0001F7E1 1 мес — 200\u20BD": {"amount": 200, "code": "1m", "days": 30},
    "\U0001F7E2 3 мес — 550\u20BD": {"amount": 550, "code": "3m", "days": 90},
    "\U0001F7E2 6 мес — 1000\u20BD": {"amount": 1000, "code": "6m", "days": 180},
    "\U0001F7E3 12 мес — 1900\u20BD": {"amount": 1900, "code": "12m", "days": 365},
}

PAY_METHODS = {
    "\U0001F4B0 СБП": ("sbp", "СБП"),
    "\U0001F4B3 Карта РФ": ("card", "Карта РФ"),
    "\U0001F3E6 Ю.Касса": ("yookassa", "Ю.Касса"),
}


def outline_manager() -> Manager:
    if not OUTLINE_API_URL:
        raise RuntimeError("OUTLINE_API_URL not configured")
    return Manager(apiurl=OUTLINE_API_URL, apicrt="")


async def create_outline_key(label: str | None = None) -> dict:
    manager = outline_manager()
    return await asyncio.to_thread(manager.new, label)


async def schedule_key_deletion(
    key_id: int,
    delay: int = 24 * 60 * 60,
    user_id: int | None = None,
    is_trial: bool | None = None,
) -> None:
    async def _remove() -> None:
        await asyncio.sleep(delay)
        manager = outline_manager()
        try:
            await asyncio.to_thread(manager.delete, key_id)
        except Exception as exc:
            logging.error("Failed to delete Outline key: %s", exc)
        if user_id is not None and is_trial is not None:
            clear_key(user_id, is_trial)

    asyncio.create_task(_remove())


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
    if has_used_trial(callback.from_user.id):
        await send_temporary(bot, callback.message.chat.id, "Вы уже использовали пробный период.")
    else:
        try:
            key = await create_outline_key(label=f"vpn_{callback.from_user.id}")
            expires = int(time.time() + 24 * 60 * 60)
            add_key(callback.from_user.id, key.get("id"), key.get("accessUrl"), expires, True)
            await schedule_key_deletion(key.get("id"), delay=24 * 60 * 60, user_id=callback.from_user.id, is_trial=True)
            await callback.message.answer(
                f"Ваш пробный ключ на 24 часа:\n{key.get('accessUrl', 'не удалось получить')}"
            )
        except Exception as exc:
            logging.error("Failed to create trial key: %s", exc)
            await send_temporary(bot, callback.message.chat.id, "Не удалось получить пробный ключ.")
    await callback.answer()


@dp.callback_query(F.data == "buy_extend")
async def callback_buy(callback: types.CallbackQuery):
    await send_temporary(bot, callback.message.chat.id, 'Вы нажали "Купить VPN | Продлить"')
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

    try:
        key = await create_outline_key(label=f"vpn_{message.from_user.id}")
        duration = tariff.get("days", 30) * 24 * 60 * 60
        expires = int(time.time() + duration)
        add_key(message.from_user.id, key.get("id"), key.get("accessUrl"), expires, False)
        await schedule_key_deletion(
            key.get("id"), delay=duration, user_id=message.from_user.id, is_trial=False
        )
        await message.answer(f"Ваш ключ:\n{key.get('accessUrl', 'не удалось получить')}")
    except Exception as exc:
        logging.error("Failed to create paid key: %s", exc)
        await send_temporary(bot, message.chat.id, "Не удалось получить ключ.")
    await state.clear()


@dp.message(F.text == "\U0001F511 Мои активные ключи")
async def menu_keys(message: types.Message):
    row = get_active_key(message.from_user.id)
    now_ts = int(time.time())
    if row:
        access_url, expires_at, is_trial = row
        if expires_at is not None and expires_at <= now_ts:
            clear_key(message.from_user.id, bool(is_trial))
            text = "Срок действия вашего ключа истёк."
        else:
            text = f"Ваш Outline ключ:\n{access_url}"
    else:
        text = "У вас нет активного ключа."
    await send_temporary(bot, message.chat.id, text)


@dp.message(F.text == "\U0001F9D1\u200D\U0001F4AC Отзывы")
async def menu_reviews(message: types.Message):
    await send_temporary(bot, message.chat.id, 'Раздел "Отзывы" пока в разработке')


@dp.message(F.text == "\U0001F381 Пригласить")
async def menu_invite(message: types.Message):
    await send_temporary(bot, message.chat.id, 'Раздел "Пригласить" пока в разработке')


@dp.message(F.text == "\U0001F198 Помощь")
async def menu_help(message: types.Message):
    await send_temporary(bot, message.chat.id, 'Раздел "Помощь" пока в разработке')


async def main() -> None:
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
