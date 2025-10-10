# OCR Setup Guide - Privacy-Focused Tesseract Only

This guide explains how to set up OCR (Optical Character Recognition) for the clipboard-to-pieces service using Tesseract only for maximum privacy.

## Overview

The OCR service uses **Tesseract only** for privacy-focused text extraction from screenshots. This ensures:
- **No proprietary APIs**: Uses open-source Tesseract OCR engine
- **Local processing**: All OCR happens on your machine
- **No cloud services**: No data sent to external services
- **Cross-platform**: Works on Windows, macOS, and Linux

## Privacy Benefits

- **Open Source**: Tesseract is completely open source
- **Local Processing**: All OCR processing happens locally
- **No Telemetry**: No usage data sent to Microsoft, Apple, or Google
- **Configurable**: Full control over OCR settings and behavior
- **Transparent**: You can inspect and modify the OCR engine

## Platform Support

### Windows
- **Tesseract OCR** (Required)
  - Download from: https://github.com/UB-Mannheim/tesseract/wiki
  - Install with default settings
  - Add to PATH or set TESSDATA_PREFIX environment variable

### macOS
- **Tesseract OCR** (Required)
  - Install via Homebrew: `brew install tesseract`
  - Automatically available after installation

### Linux
- **Tesseract OCR** (Required)
  - Install via package manager:
    - Ubuntu/Debian: `sudo apt install tesseract-ocr`
    - CentOS/RHEL: `sudo yum install tesseract`
    - Arch: `sudo pacman -S tesseract`

## Installation

### Installation Steps

#### Windows
1. Download Tesseract installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install with default settings
3. Add Tesseract to PATH or set `TESSDATA_PREFIX` environment variable
4. Restart the clipboard service

#### macOS
```bash
# Install Tesseract via Homebrew
brew install tesseract

# Verify installation
tesseract --version
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install tesseract-ocr

# CentOS/RHEL
sudo yum install tesseract

# Arch Linux
sudo pacman -S tesseract

# Verify installation
tesseract --version
```

## Configuration

OCR settings are configured in `security_config.json`:

```json
{
  "ocr": {
    "enabled": true,
    "engine": "tesseract",
    "extract_text_from_images": true,
    "apply_security_filtering": true,
    "skip_images_with_sensitive_text": false,
    "privacy_mode": true,
    "local_processing_only": true
  }
}
```

### Configuration Options

- **enabled**: Enable/disable OCR functionality
- **engine**: "tesseract" (only option for privacy)
- **extract_text_from_images**: Extract text from screenshots
- **apply_security_filtering**: Apply security filters to extracted text
- **skip_images_with_sensitive_text**: Skip importing images with sensitive content
- **privacy_mode**: Enable privacy-focused processing (always true)
- **local_processing_only**: Ensure all processing happens locally (always true)
- **visual_redaction**: Draw black rectangles over sensitive areas in images (default: true)

## How It Works

1. **Screenshot Detection**: When a screenshot is copied to clipboard
2. **Local OCR Processing**: Text is extracted using Tesseract OCR with precise bounding boxes (local only)
3. **Security Filtering**: Extracted text is analyzed for sensitive patterns
4. **Visual Redaction**: Black rectangles are drawn over sensitive areas in the image
5. **Privacy Action**: Based on configuration:
   - Log sensitive content detection (locally)
   - Redact sensitive text in metadata
   - Skip image import entirely
   - Continue with normal processing

## Security Patterns Detected

The OCR service detects the same sensitive patterns as text filtering:

- **Passwords**: password, pass, pwd fields
- **API Keys**: api_key, access_key, secret_key
- **Tokens**: bearer tokens, auth tokens
- **Database URLs**: connection strings, database URLs
- **SSH Keys**: private key blocks
- **Personal Information**: emails, credit cards, SSNs
- **Custom Patterns**: Configurable in security_config.json

## Troubleshooting

### OCR Not Working
1. Check if OCR is enabled in configuration
2. Verify OCR engine is available: Check service startup logs
3. Test with a simple text image
4. Check dependencies are installed

### Poor OCR Accuracy
1. Ensure image quality is good (high contrast, clear text)
2. Adjust Tesseract configuration in `src/ocr_service.py`
3. Adjust image compression settings
4. Use higher resolution screenshots
5. Consider installing additional Tesseract language packs

### Performance Issues
1. OCR processing adds ~1-3 seconds per screenshot
2. Consider disabling OCR for high-volume usage
3. Reduce image size before OCR processing
4. Adjust Tesseract configuration for speed vs accuracy

## Logs and Monitoring

OCR activity is logged with the following information:
- OCR engine used (Tesseract)
- Text extraction success/failure
- Number of characters extracted
- Security filtering results
- Sensitive content detection

Example log entries:
```
2025-01-09 10:30:15 - INFO - Tesseract OCR engine detected and enabled
2025-01-09 10:30:15 - INFO - OCR service available - engines: ['tesseract'], preferred: tesseract
2025-01-09 10:30:15 - INFO - Screenshots will be OCR'd for sensitive content detection
2025-01-09 10:30:20 - INFO - Extracting text from image using OCR...
2025-01-09 10:30:22 - INFO - Tesseract extracted 156 characters
2025-01-09 10:30:22 - INFO - Security filter applied to OCR text: 2 sensitive items processed
```

## Privacy Considerations

- **Local Processing Only**: OCR text extraction is performed locally using Tesseract
- **No External Services**: No OCR data is sent to Microsoft, Apple, Google, or any cloud services
- **Open Source**: Tesseract is completely open source and auditable
- **No Telemetry**: No usage data or analytics collected
- **Temporary Processing**: Extracted text is only used for security filtering
- **No Permanent Storage**: OCR results are not stored permanently
- **Memory-Based**: Images are processed in memory with temporary files
- **Configurable**: Full control over OCR settings and behavior

## Advanced Configuration

### Custom OCR Settings
For Tesseract users, you can customize OCR settings by modifying the `_extract_text_tesseract` method in `src/ocr_service.py`:

```python
# Example: Use different OCR modes
text = pytesseract.image_to_string(image, config='--psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')
```

### Language Support
Tesseract supports multiple languages. Install language packs and specify language:

```python
# Example: OCR in Spanish
text = pytesseract.image_to_string(image, lang='spa')
```

## Support

For issues with OCR functionality:
1. Check the service logs for error messages
2. Verify OCR engine installation
3. Test with simple text images
4. Check configuration settings
5. Review platform-specific requirements
