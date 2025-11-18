import os
import logging
import io
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Import our new modules
from ai_processor import analyze_receipt
from schemas import ReceiptExtraction
import gspread
from google.oauth2.service_account import Credentials

# Load environment variables
load_dotenv()

# --- Configuration ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class GoogleSheetsHandler:
    def __init__(self):
        self.scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        self.client = None
        self.sheet = None
        self._setup_client()
    
    def _setup_client(self):
        """Setup Google Sheets client using environment variable"""
        try:
            # Get credentials from environment variable
            creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
            if not creds_json:
                raise ValueError("GOOGLE_SHEETS_CREDENTIALS environment variable is required")
            
            creds_dict = json.loads(creds_json)
            creds = Credentials.from_service_account_info(creds_dict, scopes=self.scope)
            self.client = gspread.authorize(creds)
            
            # Get spreadsheet ID from environment
            spreadsheet_id = os.getenv("SPREADSHEET_ID")
            if not spreadsheet_id:
                raise ValueError("SPREADSHEET_ID environment variable is required")
            
            self.sheet = self.client.open_by_key(spreadsheet_id).sheet1
            logger.info("✅ Google Sheets client setup successfully")
            
        except Exception as e:
            logger.error(f"❌ Google Sheets setup failed: {e}")
            raise
    
    def append_transaction(self, extracted_data: ReceiptExtraction):
        """Append transaction data to Google Sheet"""
        try:
            row_data = [
                extracted_data.date_sent,
                extracted_data.sender_name,
                extracted_data.receiver_name,
                extracted_data.account_number,
                str(extracted_data.amount),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Timestamp
            ]
            
            self.sheet.append_row(row_data)
            logger.info("✅ Successfully appended transaction to Google Sheets")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to append to Google Sheets: {e}")
            return False

# Initialize Google Sheets handler
sheets_handler = GoogleSheetsHandler()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when command /start is issued."""
    welcome_text = """
🤖 **Advanced Receipt Processing Bot**

I can extract structured data from your receipt images using AI!

**Supported Documents:**
• Bank transfer receipts
• Money transfer slips  
• Payment confirmations

**How to use:**
1. Send me a clear image of your receipt
2. I'll extract: sender, receiver, account number, amount, and date
3. Data will be saved to our database

Send me a receipt image to get started!
    """
    await update.message.reply_text(welcome_text)

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming receipt images"""
    user = update.message.from_user
    logger.info(f"📸 Image received from user {user.id}")
    
    # Send processing message
    processing_msg = await update.message.reply_text("🔍 Scanning receipt with AI... Please wait.")

    try:
        # 1. Download the photo (Highest resolution)
        photo_file = await update.message.photo[-1].get_file()
        
        # Download to memory (BytesIO) instead of saving to disk
        image_stream = io.BytesIO()
        await photo_file.download_to_memory(out=image_stream)
        image_bytes = image_stream.getvalue()

        # 2. Send to GPT-4o
        extracted_data = analyze_receipt(image_bytes)

        if not extracted_data:
            await processing_msg.edit_text("❌ Could not process image. Please try again with a clearer image.")
            return

        # 3. Save to Google Sheet
        save_success = sheets_handler.append_transaction(extracted_data)
        
        if not save_success:
            await processing_msg.edit_text("✅ Data extracted but failed to save to database. Please contact admin.")
            return

        # 4. Reply to User with formatted text
        response_msg = (
            f"✅ **Receipt Processed Successfully!**\n\n"
            f"📅 **Date:** {extracted_data.date_sent}\n"
            f"👤 **Sender:** {extracted_data.sender_name}\n"
            f"📥 **Receiver:** {extracted_data.receiver_name}\n"
            f"🔢 **Account:** {extracted_data.account_number}\n"
            f"💰 **Amount:** ${extracted_data.amount:,.2f}\n\n"
            f"💾 **Data saved to database**"
        )
        
        await processing_msg.edit_text(response_msg, parse_mode='Markdown')
        logger.info(f"✅ Receipt processed for user {user.id}")

    except Exception as e:
        logger.error(f"❌ Error processing image: {e}")
        await processing_msg.edit_text("⚠️ An error occurred while processing the receipt. Please try again.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in telegram bot."""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot"""
    # Load token from Environment Variable
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    if not TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN environment variable is required")
        return
        
    if not OPENAI_API_KEY:
        logger.error("❌ OPENAI_API_KEY environment variable is required")
        return

    try:
        application = Application.builder().token(TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(MessageHandler(filters.PHOTO, handle_image))
        application.add_error_handler(error_handler)
        
        logger.info("🤖 Bot is starting...")
        print("✅ Bot is running on Render...")
        
        # Start polling
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")

if __name__ == '__main__':
    main()
