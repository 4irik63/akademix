from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
from states import OrderStates, ChatStates, AdminStates
from keyboards import (
    main_menu_keyboard,
    MENU_NEW_ORDER,
    MENU_MY_ORDERS,
    work_type_keyboard,
    confirm_keyboard,
    skip_details_keyboard,
    chat_keyboard,
    end_chat_keyboard,
    admin_panel_keyboard,
    order_action_keyboard,
    cancel_reason_keyboard,
    STATUS_LABELS,
)
from config import ADMIN_CHAT_IDS

router = Router()


# ---------- Старт и Сброс (/stop) ----------

@router.message(CommandStart())
@router.message(Command("stop"))
async def cmd_start_or_stop(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Салют! Это AkademiX Study ⚡️\n\n"
        "Мы здесь для того, чтобы учеба не мешала жить нормальной жизнью. "
        "Забудь про бессонные ночи перед сдачей — скидывай задачу нам.\n\n"
        "Выбирай в меню внизу, что нужно оформить, и считай, что дедлайн уже не горит 🤝",
        reply_markup=main_menu_keyboard(),
    )


# ---------- Начало оформления заказа ----------

@router.message(F.text == MENU_NEW_ORDER)
async def start_order(message: Message, state: FSMContext) -> None:
    await state.set_state(OrderStates.choosing_work_type)
    await message.answer(
        "Какой тип работы нужен?",
        reply_markup=work_type_keyboard(),
    )


@router.callback_query(OrderStates.choosing_work_type, F.data.startswith("worktype:"))
async def choose_work_type(callback: CallbackQuery, state: FSMContext) -> None:
    work_type = callback.data.split(":", 1)[1]
    await state.update_data(work_type=work_type)
    await state.set_state(OrderStates.entering_subject)
    await callback.message.edit_text(
        f"Тип работы: <b>{work_type}</b>\n\nПо какому предмету? Напишите название.",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(OrderStates.entering_subject)
async def enter_subject(message: Message, state: FSMContext) -> None:
    await state.update_data(subject=message.text)
    await state.set_state(OrderStates.entering_deadline)
    await message.answer("К какому сроку нужна работа? (например: 15 сентября или через 5 дней)")


@router.message(OrderStates.entering_deadline)
async def enter_deadline(message: Message, state: FSMContext) -> None:
    await state.update_data(deadline=message.text)
    await state.set_state(OrderStates.entering_details)
    await message.answer(
        "Есть дополнительные детали или пожелания? Опишите их одним сообщением, "
        "или нажмите «Пропустить».",
        reply_markup=skip_details_keyboard(),
    )


@router.message(OrderStates.entering_details)
async def enter_details(message: Message, state: FSMContext) -> None:
    await state.update_data(details=message.text)
    await show_summary(message, state)


@router.callback_query(OrderStates.entering_details, F.data == "skip_details")
async def skip_details(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(details="—")
    await show_summary(callback.message, state, edit=True)
    await callback.answer()


async def show_summary(message: Message, state: FSMContext, edit: bool = False) -> None:
    data = await state.get_data()
    await state.set_state(OrderStates.confirming)

    text = (
        "Проверьте, всё ли верно:\n\n"
        f"📚 Тип работы: <b>{data['work_type']}</b>\n"
        f"📖 Предмет: <b>{data['subject']}</b>\n"
        f"⏰ Срок: <b>{data['deadline']}</b>\n"
        f"💬 Детали: {data['details']}\n\n"
        "Подтвердить заказ?"
    )

    if edit:
        await message.edit_text(text, reply_markup=confirm_keyboard(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=confirm_keyboard(), parse_mode="HTML")


# ---------- Подтверждение / отмена клиентом ----------

@router.callback_query(OrderStates.confirming, F.data == "confirm_order")
async def confirm_order(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    user = callback.from_user

    assigned_admin_id = None
    if ADMIN_CHAT_IDS:
        count_so_far = await db.get_order_count()
        assigned_admin_id = ADMIN_CHAT_IDS[count_so_far % len(ADMIN_CHAT_IDS)]

    order_id = await db.create_order(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        work_type=data["work_type"],
        subject=data["subject"],
        deadline=data["deadline"],
        details=data["details"],
        assigned_admin_id=assigned_admin_id,
    )

    confirm_text = (
        f"✅ Заказ №{order_id} принят!\n\n"
        "Мы свяжемся с вами в ближайшее время, чтобы уточнить детали и стоимость.\n\n"
        "Посмотреть свои заказы можно кнопкой «Мои заказы» в меню внизу."
    )

    if assigned_admin_id:
        await callback.message.edit_text(confirm_text, reply_markup=chat_keyboard(order_id))
    else:
        await callback.message.edit_text(confirm_text)

    if assigned_admin_id:
        admin_text = (
            f"🆕 Новый заказ №{order_id} (назначен вам)\n\n"
            f"От: {user.full_name} (@{user.username or '—'}, id {user.id})\n"
            f"Тип работы: {data['work_type']}\n"
            f"Предмет: {data['subject']}\n"
            f"Срок: {data['deadline']}\n"
            f"Детали: {data['details']}"
        )
        try:
            await bot.send_message(assigned_admin_id, admin_text, reply_markup=chat_keyboard(order_id))
        except Exception:
            pass

    await state.clear()
    await callback.answer()


@router.callback_query(OrderStates.confirming, F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        f"Заказ отменён. Если захотите оформить новый — нажмите «{MENU_NEW_ORDER}» в меню.",
    )
    await callback.answer()


# ---------- Мои заказы ----------

@router.message(F.text == MENU_MY_ORDERS)
async def my_orders(message: Message) -> None:
    orders = await db.get_user_orders(message.from_user.id)

    if not orders:
        await message.answer(
            f"У вас пока нет заказов. Нажмите «{MENU_NEW_ORDER}», чтобы оформить первый.",
        )
        return

    lines = ["Ваши заказы:\n"]
    status_labels = {
        "new": "🆕 новый",
        "in_progress": "⏳ в работе",
        "done": "✅ выполнен",
        "cancelled": "❌ отменён",
    }
    for order in orders:
        status = status_labels.get(order["status"], order["status"])
        lines.append(
            f"№{order['id']} — {order['work_type']} по «{order['subject']}» — {status}"
        )

    await message.answer("\n".join(lines))


# ---------- Команда для админов: только свои назначенные заказы ----------

@router.message(Command("myorders"))
async def admin_my_orders(message: Message) -> None:
    if message.from_user.id not in ADMIN_CHAT_IDS:
        return

    orders = await db.get_admin_orders(message.from_user.id)

    if not orders:
        await message.answer("Вам пока не назначено ни одного заказа.")
        return

    status_labels = {
        "new": "🆕 новый",
        "in_progress": "⏳ в работе",
        "done": "✅ выполнен",
        "cancelled": "❌ отменён",
    }

    lines = ["Заказы, назначенные вам:\n"]
    for order in orders:
        status = status_labels.get(order["status"], order["status"])
        lines.append(
            f"№{order['id']} — {order['work_type']} по «{order['subject']}», "
            f"клиент @{order['username'] or '—'} — {status}"
        )

    await message.answer("\n".join(lines))


# ---------- Админ-панель: видят оба админа, показывает все заказы ----------

@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    if message.from_user.id not in ADMIN_CHAT_IDS:
        return

    await message.answer(
        "🛠 Админ-панель\n\nВыберите, какие заказы показать:",
        reply_markup=admin_panel_keyboard(),
    )


@router.callback_query(F.data.startswith("admin_filter:"))
async def admin_filter(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer("Недоступно.", show_alert=True)
        return

    status_filter = callback.data.split(":", 1)[1]

    if status_filter == "all":
        orders = await db.get_active_orders()
    else:
        orders = await db.get_orders_by_status(status_filter)

    filter_titles = {
        "new": "🆕 Новые заказы",
        "in_progress": "⏳ Заказы в работе",
        "done": "✅ Выполненные заказы",
        "cancelled": "🗄 Архив (отменённые заказы)",
        "all": "📋 Все заказы (без архива)",
    }
    title = filter_titles.get(status_filter, status_filter)

    if not orders:
        await callback.message.answer(f"{title}\n\nПусто — заказов по этому фильтру нет.")
        await callback.answer()
        return

    await callback.message.answer(f"{title} ({len(orders)}):")

    for order in orders:
        status_label = STATUS_LABELS.get(order["status"], order["status"])
        text = (
            f"№{order['id']} — {status_label}\n"
            f"📚 {order['work_type']} по «{order['subject']}»\n"
            f"⏰ Срок: {order['deadline']}\n"
            f"💬 Детали: {order['details']}\n"
            f"👤 Клиент: {order['full_name']} (@{order['username'] or '—'})"
        )
        await callback.message.answer(text, reply_markup=order_action_keyboard(order["id"], order["status"]))

    await callback.answer()


@router.callback_query(F.data.startswith("set_status:"))
async def set_order_status(callback: CallbackQuery, bot: Bot) -> None:
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer("Недоступно.", show_alert=True)
        return

    _, order_id_str, new_status = callback.data.split(":")
    order_id = int(order_id_str)

    order = await db.get_order(order_id)
    if order is None:
        await callback.answer("Заказ не найден.", show_alert=True)
        return

    await db.update_order_status(order_id, new_status)

    status_label = STATUS_LABELS.get(new_status, new_status)
    await callback.message.edit_text(
        f"№{order_id} — статус изменён на: {status_label}\n\n"
        f"📚 {order['work_type']} по «{order['subject']}»\n"
        f"👤 Клиент: {order['full_name']} (@{order['username'] or '—'})",
        reply_markup=order_action_keyboard(order_id, new_status),
    )

    client_status_texts = {
        "in_progress": f"⏳ Ваш заказ №{order_id} взят в работу!",
        "done": f"✅ Ваш заказ №{order_id} выполнен! Спасибо, что выбрали нас.",
    }
    client_text = client_status_texts.get(new_status)
    if client_text:
        try:
            await bot.send_message(order["user_id"], client_text)
        except Exception:
            pass

    await callback.answer("Статус обновлён")


# ---------- Логика отмены заказа админом с причиной ----------

@router.callback_query(F.data.startswith("cancel_order_reason:"))
async def ask_cancel_reason(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user.id not in ADMIN_CHAT_IDS:
        await callback.answer("Недоступно.", show_alert=True)
        return

    order_id = int(callback.data.split(":", 1)[1])
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Заказ не найден.", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_cancel_reason)
    await state.update_data(
        order_id=order_id,
        order_msg_id=callback.message.message_id,
        chat_id=callback.message.chat.id,
    )

    await callback.message.answer(
        f"Напишите причину отмены заказа <b>№{order_id}</b> (сообщение с причиной будет отправлено клиенту):",
        reply_markup=cancel_reason_keyboard(order_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(AdminStates.waiting_for_cancel_reason, F.data.startswith("abort_cancellation:"))
async def abort_cancellation(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Отмена заказа прервана. Статус остался прежним.")
    await callback.answer()


@router.callback_query(AdminStates.waiting_for_cancel_reason, F.data.startswith("skip_cancel_reason:"))
async def skip_cancel_reason(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    order_id = int(callback.data.split(":", 1)[1])
    data = await state.get_data()
    await state.clear()
    await process_cancellation(order_id=order_id, reason=None, admin_message=callback.message, data=data, bot=bot)
    await callback.answer()


@router.message(AdminStates.waiting_for_cancel_reason, F.text)
async def enter_cancel_reason_text(message: Message, state: FSMContext, bot: Bot) -> None:
    if message.from_user.id not in ADMIN_CHAT_IDS:
        return

    data = await state.get_data()
    order_id = data.get("order_id")
    await state.clear()

    await process_cancellation(order_id=order_id, reason=message.text, admin_message=message, data=data, bot=bot)


async def process_cancellation(
    order_id: int,
    reason: str | None,
    admin_message: Message,
    data: dict,
    bot: Bot,
) -> None:
    order = await db.get_order(order_id)
    if not order:
        await admin_message.answer("Заказ не найден.")
        return

    await db.update_order_status(order_id, "cancelled")

    if reason:
        client_text = (
            f"❌ Ваш заказ №{order_id} был отменён администратором.\n\n"
            f"<b>Причина:</b> {reason}\n\n"
            "Если у вас остались вопросы — напишите нам."
        )
    else:
        client_text = (
            f"❌ Ваш заказ №{order_id} был отменён.\n\n"
            "Если это ошибка или возникли вопросы — напишите нам."
        )

    try:
        await bot.send_message(order["user_id"], client_text, parse_mode="HTML")
    except Exception:
        pass

    status_label = STATUS_LABELS.get("cancelled", "cancelled")
    updated_card_text = (
        f"№{order_id} — {status_label}\n\n"
        f"📚 {order['work_type']} по «{order['subject']}»\n"
        f"👤 Клиент: {order['full_name']} (@{order['username'] or '—'})"
    )
    if reason:
        updated_card_text += f"\n❌ Причина отмены: {reason}"

    orig_msg_id = data.get("order_msg_id")
    chat_id = data.get("chat_id")
    if orig_msg_id and chat_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=orig_msg_id,
                text=updated_card_text,
                reply_markup=order_action_keyboard(order_id, "cancelled"),
            )
        except Exception:
            pass

    await admin_message.answer(f"✅ Заказ №{order_id} успешно отменён. Клиенту отправлено уведомление.")


# ---------- Чат клиент <-> исполнитель ----------

@router.callback_query(F.data.startswith("start_chat:"))
async def start_chat(callback: CallbackQuery, state: FSMContext) -> None:
    order_id = int(callback.data.split(":", 1)[1])
    order = await db.get_order(order_id)

    if order is None:
        await callback.answer("Заказ не найден.", show_alert=True)
        return

    user_id = callback.from_user.id

    if user_id == order["user_id"]:
        partner_id = order["assigned_admin_id"]
        partner_label = "исполнителем"
    elif user_id == order["assigned_admin_id"]:
        partner_id = order["user_id"]
        partner_label = "клиентом"
    else:
        await callback.answer("У вас нет доступа к этому чату.", show_alert=True)
        return

    if partner_id is None:
        await callback.answer("Собеседник пока не назначен.", show_alert=True)
        return

    await state.set_state(ChatStates.chatting)
    await state.update_data(order_id=order_id, partner_id=partner_id)

    await callback.message.answer(
        f"💬 Вы вошли в чат с {partner_label} по заказу №{order_id}.\n"
        "Пишите сообщения — они будут пересылаться напрямую.\n"
        "Чтобы выйти, нажмите кнопку ниже или отправьте /endchat.",
        reply_markup=end_chat_keyboard(),
    )
    await callback.answer()


@router.message(ChatStates.chatting, Command("endchat"))
async def end_chat_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Чат завершён. Возврат в меню — /start.")


@router.callback_query(ChatStates.chatting, F.data == "end_chat")
async def end_chat_button(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Чат завершён. Возврат в меню — /start.")
    await callback.answer()


@router.message(ChatStates.chatting, F.text)
async def relay_chat_message(message: Message, state: FSMContext, bot: Bot) -> None:
    if message.text.startswith("/"):
        return

    data = await state.get_data()
    partner_id = data.get("partner_id")
    order_id = data.get("order_id")

    if not partner_id:
        await state.clear()
        await message.answer("Собеседник не найден, чат завершён.")
        return

    try:
        await bot.send_message(
            partner_id,
            f"💬 Заказ №{order_id}, сообщение от {message.from_user.full_name}:\n\n{message.text}",
        )
        await message.answer("Отправлено ✅")
    except Exception:
        await message.answer(
            "Не удалось отправить сообщение — собеседник ещё не запускал бота (/start)."
        )