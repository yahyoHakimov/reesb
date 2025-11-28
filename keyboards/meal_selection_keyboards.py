from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Set, Dict


def build_meal_selection_keyboard(
    meals: List,
    selected_meal_ids: Set[int] = None,
    meal_quantities: Dict[int, int] = None
) -> InlineKeyboardMarkup:
    """
    Build keyboard for selecting individual meals with quantity controls
    
    Format:
    - Not selected: [☐ Meal name - price]
    - Selected: [✅ Meal name - price]
                [➖] [Qty: 2] [➕]
    """
    if selected_meal_ids is None:
        selected_meal_ids = set()
    
    if meal_quantities is None:
        meal_quantities = {}
    
    keyboard_buttons = []
    
    for meal in meals:
        is_selected = meal.id in selected_meal_ids
        checkbox = "✅" if is_selected else "☐"
        
        # Format price
        price_display = f"{(meal.price / meal.quantity_available):,}".replace(',', ' ')
        
        # Meal button
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"{checkbox} {meal.name} - {price_display}",
                callback_data=f"select_meal:{meal.id}"
            )
        ])
        
        # If selected, show quantity controls
        if is_selected:
            current_qty = meal_quantities.get(meal.id, 1)
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text="➖",
                    callback_data=f"qty_dec:{meal.id}"
                ),
                InlineKeyboardButton(
                    text=f"Miqdor: {current_qty}",
                    callback_data=f"qty_noop:{meal.id}"
                ),
                InlineKeyboardButton(
                    text="➕",
                    callback_data=f"qty_inc:{meal.id}"
                )
            ])
    
    # Confirm button
    keyboard_buttons.append([
        InlineKeyboardButton(
            text="✅ Tasdiqlash",
            callback_data="confirm_own_meals"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)