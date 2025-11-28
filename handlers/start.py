from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from keyboards import get_main_menu_keyboard
import logging

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    """Handle /start command"""
    await state.clear()
    
    user = message.from_user
    
    await message.answer(
        f"👋 Salom, {user.first_name}!\n\n"
        f"🍽 <b>Restaurant Check Splitter Bot</b>ga xush kelibsiz!\n\n"
        f"Men sizga check bo'lishishda yordam beraman:\n\n"
        f"📸 Check rasmini yuklang\n"
        f"✅ Men matnni o'qib olaman\n"
        f"👥 Ishtirokchilar o'z ovqatlarini tanlaydi\n"
        f"💰 Har kim qancha to'lashini ko'rsataman\n\n"
        f"Boshlash uchun <b>📸 New Receipt</b> tugmasini bosing!",
        reply_markup=get_main_menu_keyboard()
    )
    logger.info(f"✨ User {user.id} started the bot")


@router.message(Command("help"))
async def help_command(message: Message, state: FSMContext):
    """Handle /help command"""
    await state.clear()
    
    help_text = (
        "📚 <b>Yordam</b>\n\n"
        "<b>Qanday ishlaydi:</b>\n\n"
        "1️⃣ <b>Check yuklang</b>\n"
        "   Check rasmini botga yuboring\n\n"
        "2️⃣ <b>Matnni tekshiring</b>\n"
        "   Bot matnni o'qiydi, xato bo'lsa tuzating\n\n"
        "3️⃣ <b>Ma'lumot kiriting</b>\n"
        "   • Necha kishi ovqatlanganini\n"
        "   • Karta raqamini\n"
        "   • Delivery bormi yo'qmi\n\n"
        "4️⃣ <b>Ovqatlarni tanlang</b>\n"
        "   • Umumiy ovqatlarni belgilang\n"
        "   • O'zingiz nimalar yeganingizni tanlang\n\n"
        "5️⃣ <b>Link ulashing</b>\n"
        "   Boshqa ishtirokchilar linkni bosib\n"
        "   o'z ovqatlarini tanlaydi\n\n"
        "6️⃣ <b>To'lovlarni kuzating</b>\n"
        "   Har kim qancha to'lashini ko'radi\n\n"
        "<b>Buyruqlar:</b>\n"
        "/start - Botni qayta boshlash\n"
        "/help - Yordam\n"
        "/cancel - Bekor qilish"
    )
    
    await message.answer(help_text)


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    """Handle /cancel command"""
    current_state = await state.get_state()
    
    if current_state is None:
        await message.answer(
            "✅ Hech qanday faol jarayon yo'q.\n\n"
            "Yangi check yuklash uchun 📸 New Receipt tugmasini bosing."
        )
    else:
        await state.clear()
        await message.answer(
            "❌ Jarayon bekor qilindi.\n\n"
            "Qaytadan boshlash uchun 📸 New Receipt tugmasini bosing.",
            reply_markup=get_main_menu_keyboard()
        )
        logger.info(f"🚫 User {message.from_user.id} cancelled from state: {current_state}")