import logging
import sys
import os
import tempfile
import asyncio
import base64
import json
from datetime import datetime
from typing import Optional

# Import modern versions
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

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
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing Google credentials: {e}")
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

class TransactionData:
    def __init__(self, sender_name, receiver_name, account_number, amount, date_sent):
        self.sender_name = sender_name
        self.receiver_name = receiver_name
        self.account_number = account_number
        self.amount = amount
        self.date_sent = date_sent
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            sender_name=data.get('sender_name', 'Unknown'),
            receiver_name=data.get('receiver_name', 'Unknown'),
            account_number=data.get('account_number', 'Unknown'),
            amount=float(data.get('amount', 0.0)),
            date_sent=data.get('date_sent', 'Unknown')
        )

class OCRProcessor:
    def __init__(self):
        if not Config.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
    
    def extract_data(self, image_path):
        """Extract structured data from receipt image using GPT-4 Vision"""
        try:
            logger.info("Starting OCR processing...")
            
            # Read image file directly as binary
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
            
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            response = self.client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "system",
                        "content": """Extract transaction details from receipt images and return ONLY valid JSON with these fields: sender_name, receiver_name, account_number, amount, date_sent. Return ONLY JSON, no other text."""
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text", 
                                "text": "Extract transaction data from this receipt image and return ONLY valid JSON:"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.0
            )
            
            # Extract JSON from response
            raw_content = response.choices[0].message.content.strip()
            logger.info(f"Raw API response: {raw_content}")
            
            # Clean response and extract JSON
            json_str = self._extract_json_from_response(raw_content)
            
            if not json_str:
                return {"success": False, "error": "No valid JSON found", "data": None}
            
            # Parse data
            extracted_data = json.loads(json_str)
            transaction_data = TransactionData.from_dict(extracted_data)
            
            logger.info("✅ OCR processing completed successfully")
            return {"success": True, "data": transaction_data, "error": None}
            
        except Exception as e:
            logger.error(f"❌ Error in data extraction: {str(e)}")
            return {"success": False, "error": str(e), "data": None}
    
    def _extract_json_from_response(self, text):
        """Extract JSON string from API response"""
        try:
            # Try to find JSON object in the response
            start_idx = text.find('{')
            end_idx = text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != 0:
                json_str = text[start_idx:end_idx]
                # Validate it's proper JSON
                json.loads(json_str)
                return json_str
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from: {text}")
        
        return None

class GoogleSheetsHandler:
    def __init__(self):
        self.scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        self.client = None
        self.sheet = None
        self._setup_client()
    
    def _setup_client(self):
        """Setup Google Sheets client"""
        try:
            creds_dict = Config.get_google_credentials()
            if not creds_dict:
                raise ValueError("Google Sheets credentials not found")
                
            creds = Credentials.from_service_account_info(creds_dict, scopes=self.scope)
            self.client = gspread.authorize(creds)
            self.sheet = self.client.open_by_key(Config.SPREADSHEET_ID).sheet1
            logger.info("✅ Google Sheets client setup successfully")
        except Exception as e:
            logger.error(f"❌ Google Sheets setup failed: {str(e)}")
            raise
    
    def append_transaction(self, transaction_data):
        """Append transaction data to Google Sheet"""
        try:
            # Prepare row data
            row = [
                transaction_data.sender_name,
                transaction_data.receiver_name,
                transaction_data.account_number,
                str(transaction_data.amount),
                transaction_data.date_sent,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ]
            
            # Append to sheet
            self.sheet.append_row(row)
            logger.info("✅ Successfully appended transaction to Google Sheets")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to append to Google Sheets: {str(e)}")
            return False

class ReceiptBot:
    def __init__(self):
        try:
            logger.info("Initializing ReceiptBot...")
            Config.validate_config()
            self.ocr_processor = OCRProcessor()
            self.sheets_handler = GoogleSheetsHandler()
            logger.info("✅ ReceiptBot initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize ReceiptBot: {str(e)}")
            raise
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message when command /start is issued."""
        logger.info(f"Start command received from user {update.message.from_user.id}")
        welcome_text = """
🤖 Advanced Receipt Processing Bot

I can extract structured data from your receipt images!

Supported Documents:
• Bank transfer receipts
• Money transfer slips  
• Payment confirmations

How to use:
1. Send me a clear image of your receipt
2. I'll extract: sender, receiver, account number, amount, and date
3. Data will be saved to our database

Send me a receipt image to get started!
        """
        await update.message.reply_text(welcome_text)
        logger.info("✅ Start message sent successfully")
    
    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming receipt images"""
        user = update.message.from_user
        logger.info(f"📸 Image received from user {user.id}")
        
        # Send processing message
        processing_msg = await update.message.reply_text(
            "🔄 Processing your receipt... This may take 10-20 seconds."
        )
        
        temp_file_path = None
        try:
            # Download image (get the highest resolution)
            photo_file = await update.message.photo[-1].get_file()
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                temp_file_path = temp_file.name
            
            await photo_file.download_to_drive(temp_file_path)
            logger.info(f"✅ Image downloaded to {temp_file_path}")
            
            # Process image (run in thread to avoid blocking)
            extraction_result = await asyncio.get_event_loop().run_in_executor(
                None, self.ocr_processor.extract_data, temp_file_path
            )
            
            if not extraction_result["success"]:
                error_text = f"❌ Extraction failed: {extraction_result['error']}"
                if "rate limit" in extraction_result['error'].lower():
                    error_text += "\nPlease try again in a minute."
                await processing_msg.edit_text(error_text)
                return
            
            # Save to Google Sheets
            save_success = self.sheets_handler.append_transaction(extraction_result["data"])
            
            if not save_success:
                await processing_msg.edit_text(
                    "✅ Data extracted but failed to save to database. Please contact admin."
                )
                return
            
            # Send success message with extracted data
            success_text = self._format_success_message(extraction_result["data"])
            await processing_msg.edit_text(success_text)
            logger.info("✅ Receipt processed and saved successfully")
            
        except Exception as e:
            logger.error(f"❌ Error processing image: {str(e)}")
            await processing_msg.edit_text(
                "❌ An error occurred while processing your image. Please try again with a clearer image."
            )
        finally:
            # Clean up temp file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.info("✅ Temporary file cleaned up")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to delete temp file: {e}")
    
    def _format_success_message(self, data):
        """Format extracted data into a nice message"""
        return f"""
✅ Receipt Processed Successfully!

📋 Extracted Data:
┌──────────────────────────────
│ 👤 Sender: {data.sender_name}
│ 👤 Receiver: {data.receiver_name}  
│ 🔢 Account: {data.account_number}
│ 💰 Amount: ${data.amount:,.2f}
│ 📅 Date: {data.date_sent}
└──────────────────────────────

💾 Data has been saved to the database.
        """
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")

async def main():
    """Start the bot"""
    try:
        logger.info("🚀 Starting Receipt Bot...")
        
        # Validate configuration first
        Config.validate_config()
        logger.info("✅ Configuration validated")
        
        # Create bot instance
        receipt_bot = ReceiptBot()
        
        # Create application
        application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
        logger.info("✅ Application created")
        
        # Add handlers
        application.add_handler(CommandHandler("start", receipt_bot.start))
        application.add_handler(MessageHandler(filters.PHOTO, receipt_bot.handle_image))
        application.add_error_handler(receipt_bot.error_handler)
        
        # Start bot
        logger.info("✅ Starting bot polling...")
        print("🤖 Bot is starting on Render...")
        
        # Run the bot
        await application.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {str(e)}")
        print(f"❌ Bot failed to start: {e}")

if __name__ == '__main__':
    asyncio.run(main())
