from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

# --- Data Extraction Schema (Used for image processing) ---
class ReceiptExtraction(BaseModel):
    """Schema for structured data extracted from a receipt image."""
    date_sent: str = Field(..., description="The date of the transaction (e.g., '2025-11-20').")
    sender_name: str = Field(..., description="The full name of the sender/payer.")
    receiver_name: str = Field(..., description="The full name of the receiver/recipient.")
    account_number: str = Field(..., description="The account number associated with the transaction, if available. Otherwise, use 'N/A'.")
    amount: float = Field(..., description="The numerical total amount of the transaction.")

# --- Data Retrieval Schemas (NEW) ---
class QuerySchema(BaseModel):
    """Schema for a structured query to search the Google Sheet."""
    column_to_search: str = Field(..., description="The name of the column to search (e.g., 'sender_name', 'receiver_name', 'amount'). Must be lowercase.")
    search_value: str = Field(..., description="The value to search for within that column (e.g., 'Michael IWA', '2500').")

class SearchResponse(BaseModel):
    """Schema for a single transaction row retrieved from the Google Sheet."""
    date_sent: str
    sender_name: str
    receiver_name: str
    account_number: str
    amount: str # Kept as string for direct sheet output
    timestamp: str # Time data was saved
