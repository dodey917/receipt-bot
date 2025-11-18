from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional

class ReceiptExtraction(BaseModel):
    sender_name: str = Field(description="Full name of the sender. If unknown, use 'Unknown'.")
    receiver_name: str = Field(description="Full name of the receiver.")
    account_number: str = Field(description="Receiver's account number or transaction ID.")
    amount: float = Field(description="Total transaction amount. Numeric only.")
    date_sent: str = Field(description="Date of transaction in YYYY-MM-DD format.")
    
    @validator('date_sent')
    def validate_date_format(cls, v):
        if v != 'Unknown':
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError('Date must be in YYYY-MM-DD format or "Unknown"')
        return v
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return round(v, 2)
