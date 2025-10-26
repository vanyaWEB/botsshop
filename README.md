# Telegram E-commerce Bot

Полнофункциональный бот для интернет-магазина одежды в Telegram с админ-панелью, каталогом товаров, корзиной и интеграцией с ЮKassa.

## Возможности

### Для пользователей:
- 🛍 Просмотр каталога товаров через WebApp
- 🛒 Корзина с управлением количеством
- 📦 Оформление заказов
- 💳 Оплата через ЮKassa
- 📱 Отслеживание статуса заказов
- 🎨 Светлая/темная тема
- ✅ Проверка подписки на канал

### Для администраторов:
- 📂 Управление категориями (добавление, редактирование, удаление)
- 🛍 Управление товарами (добавление, редактирование, удаление, фото)
- 👥 Управление пользователями (просмотр, блокировка)
- 📦 Управление заказами (изменение статуса)
- 📊 Детальная статистика (продажи, выручка, топ товары)
- 📢 Рассылка сообщений всем пользователям
- 🔔 Уведомления о новых заказах

## Технологии

- **Python 3.10+**
- **aiogram 3.x** - Telegram Bot API
- **SQLAlchemy** - ORM для работы с БД
- **PostgreSQL** - База данных (общая для бота и веб-приложения)
- **Flask** - Web-приложение для каталога
- **YooKassa** - Платежная система
- **HTML/CSS/JavaScript** - WebApp интерфейс

## Установка

### 1. Клонирование репозитория

\`\`\`bash
git clone <repository-url>
cd telegram-ecommerce-bot
\`\`\`

### 2. Установка зависимостей

\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 3. Настройка PostgreSQL

#### Локальная разработка:

\`\`\`bash
# Установите PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Создайте базу данных
sudo -u postgres psql
CREATE DATABASE shop_db;
CREATE USER shop_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE shop_db TO shop_user;
\q
\`\`\`

#### Для Railway/Heroku:
База данных создается автоматически, переменная `DATABASE_URL` устанавливается автоматически.

### 4. Настройка окружения

Создайте файл `.env` на основе `.env.example`:

\`\`\`bash
cp .env.example .env
\`\`\`

Заполните переменные окружения:

\`\`\`env
# Telegram Bot
BOT_TOKEN=ваш_токен_от_botfather
ADMIN_IDS=ваш_telegram_id

# YooKassa
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key

# Web App
WEBAPP_URL=http://localhost:8080
WEBAPP_PORT=8080

# Database (PostgreSQL)
DATABASE_URL=postgresql://shop_user:your_password@localhost:5432/shop_db

# Channel (optional)
REQUIRED_CHANNEL_ID=@yourchannel
REQUIRED_CHANNEL_URL=https://t.me/yourchannel
\`\`\`

### 5. Запуск

#### Запуск бота и веб-приложения одной командой:

\`\`\`bash
python main.py
\`\`\`

База данных инициализируется автоматически при первом запуске.

## Структура проекта

\`\`\`
telegram-ecommerce-bot/
├── database/
│   ├── models.py          # Модели БД
│   ├── db.py             # Подключение к PostgreSQL (общая БД)
│   └── crud.py           # CRUD операции
├── handlers/
│   ├── user_handlers.py   # Обработчики для пользователей
│   ├── admin_handlers.py  # Обработчики для админов
│   ├── cart_handlers.py   # Обработчики корзины
│   ├── order_handlers.py  # Обработчики заказов
│   └── payment_handlers.py # Обработчики оплаты
├── utils/
│   ├── keyboards.py       # Клавиатуры
│   ├── helpers.py         # Вспомогательные функции
│   └── payment.py         # Интеграция с YooKassa
├── webapp/
│   ├── app.py            # Flask приложение
│   └── templates/        # HTML шаблоны
│       ├── base.html
│       ├── index.html
│       └── catalog.html
├── main.py               # 🚀 ЕДИНАЯ ТОЧКА ВХОДА (бот + webapp)
├── config.py             # Конфигурация
├── requirements.txt      # Все зависимости (включая PostgreSQL)
├── Dockerfile            # Docker конфигурация
└── railway.json          # Railway конфигурация
\`\`\`

## Использование

### Команды бота

- `/start` - Запуск бота и главное меню
- `/admin` - Админ-панель (только для администраторов)

### Админ-панель

Администраторы имеют доступ к расширенной панели управления:

1. **Категории** - Создание и управление категориями товаров
2. **Товары** - Добавление товаров с фото, описанием, размерами
3. **Заказы** - Просмотр и изменение статуса заказов
4. **Пользователи** - Управление пользователями
5. **Статистика** - Детальная аналитика продаж
6. **Рассылка** - Отправка сообщений всем пользователям

### Добавление товара

1. Откройте админ-панель `/admin`
2. Выберите "Товары"
3. Выберите категорию
4. Нажмите "Добавить товар"
5. Следуйте инструкциям:
   - Введите название
   - Введите описание
   - Укажите цену
   - Укажите размеры (через запятую)
   - Укажите количество на складе
   - Отправьте фотографии
   - Нажмите `/done`

## Деплой

### 🚂 Railway (Рекомендуется)

Самый простой способ деплоя с автоматической PostgreSQL:

1. Создайте аккаунт на [Railway.app](https://railway.app)
2. Нажмите "New Project" → "Deploy from GitHub repo"
3. Выберите ваш репозиторий
4. Добавьте PostgreSQL: "New" → "Database" → "Add PostgreSQL"
5. Настройте переменные окружения (см. `.env.example`)
6. Railway автоматически задеплоит проект

**Подробная инструкция:** См. [RAILWAY_DEPLOY.md](RAILWAY_DEPLOY.md)

### Docker

\`\`\`bash
# Сборка
docker build -t telegram-shop .

# Запуск
docker run -d \
  --name telegram-shop \
  -p 8080:8080 \
  --env-file .env \
  telegram-shop
\`\`\`

### Docker Compose

\`\`\`bash
docker-compose up -d
\`\`\`

### На VPS/Dedicated сервере

1. Установите Python 3.10+ и PostgreSQL
2. Клонируйте репозиторий
3. Установите зависимости
4. Настройте systemd сервис:

**Единый сервис** (`/etc/systemd/system/telegram-shop.service`):

\`\`\`ini
[Unit]
Description=Telegram Shop (Bot + WebApp)
After=network.target postgresql.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/telegram-ecommerce-bot
Environment="DATABASE_URL=postgresql://shop_user:password@localhost:5432/shop_db"
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
\`\`\`

5. Запустите сервис:

\`\`\`bash
sudo systemctl enable telegram-shop
sudo systemctl start telegram-shop
sudo systemctl status telegram-shop
\`\`\`

### Nginx конфигурация

\`\`\`nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
\`\`\`

## Безопасность

- ✅ Храните `.env` файл в безопасности
- ✅ Используйте HTTPS для веб-приложения
- ✅ Регулярно обновляйте зависимости
- ✅ Используйте сильные пароли для PostgreSQL
- ✅ Ограничьте доступ к базе данных
- ✅ Используйте сильные пароли для YooKassa
- ✅ Настройте firewall на сервере

## Мониторинг

### Логи

\`\`\`bash
# Просмотр логов
tail -f /var/log/telegram-shop.log

# Логи systemd
sudo journalctl -u telegram-shop -f
\`\`\`

### База данных

\`\`\`bash
# Подключение к PostgreSQL
psql -U shop_user -d shop_db

# Бэкап
pg_dump -U shop_user shop_db > backup.sql

# Восстановление
psql -U shop_user shop_db < backup.sql
\`\`\`

## Troubleshooting

### Ошибка подключения к БД

\`\`\`
FATAL: password authentication failed
\`\`\`

**Решение:** Проверьте `DATABASE_URL` в `.env` файле

### Бот не отвечает

**Решение:** 
1. Проверьте `BOT_TOKEN`
2. Проверьте логи: `python main.py`
3. Убедитесь что бот не запущен в другом месте

### Веб-приложение не открывается

**Решение:**
1. Проверьте что порт 8080 свободен
2. Проверьте `WEBAPP_URL` в `.env`
3. Проверьте firewall

## Поддержка

При возникновении проблем:

1. Проверьте логи бота
2. Убедитесь, что все переменные окружения заданы
3. Проверьте подключение к PostgreSQL
4. Убедитесь, что порты не заняты

## Лицензия

MIT License

## Автор

Создано с помощью v0 by Vercel

## Дизайн

### 🎨 Современный UI/UX

Бот и веб-приложение разработаны с фокусом на современный дизайн и удобство использования:

#### Веб-приложение:
- **Адаптивный дизайн** - Идеально работает на всех устройствах (телефоны, планшеты, десктопы)
- **Плавные анимации** - Градиенты, переходы, hover-эффекты
- **Темная/светлая тема** - Автоматическое переключение с сохранением предпочтений
- **Карусель изображений** - Красивый просмотр фото товаров с индикаторами
- **Модальные окна** - Современные всплывающие окна с backdrop blur
- **Touch-friendly** - Кнопки минимум 44px для удобного нажатия
- **Haptic feedback** - Вибрация при взаимодействии (Telegram WebApp)

#### Telegram бот:
- **Inline клавиатуры** - Удобная навигация с эмодзи
- **Красивое форматирование** - Структурированные сообщения с эмодзи
- **Быстрые ответы** - Минимальное время отклика
- **Интуитивный UX** - Понятный flow для пользователей

### Цветовая схема

**Светлая тема:**
- Primary: `#6366f1` (Indigo)
- Secondary: `#8b5cf6` (Purple)
- Background: `#ffffff`
- Surface: `#f8fafc`

**Темная тема:**
- Primary: `#818cf8` (Light Indigo)
- Secondary: `#a78bfa` (Light Purple)
- Background: `#0f172a`
- Surface: `#1e293b`
