import easyocr
import logging
from pathlib import Path
from config import OCR_LANGUAGES, OCR_GPU
import os

logger = logging.getLogger(__name__)


class OCRService:
    """Service for extracting text from receipt images"""
    
    _reader = None
    
    @classmethod
    def get_reader(cls):
        """Get or create EasyOCR reader (singleton pattern)"""
        if cls._reader is None:
            logger.info(f"Initializing EasyOCR with languages: {OCR_LANGUAGES}")
            try:
                cls._reader = easyocr.Reader(
                    OCR_LANGUAGES,
                    gpu=OCR_GPU,
                    verbose=False
                )
                logger.info("EasyOCR initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize EasyOCR: {e}")
                raise
        return cls._reader
    
    @classmethod
    async def extract_text_from_image(cls, image_path: str) -> str:
        """
        Extract text from image using EasyOCR
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Extracted text as string
        """
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            logger.info(f"Starting OCR extraction for: {image_path}")
            
            # Get reader
            reader = cls.get_reader()
            
            # Perform OCR
            results = reader.readtext(image_path)
            
            # Extract text from results
            # EasyOCR returns: [(bbox, text, confidence), ...]
            extracted_lines = []
            for (bbox, text, confidence) in results:
                if confidence > 0.3:  # Filter low confidence results
                    extracted_lines.append(text)
            
            # Join all lines
            extracted_text = "\n".join(extracted_lines)
            
            logger.info(f"OCR completed. Extracted {len(extracted_lines)} lines")
            logger.debug(f"Extracted text:\n{extracted_text}")
            
            return extracted_text
            
        except Exception as e:
            logger.error(f"Error during OCR extraction: {e}", exc_info=True)
            raise
    
    @classmethod
    async def extract_text_from_image_detailed(cls, image_path: str) -> dict:
        """
        Extract text with detailed information (confidence, bounding boxes)
        
        Returns:
            Dict with detailed OCR results
        """
        try:
            reader = cls.get_reader()
            results = reader.readtext(image_path)
            
            detailed_results = {
                'total_items': len(results),
                'items': []
            }
            
            for (bbox, text, confidence) in results:
                detailed_results['items'].append({
                    'text': text,
                    'confidence': confidence,
                    'bbox': bbox
                })
            
            return detailed_results
            
        except Exception as e:
            logger.error(f"Error during detailed OCR extraction: {e}")
            raise