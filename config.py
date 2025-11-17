import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram Bot Token
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # OpenAI API Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Google Sheets Configuration
    GOOGLE_SHEETS_CREDENTIALS = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
    SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
    
    # Extraction Schema
    EXTRACTION_SCHEMA = {
        "type": "object",
        "properties": {
            "sender_name": {"type": "string"},
            "receiver_name": {"type": "string"},
            "account_number": {"type": "string"},
            "amount": {"type": "number"},
            "date_sent": {"type": "string", "format": "date"}
        },
        "required": ["sender_name", "receiver_name", "account_number", "amount", "date_sent"],
        "additionalProperties": False
    }
