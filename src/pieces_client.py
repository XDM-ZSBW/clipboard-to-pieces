"""
Pieces.app client integration module.
Handles uploading content to Pieces.app using the pieces-os-client SDK.
"""

import logging
import os
from datetime import datetime
from typing import Optional, Union
import tempfile

try:
    from pieces_os_client.wrapper import PiecesClient
    from pieces_os_client.models import FragmentMetadata, ClassificationSpecificEnum
    PIECES_AVAILABLE = True
except ImportError:
    PIECES_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("pieces-os-client not available. Install with: pip install pieces-os-client>=4.4.1")

logger = logging.getLogger(__name__)


class PiecesUploader:
    """Handles uploading content to Pieces.app."""
    
    def __init__(self):
        """Initialize Pieces client."""
        self.client = None
        self.is_available = False
        self.backup_dir = ".pieces"
        
        if not PIECES_AVAILABLE:
            logger.error("Pieces SDK not available")
            return
            
        self._initialize_client()
        self._ensure_backup_directory()
    
    def _initialize_client(self) -> None:
        """Initialize Pieces client with error handling."""
        try:
            self.client = PiecesClient()
            # Test connection
            if hasattr(self.client, 'is_pieces_running'):
                if self.client.is_pieces_running():
                    self.is_available = True
                    logger.info("Pieces.app client initialized successfully")
                else:
                    logger.warning("Pieces.app is not running")
            else:
                # Fallback: try a simple operation
                try:
                    # This will fail if Pieces.app is not running
                    self.client.get_assets()
                    self.is_available = True
                    logger.info("Pieces.app client initialized successfully")
                except:
                    logger.warning("Pieces.app is not running or not accessible")
                    
        except Exception as e:
            logger.error(f"Failed to initialize Pieces client: {e}")
            self.is_available = False
    
    def _ensure_backup_directory(self) -> None:
        """Ensure backup directory exists."""
        try:
            if not os.path.exists(self.backup_dir):
                os.makedirs(self.backup_dir)
                logger.info(f"Created backup directory: {self.backup_dir}")
        except Exception as e:
            logger.error(f"Failed to create backup directory: {e}")
    
    def upload_text(self, text_content: str, description: str = None) -> Optional[str]:
        """
        Upload text content to Pieces.app.
        
        Args:
            text_content: Text content to upload
            description: Optional description for the content
            
        Returns:
            Asset ID if successful, None otherwise
        """
        if not self.is_available:
            logger.warning("Pieces.app not available, saving to backup")
            return self._backup_text(text_content, description)
        
        try:
            # Create metadata
            metadata = FragmentMetadata(
                ext=ClassificationSpecificEnum.TXT,
                tags=["clipboard", "auto-imported", "text"],
                description=description or f"Text from clipboard: {datetime.now().isoformat()}"
            )
            
            # Upload text content
            asset_id = self.client.create_asset(text_content, metadata)
            logger.info(f"Text uploaded successfully: {asset_id}")
            return asset_id
            
        except Exception as e:
            logger.error(f"Failed to upload text: {e}")
            return self._backup_text(text_content, description)
    
    def upload_image(self, image_path: str, description: str = None) -> Optional[str]:
        """
        Upload image file to Pieces.app.
        
        Args:
            image_path: Path to image file
            description: Optional description for the image
            
        Returns:
            Asset ID if successful, None otherwise
        """
        if not self.is_available:
            logger.warning("Pieces.app not available, saving to backup")
            return self._backup_image(image_path, description)
        
        try:
            # Create metadata
            metadata = FragmentMetadata(
                ext=ClassificationSpecificEnum.JPG,
                tags=["clipboard", "auto-imported", "image"],
                description=description or f"Image from clipboard: {datetime.now().isoformat()}"
            )
            
            # Upload image file
            asset_id = self.client.create_asset(image_path, metadata)
            logger.info(f"Image uploaded successfully: {asset_id}")
            return asset_id
            
        except Exception as e:
            logger.error(f"Failed to upload image: {e}")
            return self._backup_image(image_path, description)
    
    def upload_content(self, content: Union[str, bytes], content_type: str, 
                      description: str = None) -> Optional[str]:
        """
        Upload content to Pieces.app based on type.
        
        Args:
            content: Content to upload (text string or image bytes)
            content_type: Type of content ("text" or "image")
            description: Optional description
            
        Returns:
            Asset ID if successful, None otherwise
        """
        if content_type == "text":
            return self.upload_text(content, description)
        elif content_type == "image":
            # For image bytes, save to temporary file first
            if isinstance(content, bytes):
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                temp_file.write(content)
                temp_file.close()
                
                try:
                    result = self.upload_image(temp_file.name, description)
                    return result
                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(temp_file.name)
                    except:
                        pass
            else:
                # Assume it's a file path
                return self.upload_image(content, description)
        else:
            logger.error(f"Unknown content type: {content_type}")
            return None
    
    def _backup_text(self, text_content: str, description: str = None) -> Optional[str]:
        """
        Save text content to backup directory.
        
        Args:
            text_content: Text content to save
            description: Optional description
            
        Returns:
            Backup file path if successful, None otherwise
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"text_backup_{timestamp}.txt"
            filepath = os.path.join(self.backup_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                if description:
                    f.write(f"Description: {description}\n")
                    f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                    f.write("-" * 50 + "\n")
                f.write(text_content)
            
            logger.info(f"Text backed up to: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to backup text: {e}")
            return None
    
    def _backup_image(self, image_path: str, description: str = None) -> Optional[str]:
        """
        Save image to backup directory.
        
        Args:
            image_path: Path to image file
            description: Optional description
            
        Returns:
            Backup file path if successful, None otherwise
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"image_backup_{timestamp}.jpg"
            backup_path = os.path.join(self.backup_dir, filename)
            
            # Copy image file
            import shutil
            shutil.copy2(image_path, backup_path)
            
            # Create description file
            desc_filename = f"image_backup_{timestamp}.txt"
            desc_path = os.path.join(self.backup_dir, desc_filename)
            
            with open(desc_path, 'w', encoding='utf-8') as f:
                f.write(f"Description: {description or 'Image from clipboard'}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Original file: {image_path}\n")
                f.write(f"Backup file: {backup_path}\n")
            
            logger.info(f"Image backed up to: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to backup image: {e}")
            return None
    
    def is_pieces_running(self) -> bool:
        """
        Check if Pieces.app is running and accessible.
        
        Returns:
            True if Pieces.app is available, False otherwise
        """
        if not self.is_available:
            return False
            
        try:
            if hasattr(self.client, 'is_pieces_running'):
                return self.client.is_pieces_running()
            else:
                # Fallback: try a simple operation
                self.client.get_assets()
                return True
        except:
            self.is_available = False
            return False
    
    def reconnect(self) -> bool:
        """
        Attempt to reconnect to Pieces.app.
        
        Returns:
            True if reconnection successful, False otherwise
        """
        logger.info("Attempting to reconnect to Pieces.app...")
        self._initialize_client()
        return self.is_available


def test_pieces_client():
    """Test function for Pieces client."""
    uploader = PiecesUploader()
    
    if not uploader.is_available:
        print("Pieces.app not available. Testing backup functionality...")
        
        # Test text backup
        result = uploader.upload_text("Test text content", "Test description")
        print(f"Text upload result: {result}")
        
        # Test image backup
        test_image = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        test_image.write(b"fake image data")
        test_image.close()
        
        result = uploader.upload_image(test_image.name, "Test image")
        print(f"Image upload result: {result}")
        
        # Cleanup
        try:
            os.unlink(test_image.name)
        except:
            pass
    else:
        print("Pieces.app is available. Testing upload functionality...")
        
        # Test text upload
        result = uploader.upload_text("Test text content", "Test description")
        print(f"Text upload result: {result}")
        
        # Test image upload
        test_image = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        test_image.write(b"fake image data")
        test_image.close()
        
        result = uploader.upload_image(test_image.name, "Test image")
        print(f"Image upload result: {result}")
        
        # Cleanup
        try:
            os.unlink(test_image.name)
        except:
            pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_pieces_client()
