from typing import Dict, List
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from database.models import Session as DBSession, Meal, SessionParticipant
from database.connection import async_session_maker
from states.receipt_states import ReceiptStates
from keyboards import get_cancel_keyboard, get_yes_no_keyboard, build_meal_selection_keyboard
from utils import format_amount
import logging
import uuid

logger = logging.getLogger(__name__)

router = Router()


def calculate_totals(meals: List, participant_count: int) -> Dict:
    """Calculate shared and individual totals"""
    shared_total = 0.0
    individual_total = 0.0
    
    for meal in meals:
        meal_total = float(meal.price) * float(meal.quantity_available)
        
        if meal.is_shared:
            shared_total += meal_total
        else:
            individual_total += meal_total
    
    shared_per_person = shared_total / participant_count if participant_count > 0 else 0
    
    return {
        'shared_total': shared_total,
        'individual_total': individual_total,
        'shared_per_person': shared_per_person,
        'total': shared_total + individual_total
    }


@router.message(ReceiptStates.entering_restaurant_name)
async def process_restaurant_name(message: Message, state: FSMContext):
    """Handle restaurant name input"""
    restaurant_name = message.text.strip()
    
    if len(restaurant_name) < 2 or len(restaurant_name) > 100:
        await message.answer(
            "❌ Restoran nomi 2-100 belgi orasida bo'lishi kerak.\n"
            "Iltimos, qaytadan kiriting:"
        )
        return
    
    data = await state.get_data()
    session_id = data.get('session_id')
    
    async with async_session_maker() as session:
        try:
            result = await session.execute(
                select(DBSession).where(DBSession.id == uuid.UUID(session_id))
            )
            db_session = result.scalar_one_or_none()
            
            if db_session:
                db_session.restaurant_name = restaurant_name
                await session.commit()
                
                await message.answer(f"✅ Restoran nomi saqlandi: <b>{restaurant_name}</b>")
                
                await state.set_state(ReceiptStates.entering_participant_count)
                
                await message.answer(
                    "👥 <b>Necha kishi ovqatlandingiz?</b>\n\n"
                    "O'zingizni ham hisobga oling.\n"
                    "Masalan: agar 3 kishi bo'lsangiz, 3 deb yozing.",
                    reply_markup=get_cancel_keyboard()
                )
                
                logger.info(f"Restaurant name set: {restaurant_name} for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error saving restaurant name: {e}")
            await message.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.")


@router.message(ReceiptStates.entering_participant_count)
async def process_participant_count(message: Message, state: FSMContext):
    """Handle participant count input"""
    try:
        count = int(message.text.strip())
        
        if count < 2 or count > 50:
            await message.answer(
                "❌ Ishtirokchilar soni 2 dan 50 gacha bo'lishi kerak.\n"
                "Iltimos, to'g'ri raqam kiriting:"
            )
            return
        
        data = await state.get_data()
        session_id = data.get('session_id')
        
        async with async_session_maker() as session:
            try:
                result = await session.execute(
                    select(DBSession).where(DBSession.id == uuid.UUID(session_id))
                )
                db_session = result.scalar_one_or_none()
                
                if db_session:
                    db_session.participant_count = count
                    
                    # Calculate totals
                    meals_result = await session.execute(
                        select(Meal).where(Meal.session_id == uuid.UUID(session_id))
                    )
                    meals = meals_result.scalars().all()
                    
                    totals = calculate_totals(meals, count)
                    db_session.shared_total = totals['shared_total']
                    db_session.individual_total = totals['individual_total']
                    
                    await session.commit()
                    
                    await message.answer(f"✅ Ishtirokchilar soni: <b>{count} kishi</b>")
                    
                    await state.set_state(ReceiptStates.entering_card_number)
                    
                    await message.answer(
                        "💳 <b>Karta raqamingizni kiriting</b>\n\n"
                        "Boshqalar sizga pul o'tkazishi uchun.\n"
                        "Masalan: 8600 1234 5678 9012",
                        reply_markup=get_cancel_keyboard()
                    )
                    
                    logger.info(f"Participant count set: {count} for session {session_id}")
                
            except Exception as e:
                logger.error(f"Error saving participant count: {e}")
                await message.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.")
        
    except ValueError:
        await message.answer(
            "❌ Iltimos, faqat raqam kiriting.\n"
            "Masalan: 3"
        )


@router.message(ReceiptStates.entering_card_number)
async def process_card_number(message: Message, state: FSMContext):
    """Handle card number input"""
    card_number = message.text.strip()
    
    digits_only = ''.join(filter(str.isdigit, card_number))
    
    if len(digits_only) < 16 or len(digits_only) > 19:
        await message.answer(
            "❌ Karta raqami 16-19 raqamdan iborat bo'lishi kerak.\n"
            "Iltimos, to'g'ri karta raqamini kiriting:"
        )
        return
    
    data = await state.get_data()
    session_id = data.get('session_id')
    
    async with async_session_maker() as session:
        try:
            result = await session.execute(
                select(DBSession).where(DBSession.id == uuid.UUID(session_id))
            )
            db_session = result.scalar_one_or_none()
            
            if db_session:
                db_session.card_number = card_number
                await session.commit()
                
                await message.answer(f"✅ Karta raqami saqlandi: <code>{card_number}</code>")
                
                await state.set_state(ReceiptStates.checking_delivery)
                
                await message.answer(
                    "🚚 <b>Delivery bor edimi?</b>\n\n"
                    "Ya'ni, kimdir uchun ofisga olib kelgan ovqat bor edimi?",
                    reply_markup=get_yes_no_keyboard("delivery_yes", "delivery_no")
                )
                
                logger.info(f"Card number set for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error saving card number: {e}")
            await message.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.")


@router.callback_query(F.data == "delivery_yes")
async def delivery_yes_callback(callback: CallbackQuery, state: FSMContext):
    """Handle delivery yes"""
    data = await state.get_data()
    session_id = data.get('session_id')
    
    async with async_session_maker() as session:
        try:
            result = await session.execute(
                select(DBSession).where(DBSession.id == uuid.UUID(session_id))
            )
            db_session = result.scalar_one_or_none()
            
            if db_session:
                db_session.has_delivery = True
                await session.commit()
                
                await callback.message.edit_text("✅ Delivery bor deb belgilandi")
                
                # NEW: Move to meal selection
                await show_own_meal_selection(callback.message, state, session_id)
                
                await callback.answer()
                logger.info(f"Delivery enabled for session {session_id}")
        
        except Exception as e:
            logger.error(f"Error setting delivery: {e}")
            await callback.answer("Xatolik", show_alert=True)


@router.callback_query(F.data == "delivery_no")
async def delivery_no_callback(callback: CallbackQuery, state: FSMContext):
    """Handle delivery no"""
    data = await state.get_data()
    session_id = data.get('session_id')
    
    async with async_session_maker() as session:
        try:
            result = await session.execute(
                select(DBSession).where(DBSession.id == uuid.UUID(session_id))
            )
            db_session = result.scalar_one_or_none()
            
            if db_session:
                db_session.has_delivery = False
                await session.commit()
                
                await callback.message.edit_text("✅ Delivery yo'q deb belgilandi")
                
                # NEW: Move to meal selection
                await show_own_meal_selection(callback.message, state, session_id)
                
                await callback.answer()
                logger.info(f"No delivery for session {session_id}")
        
        except Exception as e:
            logger.error(f"Error setting delivery: {e}")
            await callback.answer("Xatolik", show_alert=True)


async def show_own_meal_selection(message: Message, state: FSMContext, session_id: str):
    """Show individual meal selection for main user"""
    async with async_session_maker() as session:
        try:
            # Get only individual meals (not shared)
            result = await session.execute(
                select(Meal)
                .where(Meal.session_id == uuid.UUID(session_id))
                .where(Meal.is_shared == False)
                .order_by(Meal.position)
            )
            individual_meals = result.scalars().all()
            
            if not individual_meals:
                await message.answer(
                    "ℹ️ <b>Individual ovqatlar yo'q</b>\n\n"
                    "Barcha ovqatlar shared deb belgilangan.\n"
                    "Keyingi stepga o'tilmoqda..."
                )
                # TODO: Skip to next step (Step 4: Share link)
                return
            
            # Set state
            await state.set_state(ReceiptStates.selecting_own_meals)
            await state.update_data(
                selected_meal_ids=set(),
                meal_quantities={}
            )
            
            # Build keyboard (without edit buttons)
            keyboard = build_meal_selection_keyboard(individual_meals)
            
            await message.answer(
                "👇 <b>O'zingiz nimalar yeganingizni tanlang:</b>\n\n"
                "Ovqatni bosing, keyin miqdorini sozlang.",
                reply_markup=keyboard
            )
            
            logger.info(f"Showing {len(individual_meals)} individual meals to main user")
            
        except Exception as e:
            logger.error(f"Error showing meal selection: {e}", exc_info=True)
            await message.answer("❌ Xatolik yuz berdi.")