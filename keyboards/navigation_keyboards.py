from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove


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


def build_categorization_keyboard(meals: list, session_id: str) -> InlineKeyboardMarkup:
    """
    Build keyboard for categorizing meals (shared/individual)
    Each meal row has: [Meal checkbox button] [Small edit button]
    """
    keyboard_buttons = []
    
    for meal in meals:
        # Checkbox based on current type
        checkbox = "✅" if meal.is_shared else "☐"
        
        # Show quantity if > 1
        qty_display = f" ({meal.quantity_available}×)" if meal.quantity_available > 1 else ""
        
        # Format price with space separator
        price_display = f"{meal.price:,}".replace(',', ' ')
        
        # Row with meal button and small edit button
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"{checkbox} {meal.name}{qty_display} - {price_display}",
                callback_data=f"toggle:{meal.id}"
            ),
            InlineKeyboardButton(
                text="✏️",  # Small edit icon only
                callback_data=f"edit:{meal.id}"
            )
        ])
    
    # Done button at the end
    keyboard_buttons.append([
        InlineKeyboardButton(
            text="✅ Davom etish",
            callback_data="meals_done"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def get_meal_edit_keyboard(meal_id: int) -> InlineKeyboardMarkup:
    """Keyboard for meal editing options"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Nomini o'zgartirish", callback_data=f"edit_name_{meal_id}"),
            ],
            [
                InlineKeyboardButton(text="💰 Narxni o'zgartirish", callback_data=f"edit_price_{meal_id}"),
            ],
            [
                InlineKeyboardButton(text="🔢 Miqdorini o'zgartirish", callback_data=f"edit_qty_{meal_id}"),
            ],
            [
                InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"delete_{meal_id}"),
            ],
            [
                InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_meals")
            ]
        ]
    )
    return keyboard


def get_yes_no_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    """Generic yes/no keyboard"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha", callback_data=yes_data),
                InlineKeyboardButton(text="❌ Yo'q", callback_data=no_data)
            ]
        ]
    )
    return keyboard


def remove_keyboard() -> ReplyKeyboardRemove:
    """Remove keyboard"""
    return ReplyKeyboardRemove()