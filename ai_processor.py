import base64
import json
from openai import OpenAI
from schemas import ReceiptExtraction
import os
import logging

logger = logging.getLogger(__name__)

# Initialize OpenAI Client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def encode_image_from_bytes(image_bytes):
    """Encodes image bytes to base64 string"""
    return base64.b64encode(image_bytes).decode('utf-8')

def analyze_receipt(image_bytes):
    """
    Sends image to GPT-4o and returns a structured ReceiptExtraction object.
    Uses fallback method if beta API is not available.
    """
    base64_image = encode_image_from_bytes(image_bytes)

    try:
        # Try the beta structured outputs first
        try:
            completion = client.beta.chat.completions.parse(
                model="gpt-4o-2024-08-06",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert financial data extraction AI. 
                        Extract transaction details from receipt images. 
                        Return ONLY the specified fields in valid JSON format.
                        For missing fields, use 'Unknown' for text or 0.0 for amount."""
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract the transaction data from this receipt."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
                response_format=ReceiptExtraction,
            )
            return completion.choices[0].message.parsed
            
        except Exception as beta_error:
            logger.warning(f"Beta API not available, using standard API: {beta_error}")
            # Fallback to standard API with JSON mode
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert financial data extraction AI. 
                        Extract ONLY these fields from receipts: sender_name, receiver_name, account_number, amount, date_sent.
                        Return ONLY valid JSON, no other text.
                        Format: {"sender_name": "...", "receiver_name": "...", "account_number": "...", "amount": 123.45, "date_sent": "YYYY-MM-DD"}
                        For missing fields, use 'Unknown' for text or 0.0 for amount."""
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract transaction data from this receipt and return ONLY valid JSON:"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=500,
                temperature=0.1
            )
            
            # Parse the JSON response and validate with Pydantic
            json_response = json.loads(completion.choices[0].message.content)
            return ReceiptExtraction(**json_response)

    except Exception as e:
        logger.error(f"AI Processing Error: {e}")
        return None
