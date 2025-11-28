from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from database.models import Session as DBSession, Meal
from database.connection import async_session_maker
from states.receipt_states import ReceiptStates
from keyboards import (
    get_cancel_keyboard,
    build_categorization_keyboard,
    get_main_menu_keyboard,
    get_meal_edit_keyboard
)
from services import AIService
from utils import format_amount
import logging
import os
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)

router = Router()

# Create temp directory for images
TEMP_DIR = Path("temp_images")
TEMP_DIR.mkdir(exist_ok=True)

# Initialize AI service
ai_service = AIService()


@router.message(F.text == "📸 New Receipt")
async def new_receipt_button(message: Message, state: FSMContext):
    """Handle 'New Receipt' button click"""
    await state.set_state(ReceiptStates.waiting_for_receipt_image)
    
    await message.answer(
        "📸 <b>Check rasmini yuklang</b>\n\n"
        "Iltimos, restoran checkining rasmini yuboring.\n\n"
        "Bekor qilish uchun /cancel",
        reply_markup=get_cancel_keyboard()
    )
    logger.info(f"📸 User {message.from_user.id} started new receipt upload")


@router.message(ReceiptStates.waiting_for_receipt_image, F.photo)
async def process_receipt_image(message: Message, state: FSMContext):
    """Process uploaded receipt image with AI"""
    user = message.from_user
    photo = message.photo[-1]
    file_id = photo.file_id
    
    try:
        processing_msg = await message.answer("⏳ <b>AI check tahlil qilyapti...</b>")
        
        # Download photo
        bot = message.bot
        file = await bot.get_file(file_id)
        file_path = file.file_path
        local_path = TEMP_DIR / f"{user.id}_{photo.file_unique_id}.jpg"
        
        await bot.download_file(file_path, local_path)
        logger.info(f"📥 Downloaded image: {local_path}")
        
        # Analyze with AI
        ai_result = await ai_service.analyze_receipt(str(local_path))
        
        restaurant_name = ai_result.get('restaurant', 'Unknown')
        total_amount = ai_result.get('total', 0)
        items = ai_result.get('items', [])
        
        if not items or len(items) == 0:
            await processing_msg.delete()
            await message.answer("❌ <b>Ovqatlar topilmadi</b>\n\nIltimos, boshqa rasm yuboring.")
            os.remove(local_path)
            return
        
        # Create session in database
        async with async_session_maker() as session:
            new_session = DBSession(
                creator_user_id=user.id,
                creator_username=user.username,
                creator_first_name=user.first_name,
                receipt_image_id=file_id,
                receipt_text=str(ai_result),
                total_amount=total_amount,
                restaurant_name=restaurant_name
            )
            
            session.add(new_session)
            await session.flush()
            
            # Create meals from AI result
            for item in items:
                is_shared = item.get('type', 'INDIVIDUAL') == 'SHARED'
                
                meal = Meal(
                    session_id=new_session.id,
                    name=item['name'],
                    price=item['price'],
                    quantity_available=item['quantity'],
                    position=items.index(item) + 1,
                    is_shared=is_shared
                )
                session.add(meal)
            
            await session.commit()
            
            await state.update_data(session_id=str(new_session.id))
            await state.set_state(ReceiptStates.configuring_meals)
            
            await processing_msg.delete()
            
            # Show instruction
            await message.answer(
                f"<b>{restaurant_name}</b> - {format_amount(total_amount)} so'm\n\n"
                "Ofitsant, non, choy, salatga o'xshash HAMMA TO'LASHI shart bo'lgan mahsulotlarni belgilang 👇\n"
                "(✅ = Shared, ☐ = Individual)"
            )
            
            # Get meals and build keyboard
            meals_result = await session.execute(
                select(Meal)
                .where(Meal.session_id == new_session.id)
                .order_by(Meal.position)
            )
            meals = meals_result.scalars().all()
            
            keyboard = build_categorization_keyboard(meals, str(new_session.id))
            
            await message.answer(
                "👇 Ovqatlarni tanlang:",
                reply_markup=keyboard
            )
            
            logger.info(f"✅ Session {new_session.id} created with {len(items)} meals from AI")
        
        os.remove(local_path)
        
    except Exception as e:
        logger.error(f"❌ Error processing receipt: {e}", exc_info=True)
        await message.answer("❌ <b>Xatolik yuz berdi</b>\n\nIltimos, qaytadan urinib ko'ring.")
        if local_path.exists():
            os.remove(local_path)


@router.callback_query(F.data.startswith("toggle:"))
async def toggle_meal_shared(callback: CallbackQuery):
    """Toggle meal shared/individual"""
    meal_id = int(callback.data.split(":")[1])
    
    async with async_session_maker() as session:
        try:
            result = await session.execute(
                select(Meal).where(Meal.id == meal_id)
            )
            meal = result.scalar_one_or_none()
            
            if meal:
                meal.is_shared = not meal.is_shared
                await session.commit()
                
                # Rebuild keyboard
                meals_result = await session.execute(
                    select(Meal)
                    .where(Meal.session_id == meal.session_id)
                    .order_by(Meal.position)
                )
                meals = meals_result.scalars().all()
                
                keyboard = build_categorization_keyboard(meals, str(meal.session_id))
                await callback.message.edit_reply_markup(reply_markup=keyboard)
                
                status = "Shared" if meal.is_shared else "Individual"
                await callback.answer(f"✅ {status}")
                logger.info(f"Meal {meal_id} toggled to {status}")
        
        except Exception as e:
            logger.error(f"Error toggling meal: {e}")
            await callback.answer("Xatolik", show_alert=True)


@router.callback_query(F.data.startswith("edit:"))
async def show_meal_edit_menu(callback: CallbackQuery):
    """Show edit menu for a meal"""
    meal_id = int(callback.data.split(":")[1])
    
    async with async_session_maker() as session:
        try:
            result = await session.execute(
                select(Meal).where(Meal.id == meal_id)
            )
            meal = result.scalar_one_or_none()
            
            if meal:
                await callback.message.answer(
                    f"✏️ <b>Tahrirlash: {meal.name}</b>\n\n"
                    f"Narxi: {format_amount(meal.price)} so'm\n"
                    f"Miqdori: {meal.quantity_available}\n\n"
                    f"Nimani o'zgartirmoqchisiz?",
                    reply_markup=get_meal_edit_keyboard(meal.id)
                )
                await callback.answer()
        
        except Exception as e:
            logger.error(f"Error showing edit menu: {e}")
            await callback.answer("Xatolik", show_alert=True)


@router.callback_query(F.data.startswith("edit_name_"))
async def edit_meal_name(callback: CallbackQuery, state: FSMContext):
    """Start editing meal name"""
    meal_id = int(callback.data.split("_")[2])
    
    await state.update_data(editing_meal_id=meal_id, editing_field="name")
    await state.set_state(ReceiptStates.editing_meal)
    
    await callback.message.answer(
        "✏️ Yangi nomini kiriting:",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_price_"))
async def edit_meal_price(callback: CallbackQuery, state: FSMContext):
    """Start editing meal price"""
    meal_id = int(callback.data.split("_")[2])
    
    await state.update_data(editing_meal_id=meal_id, editing_field="price")
    await state.set_state(ReceiptStates.editing_meal)
    
    await callback.message.answer(
        "💰 Yangi narxini kiriting (faqat raqam):\nMasalan: 35000",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_qty_"))
async def edit_meal_quantity(callback: CallbackQuery, state: FSMContext):
    """Start editing meal quantity"""
    meal_id = int(callback.data.split("_")[2])
    
    await state.update_data(editing_meal_id=meal_id, editing_field="quantity")
    await state.set_state(ReceiptStates.editing_meal)
    
    await callback.message.answer(
        "🔢 Yangi miqdorini kiriting:\nMasalan: 2",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(ReceiptStates.editing_meal)
async def process_meal_edit(message: Message, state: FSMContext):
    """Process meal editing"""
    data = await state.get_data()
    meal_id = data.get('editing_meal_id')
    field = data.get('editing_field')
    new_value = message.text.strip()
    
    async with async_session_maker() as session:
        try:
            result = await session.execute(
                select(Meal).where(Meal.id == meal_id)
            )
            meal = result.scalar_one_or_none()
            
            if not meal:
                await message.answer("❌ Ovqat topilmadi")
                return
            
            if field == "name":
                if len(new_value) < 1 or len(new_value) > 100:
                    await message.answer("❌ Nom 1-100 belgi orasida bo'lishi kerak")
                    return
                meal.name = new_value
                
            elif field == "price":
                try:
                    price = float(new_value.replace(" ", "").replace(",", ""))
                    if price < 0 or price > 10000000:
                        await message.answer("❌ Narx noto'g'ri")
                        return
                    meal.price = price
                except:
                    await message.answer("❌ Narxni faqat raqam kiriting")
                    return
                    
            elif field == "quantity":
                try:
                    qty = int(new_value)
                    if qty < 1 or qty > 100:
                        await message.answer("❌ Miqdor 1-100 orasida bo'lishi kerak")
                        return
                    meal.quantity_available = qty
                except:
                    await message.answer("❌ Miqdorni faqat raqam kiriting")
                    return
            
            await session.commit()
            
            # Recalculate session total
            session_result = await session.execute(
                select(DBSession).where(DBSession.id == meal.session_id)
            )
            db_session = session_result.scalar_one_or_none()
            
            if db_session:
                meals_result = await session.execute(
                    select(Meal).where(Meal.session_id == db_session.id)
                )
                all_meals = meals_result.scalars().all()
                db_session.total_amount = sum(m.price * m.quantity_available for m in all_meals)
                await session.commit()
            
            await message.answer(f"✅ O'zgartirildi!\n\nYangi qiymat: {new_value}")
            
            await state.set_state(ReceiptStates.configuring_meals)
            await state.update_data(editing_meal_id=None, editing_field=None)
            
            logger.info(f"Meal {meal_id} {field} updated to {new_value}")
            
        except Exception as e:
            logger.error(f"Error updating meal: {e}")
            await message.answer("❌ Xatolik yuz berdi")


@router.callback_query(F.data.startswith("delete_"))
async def delete_meal(callback: CallbackQuery, state: FSMContext):
    """Delete a meal"""
    meal_id = int(callback.data.split("_")[1])
    
    async with async_session_maker() as session:
        try:
            result = await session.execute(
                select(Meal).where(Meal.id == meal_id)
            )
            meal = result.scalar_one_or_none()
            
            if meal:
                session_id = meal.session_id
                meal_name = meal.name
                await session.delete(meal)
                await session.commit()
                
                # Recalculate total
                session_result = await session.execute(
                    select(DBSession).where(DBSession.id == session_id)
                )
                db_session = session_result.scalar_one_or_none()
                
                if db_session:
                    meals_result = await session.execute(
                        select(Meal).where(Meal.session_id == session_id)
                    )
                    all_meals = meals_result.scalars().all()
                    db_session.total_amount = sum(m.price * m.quantity_available for m in all_meals)
                    await session.commit()
                
                # Get FSM data
                data = await state.get_data()
                stored_session_id = data.get('session_id')
                
                # Rebuild main keyboard
                if str(session_id) == stored_session_id:
                    meals_result = await session.execute(
                        select(Meal)
                        .where(Meal.session_id == session_id)
                        .order_by(Meal.position)
                    )
                    remaining_meals = meals_result.scalars().all()
                    
                    # Find and update the main meals message
                    # (This would require storing message_id in FSM)
                    
                await callback.message.edit_text(f"🗑 <s>{meal_name}</s> - O'chirildi")
                await callback.answer("O'chirildi")
                logger.info(f"Meal {meal_id} deleted")
        
        except Exception as e:
            logger.error(f"Error deleting meal: {e}")
            await callback.answer("Xatolik", show_alert=True)


@router.callback_query(F.data == "back_to_meals")
async def back_to_meals(callback: CallbackQuery):
    """Close edit menu"""
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "meals_done")
async def meals_done_proceed(callback: CallbackQuery, state: FSMContext):
    """Proceed to participant count"""
    await callback.message.edit_text("✅ Ovqatlar sozlandi!")
    
    await state.set_state(ReceiptStates.entering_participant_count)
    
    await callback.message.answer(
        "👥 <b>Necha kishi ovqatlandingiz?</b>\n\n"
        "O'zingizni ham hisobga oling.\n"
        "Masalan: agar 3 kishi bo'lsangiz, 3 deb yozing.",
        reply_markup=get_cancel_keyboard()
    )
    
    await callback.answer()


@router.callback_query(F.data == "cancel_session")
async def cancel_session(callback: CallbackQuery, state: FSMContext):
    """Cancel session"""
    data = await state.get_data()
    session_id = data.get('session_id')
    
    if session_id:
        async with async_session_maker() as session:
            try:
                result = await session.execute(
                    select(DBSession).where(DBSession.id == uuid.UUID(session_id))
                )
                db_session = result.scalar_one_or_none()
                if db_session:
                    await session.delete(db_session)
                    await session.commit()
            except Exception as e:
                logger.error(f"Error deleting session: {e}")
    
    await state.clear()
    
    await callback.message.edit_text("❌ Bekor qilindi")
    
    await callback.message.answer(
        "Yangi check yuklash uchun 📸 New Receipt tugmasini bosing.",
        reply_markup=get_main_menu_keyboard()
    )
    
    await callback.answer()


@router.message(ReceiptStates.waiting_for_receipt_image)
async def invalid_receipt_format(message: Message):
    """Handle non-photo"""
    await message.answer(
        "❌ Iltimos, rasm yuboring.\n\n"
        "Rasm yuklash uchun:\n"
        "1. 📎 ikonkasini bosing\n"
        "2. Galereya yoki kamerani tanlang\n"
        "3. Check rasmini yuboring"
    )