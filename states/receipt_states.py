from aiogram.fsm.state import State, StatesGroup


class ReceiptStates(StatesGroup):
    """States for receipt upload and processing"""
    waiting_for_receipt_image = State()
    viewing_extracted_text = State()
    # We'll add more states in next steps:
    # editing_receipt_text = State()
    # entering_participant_count = State()
    # entering_card_number = State()
    # checking_delivery = State()