import base64
import json
import openai
from config import OPENAI_API_KEY
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class AIService:
    """Service for analyzing receipts using OpenAI Vision API"""
    
    def __init__(self):
        openai.api_key = OPENAI_API_KEY
    
    async def analyze_receipt(self, image_path: str) -> Dict:
        try:
            logger.info(f"Starting AI analysis for: {image_path}")
            
            # Read and encode image
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            # Call OpenAI API
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self._get_prompt()},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0
            )
            
            # Extract content
            content = response.choices[0].message.content.strip()
            logger.info(f"AI Response: {content[:200]}...")
            
            # Extract JSON
            json_text = self._extract_json(content)
            logger.info(f"Extracted JSON: {json_text}")
            
            # Parse JSON
            result = json.loads(json_text)
            
            logger.info(f"AI analysis complete. Found {len(result.get('items', []))} items")
            return result
            
        except Exception as e:
            logger.error(f"Error in AI analysis: {e}", exc_info=True)
            raise
    
    def _get_prompt(self) -> str:
        """Get the prompt for OpenAI"""
        return """
Analyze receipt and extract items. Pay careful attention to parsing the receipt correctly.

CRITICAL PARSING RULES:
The receipt has columns: Наименование (Item Name) | Кол-во (Quantity) | Сумма (Price/Sum)

QUANTITY vs PRICE DISAMBIGUATION:
- Quantity (Кол-во) is ALWAYS 1-2 digits (typically 1-10 items)
- Price/Sum (Сумма) can be much larger (3-6+ digits)
- When numbers are close together and hard to distinguish:
  1. The FIRST number under Кол-во column is the quantity (1-2 digits max)
  2. The SECOND number is the total price for that item
  3. DO NOT combine numbers into one large value (e.g., 7 413 000 is NOT 7,413,000 - it's quantity 7, price 413,000)
  4. Assume quantities rarely exceed 2 digits; if you see "7 413", it's qty=7, price=413,000

PRICE LOGIC CHECK:
- Item prices should be reasonable relative to the total
- If an item price exceeds the total, you've misread the columns
- Verify: sum of all item prices + service charge ≈ total amount

For "type" field use:
- "SHARED": Items meant to be shared (bread, tea, beverages, service charges, tips, utensils/packets)
- "INDIVIDUAL": Items for one person (main dishes, prepared foods, specific portions)

IMPORTANT: Always extract service charges/tips as separate SHARED items!

Return ONLY valid JSON in this exact format:
{
  "restaurant": "Restaurant Name",
  "total": 309680,
  "items": [
    {"name": "Лепешки", "quantity": 3, "price": 15000, "type": "SHARED"},
    {"name": "Чай", "quantity": 1, "price": 15000, "type": "SHARED"},
    {"name": "Обслуживание", "quantity": 1, "price": 33180, "type": "SHARED"},
    {"name": "Лагман", "quantity": 3, "price": 147000, "type": "INDIVIDUAL"}
  ]
}

DO NOT include any text before or after the JSON. ONLY return the JSON object.
"""
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from response text"""
        start = text.find('{')
        end = text.rfind('}') + 1
        
        if start == -1 or end == 0:
            raise ValueError(f"No JSON found in AI response: {text}")
        
        return text[start:end]