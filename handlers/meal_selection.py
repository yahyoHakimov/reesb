from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from database.models import Session as DBSession, Meal, SessionParticipant, UserMealSelection
from database.connection import async_session_maker
from states.receipt_states import ReceiptStates
from keyboards import build_meal_selection_keyboard
from utils import format_amount
import logging
import uuid

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("select_meal:"))
async def toggle_meal_selection(callback: CallbackQuery, state: FSMContext):
    """Toggle meal selection on/off"""
    meal_id = int(callback.data.split(":")[1])
    
    data = await state.get_data()
    selected_meal_ids = data.get('selected_meal_ids', set())
    meal_quantities = data.get('meal_quantities', {})
    session_id = data.get('session_id')
    
    # Toggle selection
    if meal_id in selected_meal_ids:
        selected_meal_ids.remove(meal_id)
        meal_quantities.pop(meal_id, None)
    else:
        selected_meal_ids.add(meal_id)
        meal_quantities[meal_id] = 1  # Default quantity
    
    await state.update_data(
        selected_meal_ids=selected_meal_ids,
        meal_quantities=meal_quantities
    )
    
    # Rebuild keyboard
    async with async_session_maker() as session:
        result = await session.execute(
            select(Meal)
            .where(Meal.session_id == uuid.UUID(session_id))
            .where(Meal.is_shared == False)
            .order_by(Meal.position)
        )
        meals = result.scalars().all()
        
        keyboard = build_meal_selection_keyboard(meals, selected_meal_ids, meal_quantities)
        
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer()


@router.callback_query(F.data.startswith("qty_inc:"))
async def increase_quantity(callback: CallbackQuery, state: FSMContext):
    """Increase meal quantity"""
    meal_id = int(callback.data.split(":")[1])
    
    data = await state.get_data()
    meal_quantities = data.get('meal_quantities', {})
    selected_meal_ids = data.get('selected_meal_ids', set())
    session_id = data.get('session_id')
    
    # Get meal to check max quantity
    async with async_session_maker() as session:
        result = await session.execute(
            select(Meal).where(Meal.id == meal_id)
        )
        meal = result.scalar_one_or_none()
        
        if meal:
            current_qty = meal_quantities.get(meal_id, 1)
            
            # Don't exceed available quantity
            if current_qty < meal.quantity_available:
                meal_quantities[meal_id] = current_qty + 1
                
                await state.update_data(meal_quantities=meal_quantities)
                
                # Rebuild keyboard
                meals_result = await session.execute(
                    select(Meal)
                    .where(Meal.session_id == uuid.UUID(session_id))
                    .where(Meal.is_shared == False)
                    .order_by(Meal.position)
                )
                meals = meals_result.scalars().all()
                
                keyboard = build_meal_selection_keyboard(meals, selected_meal_ids, meal_quantities)
                
                await callback.message.edit_reply_markup(reply_markup=keyboard)
                await callback.answer(f"Miqdor: {meal_quantities[meal_id]}")
            else:
                await callback.answer(f"Maksimal: {meal.quantity_available}", show_alert=True)


@router.callback_query(F.data.startswith("qty_dec:"))
async def decrease_quantity(callback: CallbackQuery, state: FSMContext):
    """Decrease meal quantity"""
    meal_id = int(callback.data.split(":")[1])
    
    data = await state.get_data()
    meal_quantities = data.get('meal_quantities', {})
    selected_meal_ids = data.get('selected_meal_ids', set())
    session_id = data.get('session_id')
    
    current_qty = meal_quantities.get(meal_id, 1)
    
    if current_qty > 1:
        meal_quantities[meal_id] = current_qty - 1
        
        await state.update_data(meal_quantities=meal_quantities)
        
        # Rebuild keyboard
        async with async_session_maker() as session:
            result = await session.execute(
                select(Meal)
                .where(Meal.session_id == uuid.UUID(session_id))
                .where(Meal.is_shared == False)
                .order_by(Meal.position)
            )
            meals = result.scalars().all()
            
            keyboard = build_meal_selection_keyboard(meals, selected_meal_ids, meal_quantities)
            
            await callback.message.edit_reply_markup(reply_markup=keyboard)
            await callback.answer(f"Miqdor: {meal_quantities[meal_id]}")
    else:
        await callback.answer("Minimal: 1", show_alert=True)


@router.callback_query(F.data.startswith("qty_noop:"))
async def quantity_noop(callback: CallbackQuery):
    """No-op for quantity display button"""
    await callback.answer()


@router.callback_query(F.data == "confirm_own_meals")
async def confirm_own_meals(callback: CallbackQuery, state: FSMContext):
    """Confirm main user's meal selections"""
    data = await state.get_data()
    selected_meal_ids = data.get('selected_meal_ids', set())
    meal_quantities = data.get('meal_quantities', {})
    session_id = data.get('session_id')
    
    if not selected_meal_ids:
        await callback.answer("Kamida bitta ovqat tanlang!", show_alert=True)
        return
    
    async with async_session_maker() as session:
        try:
            user = callback.from_user
            
            # Get session
            session_result = await session.execute(
                select(DBSession).where(DBSession.id == uuid.UUID(session_id))
            )
            db_session = session_result.scalar_one_or_none()
            
            if not db_session:
                await callback.answer("Session topilmadi", show_alert=True)
                return
            
            # Create participant record for main user
            participant = SessionParticipant(
                session_id=uuid.UUID(session_id),
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                is_creator=True,
                has_confirmed=True
            )
            session.add(participant)
            await session.flush()
            
            # Save meal selections
            individual_total = 0.0
            for meal_id in selected_meal_ids:
                qty = meal_quantities.get(meal_id, 1)
                
                # Get meal
                meal_result = await session.execute(
                    select(Meal).where(Meal.id == meal_id)
                )
                meal = meal_result.scalar_one_or_none()
                
                if meal:
                    selection = UserMealSelection(
                        meal_id=meal_id,
                        participant_id=participant.id,
                        quantity_selected=qty
                    )
                    session.add(selection)
                    
                    individual_total += float(meal.price) * float(qty)
            
            # Calculate totals
            # Calculate totals
            shared_portion = float(db_session.shared_total) / db_session.participant_count if db_session.participant_count > 0 else 0.0
            total = individual_total + shared_portion

            participant.individual_total = individual_total
            participant.shared_portion = shared_portion
            participant.total_amount = total
            
            await session.commit()
            
            await callback.message.edit_text("✅ Ovqatlaringiz saqlandi!")
            
            # Show summary
            await show_main_user_summary(callback.message, state, session_id)
            
            await callback.answer()
            logger.info(f"Main user {user.id} confirmed meals. Total: {total}")
            
        except Exception as e:
            logger.error(f"Error confirming meals: {e}", exc_info=True)
            await callback.answer("Xatolik yuz berdi", show_alert=True)


async def show_main_user_summary(message: Message, state: FSMContext, session_id: str):
    """Show summary to main user after selecting meals"""
    async with async_session_maker() as session:
        try:
            # Get session
            result = await session.execute(
                select(DBSession).where(DBSession.id == uuid.UUID(session_id))
            )
            db_session = result.scalar_one_or_none()
            
            # Get main user participant
            participant_result = await session.execute(
                select(SessionParticipant)
                .where(SessionParticipant.session_id == uuid.UUID(session_id))
                .where(SessionParticipant.is_creator == True)
            )
            participant = participant_result.scalar_one_or_none()
            
            if db_session and participant:
                summary = (
                    f"📊 <b>Sizning hisob-kitobingiz</b>\n\n"
                    f"🏪 <b>{db_session.restaurant_name}</b>\n"
                    f"💰 Jami check: {format_amount(db_session.total_amount)} so'm\n\n"
                    f"🍽 Individual ovqatlar: {format_amount(participant.individual_total)} so'm\n"
                    f"🤝 Shared ulush: {format_amount(participant.shared_portion)} so'm\n\n"
                    f"💵 <b>TO'LASH KERAK: {format_amount(participant.total_amount)} so'm</b>\n\n"
                    f"Session ID: <code>{session_id}</code>\n\n"
                    f"🎉 <b>Step 3 tugadi!</b>\n\n"
                    f"Keyingi step: Boshqa ishtirokchilarga link ulashish"
                )
                
                await message.answer(summary)
                
                # Clear state
                await state.clear()
        
        except Exception as e:
            logger.error(f"Error showing summary: {e}")