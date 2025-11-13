# Kinguin Telegram Bot

Telegram бот для покупки игровых ключей через Kinguin API v2.

## Установка

```bash
pip install -r bot/requirements.txt
```

## Конфигурация

Создайте `.env` в корне:

```env
TELEGRAM_BOT_TOKEN=ваш_токен
TELEGRAM_ALLOWED_USERS=ваш_telegram_id
KINGUIN_API_KEY=ваш_ключ
KINGUIN_API_SECRET=ваш_секрет
```

Где взять:
- Telegram токен: [@BotFather](https://t.me/BotFather) → `/newbot`
- Telegram ID: [@userinfobot](https://t.me/userinfobot)
- Kinguin API: [kinguin.net](https://kinguin.net) → Settings → API (Production)

## Запуск

```bash
python bot/main.py
```

## Команды

- `/start` - Начать работу
- `/buy <id> <qty>` - Купить товар
- `/balance` - Баланс аккаунта
- `/history` - История покупок

## Возможности

- Покупка с подтверждением через inline кнопки
- Автоотправка ключей в чат
- Фоновая проверка заказов
- SQLite история
- Контроль доступа

## Структура

```
bot/
├── main.py            # Запуск
├── telegram_bot.py    # Telegram логика
├── kinguin_client.py  # Kinguin API v2
├── database.py        # SQLite
├── config.py          # Конфиг
└── requirements.txt
```
