#!/bin/bash

# Stop script for Telegram E-commerce Bot

echo "Stopping Telegram E-commerce Bot services..."

# Stop bot
if [ -f bot.pid ]; then
    BOT_PID=$(cat bot.pid)
    if ps -p $BOT_PID > /dev/null; then
        echo "Stopping bot (PID: $BOT_PID)..."
        kill $BOT_PID
        rm bot.pid
        echo "Bot stopped."
    else
        echo "Bot process not found."
        rm bot.pid
    fi
else
    echo "Bot PID file not found."
fi

# Stop webapp
if [ -f webapp.pid ]; then
    WEBAPP_PID=$(cat webapp.pid)
    if ps -p $WEBAPP_PID > /dev/null; then
        echo "Stopping webapp (PID: $WEBAPP_PID)..."
        kill $WEBAPP_PID
        rm webapp.pid
        echo "WebApp stopped."
    else
        echo "WebApp process not found."
        rm webapp.pid
    fi
else
    echo "WebApp PID file not found."
fi

echo ""
echo "✅ All services stopped."
