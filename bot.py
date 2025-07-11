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
    get_last_notification,
    set_last_notification,
    get_connection,
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

# Device links for Outline clients
DEVICE_LINKS = {
    "android": "https://play.google.com/store/apps/details?id=org.outline.android.client",
    "ios": "https://apps.apple.com/app/outline-app/id1356177741",
    "windows": "https://getoutline.org/",
    "macos": "https://getoutline.org/",
    "androidtv": "https://play.google.com/store/apps/details?id=org.outline.android.client",
}


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


def outline_manager() -> Manager:
    if not OUTLINE_API_URL:
        raise RuntimeError("OUTLINE_API_URL not configured")
    return Manager(apiurl=OUTLINE_API_URL, apicrt="")


async def create_outline_key(label: str | None = None) -> dict:
    manager = outline_manager()
    key = await asyncio.to_thread(manager.new, label)
    if label and "id" in key:
        try:
            await asyncio.to_thread(manager.rename, key["id"], label)
        except Exception as exc:
            logging.error("Failed to rename Outline key: %s", exc)
    return key


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


async def send_activation_prompt(chat_id: int, access_url: str, expires_at: int) -> None:
    """Send activation info and device selection keyboard in three messages."""
    date_str = time.strftime("%d.%m.%Y", time.localtime(expires_at))
    first = (
        f"\U0001f389 \u0414\u043e\u0441\u0442\u0443\u043f \u0430\u043a\u0442\u0438\u0432\u0438\u0440\u043e\u0432\u0430\u043d \u0434\u043e {date_str}\n\n"
        "\U0001f511 \u0412\u0430\u0448 VPN-\u043a\u043b\u044e\u0447:"
    )
    second = access_url
    third = (
        "\U0001f4f2 \u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0441\u0432\u043e\u0451 \u0443\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u043e, \u0447\u0442\u043e\u0431\u044b \u043f\u043e\u043b\u0443\u0447\u0438\u0442\u044c \u043a\u043b\u0438\u0435\u043d\u0442 \u0438 \u0438\u043d\u0441\u0442\u0440\u0443\u043a\u0446\u0438\u044e:"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="\U0001f4f1 Android", callback_data="device_android"),
                InlineKeyboardButton(text="\U0001f34f iOS", callback_data="device_ios"),
            ],
            [
                InlineKeyboardButton(text="\U0001f4bb Windows", callback_data="device_windows"),
                InlineKeyboardButton(text="\U0001f5a5 MacOS", callback_data="device_macos"),
            ],
            [
                InlineKeyboardButton(text="\U0001f4fa Android TV", callback_data="device_androidtv"),
            ],
        ]
    )

    await bot.send_message(chat_id, first)
    await bot.send_message(chat_id, second)
    await bot.send_message(chat_id, third, reply_markup=kb)


async def notify_expirations_loop(interval: int = 60 * 60) -> None:
    """Periodically check VPN subscriptions and send reminders."""
    while True:
        now = int(time.time())
        async with get_connection() as conn:
            cursor = await conn.execute(
                "SELECT user_id, expires_at FROM vpn_access "
                "WHERE key_id IS NOT NULL AND expires_at IS NOT NULL AND is_trial=0"
            )
            rows = await cursor.fetchall()
        for user_id, expires_at in rows:
            if expires_at is None:
                continue
            days_left = (expires_at - now + 86399) // 86400
            last = await get_last_notification(user_id)
            if last and now - last < 24 * 60 * 60:
                continue
            text = None
            if days_left == 3:
                text = (
                    "\u23f3 \u041d\u0430\u043f\u043e\u043c\u0438\u043d\u0430\u0435\u043c: "
                    "\u0441\u0440\u043e\u043a \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u044f "
                    "\u0432\u0430\u0448\u0435\u0433\u043e VPN \u0441\u043a\u043e\u0440\u043e \u0437\u0430\u043a\u043e\u043d\u0447\u0438\u0442\u0441\u044f!\n"
                    "\ud83d\udcc5 \u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c \u0432\u0441\u0435\u0433\u043e 3 \u0434\u043d\u044f. \u041d\u0435 \u0437\u0430\u0431\u0443\u0434\u044c\u0442\u0435 \u043f\u0440\u043e\u0434\u043b\u0438\u0442\u044c.\n"
                    "\ud83d\udd25 \u041f\u0440\u043e\u0434\u043b\u0438\u0442\u0435 \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0443 \u043f\u0440\u044f\u043c\u043e \u0441\u0435\u0439\u0447\u0430\u0441 \u2014 \u044d\u0442\u043e \u0437\u0430\u0439\u043c\u0451\u0442 \u043d\u0435 \u0431\u043e\u043b\u044c\u0448\u0435 \u043c\u0438\u043d\u0443\u0442\u044b!"
                )
            elif days_left <= 0:
                if days_left == 0:
                    text = (
                        "\ud83d\udeab \u0421\u0440\u043e\u043a \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u044f \u0432\u0430\u0448\u0435\u0433\u043e VPN \u0437\u0430\u043a\u043e\u043d\u0447\u0438\u043b\u0441\u044f.\n"
                        "\ud83d\udd25 \u041f\u0440\u043e\u0434\u043b\u0438 \u043d\u0430 30 \u0434\u043d\u0435\u0439 \u0432\u0441\u0435\u0433\u043e \u0437\u0430 [\u0446\u0435\u043d\u0443]\n"
                        "\u25b6\ufe0f \u041d\u0430\u0436\u043c\u0438\u0442\u0435 /\u043f\u0440\u043e\u0434\u043b\u0438\u0442\u044c \u2014 \u0438 \u0434\u043e\u0441\u0442\u0443\u043f \u0432\u043e\u0441\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u0441\u044f \u0432 \u0441\u0447\u0438\u0442\u0430\u043d\u043d\u044b\u0435 \u043c\u0438\u043d\u0443\u0442\u044b!"
                    )
                else:
                    text = (
                        "\u23f3 \u041d\u0430\u043f\u043e\u043c\u0438\u043d\u0430\u0435\u043c: "
                        "\u0432\u0430\u0448 VPN \u043f\u043e-\u043f\u0440\u0435\u0436\u043d\u0435\u043c\u0443 \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d.\n"
                        "\ud83d\udca1 \u041f\u0440\u043e\u0434\u043b\u0435\u043d\u0438\u0435 \u0437\u0430\u0439\u043c\u0451\u0442 \u043c\u0438\u043d\u0443\u0442\u0443, \u0430 \u0434\u043e\u0441\u0442\u0443\u043f \u2014 \u043d\u0430 \u043c\u0435\u0441\u044f\u0446!\n"
                        "\ud83d\udd25 \u041d\u0430\u0436\u043c\u0438\u0442\u0435 /\u043f\u0440\u043e\u0434\u043b\u0438\u0442\u044c \u0438 \u0432\u0435\u0440\u043d\u0438\u0442\u0435\u0441\u044c \u043a \u0441\u043a\u043e\u0440\u043e\u0441\u0442\u0438 \u0438 \u0441\u0432\u043e\u0431\u043e\u0434\u0435 \ud83d\udee1"
                    )
            if text:
                try:
                    await bot.send_message(user_id, text)
                    await set_last_notification(user_id, now)
                except Exception as exc:
                    logging.error("Failed to send notification: %s", exc)
        await asyncio.sleep(interval)


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

        logging.info("Issued referral key %s for user %s", key.get("id"), referrer_id)

        await send_activation_prompt(
            referrer_id,
            key.get("accessUrl", "не удалось получить"),
            expires,
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
            ]
        ]
    )

    reply_kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="\U0001f6d2 Купить VPN | \U0001f4c5 Продлить"),
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
            key = await create_outline_key(label=f"vpn_{callback.from_user.id}")
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
            await send_activation_prompt(
                callback.message.chat.id,
                key.get("accessUrl", "не удалось получить"),
                expires,
            )
        except Exception as exc:
            logging.error("Failed to create trial key: %s", exc)
            await send_temporary(
                bot,
                callback.message.chat.id,
                "Не удалось получить пробный ключ.",
            )
    await callback.answer()


@dp.callback_query(F.data.startswith("device_"))
async def callback_device(callback: types.CallbackQuery):
    device = callback.data.split("_", 1)[1]
    link = DEVICE_LINKS.get(device)
    row = await get_key_info(callback.from_user.id)
    if not row:
        await callback.message.answer("\u041a\u043b\u044e\u0447 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d.")
        await callback.answer()
        return
    _, access_url, _, _ = row
    first = (
        f"\u2705 \u0421\u043a\u0430\u0447\u0430\u0442\u044c Outline Client: {link}\n\n"
        "\u2705 \u0412\u0430\u0448 \u043a\u043b\u044e\u0447:"
    )
    second = access_url
    third = (
        "\u041d\u0430\u0436\u043c\u0438\u0442\u0435 '+' , \u0432\u044b\u0431\u0435\u0440\u0438\u0442\u0435 '\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043a\u043b\u044e\u0447 \u0432\u0440\u0443\u0447\u043d\u0443\u044e', \u0432\u0441\u0442\u0430\u0432\u044c\u0442\u0435 \u0441\u0441\u044b\u043b\u043a\u0443 \u043a\u043e\u0442\u043e\u0440\u0443\u044e \u043e\u0442\u043f\u0440\u0430\u0432\u0438\u043b\u0438 \u0432\u044b\u0448\u0435\n\u0413\u043e\u0442\u043e\u0432\u043e, \u0442\u0435\u043f\u0435\u0440\u044c VPN \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d \u043d\u0430 \u0432\u0430\u0448\u0435 \u0443\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u043e"
    )
    await callback.message.answer(first)
    await callback.message.answer(second)
    await callback.message.answer(third)
    await callback.answer()


@dp.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: types.CallbackQuery):
    await cmd_start(callback.message)
    await callback.answer()


@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    await cmd_start(message)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await menu_help(message)


@dp.message(F.text == "\U0001f511 Мои активные ключи")
async def menu_keys(message: types.Message):
    row = await get_active_key(message.from_user.id)
    now_ts = int(time.time())
    if row:
        access_url, expires_at, is_trial = row
        if expires_at is not None and expires_at <= now_ts:
            await clear_key(message.from_user.id, bool(is_trial))
            await send_temporary(bot, message.chat.id, "Срок действия вашего ключа истёк.")
        else:
            date_str = time.strftime("%d.%m.%Y", time.localtime(expires_at))
            await send_temporary(
                bot, message.chat.id, f"\U0001f511 Ваш ключ активен до {date_str}"
            )
            await send_temporary(bot, message.chat.id, access_url)
    else:
        await send_temporary(bot, message.chat.id, "У вас нет активного ключа.")


@dp.message(F.text == "\U0001f9d1\u200d\U0001f4ac Отзывы")
async def menu_reviews(message: types.Message):
    await send_temporary(bot, message.chat.id, 'Раздел "Отзывы" пока в разработке')


@dp.message(F.text == "\U0001f6d2 Купить VPN | \U0001f4c5 Продлить")
async def menu_buy(message: types.Message):
    text = (
        "\U0001f525 Оформляя подписку на Premium VPN от Мировые анекдоты — "
        "вы получаете: \U0001f447\n\n"
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
    inline_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\U0001f4e3 Поделиться", switch_inline_query=link
                )
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f4a0 Главное меню", callback_data="main_menu"
                )
            ],
        ]
    )
    await message.answer(text, reply_markup=inline_kb)


@dp.message(F.text == "\U0001f198 Помощь")
async def menu_help(message: types.Message):
    await send_temporary(bot, message.chat.id, 'Раздел "Помощь" пока в разработке')


@dp.message(F.text == "\U0001f4a0 Главное меню")
async def back_to_menu(message: types.Message):
    await cmd_start(message)


async def main() -> None:
    await init_db()
    asyncio.create_task(notify_expirations_loop())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
