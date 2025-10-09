# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Architecture Overview

This is a Windows-based Python service that monitors clipboard content and automatically imports it to Pieces.app for AI-powered memory management. The architecture consists of:

### Core Components
- **Main Service (`src/robust_clipboard_service.py`)**: The core clipboard monitoring service that:
  - Detects text and image clipboard content using both `pyperclip` and Windows native clipboard APIs
  - Implements duplicate detection with 30-minute windows using MD5 hashing
  - Compresses large images (PNG→JPEG) with quality optimization (85→30% quality levels)
  - Uses PiecesOS SDK for API integration with fallback methods for asset creation
  - Maintains local file storage in `~/.clipboard-to-pieces/` directory
  - Implements process locking to prevent multiple instances

- **Windows Batch Scripts (`scripts/`)**: Service management utilities for starting, stopping, and monitoring the service

### Data Flow
1. **Clipboard Detection**: Service polls clipboard every 2 seconds using Windows clipboard API and pyperclip
2. **Content Processing**: 
   - Text content → Direct import via `PiecesClient.create_asset()` 
   - Image content → Compression pipeline → Binary upload via `assets_create_new_asset()`
3. **Duplicate Prevention**: MD5 hash tracking with 30-minute cache window
4. **Local Storage**: All content saved to `~/.clipboard-to-pieces/` with JSON metadata

### Image Processing Pipeline
- **Detection**: Windows `CF_DIB` format detection + base64 pattern matching
- **Compression**: PIL-based resizing (max 1920x1080) + JPEG quality optimization
- **Upload Strategy**: Simple `create_asset()` method with fallback to complex binary upload
- **Size Limits**: 100KB maximum file size with progressive quality reduction

## Common Development Commands

### Service Management
```powershell
# Quick setup and start
.\setup.bat

# Start service manually
.\scripts\start_clipboard_service.bat

# Stop service
.\scripts\stop_clipboard_service.bat

# Check service status and logs
.\scripts\check_status.bat
```

### Development Testing
```powershell
# Install dependencies only
pip install -r requirements.txt

# Run service directly with logs
cd src
python robust_clipboard_service.py

# Test clipboard detection
python -c "import pyperclip; pyperclip.copy('test'); print('Test copied')"

# Test PiecesOS connection
python -c "from pieces_os_client import PiecesClient; client = PiecesClient(); print('Connected')"

# View live logs
Get-Content logs/robust_clipboard_service.log -Wait -Tail 10

# Search logs for errors
Select-String -Path logs/robust_clipboard_service.log -Pattern "ERROR"
```

### Debugging
```powershell
# Enable debug logging (edit src/robust_clipboard_service.py)
# Change: logging.basicConfig(level=logging.INFO, ...)
# To:     logging.basicConfig(level=logging.DEBUG, ...)

# Clear processed items cache for testing
# In Python: service.clear_processed_cache()

# Manual image compression test
python -c "from src.robust_clipboard_service import RobustClipboardService; s=RobustClipboardService(); print(s.compress_image('test.png'))"

# Test security filter
python test_security_filter.py

# Check security statistics
python -c "from src.robust_clipboard_service import RobustClipboardService; s=RobustClipboardService(); print(s.get_security_statistics())"
```

## Technical Implementation Details

### Dependencies
- **pieces-os-client**: PiecesOS API integration
- **pyperclip**: Cross-platform clipboard access
- **Pillow (PIL)**: Image processing and compression
- **pywin32**: Windows-specific clipboard API access

### Service Architecture Patterns
- **Singleton Pattern**: Process locking prevents multiple instances
- **Strategy Pattern**: Multiple upload methods (simple vs complex binary upload)
- **Template Method**: Standardized content processing pipeline
- **Observer Pattern**: Clipboard polling with event-driven processing

### Error Handling Strategy
- **Graceful Degradation**: API failures don't prevent local file storage
- **Retry Logic**: Multiple image upload strategies with fallbacks  
- **Resource Management**: Automatic cleanup of temporary files and cache entries
- **Connection Recovery**: Client reconnection on PiecesOS failures

### Security Considerations
- **Security Filter**: Built-in sensitive data detection and redaction system
- **Configurable Protection**: Can redact sensitive data or skip importing entirely
- **Pattern-based Detection**: Detects API keys, passwords, tokens, database credentials, etc.
- **Local Storage**: Files stored in user directory with security metadata
- **API Transmission**: Content sent to Pieces.app servers (filtered content only)
- **Process Isolation**: Single instance locking prevents conflicts

## File Structure Significance
```
├── src/robust_clipboard_service.py    # Main service (600+ lines, core logic)
├── scripts/*.bat                      # Windows service management 
├── logs/                             # Service logs (auto-created)
├── requirements.txt                  # Python dependencies
└── setup.bat                        # One-command setup
```

## Integration Points

### PiecesOS API Integration
- **Primary Connection**: `http://localhost:39300` (default PiecesOS port)
- **Asset Creation**: Uses both simple text and complex binary upload methods
- **Application Registration**: Creates default OS_SERVER application if none exists
- **Metadata Management**: Automatic tagging and classification

### Windows Clipboard Integration  
- **Native API**: `win32clipboard` for direct Windows clipboard access
- **Format Detection**: `CF_DIB` for images, text for standard content
- **Fallback Support**: `pyperclip` as secondary clipboard interface

## Development Environment Requirements
- **Python 3.8+** with pip
- **Windows OS** (uses Windows-specific clipboard APIs)
- **Pieces.app installed** and PiecesOS service running
- **Network access** for pip dependencies and Pieces.app communication