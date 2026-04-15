#!/bin/bash
set -e

echo "📦 Установка зависимостей..."
pip install -r /app/requirements.txt --quiet
echo "✅ Все пакеты установлены!"
echo "🚀 Запуск бота..."
exec python /app/main.py
