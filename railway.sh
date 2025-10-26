#!/bin/bash

# Railway deployment helper script

echo "🚀 Preparing for Railway deployment..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "✅ Please edit .env with your actual values before deploying!"
    exit 1
fi

# Check required environment variables
required_vars=("BOT_TOKEN" "ADMIN_IDS" "YOOKASSA_SHOP_ID" "YOOKASSA_SECRET_KEY")

for var in "${required_vars[@]}"; do
    if ! grep -q "^${var}=" .env; then
        echo "❌ Missing required variable: $var"
        exit 1
    fi
done

echo "✅ Environment variables check passed"

# Test database connection
echo "🔍 Testing database setup..."
python -c "from database.db import init_db; init_db()" || {
    echo "❌ Database initialization failed"
    exit 1
}

echo "✅ Database setup successful"

echo ""
echo "📋 Deployment checklist:"
echo "  1. Install Railway CLI: npm i -g @railway/cli"
echo "  2. Login to Railway: railway login"
echo "  3. Create new project: railway init"
echo "  4. Add environment variables: railway variables set KEY=VALUE"
echo "  5. Deploy: railway up"
echo ""
echo "🌐 After deployment, set WEBAPP_URL in Railway dashboard"
echo ""
