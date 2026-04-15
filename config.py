# config.py — настройки бота (основные задаются в main.py)

# ── Заполняется из main.py ──────────────────────────────────
BOT_TOKEN: str = "8711038717:AAEZlwtnS5NdoI7heJrAALc8keSK54D5ScU"
ADMIN_IDS: list = [69198496]

# ── Remnawave Panel ─────────────────────────────────────────
PANEL_URL: str = "https://newpaneltestt.mooo.com"   # без слеша в конце
PANEL_TOKEN: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1dWlkIjoiZjczMDMxYmQtM2I2OC00OTFiLWEwZGItZDQ3YWFhMmZhODRiIiwidXNlcm5hbWUiOm51bGwsInJvbGUiOiJBUEkiLCJpYXQiOjE3NzYxMjcyMDIsImV4cCI6MTA0MTYwNDA4MDJ9.td8dq5CjlC_7lX6ZtmJZL0Al9l4kZQkRaXB51cdjFB0"
DEFAULT_TRAFFIC_GB: int = 300   # ГБ трафика на подписку

# ── CryptoBot (@CryptoBot) ──────────────────────────────────
CRYPTO_BOT_TOKEN: str = "567739:AAozjGimQTrEReZrUwXf7BOq9ZqhjSz6SZE"
CRYPTO_BOT_API: str = "https://pay.crypt.bot/api"  # testnet: testnet-pay.crypt.bot/api
CRYPTO_ASSET: str = "USDT"                          # USDT / TON / BTC
RUB_TO_USD_RATE: float = 90.0                       # ₽ за $1 (обновляй вручную)

# ── СБП ─────────────────────────────────────────────────────
SBP_ADMIN_LINK: str = "https://t.me/internetcomumity"  # ссылка на твой ЛС

# ── Канал и поддержка ────────────────────────────────────────
CHANNEL_USERNAME: str = "@true_vps"
SUPPORT_USERNAME: str = "@internetcomumity"

# ── Брендинг ─────────────────────────────────────────────────
VPN_NAME: str = "True VPN"

# ── Пробный период ───────────────────────────────────────────
TRIAL_DAYS: int = 3
TRIAL_DEVICES: int = 1
TRIAL_TRAFFIC_GB: int = 10

# ── База данных ──────────────────────────────────────────────
DB_PATH: str = "truevpn.db"

# ── Telegram Stars (1 звезда = N рублей) ────────────────────
STARS_RATE: float = 2.0

# ── Тарифные планы ──────────────────────────────────────────
# план: {name, days, prices: {устройств: цена_руб}}
PLANS: dict = {
    "3d": {
        "name":   "3 дня",
        "days":   3,
        "prices": {1: 30,  2: 55,   3: 80,   5: 120}
    },
    "7d": {
        "name":   "7 дней",
        "days":   7,
        "prices": {1: 50,  2: 90,   3: 130,  5: 200}
    },
    "1m": {
        "name":   "1 месяц",
        "days":   30,
        "prices": {1: 75,  2: 140,  3: 200,  5: 320}
    },
    "2m": {
        "name":   "2 месяца",
        "days":   60,
        "prices": {1: 150, 2: 270,  3: 400,  5: 620}
    },
    "3m": {
        "name":   "3 месяца",
        "days":   90,
        "prices": {1: 200, 2: 370,  3: 530,  5: 830}
    },
    "6m": {
        "name":   "6 месяцев",
        "days":   180,
        "prices": {1: 380, 2: 700,  3: 1000, 5: 1600}
    },
    "1y": {
        "name":   "1 год",
        "days":   365,
        "prices": {1: 700, 2: 1300, 3: 1900, 5: 3000}
    },
}

DEVICE_NAMES: dict = {
    1: "1 устройство",
    2: "2 устройства",
    3: "3 устройства",
    5: "5 устройств",
}
