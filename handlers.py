# handlers.py — основные обработчики пользователей

import io
import logging
from datetime import datetime, timedelta, timezone

import qrcode
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery, BufferedInputFile, InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
import database as db
import remnawave
import keyboards as kb

log    = logging.getLogger(__name__)
router = Router()

# ── Утилиты ──────────────────────────────────────────────────

def fmt_dt(iso: str) -> str:
    """ISO → «дд.мм.гггг»"""
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return iso


def is_expired(iso: str) -> bool:
    try:
        dt = datetime.fromisoformat(iso).replace(tzinfo=None)
        return dt < datetime.utcnow()
    except Exception:
        return False


def generate_qr_bytes(data: str) -> bytes:
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def get_active_sub(user_id: int) -> dict | None:
    sub = await db.get_active_subscription(user_id)
    if sub and is_expired(sub["expires_at"]):
        return None
    return sub


async def send_main_menu(target, user_id: int, edit: bool = True):
    sub  = await get_active_sub(user_id)
    text = (
        f"🏠 <b>Главное меню — {config.VPN_NAME}</b>\n\n"
        "Выберите нужный раздел:"
    )
    markup = kb.main_menu_kb(has_subscription=bool(sub))
    if edit and isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    elif isinstance(target, CallbackQuery):
        await target.message.answer(text, reply_markup=markup, parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=markup, parse_mode="HTML")


# ── /start ───────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message):
    await db.get_or_create_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.first_name or "",
    )
    name = message.from_user.first_name or message.from_user.username or "пользователь"
    text = (
        f"👋🏻 Приветствуем, <b>{name}</b>.\n\n"
        f"<b>{config.VPN_NAME}</b> — бот для подключения "
        f"к высокоскоростному личному VPN!\n\n"
        f"Присоединяйтесь к нашему каналу {config.CHANNEL_USERNAME}, "
        f"чтобы быть в курсе всех событий, новостей и конкурсов!"
    )
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(
            text="📢 Наш канал",
            url=f"https://t.me/{config.CHANNEL_USERNAME.lstrip('@')}",
        )
    )
    await message.answer(text, reply_markup=b.as_markup(), parse_mode="HTML")
    await send_main_menu(message, message.from_user.id, edit=False)


# ── Главное меню (callback) ──────────────────────────────────

@router.callback_query(F.data == "back_main")
async def cb_back_main(call: CallbackQuery):
    await send_main_menu(call, call.from_user.id)


# ── Пробный период ───────────────────────────────────────────

@router.callback_query(F.data == "trial")
async def cb_trial(call: CallbackQuery):
    user = await db.get_user(call.from_user.id)
    if user and user["has_trial"]:
        await call.answer("❌ Вы уже использовали пробный период!", show_alert=True)
        return
    await call.message.edit_text(
        f"💎 <b>Пробный период</b>\n\n"
        f"✅ Срок: <b>{config.TRIAL_DAYS} дня</b>\n"
        f"📱 Устройств: <b>{config.TRIAL_DEVICES}</b>\n"
        f"💾 Трафик: <b>{config.TRIAL_TRAFFIC_GB} ГБ</b>\n\n"
        f"Нажмите кнопку для бесплатной активации:",
        reply_markup=kb.trial_confirm_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "activate_trial")
async def cb_activate_trial(call: CallbackQuery, bot: Bot):
    user = await db.get_user(call.from_user.id)
    if user and user["has_trial"]:
        await call.answer("❌ Пробный период уже использован!", show_alert=True)
        return

    await call.message.edit_text("⏳ Активируем пробную подписку...", parse_mode="HTML")
    await _activate_subscription(
        bot, call.from_user.id,
        plan_id="trial",
        devices=config.TRIAL_DEVICES,
        days=config.TRIAL_DAYS,
        traffic_gb=config.TRIAL_TRAFFIC_GB,
        is_trial=True,
        notify_message=call.message,
    )


# ── Купить VPN ───────────────────────────────────────────────

@router.callback_query(F.data == "buy_vpn")
async def cb_buy_vpn(call: CallbackQuery):
    await call.message.edit_text(
        "🛒 <b>Выберите тарифный план:</b>",
        reply_markup=kb.plans_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("plan:"))
async def cb_plan(call: CallbackQuery):
    plan_id = call.data.split(":")[1]
    plan    = config.PLANS.get(plan_id)
    if not plan:
        await call.answer("Неверный план.", show_alert=True)
        return
    await call.message.edit_text(
        f"📅 <b>{plan['name']}</b>\n\nВыберите количество устройств:",
        reply_markup=kb.devices_select_kb(plan_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("devsel:"))
async def cb_devsel(call: CallbackQuery):
    _, plan_id, devs_str = call.data.split(":")
    devices    = int(devs_str)
    plan       = config.PLANS.get(plan_id)
    amount_rub = plan["prices"][devices]
    await call.message.edit_text(
        f"💳 <b>Способ оплаты</b>\n\n"
        f"📅 План: <b>{plan['name']}</b>\n"
        f"📱 Устройств: <b>{config.DEVICE_NAMES[devices]}</b>\n"
        f"💰 Сумма: <b>{amount_rub} ₽</b>\n\n"
        f"Выберите способ оплаты:",
        reply_markup=kb.payment_method_kb(plan_id, devices, amount_rub),
        parse_mode="HTML",
    )


# ── Профиль ──────────────────────────────────────────────────

@router.callback_query(F.data == "profile")
async def cb_profile(call: CallbackQuery):
    user = await db.get_user(call.from_user.id)
    subs = await db.get_all_user_subscriptions(call.from_user.id)
    active = await get_active_sub(call.from_user.id)

    name = call.from_user.first_name or call.from_user.username or "—"
    un   = f"@{call.from_user.username}" if call.from_user.username else "—"

    lines = [
        f"👤 <b>Профиль</b>\n",
        f"🆔 ID: <code>{call.from_user.id}</code>",
        f"👤 Ник: {un}",
        f"📋 Всего подписок: {len(subs)}",
    ]

    if active:
        plan_name = config.PLANS.get(active["plan_id"], {}).get("name", active["plan_id"])
        lines += [
            "",
            "✅ <b>Активная подписка:</b>",
            f"  📅 План: {plan_name}",
            f"  📱 Устройств: {active['devices']}",
            f"  ⏰ Истекает: {fmt_dt(active['expires_at'])}",
        ]
        b = InlineKeyboardBuilder()
        b.row(
            InlineKeyboardButton(text="🔗 Подключиться",   callback_data="connect"),
            InlineKeyboardButton(text="📱 Устройства",     callback_data="my_devices"),
        )
        b.row(InlineKeyboardButton(
            text="📋 Детали подписки",
            callback_data=f"subdetail:{active['remnawave_uuid']}",
        ))
        b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_main"))
        markup = b.as_markup()
    else:
        lines.append("\n❌ Активных подписок нет.")
        b = InlineKeyboardBuilder()
        b.row(
            InlineKeyboardButton(text="💎 Пробный период", callback_data="trial"),
            InlineKeyboardButton(text="🛒 Купить VPN",     callback_data="buy_vpn"),
        )
        b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_main"))
        markup = b.as_markup()

    await call.message.edit_text(
        "\n".join(lines), reply_markup=markup, parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("subdetail:"))
async def cb_subdetail(call: CallbackQuery):
    uuid = call.data.split(":", 1)[1]
    sub  = await db.get_subscription_by_uuid(uuid)
    if not sub:
        await call.answer("Подписка не найдена.", show_alert=True)
        return

    plan_name  = config.PLANS.get(sub["plan_id"], {}).get("name", sub["plan_id"])
    expired    = is_expired(sub["expires_at"])
    status_str = "❌ Неактивна" if expired else "✅ Активна"

    # Попробуем получить актуальные данные из панели
    remna_info  = await remnawave.get_user(uuid)
    used_gb_str = "—"
    devices_str = f"{sub['devices']}"
    if remna_info:
        used_bytes = remna_info.get("usedTrafficBytes", 0) or 0
        used_gb    = round(used_bytes / 1024 ** 3, 2)
        used_gb_str = f"{used_gb} ГБ"
        limit_bytes = remna_info.get("trafficLimitBytes", 0) or 0
        limit_gb    = round(limit_bytes / 1024 ** 3, 0)
        devices_str = f"{sub['devices']} (лимит {int(limit_gb)} ГБ)"

    text = (
        f"📋 <b>Детали подписки</b>\n\n"
        f"📅 Начало: {fmt_dt(sub['starts_at'])}\n"
        f"⏰ Конец: {fmt_dt(sub['expires_at'])}\n"
        f"🔵 Статус: {status_str}\n"
        f"📱 Устройств: {devices_str}\n"
        f"💾 Использовано: {used_gb_str}\n"
    )
    await call.message.edit_text(
        text,
        reply_markup=kb.subscription_detail_kb(uuid, sub["subscription_url"]),
        parse_mode="HTML",
    )


# ── Подключение ──────────────────────────────────────────────

@router.callback_query(F.data == "connect")
async def cb_connect(call: CallbackQuery):
    sub = await get_active_sub(call.from_user.id)
    if not sub:
        await call.answer("❌ У вас нет активной подписки.", show_alert=True)
        await send_main_menu(call, call.from_user.id)
        return
    await call.message.edit_text(
        "🔗 <b>Подключение</b>\n\nВыберите тип устройства:",
        reply_markup=kb.connect_platform_kb(),
        parse_mode="HTML",
    )


PLATFORM_INSTRUCTIONS = {
    "android": (
        "📱 <b>Android — подключение</b>\n\n"
        "1. Установите приложение <b>v2rayNG</b> из Google Play\n"
        "2. Откройте приложение → нажмите «+» → «Import config from clipboard\"\n"
        "3. Вставьте ссылку подписки ниже\n"
        "— или отсканируйте QR-код\n\n"
        "Ссылка подписки:"
    ),
    "ios": (
        "🍎 <b>iOS — подключение</b>\n\n"
        "1. Установите приложение <b>Streisand</b> или <b>V2BOX</b> из App Store\n"
        "2. Нажмите «+» → «Import from URL»\n"
        "3. Вставьте ссылку подписки ниже\n"
        "— или отсканируйте QR-код\n\n"
        "Ссылка подписки:"
    ),
    "windows": (
        "💻 <b>Windows — подключение</b>\n\n"
        "1. Скачайте <b>v2rayN</b> с GitHub (v2rayN-With-Core.zip)\n"
        "2. Запустите v2rayN → «Subscriptions» → «Add subscription group\"\n"
        "3. Вставьте ссылку подписки ниже\n"
        "4. Нажмите «Update all subscriptions»\n\n"
        "Ссылка подписки:"
    ),
    "macos": (
        "🖥 <b>macOS — подключение</b>\n\n"
        "1. Установите <b>Happ</b> или <b>ClashX Pro</b>\n"
        "2. В настройках добавьте URL подписки\n"
        "3. Вставьте ссылку подписки ниже\n"
        "— или отсканируйте QR-код\n\n"
        "Ссылка подписки:"
    ),
}


@router.callback_query(F.data.startswith("conn:"))
async def cb_conn_platform(call: CallbackQuery):
    platform = call.data.split(":")[1]
    sub      = await get_active_sub(call.from_user.id)
    if not sub:
        await call.answer("❌ Нет активной подписки.", show_alert=True)
        return

    url  = sub["subscription_url"]
    desc = PLATFORM_INSTRUCTIONS.get(platform, "Ссылка подписки:")
    text = f"{desc}\n\n<code>{url}</code>"

    await call.message.edit_text(
        text,
        reply_markup=kb.after_connect_kb(url),
        parse_mode="HTML",
    )


# ── Устройства ───────────────────────────────────────────────

@router.callback_query(F.data == "my_devices")
async def cb_my_devices(call: CallbackQuery):
    sub = await get_active_sub(call.from_user.id)
    if not sub:
        await call.answer("❌ Нет активной подписки.", show_alert=True)
        await send_main_menu(call, call.from_user.id)
        return

    remna = await remnawave.get_user(sub["remnawave_uuid"])
    if remna:
        devs_list = remna.get("devices", []) or []
        lines     = [f"📱 <b>Устройства</b>\n"]
        if devs_list:
            for i, d in enumerate(devs_list, 1):
                name = d.get("name") or d.get("userAgent", "Неизвестно")
                last = d.get("lastConnectedAt", "—")
                lines.append(f"{i}. {name}\n   Последнее подключение: {last}")
        else:
            lines.append("Нет подключённых устройств.")
        lines.append(f"\nПодключено: ?/{sub['devices']}")
        text = "\n".join(lines)
    else:
        text = f"📱 <b>Устройства</b>\n\nЛимит: {sub['devices']} устройств."

    await call.message.edit_text(
        text,
        reply_markup=kb.back_main_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("subdev:"))
async def cb_subdev(call: CallbackQuery):
    uuid  = call.data.split(":", 1)[1]
    sub   = await db.get_subscription_by_uuid(uuid)
    remna = await remnawave.get_user(uuid)

    lines = [f"📱 <b>Устройства подписки</b>\n"]
    if remna:
        devs = remna.get("devices", []) or []
        if devs:
            for i, d in enumerate(devs, 1):
                name = d.get("name") or d.get("userAgent", "Неизвестно")
                lines.append(f"{i}. {name}")
        else:
            lines.append("Нет подключённых устройств.")
        lines.append(f"\nПодключено: ?/{sub['devices'] if sub else '?'}")
    else:
        lines.append("Не удалось получить данные о устройствах.")

    await call.message.edit_text(
        "\n".join(lines),
        reply_markup=kb.back_profile_kb(),
        parse_mode="HTML",
    )


# ── QR-код ───────────────────────────────────────────────────

@router.callback_query(F.data.startswith("qr:"))
async def cb_qr(call: CallbackQuery, bot: Bot):
    uuid = call.data.split(":", 1)[1]
    sub  = await db.get_subscription_by_uuid(uuid)
    if not sub:
        await call.answer("Подписка не найдена.", show_alert=True)
        return
    qr_bytes = generate_qr_bytes(sub["subscription_url"])
    photo    = BufferedInputFile(qr_bytes, filename="qr.png")
    await bot.send_photo(
        call.from_user.id,
        photo,
        caption="📷 <b>QR-код для подключения</b>\n\nОтсканируйте в VPN-приложении.",
        parse_mode="HTML",
        reply_markup=kb.back_profile_kb(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("getlink:"))
async def cb_getlink(call: CallbackQuery):
    uuid = call.data.split(":", 1)[1]
    sub  = await db.get_subscription_by_uuid(uuid)
    if not sub:
        await call.answer("Подписка не найдена.", show_alert=True)
        return
    url  = sub["subscription_url"]
    await call.message.edit_text(
        f"🔗 <b>Ссылка подписки</b>\n\n<code>{url}</code>\n\n"
        f"Скопируйте и вставьте в VPN-приложение.",
        reply_markup=kb.subscription_detail_kb(uuid, url),
        parse_mode="HTML",
    )


# ── Продление ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("extend:"))
async def cb_extend(call: CallbackQuery):
    uuid = call.data.split(":", 1)[1]
    await call.message.edit_text(
        "🔄 <b>Продление подписки</b>\n\nВыберите период продления:",
        reply_markup=kb.extend_plans_kb(uuid),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("extplan:"))
async def cb_extplan(call: CallbackQuery):
    _, uuid, plan_id = call.data.split(":")
    plan = config.PLANS.get(plan_id)
    await call.message.edit_text(
        f"🔄 <b>Продление — {plan['name']}</b>\n\nВыберите количество устройств:",
        reply_markup=kb.extend_devices_kb(uuid, plan_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("extdev:"))
async def cb_extdev(call: CallbackQuery):
    parts      = call.data.split(":")
    uuid, plan_id, devs_str = parts[1], parts[2], parts[3]
    devices    = int(devs_str)
    amount_rub = config.PLANS[plan_id]["prices"][devices]
    plan       = config.PLANS[plan_id]
    await call.message.edit_text(
        f"💳 <b>Продление — {plan['name']}</b>\n"
        f"📱 Устройств: {config.DEVICE_NAMES[devices]}\n"
        f"💰 Сумма: {amount_rub} ₽\n\n"
        f"Выберите способ оплаты:",
        reply_markup=kb.extend_payment_kb(uuid, plan_id, devices, amount_rub),
        parse_mode="HTML",
    )


# ── Помощь ───────────────────────────────────────────────────

@router.callback_query(F.data == "help")
async def cb_help(call: CallbackQuery):
    await call.message.edit_text(
        f"❓ <b>Помощь</b>\n\n"
        f"По всем вопросам обращайтесь в поддержку:\n"
        f"👉 {config.SUPPORT_USERNAME}\n\n"
        f"Наш канал:\n"
        f"👉 {config.CHANNEL_USERNAME}",
        reply_markup=kb.channel_and_back_kb(),
        parse_mode="HTML",
    )


# ── Настройки ────────────────────────────────────────────────

@router.callback_query(F.data == "settings")
async def cb_settings(call: CallbackQuery):
    await call.message.edit_text(
        "⚙️ <b>Настройки</b>\n\nЗдесь появятся настройки бота.",
        reply_markup=kb.back_main_kb(),
        parse_mode="HTML",
    )


# ── Активация подписки (внутренняя функция) ──────────────────

async def _activate_subscription(
    bot: Bot,
    user_id: int,
    plan_id: str,
    devices: int,
    days: int,
    traffic_gb: int = None,
    is_trial: bool = False,
    notify_message=None,
):
    """Создаёт подписку в Remnawave и сохраняет в БД."""
    if traffic_gb is None:
        traffic_gb = config.DEFAULT_TRAFFIC_GB

    username = f"truevpn_{user_id}"
    if is_trial:
        username = f"truevpn_trial_{user_id}"

    remna_user = await remnawave.create_user(username, days, devices, traffic_gb)
    if not remna_user:
        err_text = (
            "❌ Ошибка создания подписки. "
            f"Обратитесь в поддержку: {config.SUPPORT_USERNAME}"
        )
        if notify_message:
            await notify_message.edit_text(err_text, parse_mode="HTML")
        else:
            await bot.send_message(user_id, err_text, parse_mode="HTML")
        return

    uuid    = remna_user.get("uuid", "")
    sub_url = (
        remna_user.get("subscriptionUrl")
        or remna_user.get("subscription_url")
        or remna_user.get("sub_url")
        or ""
    )
    now     = datetime.utcnow()
    starts  = now.isoformat()
    expires = (now + timedelta(days=days)).isoformat()

    await db.add_subscription(
        user_id=user_id,
        remnawave_uuid=uuid,
        subscription_url=sub_url,
        plan_id=plan_id,
        devices=devices,
        days=days,
        starts_at=starts,
        expires_at=expires,
    )

    if is_trial:
        await db.set_trial_used(user_id)

    plan_name = config.PLANS.get(plan_id, {}).get("name", plan_id)
    success_text = (
        f"✅ <b>Подписка активирована!</b>\n\n"
        f"📅 Тариф: <b>{plan_name if not is_trial else 'Пробный период'}</b>\n"
        f"📱 Устройств: <b>{devices}</b>\n"
        f"💾 Трафик: <b>{traffic_gb} ГБ</b>\n"
        f"⏰ Истекает: <b>{fmt_dt(expires)}</b>\n\n"
        f"Нажмите «🔗 Подключиться» для настройки VPN."
    )
    markup = kb.main_menu_kb(has_subscription=True)
    if notify_message:
        await notify_message.edit_text(success_text, reply_markup=markup, parse_mode="HTML")
    else:
        await bot.send_message(user_id, success_text, reply_markup=markup, parse_mode="HTML")
