# Telegram VPN Bot

Simple Telegram bot using [aiogram](https://docs.aiogram.dev/) v3.
The bot stores issued VPN keys in a local SQLite database so that each
user can only obtain a trial VPN once and paid keys expire automatically.

## Features

- `/start` and `/menu` commands show information about "Мировые анекдоты" VPN service and display an inline keyboard.
- Reply keyboard with quick access to common sections:
  - "🛒 Купить VPN | 📅 Продлить"
  - "🔑 Мои активные ключи"
  - "🧑‍💬 Отзывы"
  - "🎁 Пригласить"
  - "🆘 Помощь"
- Example responses for each menu item and inline button.

## Admin commands

Basic administration features are implemented in `admin.py`. Add your Telegram
user ID to the `ADMIN_IDS` list inside that file and include the router in the bot
application:

```python
from admin import router as admin_router
dp.include_router(admin_router)
```

After that administrators can use special commands:

- `/users` &mdash; list all recorded users with registration dates.
- `/active_keys` &mdash; show VPN keys that are still valid.
- `/expired_keys` &mdash; show users whose keys have expired.
- `/broadcast <message>` &mdash; send a message to every recorded user.
- `/add_user <user_id>` &mdash; manually add a user to the database.
- `/del_user <user_id>` &mdash; remove a user and their keys.
- `/wipe_db confirm` &mdash; delete **all** user and key information.

Users are stored in the database when they send the `/start` command or when
they receive a VPN key. Only IDs listed in `ADMIN_IDS` can run these commands.

## Requirements

Install dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
```

Set the `BOT_TOKEN` environment variable with your bot token and run:

```bash
python bot.py
```

The bot saves issued keys in a SQLite database. By default the database
file `vpn.sqlite` is created in the current directory. You can override
the location using the `DB_PATH` environment variable.

For Railway or Nixpacks deployments, set the start command to `python bot.py` in `nixpacks.toml` or a `Procfile`.

Messages sent via some commands are automatically deleted. You can configure the
delay using the `DELETE_DELAY` environment variable (in seconds, default `30`).

If you have an [Outline](https://getoutline.org/) VPN server, set the
`OUTLINE_API_URL` environment variable to your server's API URL. The bot will
create a new access key when you select "🔑 Мои активные ключи".

Set the `REVIEWS_CHANNEL_URL` environment variable to the link of your Telegram
channel with user reviews. When configured, the "🧑‍💬 Отзывы" button will show a
link opening this channel.

## Persistent data on Railway

To keep the SQLite database across restarts, create a Railway volume and mount
it in the container, for example at `/data`. Then set the `DB_PATH` environment
variable to a location on that volume:

```bash
DB_PATH=/data/vpn.sqlite
```

The application will create the directory for the database file if it does not
exist.

## Running Tests

After installing the dependencies, run the test suite with
[`pytest`](https://docs.pytest.org/):

```bash
pip install -r requirements.txt
pytest
```


