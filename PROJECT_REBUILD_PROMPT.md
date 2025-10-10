# Clipboard-to-Pieces Project Rebuild Prompt

## Project Overview
Create a Windows clipboard monitoring service that automatically imports text and screenshots into Pieces.app. The service should detect clipboard changes, compress images, and upload content directly to Pieces.app via API.

## Core Requirements

### 1. Clipboard Monitoring
- Monitor Windows clipboard every 2 seconds
- Detect both text and image content
- Use `pyperclip` for text and `win32clipboard` for images
- Implement duplicate detection (30-second window)

### 2. Image Processing
- Compress images to under 500KB
- Resize large images to max 1920x1080
- Convert to JPEG format for efficiency
- Use PIL (Pillow) for image manipulation

### 3. Pieces.app Integration
- Use `pieces-os-client` SDK version 4.4.1+
- Upload content directly via `client.create_asset(file_path, metadata)`
- Create proper metadata with tags and descriptions
- Handle both text and image uploads

### 4. Error Handling
- Graceful fallback if Pieces.app is not running
- Save backup files to `.pieces` directory
- Comprehensive logging
- Prevent multiple service instances

## Technical Implementation

### Dependencies
```python
# Core dependencies
pyperclip>=1.11.0
Pillow>=10.0.0
pieces-os-client>=4.4.1
pywin32>=306  # For Windows clipboard access

# Optional for advanced features
pytesseract>=0.3.10  # OCR support
```

### Key Components

#### 1. Clipboard Detection
```python
def detect_clipboard_content():
    """Detect clipboard content type and return data"""
    try:
        # Try Windows clipboard first for images
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIB):
            image_data = win32clipboard.GetClipboardData(win32con.CF_DIB)
            win32clipboard.CloseClipboard()
            return "image", image_data
        
        # Fallback to pyperclip for text/base64
        content = pyperclip.paste()
        if content.startswith(('iVBORw0KGgo', '/9j/')):
            return "image", content
        elif content.strip():
            return "text", content
        
        return None, None
    except Exception as e:
        return None, None
```

#### 2. Image Compression
```python
def compress_image(image_path, max_size=500000, max_dimensions=(1920, 1080)):
    """Compress image to reduce size"""
    with Image.open(image_path) as img:
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        # Resize if too large
        if img.size[0] > max_dimensions[0] or img.size[1] > max_dimensions[1]:
            img.thumbnail(max_dimensions, Image.Resampling.LANCZOS)
        
        # Save with quality compression
        compressed_path = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        for quality in [90, 85, 70, 50]:
            img.save(compressed_path.name, 'JPEG', quality=quality, optimize=True)
            if os.path.getsize(compressed_path.name) <= max_size:
                break
        
        return compressed_path.name
```

#### 3. Pieces.app Upload
```python
def upload_to_pieces(content_or_path, content_type):
    """Upload content directly to Pieces.app"""
    try:
        client = PiecesClient()
        
        metadata = FragmentMetadata(
            ext=ClassificationSpecificEnum.JPG if content_type == "image" else ClassificationSpecificEnum.TXT,
            tags=["clipboard", "auto-imported"],
            description=f"{content_type.title()} from clipboard: {datetime.now().isoformat()}"
        )
        
        # Use file path for images, content for text
        if content_type == "image":
            asset_id = client.create_asset(content_or_path, metadata)
        else:
            asset_id = client.create_asset(content_or_path, metadata)
        
        return asset_id
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return None
```

### Critical Success Factors

#### 1. Avoid SDK Issues
- **DO NOT** use `SeededAsset`, `TransferableBytes`, or complex binary upload methods
- **USE** simple `client.create_asset(file_path, metadata)` for images
- **USE** `client.create_asset(content, metadata)` for text
- **AVOID** `transferables=True` parameter (causes validation errors)

#### 2. Proper Error Handling
```python
# Always wrap Pieces client initialization
try:
    client = PiecesClient()
    pieces_available = True
except Exception as e:
    logger.warning(f"Pieces.app not available: {e}")
    pieces_available = False
```

#### 3. File Management
- Save temporary images to `tempfile.NamedTemporaryFile()`
- Clean up temporary files in `finally` blocks
- Save backup files to `.pieces` directory
- Use proper file path handling for Windows

#### 4. Service Architecture
```python
class ClipboardService:
    def __init__(self):
        self.pieces_client = None
        self.processed_items = {}
        self.max_cache_size = 100
        
    def run_service(self):
        while True:
            content_type, content = self.detect_clipboard_content()
            if content_type and content:
                self.process_clipboard_item(content_type, content)
            time.sleep(2)
```

## File Structure
```
clipboard-to-pieces/
├── src/
│   ├── clipboard_service.py      # Main service
│   ├── image_processor.py        # Image compression
│   └── pieces_client.py          # Pieces.app integration
├── requirements.txt              # Dependencies
├── setup.bat                     # Windows setup script
├── start_service.bat             # Service launcher
└── README.md                     # Documentation
```

## Testing Checklist

### Basic Functionality
- [ ] Service starts without errors
- [ ] Text clipboard detection works
- [ ] Image clipboard detection works
- [ ] Duplicate detection prevents reprocessing
- [ ] Service stops gracefully with Ctrl+C

### Image Processing
- [ ] Screenshots are detected correctly
- [ ] Images are compressed under 500KB
- [ ] Large images are resized appropriately
- [ ] JPEG conversion works
- [ ] Temporary files are cleaned up

### Pieces.app Integration
- [ ] Text uploads work
- [ ] Image uploads work
- [ ] Metadata is created correctly
- [ ] Assets appear in Pieces.app
- [ ] Graceful fallback when Pieces.app unavailable

### Error Handling
- [ ] Multiple instances prevented
- [ ] Invalid clipboard data handled
- [ ] Network errors handled
- [ ] File system errors handled
- [ ] Logging is comprehensive

## Common Pitfalls to Avoid

### 1. SDK Version Issues
- Use `pieces-os-client>=4.4.1`
- Avoid deprecated methods
- Test with simple `create_asset` calls first

### 2. Clipboard Access
- Use both `pyperclip` and `win32clipboard`
- Handle different image formats
- Implement proper error handling

### 3. Image Processing
- Always convert to RGB before processing
- Use appropriate quality settings
- Clean up temporary files

### 4. Service Management
- Implement proper locking mechanism
- Handle service interruption
- Prevent memory leaks with cache management

## Quick Start Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run service
python src/clipboard_service.py

# Test with clipboard content
# Copy text or take screenshot, then check Pieces.app
```

## Success Criteria
- Service runs continuously without crashes
- Text and images appear in Pieces.app within 5 seconds
- No duplicate processing of same content
- Proper error messages in logs
- Clean shutdown and resource cleanup

## Troubleshooting

### If images don't appear in Pieces.app:
1. Check if Pieces.app is running
2. Verify API connection with `client.is_pieces_running()`
3. Test direct upload with existing image file
4. Check logs for upload errors

### If service crashes:
1. Check for multiple instances
2. Verify all dependencies installed
3. Check Windows clipboard permissions
4. Review error logs

### If performance issues:
1. Adjust compression quality settings
2. Increase duplicate detection window
3. Optimize image processing pipeline
4. Monitor memory usage

This prompt ensures a robust, working clipboard-to-pieces service that avoids the common pitfalls encountered in previous implementations.

