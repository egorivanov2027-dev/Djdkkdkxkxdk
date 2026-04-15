#!/bin/bash

echo "🔧 Установка зависимостей..."

# Обновление pip
pip install --upgrade pip

# Попытка установить remnawave с PyPI
echo "📦 Установка remnawave..."
pip install remnawave

# Проверка успешности установки
if python -c "import remnawave" 2>/dev/null; then
    echo "✅ remnawave успешно установлен!"
else
    echo "⚠️  remnawave не найден на PyPI, пробуем альтернативные источники..."

    # Попытка установить из GitHub (замени URL если нужно)
    pip install git+https://github.com/remnawave/remnawave-python.git 2>/dev/null || \
    pip install git+https://github.com/remnawave/sdk.git 2>/dev/null || \
    echo "❌ Не удалось установить автоматически. Укажи точный репозиторий."
fi

# Установка остальных зависимостей если есть requirements.txt
if [ -f "requirements.txt" ]; then
    echo "📋 Установка из requirements.txt..."
    pip install -r requirements.txt
fi

echo ""
echo "✅ Готово! Запускаем бота..."
python /app/main.py
