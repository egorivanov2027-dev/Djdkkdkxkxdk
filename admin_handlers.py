# admin_handlers.py — админ-панель

import logging
from datetime import datetime, timedelta

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

import config
import database as db
import remnawave
import keyboards as kb
from handlers import _activate_subscription, fmt_dt, is_expired

log    = logging.getLogger(__name__)
router = Router()


# ── FSM ──────────────────────────────────────────────────────

class AdminStates(StatesGroup):
    waiting_user_id   = State()
    waiting_broadcast = State()


# ── Фильтр: только админы ────────────────────────────────────

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


# ── /admin ───────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа.")
        return
    await state.clear()
    await message.answer("🛠 <b>Админ-панель</b>", reply_markup=kb.admin_main_kb(), parse_mode="HTML")


@router.callback_query(F.data == "adm_panel")
async def cb_adm_panel(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет доступа.", show_alert=True)
        return
    await state.clear()
    await call.message.edit_text("🛠 <b>Админ-панель</b>", reply_markup=kb.admin_main_kb(), parse_mode="HTML")


@router.callback_query(F.data == "adm_close")
async def cb_adm_close(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()
    await call.answer()


# ── Статистика ───────────────────────────────────────────────

@router.callback_query(F.data == "adm_stats")
async def cb_adm_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌", show_alert=True)
        return
    stats = await db.get_stats()
    text  = (
        f"📊 <b>Статистика {config.VPN_NAME}</b>\n\n"
        f"👥 Всего пользователей: <b>{stats['total_users']}</b>\n"
        f"✅ Активных подписок: <b>{stats['active_subs']}</b>\n"
        f"📋 Всего подписок: <b>{stats['total_subs']}</b>\n"
        f"💰 Выручка: <b>{stats['total_revenue']:.2f} ₽</b>"
    )
    await call.message.edit_text(text, reply_markup=kb.back_admin_kb(), parse_mode="HTML")


# ── Список пользователей ─────────────────────────────────────

@router.callback_query(F.data == "adm_users")
async def cb_adm_users(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌", show_alert=True)
        return
    users = await db.get_all_users()
    if not users:
        await call.answer("Нет пользователей.", show_alert=True)
        return

    lines = [f"👥 <b>Пользователи ({len(users)})</b>\n"]
    # Показываем последних 30
    for u in users[:30]:
        un   = f"@{u['username']}" if u.get("username") else u.get("first_name", "—")
        trial = "✅" if u["has_trial"] else "❌"
        lines.append(f"• <code>{u['telegram_id']}</code> {un} | пробный: {trial}")
    if len(users) > 30:
        lines.append(f"\n... и ещё {len(users)-30} пользователей.")

    await call.message.edit_text(
        "\n".join(lines), reply_markup=kb.back_admin_kb(), parse_mode="HTML"
    )


# ── Выдать подписку ──────────────────────────────────────────

@router.callback_query(F.data == "adm_give")
async def cb_adm_give(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("❌", show_alert=True)
        return
    await state.clear()
    await state.set_state(AdminStates.waiting_user_id)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="◀️ Отмена", callback_data="adm_panel"))
    await call.message.edit_text(
        "➕ <b>Выдать подписку</b>\n\n"
        "Введите Telegram ID пользователя:",
        reply_markup=b.as_markup(),
        parse_mode="HTML",
    )


@router.message(AdminStates.waiting_user_id)
async def adm_got_user_id(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    text = message.text.strip().lstrip("@")
    try:
        target_id = int(text)
    except ValueError:
        await message.answer("❌ Введите числовой Telegram ID.")
        return

    user = await db.get_user(target_id)
    if not user:
        # Создаём пользователя
        await db.get_or_create_user(target_id, "", "Unnamed")
        user = await db.get_user(target_id)

    un = f"@{user.get('username')}" if user.get("username") else f"ID {target_id}"
    await state.update_data(target_id=target_id)
    await state.clear()

    await message.answer(
        f"👤 Пользователь: <b>{un}</b>\n\n"
        f"Выберите план подписки:",
        reply_markup=kb.admin_plans_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admplan:"))
async def cb_admplan(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("❌", show_alert=True)
        return
    plan_id = call.data.split(":")[1]
    # Получаем target_id из предыдущего сообщения (парсим текст)
    text = call.message.text or ""
    target_id = None
    for word in text.split():
        if word.startswith("ID") or word.isdigit():
            try:
                target_id = int(word.replace("ID", "").strip())
            except ValueError:
                pass
    # Запасной вариант: сохраняем в state
    data = await state.get_data()
    if not target_id:
        target_id = data.get("target_id")
    if not target_id:
        await call.answer("❌ Не удалось определить пользователя.", show_alert=True)
        return
    await state.update_data(target_id=target_id, plan_id=plan_id)
    await call.message.edit_text(
        f"📅 План: <b>{config.PLANS[plan_id]['name']}</b>\n\n"
        f"Выберите количество устройств:",
        reply_markup=kb.admin_devices_kb(plan_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admdev:"))
async def cb_admdev(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("❌", show_alert=True)
        return
    _, plan_id, devs_str = call.data.split(":")
    devices = int(devs_str)
    data    = await state.get_data()
    target_id = data.get("target_id")
    if not target_id:
        await call.answer("❌ Сессия истекла. Начните заново.", show_alert=True)
        return

    plan  = config.PLANS[plan_id]
    price = plan["prices"][devices]
    await call.message.edit_text(
        f"✅ <b>Подтверждение</b>\n\n"
        f"👤 Пользователь: <code>{target_id}</code>\n"
        f"📅 План: <b>{plan['name']}</b>\n"
        f"📱 Устройств: <b>{config.DEVICE_NAMES[devices]}</b>\n"
        f"💰 Стоимость (для справки): {price} ₽\n\n"
        f"Выдать бесплатно?",
        reply_markup=kb.admin_confirm_kb(target_id, plan_id, devices),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admconfirm:"))
async def cb_admconfirm(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin(call.from_user.id):
        await call.answer("❌", show_alert=True)
        return
    parts = call.data.split(":")
    target_id = int(parts[1])
    plan_id   = parts[2]
    devices   = int(parts[3])
    plan      = config.PLANS[plan_id]

    await call.message.edit_text("⏳ Создаём подписку...", parse_mode="HTML")
    await _activate_subscription(
        bot, target_id, plan_id, devices, plan["days"],
        notify_message=None,
    )
    await call.message.edit_text(
        f"✅ Подписка выдана пользователю <code>{target_id}</code>.",
        reply_markup=kb.back_admin_kb(),
        parse_mode="HTML",
    )
    await state.clear()


# ── Рассылка ─────────────────────────────────────────────────

@router.callback_query(F.data == "adm_broadcast")
async def cb_adm_broadcast(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("❌", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_broadcast)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="◀️ Отмена", callback_data="adm_panel"))
    await call.message.edit_text(
        "📢 <b>Рассылка</b>\n\nОтправьте сообщение для рассылки всем пользователям:",
        reply_markup=b.as_markup(),
        parse_mode="HTML",
    )


@router.message(AdminStates.waiting_broadcast)
async def adm_do_broadcast(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    users    = await db.get_all_users()
    ok, fail = 0, 0
    for u in users:
        try:
            await bot.copy_message(
                chat_id=u["telegram_id"],
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )
            ok += 1
        except Exception:
            fail += 1
    await message.answer(
        f"📢 Рассылка завершена.\n✅ Отправлено: {ok}\n❌ Ошибок: {fail}",
        reply_markup=kb.back_admin_kb(),
        parse_mode="HTML",
    )


# ── Команда /givesubscription (быстрая выдача) ───────────────

@router.message(Command("givesub"))
async def cmd_givesub(message: Message, bot: Bot):
    """
    Использование: /givesub <user_id> <plan_id> <devices>
    Пример: /givesub 123456789 1m 1
    """
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 4:
        await message.answer(
            "Использование: /givesub &lt;user_id&gt; &lt;plan_id&gt; &lt;devices&gt;\n"
            "Пример: /givesub 123456789 1m 1\n\n"
            "Планы: " + ", ".join(config.PLANS.keys()),
            parse_mode="HTML",
        )
        return
    try:
        target_id = int(parts[1])
        plan_id   = parts[2]
        devices   = int(parts[3])
    except ValueError:
        await message.answer("❌ Неверные параметры.")
        return
    if plan_id not in config.PLANS:
        await message.answer(f"❌ Неизвестный план. Доступны: {', '.join(config.PLANS)}")
        return
    if devices not in config.PLANS[plan_id]["prices"]:
        await message.answer(f"❌ Неверное кол-во устройств. Доступны: {list(config.PLANS[plan_id]['prices'].keys())}")
        return
    await db.get_or_create_user(target_id, "", "Unnamed")
    plan = config.PLANS[plan_id]
    await message.answer(f"⏳ Создаём подписку для <code>{target_id}</code>...", parse_mode="HTML")
    await _activate_subscription(bot, target_id, plan_id, devices, plan["days"])
    await message.answer(f"✅ Подписка <b>{plan['name']}</b> выдана пользователю <code>{target_id}</code>.", parse_mode="HTML")
