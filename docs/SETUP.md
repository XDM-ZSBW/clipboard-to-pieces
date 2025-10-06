# Detailed Setup Guide

## Prerequisites

### 1. Python Installation
- Download and install Python 3.8 or higher from [python.org](https://www.python.org/downloads/)
- Ensure Python is added to your system PATH
- Verify installation: `python --version`

### 2. Pieces.app Installation
- Download and install Pieces.app from [pieces.app](https://pieces.app)
- Launch Pieces.app and ensure it's running
- Verify PiecesOS service is active (usually on port 39300)

### 3. System Requirements
- Windows 10/11 (for win32clipboard support)
- At least 4GB RAM
- 1GB free disk space

## Installation Steps

### Step 1: Clone Repository
```bash
git clone https://github.com/yourusername/clipboard-to-pieces.git
cd clipboard-to-pieces
```

### Step 2: Create Virtual Environment (Recommended)
```bash
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Verify Installation
```bash
# Test PiecesOS connection
python -c "from pieces_os_client import PiecesClient; client = PiecesClient(); print('Connected:', client.applications_api.applications_snapshot())"

# Test clipboard access
python -c "import pyperclip; pyperclip.copy('test'); print('Clipboard test successful')"
```

## Configuration

### Service Configuration
The service uses default settings that work for most users. To customize:

1. Edit `src/robust_clipboard_service.py`
2. Modify these variables in the `__init__` method:
   - `check_interval`: How often to check clipboard (default: 2 seconds)
   - `max_image_size`: Maximum image size in bytes (default: 100KB)
   - `max_dimensions`: Maximum image dimensions (default: 1920x1080)

### Logging Configuration
To change logging level:
1. Edit `src/robust_clipboard_service.py`
2. Change `logging.basicConfig(level=logging.INFO)` to `logging.basicConfig(level=logging.DEBUG)`

## Running the Service

### Method 1: Direct Execution
```bash
cd src
python robust_clipboard_service.py
```

### Method 2: Using Batch Scripts
```bash
# Start service
scripts\start_clipboard_service.bat

# Check status
scripts\check_status.bat

# Stop service
scripts\stop_clipboard_service.bat
```

### Method 3: Background Service (Advanced)
For running as a Windows service, you can use tools like:
- NSSM (Non-Sucking Service Manager)
- Windows Task Scheduler
- Custom service wrapper

## Troubleshooting

### Common Issues

**"Another instance is already running"**
- Stop existing service: `scripts\stop_clipboard_service.bat`
- Or kill Python processes: `taskkill /f /im python.exe`

**"PiecesOS connection failed"**
- Ensure Pieces.app is running
- Check if port 39300 is accessible
- Restart Pieces.app

**"Clipboard access denied"**
- Run as administrator
- Check Windows clipboard service
- Restart Windows Explorer

**"Image compression failed"**
- Check PIL/Pillow installation
- Verify image format support
- Check available disk space

### Debug Mode
Enable debug logging for detailed troubleshooting:
1. Edit `src/robust_clipboard_service.py`
2. Change logging level to DEBUG
3. Restart service
4. Check logs for detailed information

### Log Analysis
```bash
# View recent logs
Get-Content logs\robust_clipboard_service.log -Tail 20

# Search for errors
Select-String -Path logs\robust_clipboard_service.log -Pattern "ERROR"

# Monitor live logs
Get-Content logs\robust_clipboard_service.log -Wait -Tail 10
```

## Performance Optimization

### System Resources
- The service uses minimal CPU and memory
- Typical usage: <1% CPU, <50MB RAM
- Image compression may temporarily use more CPU

### Network Usage
- Only connects to localhost:39300 (PiecesOS)
- No external network connections
- Image uploads may use bandwidth during compression

### Storage Usage
- Logs: ~1MB per day of operation
- Temporary files: Automatically cleaned up
- .pieces directory: Grows with imported content

## Security Considerations

### Local Access Only
- Service only accesses local clipboard
- No external network connections
- All data stays on local machine

### File Permissions
- Service creates files in user's home directory
- No system-level file access required
- Logs contain no sensitive information

### Clipboard Privacy
- Service only reads clipboard content
- Does not modify or share clipboard data
- All processing happens locally

## Advanced Configuration

### Custom Image Processing
To modify image compression settings:
```python
# In robust_clipboard_service.py __init__ method
self.max_image_size = 200000  # 200KB limit
self.max_dimensions = (2560, 1440)  # 1440p max
```

### Custom File Naming
To change file naming convention:
```python
def create_filename(self, content_type):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if content_type == "image":
        return f"IMG_{timestamp}.jpg"
    else:
        return f"TXT_{timestamp}.txt"
```

### Custom Metadata
To add custom tags or descriptions:
```python
metadata = FragmentMetadata(
    ext=ClassificationSpecificEnum.TXT,
    tags=["text", "clipboard", "auto-imported", "custom-tag"],
    description="Custom description for imported content"
)
```

## Support and Maintenance

### Regular Maintenance
- Monitor log file size (rotate if >100MB)
- Check .pieces directory for old files
- Update dependencies periodically

### Updates
- Check for PiecesOS SDK updates
- Update Python dependencies: `pip install -r requirements.txt --upgrade`
- Monitor Pieces.app updates for compatibility

### Backup
- Backup .pieces directory for imported content
- Backup configuration if customized
- Export logs for troubleshooting

## Getting Help

### Documentation
- Check this setup guide
- Review README.md for general information
- Check Pieces.app documentation for API details

### Community Support
- GitHub Issues for bug reports
- GitHub Discussions for questions
- Pieces.app community for general support

### Professional Support
- Contact Pieces.app support for API issues
- Consider professional Python development services for customizations
