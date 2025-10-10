"""
Image processing module for compressing and optimizing images.
Handles image compression, resizing, and format conversion for Pieces.app upload.
"""

import os
import tempfile
import logging
from PIL import Image, ImageOps
from typing import Optional, Tuple
import io
import base64

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Processes and compresses images for optimal upload to Pieces.app."""
    
    def __init__(self, max_size_bytes: int = 500000, max_dimensions: Tuple[int, int] = (1920, 1080)):
        """
        Initialize image processor.
        
        Args:
            max_size_bytes: Maximum file size in bytes (default 500KB)
            max_dimensions: Maximum dimensions as (width, height)
        """
        self.max_size_bytes = max_size_bytes
        self.max_dimensions = max_dimensions
        
    def process_image(self, image_data: bytes, source_format: str = "DIB") -> Optional[str]:
        """
        Process image data and return path to compressed image file.
        
        Args:
            image_data: Raw image data
            source_format: Source format ("DIB", "base64", etc.)
            
        Returns:
            Path to temporary compressed image file or None if processing failed
        """
        try:
            # Convert DIB to PIL Image
            if source_format == "DIB":
                image = self._dib_to_pil_image(image_data)
            elif source_format == "base64":
                image = self._base64_to_pil_image(image_data)
            else:
                # Assume it's already bytes that can be opened by PIL
                image = Image.open(io.BytesIO(image_data))
            
            if not image:
                logger.error("Failed to convert image data to PIL Image")
                return None
            
            # Process the image
            processed_image = self._compress_image(image)
            if not processed_image:
                logger.error("Failed to compress image")
                return None
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            processed_image.save(temp_file.name, 'JPEG', quality=85, optimize=True)
            temp_file.close()
            
            logger.info(f"Image processed successfully: {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return None
    
    def _dib_to_pil_image(self, dib_data: bytes) -> Optional[Image.Image]:
        """
        Convert Windows DIB (Device Independent Bitmap) to PIL Image.
        
        Args:
            dib_data: Raw DIB data
            
        Returns:
            PIL Image or None if conversion failed
        """
        try:
            # DIB format starts with BITMAPINFOHEADER
            # We need to create a proper BMP file from DIB data
            bmp_data = self._dib_to_bmp(dib_data)
            if bmp_data:
                return Image.open(io.BytesIO(bmp_data))
            return None
        except Exception as e:
            logger.error(f"Error converting DIB to PIL Image: {e}")
            return None
    
    def _dib_to_bmp(self, dib_data: bytes) -> Optional[bytes]:
        """
        Convert DIB data to BMP format.
        
        Args:
            dib_data: Raw DIB data
            
        Returns:
            BMP data as bytes or None if conversion failed
        """
        try:
            # DIB to BMP conversion
            # BMP header is 14 bytes, DIB header starts after that
            if len(dib_data) < 14:
                return None
                
            # Extract dimensions from BITMAPINFOHEADER
            width = int.from_bytes(dib_data[4:8], 'little')
            height = int.from_bytes(dib_data[8:12], 'little')
            bits_per_pixel = int.from_bytes(dib_data[14:16], 'little')
            
            # Calculate row padding
            row_size = ((width * bits_per_pixel + 31) // 32) * 4
            image_size = row_size * abs(height)
            
            # Create BMP header
            bmp_header = bytearray(14)
            bmp_header[0:2] = b'BM'  # Signature
            bmp_header[2:6] = (14 + len(dib_data)).to_bytes(4, 'little')  # File size
            bmp_header[6:10] = b'\x00\x00\x00\x00'  # Reserved
            bmp_header[10:14] = (14).to_bytes(4, 'little')  # Data offset
            
            return bytes(bmp_header) + dib_data
            
        except Exception as e:
            logger.error(f"Error converting DIB to BMP: {e}")
            return None
    
    def _base64_to_pil_image(self, base64_data: str) -> Optional[Image.Image]:
        """
        Convert base64 image data to PIL Image.
        
        Args:
            base64_data: Base64 encoded image data
            
        Returns:
            PIL Image or None if conversion failed
        """
        try:
            # Remove data URL prefix if present
            if base64_data.startswith('data:image'):
                base64_data = base64_data.split(',')[1]
            
            # Decode base64 data
            image_bytes = base64.b64decode(base64_data)
            return Image.open(io.BytesIO(image_bytes))
            
        except Exception as e:
            logger.error(f"Error converting base64 to PIL Image: {e}")
            return None
    
    def _compress_image(self, image: Image.Image) -> Optional[Image.Image]:
        """
        Compress image to meet size and dimension requirements.
        
        Args:
            image: PIL Image to compress
            
        Returns:
            Compressed PIL Image or None if compression failed
        """
        try:
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                # Create white background for transparency
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if too large
            if image.size[0] > self.max_dimensions[0] or image.size[1] > self.max_dimensions[1]:
                image.thumbnail(self.max_dimensions, Image.Resampling.LANCZOS)
                logger.info(f"Image resized to: {image.size}")
            
            # Auto-orient based on EXIF data
            image = ImageOps.exif_transpose(image)
            
            return image
            
        except Exception as e:
            logger.error(f"Error compressing image: {e}")
            return None
    
    def save_image_with_quality(self, image: Image.Image, output_path: str) -> bool:
        """
        Save image with optimal quality to meet size requirements.
        
        Args:
            image: PIL Image to save
            output_path: Path to save the image
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Try different quality levels
            for quality in [90, 85, 70, 50, 30]:
                image.save(output_path, 'JPEG', quality=quality, optimize=True)
                
                # Check if file size meets requirements
                if os.path.getsize(output_path) <= self.max_size_bytes:
                    logger.info(f"Image saved with quality {quality}, size: {os.path.getsize(output_path)} bytes")
                    return True
            
            # If still too large, resize further
            logger.warning("Image still too large after quality reduction, resizing further")
            while os.path.getsize(output_path) > self.max_size_bytes:
                new_size = (int(image.size[0] * 0.8), int(image.size[1] * 0.8))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                image.save(output_path, 'JPEG', quality=30, optimize=True)
                
                if image.size[0] < 100 or image.size[1] < 100:
                    logger.error("Image too small after compression")
                    return False
            
            logger.info(f"Image saved after additional resizing, size: {os.path.getsize(output_path)} bytes")
            return True
            
        except Exception as e:
            logger.error(f"Error saving image: {e}")
            return False
    
    def cleanup_temp_file(self, file_path: str) -> None:
        """
        Clean up temporary file.
        
        Args:
            file_path: Path to temporary file to delete
        """
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.debug(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up temporary file {file_path}: {e}")


def test_image_processor():
    """Test function for image processor."""
    processor = ImageProcessor()
    
    # Test with a simple image
    try:
        # Create a test image
        test_image = Image.new('RGB', (100, 100), color='red')
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        test_image.save(temp_file.name, 'JPEG')
        temp_file.close()
        
        # Read the image data
        with open(temp_file.name, 'rb') as f:
            image_data = f.read()
        
        # Process the image
        result_path = processor.process_image(image_data, "bytes")
        if result_path:
            print(f"Image processed successfully: {result_path}")
            print(f"File size: {os.path.getsize(result_path)} bytes")
            processor.cleanup_temp_file(result_path)
        else:
            print("Image processing failed")
        
        # Cleanup test file
        processor.cleanup_temp_file(temp_file.name)
        
    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_image_processor()
