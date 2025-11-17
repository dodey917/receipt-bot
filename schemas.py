from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import re

class TransactionData(BaseModel):
    sender_name: str = Field(..., description="Full name of the sender")
    receiver_name: str = Field(..., description="Full name of the receiver")
    account_number: str = Field(..., description="Receiver's account number or transfer ID")
    amount: float = Field(..., description="Transaction amount", gt=0)
    date_sent: str = Field(..., description="Transaction date in YYYY-MM-DD format")
    
    @validator('date_sent')
    def validate_date_format(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return round(v, 2)

class ExtractionResponse(BaseModel):
    success: bool
    data: Optional[TransactionData] = None
    error: Optional[str] = None
    raw_response: Optional[str] = None
