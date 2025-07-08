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

## Testing

Install requirements and run the test suite:

```bash
pip install -r requirements.txt
pytest
```

The tests patch out external dependencies, so no network services are required.
