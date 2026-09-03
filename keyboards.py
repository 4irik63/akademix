from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


WORK_TYPES = [
    "Курсовая работа",
    "ВКР",
    "Эссе",
    "Реферат",
    "Презентация",
    "Контрольная работа",
    "Другое",
]

MENU_NEW_ORDER = "📝 Сделать заказ"
MENU_MY_ORDERS = "📋 Мои заказы"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Постоянная клавиатура внизу экрана — не пропадает после ответа бота,
    поэтому пользователю не нужно каждый раз вводить /start."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MENU_NEW_ORDER)],
            [KeyboardButton(text=MENU_MY_ORDERS)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


def work_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for work_type in WORK_TYPES:
        builder.button(text=work_type, callback_data=f"worktype:{work_type}")
    builder.adjust(2)
    return builder.as_markup()


def confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_order")
    builder.button(text="❌ Отменить", callback_data="cancel_order")
    builder.adjust(2)
    return builder.as_markup()


def skip_details_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Пропустить", callback_data="skip_details")
    return builder.as_markup()


def chat_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Кнопка входа в чат по конкретному заказу — показывается и клиенту,
    и назначенному администратору."""
    builder = InlineKeyboardBuilder()
    builder.button(text="💬 Чат по заказу", callback_data=f"start_chat:{order_id}")
    return builder.as_markup()


def end_chat_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🚪 Завершить чат", callback_data="end_chat")
    return builder.as_markup()


# ---------- Админ-панель ----------

STATUS_LABELS = {
    "new": "🆕 Новый",
    "in_progress": "⏳ В работе",
    "done": "✅ Выполнен",
    "cancelled": "❌ Отменён",
}


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🆕 Новые", callback_data="admin_filter:new")
    builder.button(text="⏳ В работе", callback_data="admin_filter:in_progress")
    builder.button(text="✅ Выполненные", callback_data="admin_filter:done")
    builder.button(text="🗄 Архив", callback_data="admin_filter:cancelled")
    builder.button(text="📋 Все заказы", callback_data="admin_filter:all")
    builder.adjust(2)
    return builder.as_markup()


def order_action_keyboard(order_id: int, status: str) -> InlineKeyboardMarkup:
    """Кнопки действий по конкретному заказу — набор зависит от текущего статуса."""
    builder = InlineKeyboardBuilder()

    if status == "new":
        builder.button(text="▶️ Взять в работу", callback_data=f"set_status:{order_id}:in_progress")
    if status in ("new", "in_progress"):
        builder.button(text="✅ Готово", callback_data=f"set_status:{order_id}:done")
    if status in ("new", "in_progress"):
        builder.button(text="❌ Отменить", callback_data=f"set_status:{order_id}:cancelled")

    builder.button(text="💬 Чат с клиентом", callback_data=f"start_chat:{order_id}")
    builder.adjust(1)
    return builder.as_markup()
