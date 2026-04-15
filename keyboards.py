# keyboards.py — все клавиатуры бота

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import config


# ── Главное меню ─────────────────────────────────────────────

def main_menu_kb(has_subscription: bool = False) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if has_subscription:
        b.row(
            InlineKeyboardButton(text="🔗 Подключиться",  callback_data="connect"),
            InlineKeyboardButton(text="📱 Устройства",    callback_data="my_devices"),
        )
        b.row(
            InlineKeyboardButton(text="👤 Профиль",       callback_data="profile"),
            InlineKeyboardButton(text="🔄 Продлить VPN",  callback_data="buy_vpn"),
        )
    else:
        b.row(InlineKeyboardButton(text="💎 Пробный период", callback_data="trial"))
        b.row(
            InlineKeyboardButton(text="🛒 Купить VPN",    callback_data="buy_vpn"),
            InlineKeyboardButton(text="👤 Профиль",       callback_data="profile"),
        )
    b.row(
        InlineKeyboardButton(text="❓ Помощь",    callback_data="help"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"),
    )
    return b.as_markup()


# ── Пробный период ───────────────────────────────────────────

def trial_confirm_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Активировать", callback_data="activate_trial"),
        InlineKeyboardButton(text="◀️ Назад",        callback_data="back_main"),
    )
    return b.as_markup()


# ── Выбор плана ──────────────────────────────────────────────

def plans_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for pid, plan in config.PLANS.items():
        min_p = min(plan["prices"].values())
        b.row(InlineKeyboardButton(
            text=f"📅 {plan['name']}  |  от {min_p} ₽",
            callback_data=f"plan:{pid}",
        ))
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_main"))
    return b.as_markup()


# ── Выбор устройств ──────────────────────────────────────────

def devices_select_kb(plan_id: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for devs, price in config.PLANS[plan_id]["prices"].items():
        b.row(InlineKeyboardButton(
            text=f"📱 {config.DEVICE_NAMES[devs]}  |  {price} ₽",
            callback_data=f"devsel:{plan_id}:{devs}",
        ))
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="buy_vpn"))
    return b.as_markup()


# ── Способ оплаты ────────────────────────────────────────────

def payment_method_kb(plan_id: str, devices: int, amount_rub: float) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    stars = max(1, round(amount_rub / config.STARS_RATE))
    usd   = round(amount_rub / config.RUB_TO_USD_RATE, 2)

    b.row(InlineKeyboardButton(
        text=f"₿ Крипто  ({usd} {config.CRYPTO_ASSET})",
        callback_data=f"paycrypto:{plan_id}:{devices}",
    ))
    b.row(InlineKeyboardButton(
        text=f"⭐ Telegram Stars  ({stars} ★)",
        callback_data=f"paystars:{plan_id}:{devices}",
    ))
    b.row(InlineKeyboardButton(
        text="🏦 СБП  (написать администратору)",
        url=config.SBP_ADMIN_LINK,
    ))
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data=f"plan:{plan_id}"))
    return b.as_markup()


# ── Подключение: выбор платформы ─────────────────────────────

def connect_platform_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="📱 Android", callback_data="conn:android"),
        InlineKeyboardButton(text="🍎 iOS",     callback_data="conn:ios"),
    )
    b.row(
        InlineKeyboardButton(text="💻 Windows", callback_data="conn:windows"),
        InlineKeyboardButton(text="🖥 macOS",   callback_data="conn:macos"),
    )
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_main"))
    return b.as_markup()


# ── После показа QR / ссылки ─────────────────────────────────

def after_connect_kb(sub_url: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🌐 Открыть страницу подписки", url=sub_url))
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="connect"))
    return b.as_markup()


# ── Профиль / детали подписки ────────────────────────────────

def subscription_detail_kb(remna_uuid: str, sub_url: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(
        text="🔄 Продлить подписку", callback_data=f"extend:{remna_uuid}",
    ))
    b.row(
        InlineKeyboardButton(text="📱 Устройства",    callback_data=f"subdev:{remna_uuid}"),
        InlineKeyboardButton(text="📷 QR-код",        callback_data=f"qr:{remna_uuid}"),
    )
    b.row(InlineKeyboardButton(
        text="🔗 Показать ссылку", callback_data=f"getlink:{remna_uuid}",
    ))
    b.row(InlineKeyboardButton(
        text="🌐 Открыть страницу", url=sub_url,
    ))
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="profile"))
    return b.as_markup()


# ── Продление ────────────────────────────────────────────────

def extend_plans_kb(remna_uuid: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for pid, plan in config.PLANS.items():
        min_p = min(plan["prices"].values())
        b.row(InlineKeyboardButton(
            text=f"📅 {plan['name']}  |  от {min_p} ₽",
            callback_data=f"extplan:{remna_uuid}:{pid}",
        ))
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="profile"))
    return b.as_markup()


def extend_devices_kb(remna_uuid: str, plan_id: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for devs, price in config.PLANS[plan_id]["prices"].items():
        b.row(InlineKeyboardButton(
            text=f"📱 {config.DEVICE_NAMES[devs]}  |  {price} ₽",
            callback_data=f"extdev:{remna_uuid}:{plan_id}:{devs}",
        ))
    b.row(InlineKeyboardButton(
        text="◀️ Назад", callback_data=f"extend:{remna_uuid}",
    ))
    return b.as_markup()


def extend_payment_kb(remna_uuid: str, plan_id: str,
                      devices: int, amount_rub: float) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    stars = max(1, round(amount_rub / config.STARS_RATE))
    usd   = round(amount_rub / config.RUB_TO_USD_RATE, 2)

    b.row(InlineKeyboardButton(
        text=f"₿ Крипто  ({usd} {config.CRYPTO_ASSET})",
        callback_data=f"extpaycrypto:{remna_uuid}:{plan_id}:{devices}",
    ))
    b.row(InlineKeyboardButton(
        text=f"⭐ Telegram Stars  ({stars} ★)",
        callback_data=f"extpaystars:{remna_uuid}:{plan_id}:{devices}",
    ))
    b.row(InlineKeyboardButton(
        text="🏦 СБП  (написать администратору)",
        url=config.SBP_ADMIN_LINK,
    ))
    b.row(InlineKeyboardButton(
        text="◀️ Назад",
        callback_data=f"extdev:{remna_uuid}:{plan_id}:{devices}",
    ))
    return b.as_markup()


# ── Простые кнопки назад ─────────────────────────────────────

def back_main_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="◀️ В главное меню", callback_data="back_main"))
    return b.as_markup()


def back_profile_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="profile"))
    return b.as_markup()


def channel_and_back_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(
            text="📢 Наш канал",
            url=f"https://t.me/{config.CHANNEL_USERNAME.lstrip('@')}",
        ),
        InlineKeyboardButton(
            text="💬 Поддержка",
            url=f"https://t.me/{config.SUPPORT_USERNAME.lstrip('@')}",
        ),
    )
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_main"))
    return b.as_markup()


# ── Админ-панель ─────────────────────────────────────────────

def admin_main_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📊 Статистика",      callback_data="adm_stats"))
    b.row(
        InlineKeyboardButton(text="👥 Пользователи",      callback_data="adm_users"),
        InlineKeyboardButton(text="➕ Выдать подписку",   callback_data="adm_give"),
    )
    b.row(InlineKeyboardButton(text="📢 Рассылка",        callback_data="adm_broadcast"))
    b.row(InlineKeyboardButton(text="✖️ Закрыть",         callback_data="adm_close"))
    return b.as_markup()


def admin_plans_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for pid, plan in config.PLANS.items():
        b.row(InlineKeyboardButton(
            text=f"📅 {plan['name']}", callback_data=f"admplan:{pid}",
        ))
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="adm_panel"))
    return b.as_markup()


def admin_devices_kb(plan_id: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for devs in config.PLANS[plan_id]["prices"]:
        b.row(InlineKeyboardButton(
            text=f"📱 {config.DEVICE_NAMES[devs]}",
            callback_data=f"admdev:{plan_id}:{devs}",
        ))
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="adm_give"))
    return b.as_markup()


def admin_confirm_kb(target_id: int, plan_id: str, devices: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(
            text="✅ Выдать",
            callback_data=f"admconfirm:{target_id}:{plan_id}:{devices}",
        ),
        InlineKeyboardButton(text="❌ Отмена", callback_data="adm_give"),
    )
    return b.as_markup()


def back_admin_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="◀️ В админ-панель", callback_data="adm_panel"))
    return b.as_markup()
