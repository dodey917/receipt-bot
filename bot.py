import base64
import os
import json
from openai import OpenAI
from pydantic import ValidationError

# Import schemas
from schemas import ReceiptExtraction, QuerySchema

# Initialize OpenAI Client (It will automatically look for OPENAI_API_KEY environment variable)
client = OpenAI()

# Define the columns available in your Google Sheet for the AI to choose from
# Note: These must match the headers/order you use when querying the sheet.
SHEET_COLUMNS = [
    "Date_Sent", 
    "Sender_Name", 
    "Receiver_Name", 
    "Account_Number", 
    "Amount", 
    "Timestamp"
]

def analyze_receipt(image_bytes: bytes) -> Optional[ReceiptExtraction]:
    """
    Uses GPT-4o with function calling (Pydantic) to extract structured data from a receipt image.
    """
    try:
        # Encode image to base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # Define the tool (function) the model can use
        tools = [{
            "type": "function",
            "function": {
                "name": "extract_receipt_data",
                "description": "Extracts structured financial transaction data from a bank receipt image.",
                "parameters": ReceiptExtraction.model_json_schema()
            }
        }]
        
        # Call the OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert receipt data extractor. Analyze the image and extract the requested fields. The transaction date should be in YYYY-MM-DD format. The amount must be a number."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all transaction details from this image."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "extract_receipt_data"}}
        )

        # Check for function call in the response
        message = response.choices[0].message
        if not message.tool_calls:
            print("AI did not call the extraction function.")
            return None

        # Process the function call argument
        func_call = message.tool_calls[0].function
        if func_call.name == "extract_receipt_data":
            args = json.loads(func_call.arguments)
            return ReceiptExtraction(**args)

    except Exception as e:
        print(f"Error during receipt analysis: {e}")
        return None
        
def generate_sheet_query(user_prompt: str) -> Optional[QuerySchema]:
    """
    (NEW FUNCTION) Uses GPT-4o with function calling to convert a user's natural
    language request into a structured query for the Google Sheet.
    """
    try:
        tools = [{
            "type": "function",
            "function": {
                "name": "create_search_query",
                "description": f"Converts a user's request into a structured query for the database. Available columns for searching are: {', '.join(SHEET_COLUMNS)}.",
                "parameters": QuerySchema.model_json_schema()
            }
        }]
        
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Using a smaller, faster model for this simple task
            messages=[
                {"role": "system", "content": f"Analyze the user's request and formulate a precise search query based on the available columns: {', '.join(SHEET_COLUMNS)}. The search value should be the exact value the user is looking for. The column name must be one of the available columns."},
                {"role": "user", "content": user_prompt}
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "create_search_query"}}
        )
        
        message = response.choices[0].message
        if not message.tool_calls:
            # Fallback if AI doesn't call the function
            return None 

        func_call = message.tool_calls[0].function
        if func_call.name == "create_search_query":
            args = json.loads(func_call.arguments)
            
            # Simple validation check against our defined columns
            if args.get('column_to_search') in [col.lower() for col in SHEET_COLUMNS]:
                return QuerySchema(**args)
            
            print(f"Invalid column selected by AI: {args.get('column_to_search')}")
            return None # Invalid query

    except (Exception, ValidationError) as e:
        print(f"Error during query generation: {e}")
        return None
