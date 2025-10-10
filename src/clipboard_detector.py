"""
Clipboard detection module for Windows clipboard monitoring.
Handles both text and image content detection using pyperclip and win32clipboard.
"""

import pyperclip
import win32clipboard
import win32con
import logging
import hashlib
from typing import Tuple, Optional, Union

logger = logging.getLogger(__name__)


class ClipboardDetector:
    """Detects clipboard content changes and handles different content types."""
    
    def __init__(self):
        self.last_content_hash = None
        self.last_detection_time = 0
        
    def detect_clipboard_content(self) -> Tuple[Optional[str], Optional[Union[str, bytes]]]:
        """
        Detect clipboard content type and return data.
        
        Returns:
            Tuple of (content_type, content) where:
            - content_type: "text", "image", or None
            - content: string for text, bytes/string for image, or None
        """
        try:
            # Try Windows clipboard first for images
            win32clipboard.OpenClipboard()
            
            # Check for DIB (Device Independent Bitmap) format
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIB):
                image_data = win32clipboard.GetClipboardData(win32con.CF_DIB)
                win32clipboard.CloseClipboard()
                
                # Create hash for duplicate detection
                content_hash = hashlib.md5(image_data).hexdigest()
                if self._is_duplicate(content_hash):
                    return None, None
                    
                self.last_content_hash = content_hash
                return "image", image_data
            
            win32clipboard.CloseClipboard()
            
            # Fallback to pyperclip for text/base64
            content = pyperclip.paste()
            if not content or not content.strip():
                return None, None
                
            # Check if content is base64 image data
            if content.startswith(('iVBORw0KGgo', '/9j/', 'data:image')):
                content_hash = hashlib.md5(content.encode()).hexdigest()
                if self._is_duplicate(content_hash):
                    return None, None
                    
                self.last_content_hash = content_hash
                return "image", content
            
            # Regular text content
            content_hash = hashlib.md5(content.encode()).hexdigest()
            if self._is_duplicate(content_hash):
                return None, None
                
            self.last_content_hash = content_hash
            return "text", content
            
        except Exception as e:
            logger.error(f"Error detecting clipboard content: {e}")
            try:
                win32clipboard.CloseClipboard()
            except:
                pass
            return None, None
    
    def _is_duplicate(self, content_hash: str) -> bool:
        """
        Check if content is a duplicate within the last 30 seconds.
        
        Args:
            content_hash: MD5 hash of the content
            
        Returns:
            True if duplicate, False otherwise
        """
        import time
        current_time = time.time()
        
        # If same content and within 30 seconds, consider duplicate
        if (self.last_content_hash == content_hash and 
            current_time - self.last_detection_time < 30):
            return True
            
        self.last_detection_time = current_time
        return False
    
    def get_clipboard_text(self) -> Optional[str]:
        """
        Get text content from clipboard.
        
        Returns:
            Text content or None if no text available
        """
        try:
            content = pyperclip.paste()
            return content if content and content.strip() else None
        except Exception as e:
            logger.error(f"Error getting clipboard text: {e}")
            return None
    
    def get_clipboard_image(self) -> Optional[bytes]:
        """
        Get image data from Windows clipboard.
        
        Returns:
            Image data as bytes or None if no image available
        """
        try:
            win32clipboard.OpenClipboard()
            
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIB):
                image_data = win32clipboard.GetClipboardData(win32con.CF_DIB)
                win32clipboard.CloseClipboard()
                return image_data
            
            win32clipboard.CloseClipboard()
            return None
            
        except Exception as e:
            logger.error(f"Error getting clipboard image: {e}")
            try:
                win32clipboard.CloseClipboard()
            except:
                pass
            return None


def test_clipboard_detection():
    """Test function for clipboard detection."""
    detector = ClipboardDetector()
    
    print("Clipboard detector test - copy some text or an image to clipboard")
    print("Press Ctrl+C to stop...")
    
    try:
        while True:
            content_type, content = detector.detect_clipboard_content()
            if content_type:
                if content_type == "text":
                    print(f"Text detected: {content[:50]}...")
                elif content_type == "image":
                    print(f"Image detected: {len(content)} bytes")
            
            import time
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nTest stopped.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_clipboard_detection()
