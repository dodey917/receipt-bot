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
            try:
                return json.loads(cls.GOOGLE_SHEETS_CREDENTIALS)
            except json.JSONDecodeError:
                return None
        return None
    
    @classmethod
    def validate_config(cls):
        """Validate required configuration"""
        errors = []
        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN is required")
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required")
        if not cls.SPREADSHEET_ID:
            errors.append("SPREADSHEET_ID is required")
        if not cls.get_google_credentials():
            errors.append("GOOGLE_SHEETS_CREDENTIALS is required or invalid")
        
        if errors:
            raise ValueError("Configuration errors: " + "; ".join(errors))
