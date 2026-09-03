from aiogram.fsm.state import State, StatesGroup


class OrderStates(StatesGroup):
    """Шаги, через которые проходит пользователь при оформлении заказа."""
    choosing_work_type = State()
    entering_subject = State()
    entering_deadline = State()
    entering_details = State()
    confirming = State()


class ChatStates(StatesGroup):
    """Состояние переписки с исполнителем/клиентом по заказу."""
    chatting = State()
