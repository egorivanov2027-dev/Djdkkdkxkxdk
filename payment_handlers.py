# payment_handlers.py — обработка платежей (CryptoBot + Telegram Stars)

import logging
import asyncio
from datetime import datetime, timedelta

import aiohttp
from aiogram import Router, F, Bot
from aiogram.types import (
    CallbackQuery, Message, LabeledPrice,
    PreCheckoutQuery,
)

import config
import database as db
import keyboards as kb
from handlers import _activate_subscription

log    = logging.getLogger(__name__)
router = Router()


# ══════════════════════════════════════════════════════════════
#  CryptoBot
# ══════════════════════════════════════════════════════════════

async def _crypto_create_invoice(
    user_id: int, plan_id: str, devices: int,
    amount_rub: float,
) -> dict | None:
    """Создаёт инвойс в CryptoBot и возвращает {'invoice_id', 'pay_url'}."""
    usd_amount = round(amount_rub / config.RUB_TO_USD_RATE, 2)
    plan_name  = config.PLANS[plan_id]["name"]
    payload    = f"user_{user_id}_plan_{plan_id}_dev_{devices}"

    params = {
        "asset":          config.CRYPTO_ASSET,
        "amount":         str(usd_amount),
        "description":    f"{config.VPN_NAME} — {plan_name}",
        "payload":        payload,
        "paid_btn_name":  "openBot",
        "paid_btn_url":   "https://t.me/TrueVlessVpn_bot",
        "expires_in":     3600,
    }
    headers = {"Crypto-Pay-API-Token": config.CRYPTO_BOT_TOKEN}

    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(
                f"{config.CRYPTO_BOT_API}/createInvoice",
                json=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:
                data = await r.json()
                if data.get("ok"):
                    result = data["result"]
                    return {
                        "invoice_id": str(result["invoice_id"]),
                        "pay_url":    result["pay_url"],
                    }
                log.error("CryptoBot createInvoice: %s", data)
                return None
    except Exception as e:
        log.error("CryptoBot exception: %s", e)
        return None


async def _crypto_check_invoice(invoice_id: str) -> str:
    """Проверяет статус инвойса: 'paid' | 'active' | 'expired' | 'error'."""
    headers = {"Crypto-Pay-API-Token": config.CRYPTO_BOT_TOKEN}
    params  = {"invoice_ids": invoice_id}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                f"{config.CRYPTO_BOT_API}/getInvoices",
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                data = await r.json()
                if data.get("ok"):
                    items = data["result"].get("items", [])
                    if items:
                        return items[0].get("status", "error")
                return "error"
    except Exception as e:
        log.error("CryptoBot check invoice: %s", e)
        return "error"


# ── Обработчик кнопки «Крипто» (новая подписка) ─────────────

@router.callback_query(F.data.startswith("paycrypto:"))
async def cb_paycrypto(call: CallbackQuery):
    _, plan_id, devs_str = call.data.split(":")
    devices    = int(devs_str)
    amount_rub = config.PLANS[plan_id]["prices"][devices]

    invoice = await _crypto_create_invoice(
        call.from_user.id, plan_id, devices, amount_rub
    )
    if not invoice:
        await call.answer(
            "❌ Ошибка создания платежа. Попробуйте позже.", show_alert=True
        )
        return

    await db.create_pending_payment(
        user_id=call.from_user.id,
        plan_id=plan_id,
        devices=devices,
        amount_rub=amount_rub,
        amount_stars=0,
        payment_type="crypto",
        payment_id=invoice["invoice_id"],
    )

    stars = max(1, round(amount_rub / config.STARS_RATE))
    usd   = round(amount_rub / config.RUB_TO_USD_RATE, 2)
    text  = (
        f"₿ <b>Оплата криптовалютой</b>\n\n"
        f"Сумма: <b>{usd} {config.CRYPTO_ASSET}</b> (~{amount_rub} ₽)\n\n"
        f"Нажмите кнопку ниже для оплаты.\n"
        f"После оплаты подписка активируется автоматически в течение 1 минуты."
    )
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="💳 Оплатить", url=invoice["pay_url"]))
    b.row(InlineKeyboardButton(text="🔄 Проверить оплату",
                               callback_data=f"checkcrypto:{invoice['invoice_id']}"))
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data=f"devsel:{plan_id}:{devices}"))
    await call.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")


# ── Обработчик кнопки «Крипто» (продление) ──────────────────

@router.callback_query(F.data.startswith("extpaycrypto:"))
async def cb_extpaycrypto(call: CallbackQuery):
    parts   = call.data.split(":")
    uuid, plan_id, devs_str = parts[1], parts[2], parts[3]
    devices    = int(devs_str)
    amount_rub = config.PLANS[plan_id]["prices"][devices]

    invoice = await _crypto_create_invoice(
        call.from_user.id, plan_id, devices, amount_rub
    )
    if not invoice:
        await call.answer("❌ Ошибка. Попробуйте позже.", show_alert=True)
        return

    # Сохраняем invoice с meta для продления
    await db.create_pending_payment(
        user_id=call.from_user.id,
        plan_id=f"ext::{uuid}::{plan_id}",  # кодируем UUID для продления
        devices=devices,
        amount_rub=amount_rub,
        amount_stars=0,
        payment_type="crypto",
        payment_id=invoice["invoice_id"],
    )

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="💳 Оплатить", url=invoice["pay_url"]))
    b.row(InlineKeyboardButton(text="🔄 Проверить оплату",
                               callback_data=f"checkcrypto:{invoice['invoice_id']}"))
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data=f"extend:{uuid}"))
    usd = round(amount_rub / config.RUB_TO_USD_RATE, 2)
    await call.message.edit_text(
        f"₿ <b>Оплата криптовалютой</b>\n\nСумма: <b>{usd} {config.CRYPTO_ASSET}</b>",
        reply_markup=b.as_markup(),
        parse_mode="HTML",
    )


# ── Ручная проверка статуса оплаты (кнопка) ─────────────────

@router.callback_query(F.data.startswith("checkcrypto:"))
async def cb_checkcrypto(call: CallbackQuery, bot: Bot):
    invoice_id = call.data.split(":", 1)[1]
    status     = await _crypto_check_invoice(invoice_id)

    if status == "paid":
        payment = await db.get_pending_payment(invoice_id, "crypto")
        if not payment:
            await call.answer("Платёж уже обработан.", show_alert=True)
            return
        await _process_crypto_payment(bot, payment)
        await call.answer("✅ Оплата прошла! Подписка активирована.", show_alert=True)
    elif status == "active":
        await call.answer("⏳ Ожидаем оплату...", show_alert=True)
    elif status == "expired":
        await call.answer("❌ Время оплаты истекло. Создайте новый платёж.", show_alert=True)
    else:
        await call.answer("❌ Ошибка проверки. Попробуйте позже.", show_alert=True)


async def _process_crypto_payment(bot: Bot, payment: dict):
    """Активирует подписку после успешного крипто-платежа."""
    await db.complete_payment(payment["payment_id"], "crypto")
    plan_id_raw = payment["plan_id"]
    user_id     = payment["user_id"]
    devices     = payment["devices"]

    if plan_id_raw.startswith("ext::"):
        # Продление: ext::UUID::plan_id
        _, uuid, plan_id = plan_id_raw.split("::", 2)
        plan    = config.PLANS[plan_id]
        import remnawave as rw
        result  = await rw.extend_user(uuid, plan["days"])
        if result:
            await bot.send_message(
                user_id,
                f"✅ <b>Подписка продлена!</b>\n\n"
                f"📅 Добавлено: {plan['name']}\n"
                f"📱 Устройств: {config.DEVICE_NAMES.get(devices, devices)}",
                reply_markup=kb.main_menu_kb(has_subscription=True),
                parse_mode="HTML",
            )
        else:
            await bot.send_message(
                user_id,
                f"❌ Ошибка продления. Обратитесь в поддержку: {config.SUPPORT_USERNAME}",
                parse_mode="HTML",
            )
    else:
        plan   = config.PLANS[plan_id_raw]
        await _activate_subscription(
            bot, user_id, plan_id_raw, devices, plan["days"],
        )


# ── Фоновая задача: авто-проверка крипто-платежей ────────────

async def crypto_payment_checker(bot: Bot):
    """Каждые 30 секунд проверяет незакрытые крипто-платежи."""
    while True:
        await asyncio.sleep(30)
        try:
            pending = await db.get_all_pending_crypto()
            for payment in pending:
                status = await _crypto_check_invoice(payment["payment_id"])
                if status == "paid":
                    await _process_crypto_payment(bot, payment)
                elif status == "expired":
                    await db.complete_payment(payment["payment_id"], "crypto")
                    # Можно уведомить пользователя
        except Exception as e:
            log.error("crypto_payment_checker error: %s", e)


# ══════════════════════════════════════════════════════════════
#  Telegram Stars
# ══════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("paystars:"))
async def cb_paystars(call: CallbackQuery, bot: Bot):
    _, plan_id, devs_str = call.data.split(":")
    devices    = int(devs_str)
    amount_rub = config.PLANS[plan_id]["prices"][devices]
    stars      = max(1, round(amount_rub / config.STARS_RATE))
    plan_name  = config.PLANS[plan_id]["name"]

    payload = f"new::{plan_id}::{devices}"
    await bot.send_invoice(
        chat_id=call.from_user.id,
        title=f"{config.VPN_NAME} — {plan_name}",
        description=(
            f"VPN подписка: {plan_name}, "
            f"{config.DEVICE_NAMES.get(devices, devices)}"
        ),
        payload=payload,
        currency="XTR",
        prices=[LabeledPrice(label=config.VPN_NAME, amount=stars)],
    )
    await call.answer()


@router.callback_query(F.data.startswith("extpaystars:"))
async def cb_extpaystars(call: CallbackQuery, bot: Bot):
    parts               = call.data.split(":")
    uuid, plan_id, devs_str = parts[1], parts[2], parts[3]
    devices    = int(devs_str)
    amount_rub = config.PLANS[plan_id]["prices"][devices]
    stars      = max(1, round(amount_rub / config.STARS_RATE))
    plan_name  = config.PLANS[plan_id]["name"]

    payload = f"ext::{uuid}::{plan_id}::{devices}"
    await bot.send_invoice(
        chat_id=call.from_user.id,
        title=f"{config.VPN_NAME} — продление",
        description=f"Продление: {plan_name}, {config.DEVICE_NAMES.get(devices, devices)}",
        payload=payload,
        currency="XTR",
        prices=[LabeledPrice(label=f"Продление {plan_name}", amount=stars)],
    )
    await call.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message, bot: Bot):
    payload = message.successful_payment.invoice_payload
    user_id = message.from_user.id

    if payload.startswith("new::"):
        _, plan_id, devs_str = payload.split("::")
        devices = int(devs_str)
        plan    = config.PLANS[plan_id]
        await _activate_subscription(bot, user_id, plan_id, devices, plan["days"])

    elif payload.startswith("ext::"):
        _, uuid, plan_id, devs_str = payload.split("::")
        devices = int(devs_str)
        plan    = config.PLANS[plan_id]
        import remnawave as rw
        result  = await rw.extend_user(uuid, plan["days"])
        if result:
            await bot.send_message(
                user_id,
                f"✅ <b>Подписка продлена!</b>\n\n"
                f"📅 Добавлено: {plan['name']}\n"
                f"📱 Устройств: {config.DEVICE_NAMES.get(devices, devices)}",
                reply_markup=kb.main_menu_kb(has_subscription=True),
                parse_mode="HTML",
            )
        else:
            await bot.send_message(
                user_id,
                f"❌ Ошибка продления. Напишите в поддержку: {config.SUPPORT_USERNAME}",
                parse_mode="HTML",
            )
