import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Validate required settings
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env file")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env file")

# Receipt parsing settings
CURRENCY_SYMBOL = "so'm"

# Telegram file size limit
MAX_FILE_SIZE_MB = 20