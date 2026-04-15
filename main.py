# main.py — точка входа. Здесь настраиваются все основные параметры.
# ┌─────────────────────────────────────────────────────────────┐
# │            НАСТРОЙКИ — ЗАПОЛНИ ПЕРЕД ЗАПУСКОМ              │
# └─────────────────────────────────────────────────────────────┘

import config

# ── Токен бота (получить у @BotFather) ──────────────────────
config.BOT_TOKEN = "8711038717:AAEZlwtnS5NdoI7heJrAALc8keSK54D5ScU"

# ── Telegram ID администратора(ов) ──────────────────────────
# Узнать свой ID можно у @userinfobot
config.ADMIN_IDS = [69198496]   # Замени на свой ID

# ── Remnawave Panel ─────────────────────────────────────────
config.PANEL_URL   = "https://newpaneltestt.mooo.com"  # URL панели (без слеша)
config.PANEL_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1dWlkIjoiZjczMDMxYmQtM2I2OC00OTFiLWEwZGItZDQ3YWFhMmZhODRiIiwidXNlcm5hbWUiOm51bGwsInJvbGUiOiJBUEkiLCJpYXQiOjE3NzYxMjcyMDIsImV4cCI6MTA0MTYwNDA4MDJ9.td8dq5CjlC_7lX6ZtmJZL0Al9l4kZQkRaXB51cdjFB0"        # API токен панели

# ── CryptoBot (токен от @CryptoBot) ─────────────────────────
config.CRYPTO_BOT_TOKEN = "567739:AAozjGimQTrEReZrUwXf7BOq9ZqhjSz6SZE"
config.CRYPTO_ASSET     = "USDT"   # Валюта (USDT / TON / BTC)
config.RUB_TO_USD_RATE  = 90.0     # Курс ₽/$, обновляй вручную

# ── СБП: ссылка на твой ЛС для ручной оплаты ────────────────
config.SBP_ADMIN_LINK = "https://t.me/your_username"

# ── Telegram Stars: 1 звезда = N рублей ─────────────────────
config.STARS_RATE = 2.0

# ─────────────────────────────────────────────────────────────

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from database import init_db
from handlers import router as user_router
from admin_handlers import router as admin_router
from payment_handlers import router as payment_router, crypto_payment_checker


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    log = logging.getLogger("main")

    # Валидация конфига
    assert config.BOT_TOKEN != "YOUR_BOT_TOKEN_HERE", "Задай BOT_TOKEN в main.py!"
    assert config.ADMIN_IDS != [123456789], "Задай свой ADMIN_IDS в main.py!"

    bot = Bot(token=config.BOT_TOKEN)
    dp  = Dispatcher(storage=MemoryStorage())

    # Инициализация БД
    await init_db()
    log.info("База данных инициализирована.")

    # Роутеры (порядок важен: админский первым)
    dp.include_router(admin_router)
    dp.include_router(payment_router)
    dp.include_router(user_router)

    # Фоновая задача: проверка крипто-платежей
    asyncio.create_task(crypto_payment_checker(bot))

    await bot.delete_webhook(drop_pending_updates=True)
    log.info("Бот запущен! Нажми Ctrl+C для остановки.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
