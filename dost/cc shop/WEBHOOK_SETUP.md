# 🌐 Настройка вебхуков для LUXURY SHOP

## 📋 Что такое вебхуки?

Вебхуки - это автоматические уведомления от CryptoBot о статусе платежей. Вместо ручной проверки, бот автоматически получает информацию о:
- ✅ Успешных платежах
- ❌ Отмененных платежах  
- ⏰ Истекших платежах

## 🚀 Преимущества вебхуков

1. **Автоматическая выдача товаров** - товар выдается сразу после оплаты
2. **Мгновенное обновление статусов** - заказы обновляются в реальном времени
3. **Снижение нагрузки** - не нужно постоянно опрашивать API
4. **Надежность** - гарантированное получение уведомлений

## ⚙️ Настройка вебхуков

### Шаг 1: Настройка .env файла

Добавьте в ваш `.env` файл:

```env
# Webhook настройки
WEBHOOK_URL=https://yourdomain.com/webhook
WEBHOOK_SECRET=your_webhook_secret_key
```

### Шаг 2: Настройка домена

У вас должен быть доступный из интернета домен с SSL сертификатом. Варианты:

#### Вариант A: VPS/Хостинг
```bash
# Установите nginx или apache
sudo apt update
sudo apt install nginx

# Настройте reverse proxy на порт 8080
# Создайте SSL сертификат через Let's Encrypt
```

#### Вариант B: Ngrok (для тестирования)
```bash
# Установите ngrok
# Запустите туннель
ngrok http 8080

# Скопируйте HTTPS URL (например: https://abc123.ngrok.io)
# Добавьте в .env: WEBHOOK_URL=https://abc123.ngrok.io/webhook
```

### Шаг 3: Настройка CryptoBot

1. Откройте [@CryptoBot](https://t.me/CryptoBot)
2. Отправьте `/start`
3. Выберите "Crypto Pay" → "My Apps"
4. Выберите ваше приложение
5. Нажмите "Webhooks"
6. Добавьте URL: `https://yourdomain.com/webhook`
7. Сохраните

### Шаг 4: Запуск вебхук сервера

#### Windows
```bash
# Двойной клик на файл
start_webhook.bat
```

#### Linux/Mac
```bash
python3 webhook_handler.py
```

## 🔧 Конфигурация вебхук сервера

### Порт по умолчанию: 8080

Если нужно изменить порт, отредактируйте `webhook_handler.py`:

```python
# В конце файла
if __name__ == "__main__":
    asyncio.run(start_webhook_server(port=9000))  # Измените порт
```

### Настройка хоста

```python
# Для локального доступа только
asyncio.run(start_webhook_server(host='127.0.0.1', port=8080))

# Для доступа из интернета
asyncio.run(start_webhook_server(host='0.0.0.0', port=8080))
```

## 📊 Мониторинг вебхуков

### Через административную панель

1. Запустите `admin.py`
2. Выберите "11. 📡 Статус вебхуков"
3. Просмотрите статистику

### Через базу данных

```sql
-- Последние вебхуки
SELECT * FROM webhook_logs ORDER BY processed_at DESC LIMIT 10;

-- Статистика по типам
SELECT webhook_type, COUNT(*) FROM webhook_logs GROUP BY webhook_type;

-- Успешные вебхуки
SELECT * FROM webhook_logs WHERE success = 1;
```

## 🔒 Безопасность

### Проверка подписи

Вебхуки проверяются через HMAC-SHA256 подпись:

```python
# В webhook_handler.py
def verify_webhook_signature(self, payload: str, signature: str) -> bool:
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)
```

### Рекомендации по безопасности

1. **Используйте HTTPS** - все вебхуки должны приходить по защищенному соединению
2. **Сложный секрет** - используйте длинный случайный секрет для WEBHOOK_SECRET
3. **Ограничение доступа** - настройте firewall для доступа только с IP CryptoBot
4. **Логирование** - все вебхуки логируются в базу данных

## 🆘 Устранение неполадок

### Проблема: Вебхуки не приходят

**Решение:**
1. Проверьте доступность URL: `curl https://yourdomain.com/webhook`
2. Убедитесь, что сервер запущен: `python webhook_handler.py`
3. Проверьте настройки в CryptoBot
4. Проверьте логи сервера

### Проблема: Ошибка подписи

**Решение:**
1. Проверьте WEBHOOK_SECRET в .env
2. Убедитесь, что секрет совпадает с настройками CryptoBot
3. Проверьте формат данных вебхука

### Проблема: Сервер не запускается

**Решение:**
1. Проверьте зависимости: `pip install -r requirements.txt`
2. Убедитесь, что порт 8080 свободен
3. Проверьте права доступа к файлам

## 📱 Тестирование вебхуков

### Тестовый вебхук

```bash
# Отправьте тестовый POST запрос
curl -X POST https://yourdomain.com/webhook \
  -H "Content-Type: application/json" \
  -H "X-Crypto-Pay-API-Signature: test_signature" \
  -d '{"status": "paid", "invoice_id": "test_123"}'
```

### Проверка в базе данных

```sql
-- Проверьте, что вебхук записался
SELECT * FROM webhook_logs WHERE webhook_type = 'test';
```

## 🚀 Автозапуск вебхук сервера

### Windows (через планировщик задач)

1. Откройте "Планировщик задач"
2. Создайте новую задачу
3. Настройте запуск `start_webhook.bat` при старте системы

### Linux (через systemd)

Создайте файл `/etc/systemd/system/luxury-shop-webhook.service`:

```ini
[Unit]
Description=LUXURY SHOP Webhook Server
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/luxury-shop
ExecStart=/usr/bin/python3 webhook_handler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Затем:
```bash
sudo systemctl enable luxury-shop-webhook
sudo systemctl start luxury-shop-webhook
```

## 📈 Масштабирование

### Несколько серверов

Для высокой нагрузки можно запустить несколько экземпляров:

```bash
# Сервер 1
python webhook_handler.py --port 8080

# Сервер 2  
python webhook_handler.py --port 8081

# Настройте nginx для балансировки нагрузки
```

### Мониторинг производительности

```python
# В webhook_handler.py добавьте метрики
import time

async def webhook_handler(request):
    start_time = time.time()
    
    # ... обработка вебхука ...
    
    processing_time = time.time() - start_time
    print(f"Webhook processed in {processing_time:.3f}s")
```

---

**🌐 LUXURY SHOP Webhook System** - Автоматизация платежей на максимальном уровне! 🚀
