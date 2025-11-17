import base64
import json
from openai import OpenAI
from config import Config
from schemas import TransactionData, ExtractionResponse
import logging

logger = logging.getLogger(__name__)

class OCRProcessor:
    def __init__(self):
        if not Config.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
    
    def extract_data(self, image_path):
        """Extract structured data from receipt image using GPT-4 Vision"""
        try:
            # Read image file directly as binary
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
            
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # System prompt for structured extraction
            system_prompt = """You are an expert financial document processor. Extract transaction details from receipt images and return ONLY valid JSON.

IMPORTANT: Return ONLY JSON, no other text.

Required JSON structure:
{
    "sender_name": "Full name of sender",
    "receiver_name": "Full name of receiver", 
    "account_number": "Account number or transfer ID",
    "amount": 123.45,
    "date_sent": "YYYY-MM-DD"
}

Guidelines:
- If a field is not found, use "Unknown" for strings or 0.0 for amount
- Convert all dates to YYYY-MM-DD format
- Remove currency symbols, keep only numeric amount
- Be precise with names and account numbers
- Return ONLY the JSON object, no other text"""
            
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
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from: {text}")
        
        return None
