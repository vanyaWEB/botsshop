# Installation Guide

## Quick Start

### 1. Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Telegram Bot Token (from @BotFather)
- YooKassa account (for payments)

### 2. Installation Steps

#### Clone or Download

Download the project files to your server or local machine.

#### Install Dependencies

\`\`\`bash
pip install -r requirements.txt
\`\`\`

#### Configure Environment

Copy `.env.example` to `.env`:

\`\`\`bash
cp .env.example .env
\`\`\`

Edit `.env` file with your credentials:

\`\`\`env
# Telegram Bot
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
BOT_URL=https://yourdomain.com
ADMIN_IDS=123456789,987654321

# YooKassa
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key

# Web App
WEBAPP_URL=https://yourdomain.com
WEBAPP_PORT=8080

# Database
DATABASE_URL=sqlite:///./shop.db

# Channel (optional)
REQUIRED_CHANNEL_ID=@yourchannel
REQUIRED_CHANNEL_URL=https://t.me/yourchannel
\`\`\`

### 3. Getting Credentials

#### Telegram Bot Token

1. Open Telegram and search for @BotFather
2. Send `/newbot` command
3. Follow instructions to create your bot
4. Copy the token provided

#### Admin IDs

1. Search for @userinfobot in Telegram
2. Send any message to get your Telegram ID
3. Add your ID to ADMIN_IDS (comma-separated for multiple admins)

#### YooKassa Credentials

1. Register at https://yookassa.ru/
2. Create a shop in your account
3. Get Shop ID and Secret Key from settings
4. Add them to .env file

### 4. Running the Bot

#### Development Mode

\`\`\`bash
# Start bot
python run.py

# In another terminal, start webapp
python webapp/app.py
\`\`\`

#### Production Mode (Linux)

Use the provided scripts:

\`\`\`bash
# Make scripts executable
chmod +x start.sh stop.sh

# Start all services
./start.sh

# Stop all services
./stop.sh
\`\`\`

#### Using Docker

\`\`\`bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
\`\`\`

### 5. Setting Up WebApp URL

For the catalog WebApp to work, you need to:

1. Deploy the webapp to a public URL (with HTTPS)
2. Update `WEBAPP_URL` in .env
3. Restart the bot

Options for hosting:
- Vercel (free, easy)
- Heroku (free tier available)
- Your own VPS with nginx

### 6. First Steps After Installation

1. Start the bot with `/start` command
2. Access admin panel with `/admin` command
3. Create categories
4. Add products with photos
5. Test ordering process

### 7. Troubleshooting

#### Bot doesn't respond
- Check BOT_TOKEN is correct
- Ensure bot is running (check logs)
- Verify firewall allows connections

#### WebApp doesn't load
- Check WEBAPP_URL is accessible via HTTPS
- Verify webapp is running
- Check browser console for errors

#### Payments don't work
- Verify YooKassa credentials
- Check shop is activated in YooKassa
- Ensure BOT_URL is set correctly

#### Database errors
- Check write permissions for shop.db
- Ensure SQLite is installed
- Try deleting shop.db and restarting

### 8. Security Recommendations

- Never commit .env file to git
- Use strong passwords for YooKassa
- Keep ADMIN_IDS private
- Use HTTPS for webapp
- Regularly backup shop.db
- Update dependencies regularly

### 9. Updating

\`\`\`bash
# Pull latest changes
git pull

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart services
./stop.sh
./start.sh
\`\`\`

### 10. Support

For issues:
1. Check logs (bot.log, webapp.log)
2. Review this guide
3. Check GitHub issues
4. Contact support

## Advanced Configuration

### Custom Database

To use PostgreSQL instead of SQLite:

\`\`\`env
DATABASE_URL=postgresql://user:password@localhost/dbname
\`\`\`

Install PostgreSQL driver:
\`\`\`bash
pip install psycopg2-binary
\`\`\`

### Multiple Admins

Add multiple admin IDs separated by commas:
\`\`\`env
ADMIN_IDS=123456789,987654321,555666777
\`\`\`

### Custom Port

Change webapp port:
\`\`\`env
WEBAPP_PORT=3000
\`\`\`

### Production Deployment

For production, use:
- gunicorn for webapp
- systemd for process management
- nginx as reverse proxy
- Let's Encrypt for SSL

See README.md for detailed production setup.
