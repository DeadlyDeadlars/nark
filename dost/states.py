from aiogram.fsm.state import State, StatesGroup

class OrderStates(StatesGroup):
    """Состояния для процесса заказа"""
    waiting_for_address = State()
    waiting_for_confirmation = State()

class AdminStates(StatesGroup):
    """Состояния для административных функций"""
    waiting_for_user_id = State()
    waiting_for_admin_message = State() 
    waiting_for_broadcast_text = State()