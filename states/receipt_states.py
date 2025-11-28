from aiogram.fsm.state import State, StatesGroup


class ReceiptStates(StatesGroup):
    """States for receipt upload and processing"""
    waiting_for_receipt_image = State()
    configuring_meals = State()
    editing_meal = State()
    entering_restaurant_name = State()
    entering_participant_count = State()
    entering_card_number = State()
    checking_delivery = State()
    
    # NEW: Main user meal selection
    selecting_own_meals = State()