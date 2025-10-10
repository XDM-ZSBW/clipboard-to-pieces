"""
Main clipboard monitoring service.
Coordinates clipboard detection, image processing, and Pieces.app upload.
"""

import time
import logging
import signal
import sys
import os
from datetime import datetime
from typing import Optional, Union
import threading
import tempfile
import msvcrt

from clipboard_detector import ClipboardDetector
from image_processor import ImageProcessor
from pieces_client import PiecesUploader

logger = logging.getLogger(__name__)


class ClipboardService:
    """Main clipboard monitoring service."""
    
    def __init__(self, check_interval: int = 2, max_cache_size: int = 100):
        """
        Initialize clipboard service.
        
        Args:
            check_interval: Seconds between clipboard checks
            max_cache_size: Maximum number of processed items to cache
        """
        self.check_interval = check_interval
        self.max_cache_size = max_cache_size
        self.processed_items = {}
        self.running = False
        self.lock = threading.Lock()
        
        # Initialize components
        self.detector = ClipboardDetector()
        self.image_processor = ImageProcessor()
        self.uploader = PiecesUploader()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Service lock file
        self.lock_file = None
        self._acquire_service_lock()
    
    def _acquire_service_lock(self) -> bool:
        """
        Acquire service lock to prevent multiple instances.
        
        Returns:
            True if lock acquired, False otherwise
        """
        try:
            lock_path = os.path.join(tempfile.gettempdir(), "clipboard_service.lock")
            self.lock_file = open(lock_path, 'w')
            msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            self.lock_file.write(str(os.getpid()))
            self.lock_file.flush()
            logger.info("Service lock acquired")
            return True
        except (OSError, IOError) as e:
            logger.error(f"Another instance is already running: {e}")
            return False
    
    def _release_service_lock(self) -> None:
        """Release service lock."""
        try:
            if self.lock_file:
                msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                self.lock_file.close()
                self.lock_file = None
                logger.info("Service lock released")
        except Exception as e:
            logger.error(f"Error releasing service lock: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def start(self) -> None:
        """Start the clipboard monitoring service."""
        if not self._acquire_service_lock():
            logger.error("Cannot start service: another instance is running")
            return
        
        self.running = True
        logger.info("Clipboard service started")
        
        try:
            while self.running:
                self._check_clipboard()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("Service interrupted by user")
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop the clipboard monitoring service."""
        if not self.running:
            return
            
        self.running = False
        logger.info("Clipboard service stopped")
        self._release_service_lock()
    
    def _check_clipboard(self) -> None:
        """Check clipboard for new content."""
        try:
            content_type, content = self.detector.detect_clipboard_content()
            if content_type and content:
                self._process_clipboard_item(content_type, content)
        except Exception as e:
            logger.error(f"Error checking clipboard: {e}")
    
    def _process_clipboard_item(self, content_type: str, content: Union[str, bytes]) -> None:
        """
        Process clipboard item and upload to Pieces.app.
        
        Args:
            content_type: Type of content ("text" or "image")
            content: Content data
        """
        try:
            logger.info(f"Processing {content_type} content")
            
            if content_type == "text":
                self._process_text_content(content)
            elif content_type == "image":
                self._process_image_content(content)
            else:
                logger.warning(f"Unknown content type: {content_type}")
                
        except Exception as e:
            logger.error(f"Error processing clipboard item: {e}")
    
    def _process_text_content(self, text_content: str) -> None:
        """
        Process text content.
        
        Args:
            text_content: Text content to process
        """
        try:
            # Create description
            description = f"Text from clipboard: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Upload to Pieces.app
            asset_id = self.uploader.upload_text(text_content, description)
            
            if asset_id:
                logger.info(f"Text uploaded successfully: {asset_id}")
            else:
                logger.warning("Text upload failed")
                
        except Exception as e:
            logger.error(f"Error processing text content: {e}")
    
    def _process_image_content(self, image_data: Union[str, bytes]) -> None:
        """
        Process image content.
        
        Args:
            image_data: Image data to process
        """
        temp_file_path = None
        
        try:
            # Determine source format
            if isinstance(image_data, str):
                source_format = "base64"
            else:
                source_format = "DIB"
            
            # Process image
            temp_file_path = self.image_processor.process_image(image_data, source_format)
            
            if not temp_file_path:
                logger.error("Image processing failed")
                return
            
            # Create description
            description = f"Screenshot from clipboard: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Upload to Pieces.app
            asset_id = self.uploader.upload_image(temp_file_path, description)
            
            if asset_id:
                logger.info(f"Image uploaded successfully: {asset_id}")
            else:
                logger.warning("Image upload failed")
                
        except Exception as e:
            logger.error(f"Error processing image content: {e}")
        finally:
            # Clean up temporary file
            if temp_file_path:
                self.image_processor.cleanup_temp_file(temp_file_path)
    
    def get_status(self) -> dict:
        """
        Get service status information.
        
        Returns:
            Dictionary with status information
        """
        return {
            "running": self.running,
            "pieces_available": self.uploader.is_available,
            "processed_items": len(self.processed_items),
            "check_interval": self.check_interval,
            "timestamp": datetime.now().isoformat()
        }
    
    def reconnect_pieces(self) -> bool:
        """
        Attempt to reconnect to Pieces.app.
        
        Returns:
            True if reconnection successful, False otherwise
        """
        return self.uploader.reconnect()


def setup_logging(log_level: str = "INFO") -> None:
    """
    Setup logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # Configure logging
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file = os.path.join("logs", "clipboard_service.log")
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger.info(f"Logging configured: {log_level} level, file: {log_file}")


def main():
    """Main entry point for the clipboard service."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clipboard-to-Pieces monitoring service")
    parser.add_argument("--interval", type=int, default=2, 
                       help="Check interval in seconds (default: 2)")
    parser.add_argument("--log-level", default="INFO", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level (default: INFO)")
    parser.add_argument("--test", action="store_true", 
                       help="Run in test mode (single check)")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Create and start service
    service = ClipboardService(check_interval=args.interval)
    
    try:
        if args.test:
            logger.info("Running in test mode")
            service._check_clipboard()
            logger.info("Test completed")
        else:
            service.start()
    except Exception as e:
        logger.error(f"Service error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
