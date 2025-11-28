import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

# Validate required settings
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env file")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file")

# OCR Configuration
OCR_LANGUAGES = ['ru', 'en']  # Russian and English (covers Uzbek Cyrillic)
OCR_GPU = False  # Set to True if you have CUDA GPU

# Receipt parsing settings
CURRENCY_SYMBOL = "so'm"
ALTERNATIVE_CURRENCY_SYMBOLS = ["sum", "сум", "сўм"]

# Telegram file size limit
MAX_FILE_SIZE_MB = 20