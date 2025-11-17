import gspread
from google.oauth2.service_account import Credentials
from config import Config
from schemas import TransactionData
import logging

logger = logging.getLogger(__name__)

class GoogleSheetsHandler:
    def __init__(self):
        self.scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        self._setup_client()
    
    def _setup_client(self):
        """Setup Google Sheets client"""
        try:
            creds_dict = json.loads(Config.GOOGLE_SHEETS_CREDENTIALS)
            creds = Credentials.from_service_account_info(creds_dict, scopes=self.scope)
            self.client = gspread.authorize(creds)
            self.sheet = self.client.open_by_key(Config.SPREADSHEET_ID).sheet1
        except Exception as e:
            logger.error(f"Google Sheets setup failed: {str(e)}")
            raise
    
    def append_transaction(self, transaction_data: TransactionData):
        """Append transaction data to Google Sheet"""
        try:
            # Prepare row data
            row = [
                transaction_data.sender_name,
                transaction_data.receiver_name,
                transaction_data.account_number,
                str(transaction_data.amount),
                transaction_data.date_sent,
                str(datetime.now())  # Timestamp of entry
            ]
            
            # Append to sheet
            self.sheet.append_row(row)
            logger.info("Successfully appended transaction to Google Sheets")
            return True
            
        except Exception as e:
            logger.error(f"Failed to append to Google Sheets: {str(e)}")
            return False
