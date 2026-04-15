# database.py — работа с базой данных (SQLite + aiosqlite)

import aiosqlite
import config


async def init_db():
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id  INTEGER PRIMARY KEY,
                username     TEXT,
                first_name   TEXT,
                has_trial    INTEGER DEFAULT 0,
                created_at   TEXT    DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id          INTEGER NOT NULL,
                remnawave_uuid   TEXT,
                subscription_url TEXT,
                plan_id          TEXT,
                devices          INTEGER,
                days             INTEGER,
                starts_at        TEXT,
                expires_at       TEXT,
                is_active        INTEGER DEFAULT 1,
                created_at       TEXT    DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(telegram_id)
            );

            CREATE TABLE IF NOT EXISTS pending_payments (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                plan_id      TEXT,
                devices      INTEGER,
                amount_rub   REAL,
                amount_stars INTEGER,
                payment_type TEXT,
                payment_id   TEXT    UNIQUE,
                status       TEXT    DEFAULT 'pending',
                created_at   TEXT    DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.commit()


# ── Пользователи ─────────────────────────────────────────────

async def get_or_create_user(telegram_id: int, username: str, first_name: str) -> dict:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cur:
            row = await cur.fetchone()
        if not row:
            await db.execute(
                "INSERT INTO users (telegram_id, username, first_name) VALUES (?,?,?)",
                (telegram_id, username or "", first_name or "")
            )
            await db.commit()
            async with db.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            ) as cur:
                row = await cur.fetchone()
        return dict(row)


async def get_user(telegram_id: int) -> dict | None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cur:
            row = await cur.fetchone()
        return dict(row) if row else None


async def set_trial_used(telegram_id: int):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            "UPDATE users SET has_trial = 1 WHERE telegram_id = ?", (telegram_id,)
        )
        await db.commit()


async def get_all_users() -> list[dict]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users ORDER BY created_at DESC"
        ) as cur:
            rows = await cur.fetchall()
        return [dict(r) for r in rows]


# ── Подписки ─────────────────────────────────────────────────

async def add_subscription(
    user_id: int, remnawave_uuid: str, subscription_url: str,
    plan_id: str, devices: int, days: int,
    starts_at: str, expires_at: str
) -> int:
    async with aiosqlite.connect(config.DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO subscriptions
               (user_id, remnawave_uuid, subscription_url, plan_id, devices, days, starts_at, expires_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (user_id, remnawave_uuid, subscription_url, plan_id, devices, days, starts_at, expires_at)
        )
        await db.commit()
        return cur.lastrowid


async def get_active_subscription(user_id: int) -> dict | None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM subscriptions
               WHERE user_id = ? AND is_active = 1
               ORDER BY expires_at DESC LIMIT 1""",
            (user_id,)
        ) as cur:
            row = await cur.fetchone()
        return dict(row) if row else None


async def get_all_user_subscriptions(user_id: int) -> list[dict]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM subscriptions WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ) as cur:
            rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def get_subscription_by_uuid(uuid: str) -> dict | None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM subscriptions WHERE remnawave_uuid = ?", (uuid,)
        ) as cur:
            row = await cur.fetchone()
        return dict(row) if row else None


async def deactivate_subscription(sub_id: int):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            "UPDATE subscriptions SET is_active = 0 WHERE id = ?", (sub_id,)
        )
        await db.commit()


# ── Платежи ──────────────────────────────────────────────────

async def create_pending_payment(
    user_id: int, plan_id: str, devices: int,
    amount_rub: float, amount_stars: int,
    payment_type: str, payment_id: str
) -> int:
    async with aiosqlite.connect(config.DB_PATH) as db:
        try:
            cur = await db.execute(
                """INSERT INTO pending_payments
                   (user_id, plan_id, devices, amount_rub, amount_stars, payment_type, payment_id)
                   VALUES (?,?,?,?,?,?,?)""",
                (user_id, plan_id, devices, amount_rub, amount_stars, payment_type, payment_id)
            )
            await db.commit()
            return cur.lastrowid
        except Exception:
            return 0


async def get_pending_payment(payment_id: str, payment_type: str) -> dict | None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM pending_payments
               WHERE payment_id = ? AND payment_type = ? AND status = 'pending'""",
            (payment_id, payment_type)
        ) as cur:
            row = await cur.fetchone()
        return dict(row) if row else None


async def get_all_pending_crypto() -> list[dict]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM pending_payments WHERE payment_type = 'crypto' AND status = 'pending'"
        ) as cur:
            rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def complete_payment(payment_id: str, payment_type: str):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            "UPDATE pending_payments SET status = 'completed' WHERE payment_id = ? AND payment_type = ?",
            (payment_id, payment_type)
        )
        await db.commit()


# ── Статистика ───────────────────────────────────────────────

async def get_stats() -> dict:
    async with aiosqlite.connect(config.DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            total_users = (await c.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM subscriptions WHERE is_active = 1"
        ) as c:
            active_subs = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM subscriptions") as c:
            total_subs = (await c.fetchone())[0]
        async with db.execute(
            "SELECT COALESCE(SUM(amount_rub),0) FROM pending_payments WHERE status='completed'"
        ) as c:
            total_revenue = (await c.fetchone())[0]
    return {
        "total_users":   total_users,
        "active_subs":   active_subs,
        "total_subs":    total_subs,
        "total_revenue": total_revenue,
    }
