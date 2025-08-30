## Netlify Functions: Webhook для CryptoBot

Этот проект может принимать вебхуки через Netlify Functions, не поднимая свой сервер. Мы добавили:

- `netlify/functions/cryptobot-webhook.js` — обработчик вебхука
- `netlify.toml` — маршрут `/webhook` → функция

### 1) Что делает функция

- Проверяет подпись `X-Crypto-Pay-API-Signature` по `WEBHOOK_SECRET`
- Подтверждает статус счета через CryptoBot API (`CRYPTOBOT_TOKEN`)
- При статусе `paid` может отправить уведомление администратору в Telegram (опционально)
- Опционально ретранслирует проверенный вебхук на ваш сервер (экономит второй дедик)

Важно: локальная `SQLite` база на Netlify не сохранится между вызовами функции. Для реальной выдачи/обновления заказов используйте внешнюю БД (например, Supabase, Postgres, Firebase) или ретрансляцию на ваш сервер.

### 2) Переменные окружения (Netlify → Site settings → Environment variables)

- `WEBHOOK_SECRET` — секрет для HMAC подписи (должен совпадать с настройками в CryptoBot)
- `CRYPTOBOT_TOKEN` — токен Crypto Pay API
- `BOT_TOKEN` — Telegram бот токен (опционально, для уведомлений)
- `ADMIN_ID` — Telegram chat_id админа (опционально)
- `FORWARD_URL` — ваш бекенд-эндпоинт, который будет принимать проверенный вебхук
- `RELAY_TOKEN` — произвольный секрет для аутентификации ретрансляции (передается в заголовке `X-Relay-Token`)

### 3) Деплой

Вариант A — через UI:
- Создайте новый сайт в Netlify, подключите этот репозиторий
- Установите переменные окружения (см. выше)
- Деплойте ветку

Вариант B — через CLI:
```bash
npm i -g netlify-cli
netlify login
netlify init  # создать/привязать сайт
netlify env:set WEBHOOK_SECRET your_secret
netlify env:set CRYPTOBOT_TOKEN your_token
# опционально
netlify env:set BOT_TOKEN 123:ABC
netlify env:set ADMIN_ID 123456789
netlify env:set FORWARD_URL https://your-backend.example.com/webhook
netlify env:set RELAY_TOKEN your_relay_secret
netlify deploy --prod
```

После деплоя URL вебхука будет:
```
https://<your-site>.netlify.app/webhook
```

### 4) Настройка в CryptoBot

В кабинете Crypto Pay укажите URL вебхука `https://<your-site>.netlify.app/webhook` и тот же `WEBHOOK_SECRET`.

### 5) Тест

```bash
curl -X POST https://<your-site>.netlify.app/webhook \
  -H "Content-Type: application/json" \
  -H "X-Crypto-Pay-API-Signature: <hmac_sha256_hex>" \
  -d '{"status":"paid","invoice_id":"test_123","amount":"10","currency":"USDT"}'
```

Где `<hmac_sha256_hex>` — HMAC-SHA256 тела запроса по ключу `WEBHOOK_SECRET`.

### 6) Обновление заказов/выдача товара

Так как Netlify Function — статeless, используйте один из подходов:

- Внешняя БД: переместите таблицы из `sqlite` в облачную БД; обновляйте заказы из функции
- Ретрансляция: функция после валидации делает POST на ваш бекенд (`FORWARD_URL`) + `X-Relay-Token` → на сервере проверьте токен и обработайте заказ
- Уведомление: функция шлет сообщение админу в Telegram (уже реализовано как опция)


