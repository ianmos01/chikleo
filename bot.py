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
from urllib.parse import quote_plus
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import F
from outline_api import Manager
import time
from db import (
    init_db,
    add_key,
    clear_key,
    has_used_trial,
    get_active_key,
    record_referral,
    get_key_info,
    update_expiration,
)

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

if not TOKEN:
    raise RuntimeError("BOT_TOKEN not configured")

bot = Bot(token=TOKEN)
dp = Dispatcher()

BOT_USERNAME: str | None = None

OUTLINE_API_URL = os.getenv("OUTLINE_API_URL")

DELETE_DELAY = int(os.getenv("DELETE_DELAY", "30"))

# Number of days granted to a referrer for each invited user
REFERRAL_BONUS_DAYS = 3

# Track scheduled deletion tasks so we can reschedule them
DELETION_TASKS: dict[tuple[int, bool], asyncio.Task] = {}


async def get_bot_username() -> str:
    global BOT_USERNAME
    if BOT_USERNAME is None:
        me = await bot.get_me()
        BOT_USERNAME = me.username
    return BOT_USERNAME


async def send_temporary(
    bot: Bot, chat_id: int, text: str, delay: int = DELETE_DELAY, **kwargs
) -> types.Message:
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
    "\U0001f7e1 1 мес — 199\u20bd": {
        "amount": 199,
        "code": "1m",
        "days": 30,
        "months": 1,
    },
    "\U0001f7e2 3 мес — 529\u20bd": {
        "amount": 529,
        "code": "3m",
        "days": 90,
        "months": 3,
    },
    "\U0001f7e2 6 мес — 949\u20bd": {
        "amount": 949,
        "code": "6m",
        "days": 180,
        "months": 6,
    },
    "\U0001f7e3 12 мес — 1659\u20bd": {
        "amount": 1659,
        "code": "12m",
        "days": 365,
        "months": 12,
    },
}

PAY_METHODS = {
    "\U0001f4b0 СБП": ("sbp", "СБП"),
    "\U0001f4b3 Карта РФ": ("card", "Карта РФ"),
    "\U0001f3e6 Ю.Касса": ("yookassa", "Ю.Касса"),
}


def outline_manager() -> Manager:
    if not OUTLINE_API_URL:
        raise RuntimeError("OUTLINE_API_URL not configured")
    return Manager(apiurl=OUTLINE_API_URL, apicrt="")


async def create_outline_key(label: str | None = None) -> dict:
    manager = outline_manager()
    return await asyncio.to_thread(manager.new, label)


def schedule_key_deletion(
    key_id: int,
    delay: int = 24 * 60 * 60,
    user_id: int | None = None,
    is_trial: bool | None = None,
) -> asyncio.Task:
    """Schedule Outline key removal and return the created task."""

    async def _remove() -> None:
        await asyncio.sleep(delay)
        manager = outline_manager()
        try:
            await asyncio.to_thread(manager.delete, key_id)
        except Exception as exc:
            logging.error("Failed to delete Outline key: %s", exc)
        if user_id is not None and is_trial is not None:
            await clear_key(user_id, is_trial)
            DELETION_TASKS.pop((user_id, is_trial), None)

    if user_id is not None and is_trial is not None:
        old = DELETION_TASKS.pop((user_id, is_trial), None)
        if old:
            old.cancel()
    task = asyncio.create_task(_remove())
    if user_id is not None and is_trial is not None:
        DELETION_TASKS[(user_id, is_trial)] = task
    return task


async def grant_referral_bonus(referrer_id: int) -> None:
    """Issue a 3 day key for the referrer."""
    bonus_seconds = REFERRAL_BONUS_DAYS * 24 * 60 * 60
    now_ts = int(time.time())
    label = f"ref_bonus_{referrer_id}_{now_ts}"
    try:
        key = await create_outline_key(label=label)
        expires = now_ts + bonus_seconds
        await add_key(referrer_id, key.get("id"), key.get("accessUrl"), expires, False)
        schedule_key_deletion(
            key.get("id"), delay=bonus_seconds, user_id=referrer_id, is_trial=False
        )

        logging.info(
            "Issued referral key %s for user %s", key.get("id"), referrer_id
        )

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="\U0001f4f2 Инструкция", callback_data="help")],
                [InlineKeyboardButton(text="\U0001f538 Главное меню", callback_data="main_menu")],
            ]
        )

        await bot.send_message(
            referrer_id,
            "\U0001f511 Спасибо, кто-то зашел по твоей ссылке и теперь ты получаешь "
            f"{REFERRAL_BONUS_DAYS} дня доступа к VPN \U0001f30d\n\n"
            "Вот твой ключ:\n"
            f"{key.get('accessUrl', 'не удалось получить')}\n\n"
            "\u2705 Вы можете продолжать приглашать друзей и получать ещё +3 дня доступа \u263a\ufe0f",
            reply_markup=kb,
        )
    except Exception as exc:
        logging.error("Failed to create referral key: %s", exc)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    first_name = message.from_user.first_name or "друг"
    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1].startswith("ref"):
        try:
            ref_id = int(args[1][3:])
        except ValueError:
            ref_id = None
        if ref_id is not None:
            if await record_referral(message.from_user.id, ref_id):
                logging.info(
                    "User %s joined via referral from %s",
                    message.from_user.id,
                    ref_id,
                )
                await grant_referral_bonus(ref_id)
    await message.answer(f"Привет, {first_name}! \U0001f44b")

    text = (
        "Мы — Мировые анекдоты, и да, у нас есть свой VPN, который работает так же надёжно, "
        "как хорошая шутка заходит в пятницу вечером \U0001f60f\n\n"
        "Почему выбирают Мировые анекдоты?\n\n"
        "\u2705 Приватный сервер — вас никто не увидит и не заблокирует\n"
        "\U0001f680 Скорость до 1 Гбит/сек — летает, как смех в хорошей компании\n"
        "\U0001f4f5 Без рекламы и вылетов — ничего не раздражает\n"
        "\U0001f4ca Безлимитный трафик — никаких ограничений, хоть сутки напролёт\n"
        "\U0001f6e1 100% защита данных — всё по-взрослому, только безопасность\n"
        "\U0001f4f1 Поддержка: iOS, Android, Windows, MacOS, Android TV\n\n"
        "Мировые анекдоты — это не только про весёлое настроение,\n"
        "а ещё и про свободу доступа в интернете \U0001f680"
    )

    inline_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\U0001f511 Пробный период", callback_data="trial"
                )
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f6d2 Купить VPN | \U0001f4c5 Продлить",
                    callback_data="buy_extend",
                )
            ],
        ]
    )

    reply_kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="\U0001f6d2 Купить VPN | \U0001f4c5 Продлить"
                ),
                KeyboardButton(text="\U0001f511 Мои активные ключи"),
            ],
            [
                KeyboardButton(text="\U0001f9d1\u200d\U0001f4ac Отзывы"),
                KeyboardButton(text="\U0001f381 Пригласить"),
            ],
            [KeyboardButton(text="\U0001f198 Помощь")],
        ],
        resize_keyboard=True,
    )

    await message.answer(text, reply_markup=inline_kb)
    await message.answer("Выберите действие:", reply_markup=reply_kb)


@dp.callback_query(F.data == "trial")
async def callback_trial(callback: types.CallbackQuery):
    if await has_used_trial(callback.from_user.id):
        await send_temporary(
            bot,
            callback.message.chat.id,
            "Вы уже использовали пробный период.",
        )
    else:
        try:
            key = await create_outline_key(
                label=f"vpn_{callback.from_user.id}"
            )
            expires = int(time.time() + 24 * 60 * 60)
            await add_key(
                callback.from_user.id,
                key.get("id"),
                key.get("accessUrl"),
                expires,
                True,
            )
            schedule_key_deletion(
                key.get("id"),
                delay=24 * 60 * 60,
                user_id=callback.from_user.id,
                is_trial=True,
            )
            await callback.message.answer(
                "Ваш пробный ключ на 24 часа:\n"
                f"{key.get('accessUrl', 'не удалось получить')}"
            )
        except Exception as exc:
            logging.error("Failed to create trial key: %s", exc)
            await send_temporary(
                bot,
                callback.message.chat.id,
                "Не удалось получить пробный ключ.",
            )
    await callback.answer()


@dp.callback_query(F.data == "buy_extend")
async def callback_buy(callback: types.CallbackQuery, state: FSMContext):
    await menu_buy(callback.message, state)
    await callback.answer()


@dp.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: types.CallbackQuery, state: FSMContext | None = None):
    await cmd_start(callback.message)
    await callback.answer()


@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    await cmd_start(message)


@dp.message(Command("buy"))
async def cmd_buy(message: types.Message, state: FSMContext):
    await menu_buy(message, state)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await menu_help(message)


@dp.message(F.text == "\U0001f6d2 Купить VPN | \U0001f4c5 Продлить")
async def menu_buy(message: types.Message, state: FSMContext):
    text = (
        "\U0001f525 Оформляя подписку на Premium VPN от Мировые анекдоты — "
        "вы получаете: \ud83d\udc47\n\n"
        "└ 🚀 Максимальную скорость и стабильное соединение  \n"
        "└ 👥 Оперативную поддержку в чате — @andekdot_support  \n"
        "└ 🖥 Доступ с любых устройств — iOS, Android, Windows, MacOS, Android"
        " TV  \n"
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
                KeyboardButton(text="\U0001f7e1 1 мес — 199\u20bd"),
                KeyboardButton(text="\U0001f7e2 3 мес — 529\u20bd"),
                KeyboardButton(text="\U0001f7e2 6 мес — 949\u20bd"),
            ],
            [KeyboardButton(text="\U0001f7e3 12 мес — 1659\u20bd")],
            [KeyboardButton(text="\U0001f4a0 Главное меню")],
        ],
        resize_keyboard=True,
    )

    await message.answer(text, reply_markup=tariff_kb)
    await state.set_state(BuyVPN.waiting_tariff)


@dp.message(BuyVPN.waiting_tariff, F.text == "\U0001f6d2 Купить VPN | \U0001f4c5 Продлить")
@dp.message(BuyVPN.waiting_method, F.text == "\U0001f6d2 Купить VPN | \U0001f4c5 Продлить")
async def restart_buy(message: types.Message, state: FSMContext):
    await state.clear()
    await menu_buy(message, state)


@dp.message(BuyVPN.waiting_tariff, F.text.in_(TARIFFS.keys()))
async def select_tariff(message: types.Message, state: FSMContext):
    info = TARIFFS.get(message.text)
    months = info.get("months", 1) if info else 1
    suffix = "месяц" if months == 1 else ("месяца" if months in (2, 3, 4) else "месяцев")
    await message.answer(
        f"Вы выбрали тариф на {months} {suffix}. "
        "Для оформления напишите: @andekdot_support"
    )
    await state.clear()


@dp.message(BuyVPN.waiting_tariff, F.text == "\U0001f4a0 Главное меню")
async def tariff_back_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await cmd_start(message)


@dp.message(BuyVPN.waiting_method, F.text.in_(PAY_METHODS.keys()))
async def select_method(message: types.Message, state: FSMContext):
    data = await state.get_data()
    tariff_button = data.get("tariff")
    tariff = TARIFFS.get(tariff_button)
    method_code, method_name = PAY_METHODS[message.text]
    url = (
        f"https://ваш-домен.ру/pay?tariff={tariff['code']}&method="
        f"{method_code}"
    )
    await message.answer(
        f"Вы выбрали оплату через {method_name}.\n"
        f"Для оплаты используйте следующую ссылку:\n{url}\n"
        f"После оплаты напишите менеджеру: @andekdot_support"
    )

    pay_url = (
        f"https://ваш-сайт.ру/pay?amount={tariff['amount']}&method="
        f"{method_code}"
    )
    inline_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"\U0001f3e6 Оплатить {tariff['amount']} \u20bd",
                    url=pay_url,
                )
            ]
        ]
    )
    await message.answer(
        "\u2611\ufe0f Создали запрос на покупку.\n"
        "Нажмите на кнопку: «\U0001f3e6 Оплатить»",
        reply_markup=inline_kb,
    )

    try:
        key = await create_outline_key(label=f"vpn_{message.from_user.id}")
        duration = tariff.get("days", 30) * 24 * 60 * 60
        expires = int(time.time() + duration)
        await add_key(
            message.from_user.id,
            key.get("id"),
            key.get("accessUrl"),
            expires,
            False,
        )
        schedule_key_deletion(
            key.get("id"),
            delay=duration,
            user_id=message.from_user.id,
            is_trial=False,
        )
        await message.answer(
            f"Ваш ключ:\n{key.get('accessUrl', 'не удалось получить')}"
        )
    except Exception as exc:
        logging.error("Failed to create paid key: %s", exc)
        await send_temporary(bot, message.chat.id, "Не удалось получить ключ.")
    await state.clear()


@dp.message(F.text == "\U0001f511 Мои активные ключи")
async def menu_keys(message: types.Message):
    row = await get_active_key(message.from_user.id)
    now_ts = int(time.time())
    if row:
        access_url, expires_at, is_trial = row
        if expires_at is not None and expires_at <= now_ts:
            await clear_key(message.from_user.id, bool(is_trial))
            text = "Срок действия вашего ключа истёк."
        else:
            text = f"Ваш Outline ключ:\n{access_url}"
    else:
        text = "У вас нет активного ключа."
    await send_temporary(bot, message.chat.id, text)


@dp.message(F.text == "\U0001f9d1\u200d\U0001f4ac Отзывы")
async def menu_reviews(message: types.Message):
    await send_temporary(
        bot, message.chat.id, 'Раздел "Отзывы" пока в разработке'
    )


@dp.message(F.text == "\U0001f381 Пригласить")
async def menu_invite(message: types.Message):
    first_name = message.from_user.first_name or "друг"
    username = await get_bot_username()
    link = f"https://t.me/{username}?start=ref{message.from_user.id}"
    text = (
        f"{first_name}, ты знал(а)\U0001f914, что за каждого приглашенного друга, "
        f"ты получишь \U0001f4c5 {REFERRAL_BONUS_DAYS} дня VPN \U0001f310 в подарок \U0001f381?\n\n"
        "Вот твоя реферальная ссылка \U0001f60a:\n"
        f"{link}"
    )
    share_url = (
        "https://t.me/share/url?url="
        f"{quote_plus(link)}&text={quote_plus(link)}"
    )
    inline_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="\U0001f4e3 Поделиться", url=share_url)],
            [InlineKeyboardButton(text="\U0001f4a0 Главное меню", callback_data="main_menu")],
        ]
    )
    await message.answer(text, reply_markup=inline_kb)


@dp.message(F.text == "\U0001f198 Помощь")
async def menu_help(message: types.Message):
    await send_temporary(
        bot, message.chat.id, 'Раздел "Помощь" пока в разработке'
    )


async def main() -> None:
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
