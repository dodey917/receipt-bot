import base64
import json
from openai import OpenAI
from config import Config
from schemas import TransactionData, ExtractionResponse
import logging

logger = logging.getLogger(__name__)

class OCRProcessor:
    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
    
    def encode_image(self, image_path):
        """Encode image to base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def extract_data(self, image_path):
        """Extract structured data from receipt image using GPT-4 Vision"""
        try:
            # Encode image
            base64_image = self.encode_image(image_path)
            
            # System prompt for structured extraction
            system_prompt = """
            You are an expert financial document processor. Extract the following fields from the receipt image:
            
            REQUIRED FIELDS:
            - sender_name: Full name of the sender/money sender
            - receiver_name: Full name of the receiver/beneficiary  
            - account_number: Receiver's account number, IBAN, or unique transfer identifier
            - amount: Total monetary value of the transaction (as float)
            - date_sent: Transaction date in YYYY-MM-DD format
            
            IMPORTANT INSTRUCTIONS:
            1. Extract ONLY the specified fields
            2. Return data as valid JSON
            3. If a field is not found, use "Unknown" for strings or 0.0 for amount
            4. Convert dates to YYYY-MM-DD format
            5. Remove currency symbols from amount, keep only numeric value
            6. Be precise with names and account numbers
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text", 
                                "text": "Extract the transaction data from this receipt. Return ONLY valid JSON:"
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
                temperature=0.1  # Low temperature for consistent formatting
            )
            
            # Extract JSON from response
            raw_content = response.choices[0].message.content
            logger.info(f"Raw API response: {raw_content}")
            
            # Clean response and extract JSON
            json_str = self._extract_json_from_response(raw_content)
            
            if not json_str:
                return ExtractionResponse(
                    success=False,
                    error="No valid JSON found in API response",
                    raw_response=raw_content
                )
            
            # Parse and validate data
            extracted_data = json.loads(json_str)
            validated_data = TransactionData(**extracted_data)
            
            return ExtractionResponse(
                success=True,
                data=validated_data,
                raw_response=raw_content
            )
            
        except Exception as e:
            logger.error(f"Error in data extraction: {str(e)}")
            return ExtractionResponse(
                success=False,
                error=str(e),
                raw_response=None
            )
    
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
        except:
            pass
        
        return None
