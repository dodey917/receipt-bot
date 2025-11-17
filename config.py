import os
from dotenv import load_dotenv
import json

load_dotenv()

class Config:
    # Telegram Bot Token
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # OpenAI API Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Google Sheets Configuration
    GOOGLE_SHEETS_CREDENTIALS = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
    SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
    
    @classmethod
    def get_google_credentials(cls):
        """Parse Google Sheets credentials from environment variable"""
        if cls.GOOGLE_SHEETS_CREDENTIALS:
            return json.loads(cls.GOOGLE_SHEETS_CREDENTIALS)
        return None
