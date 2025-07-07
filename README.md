# Telegram VPN Bot

Simple Telegram bot using [aiogram](https://docs.aiogram.dev/) v3.

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

For Railway or Nixpacks deployments, set the start command to `python bot.py` in `nixpacks.toml` or a `Procfile`.
