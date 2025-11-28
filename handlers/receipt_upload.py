from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database.models import Session as DBSession
from database.connection import async_session_maker
from states.receipt_states import ReceiptStates
from keyboards import get_cancel_keyboard, get_receipt_actions_keyboard
from services import OCRService
from utils import format_receipt_text
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

router = Router()

# Create temp directory for images
TEMP_DIR = Path("temp_images")
TEMP_DIR.mkdir(exist_ok=True)


@router.message(F.text == "📸 New Receipt")
async def new_receipt_button(message: Message, state: FSMContext):
    """Handle 'New Receipt' button click"""
    await state.set_state(ReceiptStates.waiting_for_receipt_image)
    
    await message.answer(
        "📸 <b>Check rasmini yuklang</b>\n\n"
        "Iltimos, restoran checkining rasmini yuboring.\n\n"
        "📝 <b>Maslahat:</b>\n"
        "• Rasm aniq va yorug' bo'lsin\n"
        "• Barcha matnlar o'qilishi kerak\n"
        "• Check to'g'ri yo'nalishda bo'lsin\n\n"
        "Bekor qilish uchun /cancel",
        reply_markup=get_cancel_keyboard()
    )
    logger.info(f"📸 User {message.from_user.id} started new receipt upload")


@router.message(ReceiptStates.waiting_for_receipt_image, F.photo)
async def process_receipt_image(message: Message, state: FSMContext):
    """Process uploaded receipt image"""
    user = message.from_user
    
    # Get the largest photo
    photo = message.photo[-1]
    file_id = photo.file_id
    
    try:
        # Send processing message
        processing_msg = await message.answer(
            "⏳ <b>Check o'qilmoqda...</b>\n\n"
            "Bu bir necha soniya vaqt olishi mumkin.\n"
            "Iltimos, kuting..."
        )
        
        # Download photo
        bot = message.bot
        file = await bot.get_file(file_id)
        file_path = file.file_path
        
        # Create local file path
        local_path = TEMP_DIR / f"{user.id}_{photo.file_unique_id}.jpg"
        
        # Download file
        await bot.download_file(file_path, local_path)
        logger.info(f"📥 Downloaded image: {local_path}")
        
        # Perform OCR
        extracted_text = await OCRService.extract_text_from_image(str(local_path))
        
        # Delete processing message
        await processing_msg.delete()
        
        if not extracted_text or len(extracted_text.strip()) < 10:
            await message.answer(
                "❌ <b>Matn topilmadi</b>\n\n"
                "Rasm sifati yomon bo'lishi mumkin.\n"
                "Iltimos, yanada aniq rasm yuboring."
            )
            # Clean up
            os.remove(local_path)
            return
        
        # Store in FSM
        await state.update_data(
            receipt_image_id=file_id,
            receipt_text=extracted_text,
            image_path=str(local_path)
        )
        
        # Format text for display
        formatted_text = format_receipt_text(extracted_text)
        
        # Move to next state
        await state.set_state(ReceiptStates.viewing_extracted_text)
        
        # Send extracted text
        await message.answer(
            f"✅ <b>Matn muvaffaqiyatli o'qildi!</b>\n\n"
            f"📝 <b>O'qilgan matn:</b>\n\n"
            f"<code>{formatted_text[:3000]}</code>\n\n"  # Telegram message limit
            f"{'...(matn juda uzun)' if len(formatted_text) > 3000 else ''}\n\n"
            f"Matn to'g'rimi?",
            reply_markup=get_receipt_actions_keyboard()
        )
        
        logger.info(f"✅ OCR completed for user {user.id}. Extracted {len(extracted_text)} characters")
        
    except Exception as e:
        logger.error(f"❌ Error processing receipt image: {e}", exc_info=True)
        await message.answer(
            "❌ <b>Xatolik yuz berdi</b>\n\n"
            "Rasmni qayta ishlashda muammo bo'ldi.\n"
            "Iltimos, qaytadan urinib ko'ring."
        )
        
        # Clean up on error
        if local_path.exists():
            os.remove(local_path)


@router.message(ReceiptStates.waiting_for_receipt_image)
async def invalid_receipt_format(message: Message):
    """Handle non-photo messages when waiting for receipt"""
    await message.answer(
        "❌ Iltimos, rasm yuboring.\n\n"
        "Rasm yuklash uchun:\n"
        "1. 📎 ikonkasini bosing\n"
        "2. Galereya yoki kamerani tanlang\n"
        "3. Check rasmini yuboring"
    )


@router.callback_query(F.data == "confirm_receipt_text")
async def confirm_receipt_text(callback: CallbackQuery, state: FSMContext):
    """Handle receipt text confirmation"""
    data = await state.get_data()
    receipt_text = data.get('receipt_text')
    receipt_image_id = data.get('receipt_image_id')
    
    # Save to database
    async with async_session_maker() as session:
        try:
            user = callback.from_user
            
            new_session = DBSession(
                creator_user_id=user.id,
                creator_username=user.username,
                creator_first_name=user.first_name,
                receipt_image_id=receipt_image_id,
                receipt_text=receipt_text
            )
            
            session.add(new_session)
            await session.commit()
            
            # Store session_id in FSM for later use
            await state.update_data(session_id=str(new_session.id))
            
            await callback.message.edit_text(
                "✅ <b>Matn tasdiqlandi!</b>\n\n"
                f"Session ID: <code>{new_session.id}</code>\n\n"
                "Keyingi qadamda ovqatlar ro'yxatini tahlil qilamiz..."
            )
            
            await callback.answer("Matn saqlandi!")
            
            logger.info(f"💾 Session {new_session.id} created for user {user.id}")
            
            # TODO: Next step - parse meals and continue
            # For now, just show success
            await callback.message.answer(
                "🎉 <b>Step 1 tugadi!</b>\n\n"
                "Keyingi step'larda:\n"
                "• Matnni tahrirlash\n"
                "• Ovqatlarni ajratish\n"
                "• Ma'lumot to'ldirish\n\n"
                "Hozircha bu Step 1 testi."
            )
            
        except Exception as e:
            logger.error(f"❌ Error saving session: {e}", exc_info=True)
            await callback.message.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.")


@router.callback_query(F.data == "edit_receipt_text")
async def edit_receipt_text(callback: CallbackQuery):
    """Handle edit receipt text request"""
    # TODO: Implement in Step 2
    await callback.answer("Bu funksiya Step 2da qo'shiladi", show_alert=True)


@router.callback_query(F.data == "reupload_receipt")
async def reupload_receipt(callback: CallbackQuery, state: FSMContext):
    """Handle receipt re-upload request"""
    await state.set_state(ReceiptStates.waiting_for_receipt_image)
    
    await callback.message.edit_text(
        "📸 Yangi rasm yuklang"
    )
    
    await callback.message.answer(
        "📸 <b>Yangi check rasmini yuklang</b>\n\n"
        "Iltimos, restoran checkining rasmini yuboring.",
        reply_markup=get_cancel_keyboard()
    )
    
    await callback.answer("Qaytadan yuklash")


@router.callback_query(F.data == "cancel_session")
async def cancel_session(callback: CallbackQuery, state: FSMContext):
    """Handle session cancellation"""
    from keyboards import get_main_menu_keyboard
    
    await state.clear()
    
    await callback.message.edit_text(
        "❌ Jarayon bekor qilindi."
    )
    
    await callback.message.answer(
        "Yangi check yuklash uchun 📸 New Receipt tugmasini bosing.",
        reply_markup=get_main_menu_keyboard()
    )
    
    await callback.answer("Bekor qilindi")