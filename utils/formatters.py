from typing import List
import re


def format_amount(amount: float) -> str:
    """Format amount with thousands separator"""
    return f"{amount:,.0f}".replace(",", " ")


def format_receipt_text(text: str) -> str:
    """Format extracted receipt text for display"""
    # Add line numbers for easier editing
    lines = text.split('\n')
    formatted_lines = []
    
    for i, line in enumerate(lines, 1):
        if line.strip():
            formatted_lines.append(f"{i}. {line.strip()}")
    
    return '\n'.join(formatted_lines)


def clean_receipt_text(text: str) -> str:
    """Clean and normalize receipt text"""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters that might interfere
    text = re.sub(r'[^\w\s\d.,:-]', '', text)
    return text.strip()