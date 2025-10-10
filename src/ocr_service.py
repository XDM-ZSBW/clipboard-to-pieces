#!/usr/bin/env python3
"""
OCR Service for Image Text Extraction
Supports Windows, macOS, and Linux with multiple OCR engines
"""

import os
import sys
import logging
from typing import Optional, Tuple
from pathlib import Path
from PIL import Image
import tempfile

class OCRService:
    """OCR service for extracting text from images using Tesseract only
    
    Privacy-focused implementation using only Tesseract OCR engine:
    - Cross-platform: Windows, macOS, Linux
    - Open source: No proprietary APIs or cloud services
    - Local processing: All OCR happens locally
    - Configurable: Multiple language support and custom settings
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.available_engines = []
        self.preferred_engine = None
        self._detect_available_engines()
    
    def _detect_available_engines(self):
        """Detect available OCR engines - Tesseract only for privacy"""
        self.available_engines = []
        
        # Only use Tesseract for maximum privacy
        if self._check_tesseract():
            self.available_engines.append("tesseract")
            self.preferred_engine = "tesseract"
            self.logger.info("Tesseract OCR engine detected and enabled")
        else:
            self.logger.warning("Tesseract OCR not available - OCR functionality disabled")
            self.logger.info("Install Tesseract for OCR support:")
            if sys.platform == "win32":
                self.logger.info("  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
            elif sys.platform == "darwin":
                self.logger.info("  macOS: brew install tesseract")
            else:
                self.logger.info("  Linux: sudo apt install tesseract-ocr (Ubuntu/Debian)")
        
        self.logger.info(f"Available OCR engines: {self.available_engines}")
        self.logger.info(f"Preferred engine: {self.preferred_engine}")
    
    
    def _check_tesseract(self) -> bool:
        """Check if Tesseract is available"""
        try:
            import pytesseract
            
            # Try default path first
            try:
                pytesseract.get_tesseract_version()
                return True
            except:
                # Try Windows default installation path
                pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                pytesseract.get_tesseract_version()
                return True
                
        except (ImportError, Exception):
            return False
    
    def extract_text(self, image_path: str, engine: Optional[str] = None) -> Tuple[str, bool]:
        """
        Extract text from image using OCR
        
        Args:
            image_path: Path to the image file
            engine: OCR engine to use (optional, uses preferred if not specified)
            
        Returns:
            Tuple of (extracted_text, success_flag)
        """
        if not self.available_engines:
            self.logger.warning("No OCR engines available")
            return "", False
        
        if engine is None:
            engine = self.preferred_engine
        
        if engine not in self.available_engines:
            self.logger.warning(f"OCR engine '{engine}' not available, using '{self.preferred_engine}'")
            engine = self.preferred_engine
        
        try:
            if engine == "tesseract":
                return self._extract_text_tesseract(image_path)
            else:
                self.logger.error(f"Unknown OCR engine: {engine}")
                return "", False
                
        except Exception as e:
            self.logger.error(f"OCR extraction failed with {engine}: {e}")
            return "", False
    
    def extract_text_with_boxes(self, image_path: str, engine: Optional[str] = None) -> Tuple[str, bool, list]:
        """
        Extract text from image using OCR with bounding boxes
        
        Args:
            image_path: Path to the image file
            engine: OCR engine to use (optional, uses preferred if not specified)
            
        Returns:
            Tuple of (extracted_text, success_flag, bounding_boxes)
        """
        if not self.available_engines:
            self.logger.warning("No OCR engines available")
            return "", False, []
        
        if engine is None:
            engine = self.preferred_engine
        
        if engine not in self.available_engines:
            self.logger.warning(f"OCR engine '{engine}' not available, using '{self.preferred_engine}'")
            engine = self.preferred_engine
        
        try:
            if engine == "tesseract":
                return self._extract_text_with_boxes_tesseract(image_path)
            else:
                self.logger.error(f"Unknown OCR engine: {engine}")
                return "", False, []
                
        except Exception as e:
            self.logger.error(f"OCR extraction failed with {engine}: {e}")
            return "", False, []
    
    
    def _extract_text_tesseract(self, image_path: str) -> Tuple[str, bool]:
        """Extract text using Tesseract with privacy-focused configuration"""
        try:
            import pytesseract
            
            # Set Tesseract path if needed
            try:
                pytesseract.get_tesseract_version()
            except:
                pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

            # Load image and convert to RGB format
            image = Image.open(image_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Privacy-focused OCR configuration
            # --psm 6: Assume a single uniform block of text
            # --oem 3: Default OCR Engine Mode (LSTM + Legacy)
            # -c preserve_interword_spaces=1: Preserve spacing for better readability
            config = '--psm 6 --oem 3 -c preserve_interword_spaces=1'
            
            # Extract text with privacy-focused settings
            text = pytesseract.image_to_string(image, config=config)
            
            # Clean up extracted text
            cleaned_text = text.strip()
            
            if cleaned_text:
                self.logger.debug(f"Tesseract extracted {len(cleaned_text)} characters")
                return cleaned_text, True
            else:
                self.logger.debug("No text extracted by Tesseract")
                return "", False
            
        except Exception as e:
            self.logger.error(f"Tesseract OCR failed: {e}")
            return "", False
    
    def _extract_text_with_boxes_tesseract(self, image_path: str) -> Tuple[str, bool, list]:
        """Extract text using Tesseract with bounding boxes for redaction"""
        try:
            import pytesseract
            
            # Set Tesseract path if needed
            try:
                pytesseract.get_tesseract_version()
            except:
                pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            
            # Load image and convert to RGB format
            image = Image.open(image_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Privacy-focused OCR configuration
            config = '--psm 6 --oem 3 -c preserve_interword_spaces=1'
            
            # Extract text with bounding boxes
            data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
            
            # Process the data to get text and bounding boxes
            extracted_text = ""
            bounding_boxes = []
            
            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                if text:  # Only process non-empty text
                    extracted_text += text + " "
                    
                    # Get bounding box coordinates
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]
                    
                    # Only include boxes with valid coordinates
                    if w > 0 and h > 0:
                        bounding_boxes.append({
                            'text': text,
                            'x': x,
                            'y': y,
                            'width': w,
                            'height': h,
                            'confidence': data['conf'][i]
                        })
            
            # Clean up extracted text
            cleaned_text = extracted_text.strip()
            
            if cleaned_text:
                self.logger.debug(f"Tesseract extracted {len(cleaned_text)} characters with {len(bounding_boxes)} bounding boxes")
                return cleaned_text, True, bounding_boxes
            else:
                self.logger.debug("No text extracted by Tesseract")
                return "", False, []
            
        except Exception as e:
            self.logger.error(f"Tesseract OCR with boxes failed: {e}")
            return "", False, []
    
    def is_available(self) -> bool:
        """Check if OCR service is available"""
        return len(self.available_engines) > 0
    
    def get_available_engines(self) -> list:
        """Get list of available OCR engines"""
        return self.available_engines.copy()
    
    def get_preferred_engine(self) -> Optional[str]:
        """Get the preferred OCR engine"""
        return self.preferred_engine

# Global OCR service instance
_ocr_service = None

def get_ocr_service() -> OCRService:
    """Get global OCR service instance"""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service
