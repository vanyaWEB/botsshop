# 🚀 Руководство по развертыванию

## Railway Deployment (Рекомендуется)

### Шаг 1: Подготовка

1. Создайте аккаунт на [Railway.app](https://railway.app)
2. Установите Railway CLI (опционально):
\`\`\`bash
npm i -g @railway/cli
\`\`\`

### Шаг 2: Создание проекта

1. Нажмите "New Project" в Railway
2. Выберите "Deploy from GitHub repo"
3. Подключите ваш GitHub репозиторий

### Шаг 3: Добавление PostgreSQL

1. В проекте нажмите "New" → "Database" → "Add PostgreSQL"
2. Railway автоматически создаст переменную `DATABASE_URL`

### Шаг 4: Настройка переменных окружения

Добавьте следующие переменные в Railway:

\`\`\`env
BOT_TOKEN=your_bot_token_from_botfather
WEBAPP_URL=https://your-app.railway.app
ADMIN_IDS=123456789,987654321
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key
REQUIRED_CHANNEL_ID=@your_channel
REQUIRED_CHANNEL_URL=https://t.me/your_channel
\`\`\`

### Шаг 5: Деплой

1. Railway автоматически задеплоит приложение
2. Получите URL вашего приложения
3. Обновите `WEBAPP_URL` на актуальный URL

### Шаг 6: Настройка домена (опционально)

1. В настройках проекта перейдите в "Settings"
2. Добавьте свой домен в разделе "Domains"

## Альтернативные варианты

### Docker Deployment

\`\`\`bash
# Сборка образа
docker build -t telegram-shop .

# Запуск с PostgreSQL
docker-compose up -d
\`\`\`

### VPS Deployment

1. Установите зависимости:
\`\`\`bash
sudo apt update
sudo apt install python3.11 python3-pip postgresql
\`\`\`

2. Создайте базу данных:
\`\`\`bash
sudo -u postgres psql
CREATE DATABASE telegram_shop;
CREATE USER shop_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE telegram_shop TO shop_user;
\q
\`\`\`

3. Настройте переменные окружения:
\`\`\`bash
cp .env.example .env
nano .env
\`\`\`

4. Установите зависимости Python:
\`\`\`bash
pip install -r requirements.txt
\`\`\`

5. Запустите приложение:
\`\`\`bash
python main.py
\`\`\`

6. Настройте systemd для автозапуска:
\`\`\`bash
sudo nano /etc/systemd/system/telegram-shop.service
\`\`\`

\`\`\`ini
[Unit]
Description=Telegram Shop Bot
After=network.target postgresql.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/telegram-shop
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
\`\`\`

\`\`\`bash
sudo systemctl enable telegram-shop
sudo systemctl start telegram-shop
\`\`\`

## Проверка работоспособности

1. Откройте бота в Telegram
2. Отправьте команду `/start`
3. Проверьте доступность веб-приложения
4. Протестируйте админ-панель командой `/admin`

## Мониторинг

### Railway
- Логи доступны в разделе "Deployments" → "View Logs"
- Метрики в разделе "Metrics"

### VPS
\`\`\`bash
# Просмотр логов
sudo journalctl -u telegram-shop -f

# Проверка статуса
sudo systemctl status telegram-shop
\`\`\`

## Обновление

### Railway
1. Сделайте push в GitHub
2. Railway автоматически задеплоит новую версию

### VPS
\`\`\`bash
git pull
sudo systemctl restart telegram-shop
\`\`\`

## Резервное копирование

### PostgreSQL
\`\`\`bash
# Создание бэкапа
pg_dump -U shop_user telegram_shop > backup.sql

# Восстановление
psql -U shop_user telegram_shop < backup.sql
\`\`\`

## Troubleshooting

### Бот не отвечает
1. Проверьте логи
2. Убедитесь, что `BOT_TOKEN` правильный
3. Проверьте подключение к базе данных

### Веб-приложение не открывается
1. Проверьте `WEBAPP_URL` в переменных окружения
2. Убедитесь, что приложение запущено
3. Проверьте CORS настройки

### Ошибки базы данных
1. Проверьте `DATABASE_URL`
2. Убедитесь, что PostgreSQL запущен
3. Проверьте права доступа пользователя

## Поддержка

При возникновении проблем:
1. Проверьте логи приложения
2. Убедитесь, что все переменные окружения настроены
3. Проверьте документацию Railway/вашего хостинга
