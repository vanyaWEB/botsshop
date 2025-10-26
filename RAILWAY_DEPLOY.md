# 🚂 Деплой на Railway - Пошаговая инструкция

## Шаг 1: Подготовка

1. Создайте аккаунт на [Railway.app](https://railway.app)
2. Установите Railway CLI (опционально):
\`\`\`bash
npm i -g @railway/cli
\`\`\`

## Шаг 2: Создание проекта

### Через веб-интерфейс:

1. Нажмите **"New Project"**
2. Выберите **"Deploy from GitHub repo"**
3. Подключите ваш GitHub репозиторий
4. Railway автоматически определит Python проект

### Через CLI:

\`\`\`bash
railway login
railway init
railway link
\`\`\`

## Шаг 3: Добавление PostgreSQL

1. В проекте нажмите **"New"** → **"Database"** → **"Add PostgreSQL"**
2. Railway автоматически создаст переменную `DATABASE_URL`

## Шаг 4: Настройка переменных окружения

В разделе **"Variables"** добавьте:

### Обязательные:
\`\`\`env
BOT_TOKEN=ваш_токен_от_BotFather
ADMIN_IDS=ваш_telegram_id
WEBAPP_URL=https://ваш-проект.up.railway.app
YOOKASSA_SHOP_ID=ваш_shop_id
YOOKASSA_SECRET_KEY=ваш_secret_key
SECRET_KEY=случайная_строка_для_flask
\`\`\`

### Опциональные:
\`\`\`env
REQUIRED_CHANNEL_ID=@ваш_канал
REQUIRED_CHANNEL_URL=https://t.me/ваш_канал
WEBAPP_PORT=8080
\`\`\`

## Шаг 5: Настройка домена

1. Перейдите в **"Settings"** → **"Networking"**
2. Нажмите **"Generate Domain"**
3. Скопируйте сгенерированный URL
4. Обновите переменную `WEBAPP_URL` этим URL

## Шаг 6: Деплой

Railway автоматически задеплоит проект при пуше в GitHub.

### Ручной деплой через CLI:
\`\`\`bash
railway up
\`\`\`

## Шаг 7: Проверка

1. Откройте логи: **"Deployments"** → выберите деплой → **"View Logs"**
2. Убедитесь что видите:
\`\`\`
Starting E-Commerce Telegram Bot System
Telegram Bot started successfully!
Web App started on port 8080
\`\`\`

3. Откройте ваш бот в Telegram и отправьте `/start`

## Шаг 8: Настройка ЮKassa

1. Войдите в [ЮKassa](https://yookassa.ru)
2. Создайте магазин
3. Получите `SHOP_ID` и `SECRET_KEY`
4. Добавьте их в переменные окружения Railway
5. Настройте webhook URL: `https://ваш-проект.up.railway.app/payment/webhook`

## Troubleshooting

### Бот не отвечает:
- Проверьте `BOT_TOKEN` в переменных
- Проверьте логи на ошибки
- Убедитесь что бот запущен: `railway logs`

### База данных не работает:
- Убедитесь что PostgreSQL плагин добавлен
- Проверьте что `DATABASE_URL` установлена автоматически
- Проверьте логи миграций

### Веб-приложение не открывается:
- Проверьте что `WEBAPP_URL` совпадает с Railway доменом
- Убедитесь что порт `8080` используется
- Проверьте логи Flask

### Платежи не работают:
- Проверьте `YOOKASSA_SHOP_ID` и `YOOKASSA_SECRET_KEY`
- Убедитесь что webhook настроен в ЮKassa
- Проверьте что магазин активирован

## Полезные команды Railway CLI

\`\`\`bash
# Просмотр логов
railway logs

# Подключение к базе данных
railway connect postgres

# Просмотр переменных
railway variables

# Перезапуск
railway restart

# Статус
railway status
\`\`\`

## Мониторинг

Railway предоставляет:
- 📊 Метрики использования CPU/RAM
- 📈 Графики трафика
- 🔍 Логи в реальном времени
- ⚡ Автоматический перезапуск при сбоях

## Масштабирование

Railway автоматически масштабирует приложение при необходимости.

Для ручного масштабирования:
1. **Settings** → **Resources**
2. Увеличьте лимиты CPU/RAM

## Бэкапы

PostgreSQL на Railway автоматически создает бэкапы.

Для ручного бэкапа:
\`\`\`bash
railway connect postgres
pg_dump > backup.sql
\`\`\`

## Стоимость

- **Hobby Plan:** $5/месяц (500 часов выполнения)
- **Pro Plan:** $20/месяц (безлимит)

PostgreSQL включен в стоимость плана.

---

**Готово! Ваш магазин работает 24/7 🎉**
