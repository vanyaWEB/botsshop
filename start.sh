#!/bin/bash

# Start script for Telegram E-commerce Bot

echo "Starting Telegram E-commerce Bot..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please copy .env.example to .env and configure it."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Start bot in background
echo "Starting bot..."
nohup python run.py > bot.log 2>&1 &
BOT_PID=$!
echo $BOT_PID > bot.pid
echo "Bot started with PID: $BOT_PID"

# Start webapp in background
echo "Starting webapp..."
nohup gunicorn -w 4 -b 0.0.0.0:8080 webapp.app:app > webapp.log 2>&1 &
WEBAPP_PID=$!
echo $WEBAPP_PID > webapp.pid
echo "WebApp started with PID: $WEBAPP_PID"

echo ""
echo "✅ All services started successfully!"
echo ""
echo "Bot PID: $BOT_PID (log: bot.log)"
echo "WebApp PID: $WEBAPP_PID (log: webapp.log)"
echo ""
echo "To stop services, run: ./stop.sh"
