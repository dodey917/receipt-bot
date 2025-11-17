import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import Config
from ocr_processor import OCRProcessor
from google_sheets import GoogleSheetsHandler
from schemas import ExtractionResponse
import tempfile
import os
import asyncio

# Setup logging
logging.basicConfig(
    format='%(asasctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ReceiptBot:
    def __init__(self):
        try:
            self.ocr_processor = OCRProcessor()
            self.sheets_handler = GoogleSheetsHandler()
            logger.info("ReceiptBot initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ReceiptBot: {str(e)}")
            # Continue with limited functionality
            self.ocr_processor = None
            self.sheets_handler = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message when command /start is issued."""
        welcome_text = """
🤖 **Advanced Receipt Processing Bot**

I can extract structured data from your receipt images!

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
    
    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming receipt images"""
        if not self.ocr_processor:
            await update.message.reply_text("❌ Bot is not properly initialized. Please check server logs.")
            return
            
        user = update.message.from_user
        logger.info(f"Image received from user {user.id}")
        
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
            logger.info(f"Image downloaded to {temp_file_path}")
            
            # Process image (run in thread to avoid blocking)
            extraction_result = await asyncio.get_event_loop().run_in_executor(
                None, self.ocr_processor.extract_data, temp_file_path
            )
            
            if not extraction_result.success:
                error_text = f"❌ Extraction failed: {extraction_result.error}"
                if "rate limit" in extraction_result.error.lower():
                    error_text += "\nPlease try again in a minute."
                await processing_msg.edit_text(error_text)
                return
            
            # Save to Google Sheets if available
            if self.sheets_handler:
                save_success = self.sheets_handler.append_transaction(extraction_result.data)
                save_status = "💾 Data has been saved to the database." if save_success else "💾 Data extracted but not saved to database."
            else:
                save_status = "⚠️  Data extracted but database not available."
            
            # Send success message with extracted data
            success_text = self._format_success_message(extraction_result.data, save_status)
            await processing_msg.edit_text(success_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            await processing_msg.edit_text(
                "❌ An error occurred while processing your image. Please try again with a clearer image."
            )
        finally:
            # Clean up temp file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
    
    def _format_success_message(self, data, save_status):
        """Format extracted data into a nice message"""
        return f"""
✅ **Receipt Processed Successfully!**

📋 **Extracted Data:**
┌──────────────────────────────
│ 👤 **Sender:** {data.sender_name}
│ 👤 **Receiver:** {data.receiver_name}  
│ 🔢 **Account:** {data.account_number}
│ 💰 **Amount:** ${data.amount:,.2f}
│ 📅 **Date:** {data.date_sent}
└──────────────────────────────

{save_status}
        """
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot"""
    if not Config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set in environment variables")
        return
    
    # Create bot instance
    receipt_bot = ReceiptBot()
    
    # Create application
    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", receipt_bot.start))
    application.add_handler(MessageHandler(filters.PHOTO, receipt_bot.handle_image))
    application.add_error_handler(receipt_bot.error_handler)
    
    # Start bot
    logger.info("Bot is starting...")
    print("🤖 Bot is running on Render...")
    
    # Run the bot
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()• Bank transfer receipts
• Money transfer slips  
• Payment confirmations

**How to use:**
1. Send me a clear image of your receipt
2. I'll extract: sender, receiver, account number, amount, and date
3. Data will be saved to our database

Send me a receipt image to get started!
        """
        await update.message.reply_text(welcome_text)
    
    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming receipt images"""
        user = update.message.from_user
        logger.info(f"Image received from user {user.id}")
        
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
            logger.info(f"Image downloaded to {temp_file_path}")
            
            # Process image (run in thread to avoid blocking)
            extraction_result = await asyncio.get_event_loop().run_in_executor(
                None, self.ocr_processor.extract_data, temp_file_path
            )
            
            if not extraction_result.success:
                error_text = f"❌ Extraction failed: {extraction_result.error}"
                if "rate limit" in extraction_result.error.lower():
                    error_text += "\nPlease try again in a minute."
                await processing_msg.edit_text(error_text)
                return
            
            # Save to Google Sheets
            save_success = self.sheets_handler.append_transaction(extraction_result.data)
            
            if not save_success:
                await processing_msg.edit_text(
                    "✅ Data extracted but failed to save to database. Please contact admin."
                )
                return
            
            # Send success message with extracted data
            success_text = self._format_success_message(extraction_result.data)
            await processing_msg.edit_text(success_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            await processing_msg.edit_text(
                "❌ An error occurred while processing your image. Please try again with a clearer image."
            )
        finally:
            # Clean up temp file
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def _format_success_message(self, data):
        """Format extracted data into a nice message"""
        return f"""
✅ **Receipt Processed Successfully!**

📋 **Extracted Data:**
┌──────────────────────────────
│ 👤 **Sender:** {data.sender_name}
│ 👤 **Receiver:** {data.receiver_name}  
│ 🔢 **Account:** {data.account_number}
│ 💰 **Amount:** ${data.amount:,.2f}
│ 📅 **Date:** {data.date_sent}
└──────────────────────────────

💾 Data has been saved to the database.
        """
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot"""
    if not Config.TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in environment variables")
    
    # Create bot instance
    try:
        receipt_bot = ReceiptBot()
    except Exception as e:
        logger.error(f"Failed to create ReceiptBot: {str(e)}")
        return
    
    # Create application
    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", receipt_bot.start))
    application.add_handler(MessageHandler(filters.PHOTO, receipt_bot.handle_image))
    application.add_error_handler(receipt_bot.error_handler)
    
    # Start bot
    logger.info("Bot is starting...")
    print("🤖 Bot is running on Render...")
    
    # Run the bot until Ctrl-C is pressed
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        close_loop=False
    )

if __name__ == '__main__':
    main()2. I'll extract: sender, receiver, account number, amount, and date
3. Data will be saved to our database

**Example fields I extract:**
- 👤 Sender Name
- 👤 Receiver Name  
- 🔢 Account Number
- 💰 Amount
- 📅 Date (YYYY-MM-DD)

Send me a receipt image to get started!
        """
        await update.message.reply_text(welcome_text)
    
    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming receipt images"""
        user = update.message.from_user
        logger.info(f"Image received from user {user.id}")
        
        # Send processing message
        processing_msg = await update.message.reply_text(
            "🔄 Processing your receipt... This may take a few seconds."
        )
        
        try:
            # Download image
            photo_file = await update.message.photo[-1].get_file()
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                await photo_file.download_to_drive(temp_file.name)
                
                # Process image
                extraction_result: ExtractionResponse = self.ocr_processor.extract_data(temp_file.name)
                
                # Clean up temp file
                os.unlink(temp_file.name)
            
            if not extraction_result.success:
                await processing_msg.edit_text(
                    f"❌ Extraction failed: {extraction_result.error}\n"
                    "Please try again with a clearer image."
                )
                return
            
            # Save to Google Sheets
            save_success = self.sheets_handler.append_transaction(extraction_result.data)
            
            if not save_success:
                await processing_msg.edit_text(
                    "✅ Data extracted but failed to save to database. Please contact admin."
                )
                return
            
            # Send success message with extracted data
            success_text = self._format_success_message(extraction_result.data)
            await processing_msg.edit_text(success_text)
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            await processing_msg.edit_text(
                "❌ An error occurred while processing your image. Please try again."
            )
    
    def _format_success_message(self, data):
        """Format extracted data into a nice message"""
        return f"""
✅ **Receipt Processed Successfully!**

📋 **Extracted Data:**
┌──────────────────────────────
│ 👤 **Sender:** {data.sender_name}
│ 👤 **Receiver:** {data.receiver_name}  
│ 🔢 **Account:** {data.account_number}
│ 💰 **Amount:** ${data.amount:,.2f}
│ 📅 **Date:** {data.date_sent}
└──────────────────────────────

💾 Data has been saved to the database.
        """
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot"""
    if not Config.TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in environment variables")
    
    # Create bot instance
    receipt_bot = ReceiptBot()
    
    # Create application
    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", receipt_bot.start))
    application.add_handler(MessageHandler(filters.PHOTO, receipt_bot.handle_image))
    application.add_error_handler(receipt_bot.error_handler)
    
    # Start bot
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
