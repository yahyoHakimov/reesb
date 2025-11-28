from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Main menu keyboard"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📸 New Receipt"),
                KeyboardButton(text="📋 My Sessions")
            ],
            [
                KeyboardButton(text="❓ Help")
            ]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel button"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_session")
            ]
        ]
    )
    return keyboard


def get_receipt_actions_keyboard() -> InlineKeyboardMarkup:
    """Actions for extracted receipt text"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Text is Correct", callback_data="confirm_receipt_text"),
            ],
            [
                InlineKeyboardButton(text="✏️ Edit Text", callback_data="edit_receipt_text"),
            ],
            [
                InlineKeyboardButton(text="🔄 Upload Again", callback_data="reupload_receipt"),
            ],
            [
                InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_session")
            ]
        ]
    )
    return keyboard