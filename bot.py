import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from config import Config
from ocr_processor import OCRProcessor
from google_sheets import GoogleSheetsHandler
from schemas import ExtractionResponse
import tempfile
import os
import threading

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ReceiptBot:
    def __init__(self):
        try:
            Config.validate_config()
            self.ocr_processor = OCRProcessor()
            self.sheets_handler = GoogleSheetsHandler()
            logger.info("ReceiptBot initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ReceiptBot: {str(e)}")
            raise
    
    def start(self, update: Update, context: CallbackContext):
        """Send welcome message when command /start is issued."""
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
        update.message.reply_text(welcome_text)
    
    def handle_image(self, update: Update, context: CallbackContext):
        """Handle incoming receipt images"""
        user = update.message.from_user
        logger.info(f"Image received from user {user.id}")
        
        # Send processing message
        processing_msg = update.message.reply_text(
            "Processing your receipt... This may take 10-20 seconds."
        )
        
        # Process image in a separate thread to avoid blocking
        thread = threading.Thread(
            target=self._process_image_thread,
            args=(update, context, processing_msg)
        )
        thread.start()
    
    def _process_image_thread(self, update: Update, context: CallbackContext, processing_msg):
        """Process image in a separate thread"""
        temp_file_path = None
        try:
            # Download image (get the highest resolution)
            photo_file = update.message.photo[-1].get_file()
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                temp_file_path = temp_file.name
            
            photo_file.download(temp_file_path)
            logger.info(f"Image downloaded to {temp_file_path}")
            
            # Process image
            extraction_result = self.ocr_processor.extract_data(temp_file_path)
            
            if not extraction_result.success:
                error_text = f"Extraction failed: {extraction_result.error}"
                if "rate limit" in extraction_result.error.lower():
                    error_text += "\nPlease try again in a minute."
                context.bot.edit_message_text(
                    chat_id=processing_msg.chat_id,
                    message_id=processing_msg.message_id,
                    text=error_text
                )
                return
            
            # Save to Google Sheets
            save_success = self.sheets_handler.append_transaction(extraction_result.data)
            
            if not save_success:
                context.bot.edit_message_text(
                    chat_id=processing_msg.chat_id,
                    message_id=processing_msg.message_id,
                    text="Data extracted but failed to save to database. Please contact admin."
                )
                return
            
            # Send success message with extracted data
            success_text = self._format_success_message(extraction_result.data)
            context.bot.edit_message_text(
                chat_id=processing_msg.chat_id,
                message_id=processing_msg.message_id,
                text=success_text
            )
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            context.bot.edit_message_text(
                chat_id=processing_msg.chat_id,
                message_id=processing_msg.message_id,
                text="An error occurred while processing your image. Please try again with a clearer image."
            )
        finally:
            # Clean up temp file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file: {e}")
    
    def _format_success_message(self, data):
        """Format extracted data into a nice message"""
        return f"""
Receipt Processed Successfully!

Extracted Data:
Sender: {data.sender_name}
Receiver: {data.receiver_name}
Account: {data.account_number}
Amount: ${data.amount:,.2f}
Date: {data.date_sent}

Data has been saved to the database.
        """
    
    def error_handler(self, update: Update, context: CallbackContext):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot"""
    try:
        # Validate configuration first
        Config.validate_config()
        
        # Create bot instance
        receipt_bot = ReceiptBot()
        
        # Create updater
        updater = Updater(Config.TELEGRAM_BOT_TOKEN, use_context=True)
        
        # Get dispatcher to register handlers
        dp = updater.dispatcher
        
        # Add handlers
        dp.add_handler(CommandHandler("start", receipt_bot.start))
        dp.add_handler(MessageHandler(Filters.photo, receipt_bot.handle_image))
        dp.add_error_handler(receipt_bot.error_handler)
        
        # Start bot
        logger.info("Bot is starting...")
        print("Bot is running on Render...")
        
        # Start polling
        updater.start_polling()
        
        # Run the bot until you press Ctrl-C
        updater.idle()
        
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}")
        print(f"Bot failed to start: {e}")

if __name__ == '__main__':
    main()
