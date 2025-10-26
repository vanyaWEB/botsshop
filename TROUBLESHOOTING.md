# 🔧 Решение проблем

## Частые ошибки и их решения

### 1. Бот не отвечает

**Проблема:** Бот не реагирует на команды

**Решение:**
\`\`\`bash
# Проверьте токен бота
echo $BOT_TOKEN

# Проверьте логи
tail -f logs/bot.log

# Перезапустите бота
python main.py
\`\`\`

### 2. Ошибка подключения к БД

**Проблема:** `connection refused` или `could not connect to server`

**Решение:**
\`\`\`bash
# Проверьте PostgreSQL
sudo systemctl status postgresql

# Проверьте DATABASE_URL
echo $DATABASE_URL

# Проверьте подключение
psql $DATABASE_URL -c "SELECT 1"
\`\`\`

### 3. ЮKassa ошибки

**Проблема:** Платежи не проходят

**Решение:**
- Проверьте `YOOKASSA_SHOP_ID` и `YOOKASSA_SECRET_KEY`
- Убедитесь что используете правильный режим (test/prod)
- Проверьте webhook URL в личном кабинете ЮKassa
- Проверьте логи: `tail -f logs/payment.log`

### 4. WebApp не загружается

**Проблема:** Белый экран или ошибка загрузки

**Решение:**
\`\`\`bash
# Проверьте WEBAPP_URL
echo $WEBAPP_URL

# Проверьте Flask
curl http://localhost:8080/health

# Проверьте логи
tail -f logs/webapp.log
\`\`\`

### 5. Фото не загружаются

**Проблема:** Изображения не отображаются

**Решение:**
- Проверьте file_id в базе данных
- Убедитесь что бот имеет доступ к файлам
- Проверьте размер файлов (макс 20MB)
- Используйте правильный формат (JPG, PNG)

### 6. Медленная работа

**Проблема:** Бот медленно отвечает

**Решение:**
\`\`\`bash
# Проверьте нагрузку на сервер
htop

# Проверьте подключения к БД
SELECT count(*) FROM pg_stat_activity;

# Оптимизируйте запросы
EXPLAIN ANALYZE SELECT * FROM products;

# Добавьте индексы
CREATE INDEX idx_products_category ON products(category_id);
\`\`\`

### 7. Ошибки миграций

**Проблема:** Alembic ошибки при миграции

**Решение:**
\`\`\`bash
# Проверьте текущую версию
alembic current

# Откатите последнюю миграцию
alembic downgrade -1

# Примените заново
alembic upgrade head

# Если не помогает - пересоздайте БД
dropdb dbname
createdb dbname
alembic upgrade head
\`\`\`

### 8. Railway деплой ошибки

**Проблема:** Деплой падает на Railway

**Решение:**
- Проверьте логи в Railway dashboard
- Убедитесь что все env переменные установлены
- Проверьте `railway.json` конфигурацию
- Проверьте `Dockerfile` и `requirements.txt`

### 9. Память заканчивается

**Проблема:** Out of memory errors

**Решение:**
\`\`\`bash
# Проверьте использование памяти
free -h

# Оптимизируйте запросы
# Используйте pagination
# Закрывайте сессии БД

# Увеличьте лимиты в Railway
# Settings -> Resources -> Memory
\`\`\`

### 10. CORS ошибки

**Проблема:** WebApp не может обращаться к API

**Решение:**
\`\`\`python
# В webapp/app.py добавьте:
from flask_cors import CORS
CORS(app, origins=[config.WEBAPP_URL])
\`\`\`

## Логи и отладка

### Включить debug режим

\`\`\`python
# В config.py
DEBUG = True
LOG_LEVEL = 'DEBUG'
\`\`\`

### Просмотр логов

\`\`\`bash
# Все логи
tail -f logs/*.log

# Только ошибки
grep ERROR logs/*.log

# Последние 100 строк
tail -n 100 logs/bot.log
\`\`\`

### Отладка в production

\`\`\`bash
# Подключитесь к Railway
railway run bash

# Проверьте переменные
env | grep BOT

# Проверьте процессы
ps aux | grep python

# Проверьте порты
netstat -tulpn
\`\`\`

## Получение помощи

Если проблема не решена:

1. Проверьте [Issues](https://github.com/your-repo/issues)
2. Создайте новый Issue с:
   - Описанием проблемы
   - Логами ошибок
   - Шагами для воспроизведения
   - Версией Python и зависимостей
3. Напишите в поддержку: support@example.com
