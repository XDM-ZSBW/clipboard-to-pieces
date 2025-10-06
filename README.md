# Clipboard to Pieces v2.0.0

A lightweight clipboard monitoring service that automatically imports your clipboard content (text and images) into Pieces.app Drive for AI-powered memory management.

## ⚠️ **SECURITY WARNING - READ BEFORE USE**

**This service monitors and processes ALL clipboard content on your system. Use with extreme caution on development machines.**

### **Critical Security Risks:**

1. **🔐 Sensitive Data Exposure**: 
   - **Passwords, API keys, tokens, and credentials** copied to clipboard will be captured
   - **Private code, proprietary information** may be processed and stored
   - **Personal data, financial information** could be logged or transmitted

2. **🛡️ Development Environment Risks**:
   - **Database connection strings** with credentials
   - **SSH keys, certificates, and private keys**
   - **Configuration files** containing sensitive settings
   - **Debug information** with internal system details

3. **📡 Data Transmission**:
   - Content is sent to Pieces.app via PiecesOS API
   - Images are compressed and uploaded to Pieces.app servers
   - Text content is processed by Pieces.app's AI systems

### **Recommended Usage Guidelines:**

- ✅ **Use only on trusted, secure development machines**
- ✅ **Review all clipboard content before copying sensitive data**
- ✅ **Consider using a separate, isolated environment for testing**
- ✅ **Regularly audit Pieces.app for any sensitive content**
- ❌ **DO NOT use on production systems or shared workstations**
- ❌ **DO NOT use when handling customer data or PII**
- ❌ **DO NOT use when working with financial or healthcare data**

### **Data Privacy Considerations:**

- All imported content becomes part of your Pieces.app data
- Pieces.app may use this data for AI training and improvement
- Consider the privacy implications of your organization's data policies
- Ensure compliance with your company's security and privacy requirements

## 🎯 What It Does

This service runs in the background and automatically:
- **Monitors your clipboard** every 2 seconds
- **Detects text and image content** 
- **Compresses large images** (PNG → JPEG) for optimal storage
- **Imports content to Pieces.app Drive** using the PiecesOS API
- **Creates searchable memories** for AI assistance and context sharing

## 🚀 Features

- **🔄 Automatic Clipboard Monitoring**: Runs continuously in the background
- **📝 Text Import**: Captures and imports text content to Pieces.app
- **🖼️ Image Import**: Captures screenshots and images with automatic compression
- **🗜️ Smart Compression**: Converts large PNG files to optimized JPEG format
- **🔍 Duplicate Detection**: Prevents importing the same content multiple times
- **📊 Detailed Logging**: Comprehensive logging with configurable verbosity
- **⚡ Lightweight**: Minimal resource usage, focused on core functionality
- **🔧 Easy Setup**: Simple installation and configuration

## 🛠️ Tech Stack

- **Python 3.8+** with PiecesOS SDK
- **PIL (Pillow)** for image processing and compression
- **pyperclip** for clipboard monitoring
- **win32clipboard** for Windows clipboard access
- **Logging** for service monitoring and debugging

## 📦 Installation

### Prerequisites

- Python 3.8+
- Pieces.app installed and running
- PiecesOS service running (usually on port 39300)

### Quick Start

1. **Clone the repository:**
```bash
git clone https://github.com/ZSBW/clipboard-to-pieces.git
cd clipboard-to-pieces
```

2. **Run setup (automatically installs dependencies):**
```bash
# Windows
setup.bat

# Or start directly (dependencies auto-installed)
scripts/start_clipboard_service.bat
```

3. **That's it!** The service will automatically:
   - Check Python installation
   - Install required dependencies
   - Start monitoring your clipboard

## ⚙️ Configuration

### Service Settings

The service is configured with sensible defaults:

- **Check Interval**: 2 seconds
- **Max Image Size**: 100KB (compressed)
- **Image Quality**: 85% JPEG quality
- **Log Level**: INFO (set to DEBUG for verbose output)
- **Log Location**: `logs/robust_clipboard_service.log`

### Pieces.app Integration

The service automatically connects to PiecesOS on `localhost:39300`. Ensure:
- Pieces.app is running
- PiecesOS service is active
- No firewall blocking port 39300

## 🎯 Usage

### Starting the Service

```bash
# Method 1: Direct execution
cd src
python robust_clipboard_service.py

# Method 2: Using startup script
scripts/start_clipboard_service.bat

# Method 3: Install as Windows service (optional)
scripts/install_service.bat
```

### Monitoring the Service

```bash
# View live logs
Get-Content logs/robust_clipboard_service.log -Wait -Tail 10

# Check service status
scripts/check_status.bat
```

### Stopping the Service

```bash
# Stop the service
scripts/stop_clipboard_service.bat

# Or use Ctrl+C if running directly
```

## 📊 How It Works

### Text Processing
1. **Detects text** in clipboard
2. **Creates timestamped filename** (e.g., `Text_2025-10-05_18-29-19.txt`)
3. **Uses PiecesOS SDK** to create text asset
4. **Saves to Pieces Drive** for AI processing

### Image Processing
1. **Detects image** in clipboard
2. **Validates image format** (PNG, JPEG, etc.)
3. **Compresses if needed** (resize + quality reduction)
4. **Converts to JPEG** for optimal storage
5. **Creates binary asset** using PiecesOS Seed structure
6. **Saves to Pieces Drive** with proper metadata

### Duplicate Prevention
- **Tracks processed content** with timestamps
- **Skips duplicates** within 30-minute window
- **Logs duplicate detection** at DEBUG level

## 🏗️ Project Structure

```
clipboard-to-pieces/
├── README.md
├── requirements.txt
├── .gitignore
├── src/
│   └── robust_clipboard_service.py    # Main service
├── scripts/
│   ├── start_clipboard_service.bat    # Start service
│   ├── stop_clipboard_service.bat     # Stop service
│   ├── check_status.bat               # Check status
│   └── install_service.bat           # Install as Windows service
├── logs/
│   └── robust_clipboard_service.log   # Service logs
└── docs/
    └── SETUP.md                       # Detailed setup guide
```

## 🔧 Development

### Running Tests

```bash
# Test clipboard detection
python -c "import pyperclip; pyperclip.copy('test'); print('Test text copied')"

# Test PiecesOS connection
python -c "from pieces_os_client import PiecesClient; client = PiecesClient(); print('Connected:', client.applications_api.applications_snapshot())"
```

### Debugging

```bash
# Enable verbose logging
# Edit src/robust_clipboard_service.py and change logging level to DEBUG

# Monitor service activity
Get-Content logs/robust_clipboard_service.log -Wait -Tail 20
```

## 🔒 Security Best Practices

### **Before Using This Service:**

1. **Audit Your Development Environment**:
   - Identify all sensitive data types you work with
   - Review your organization's data handling policies
   - Ensure you have permission to use clipboard monitoring tools

2. **Implement Safeguards**:
   - Use a dedicated development machine for testing
   - Consider running in a virtual machine or container
   - Set up regular cleanup of Pieces.app data
   - Monitor Pieces.app for unexpected content

3. **Emergency Procedures**:
   - Know how to quickly stop the service: `scripts/stop_clipboard_service.bat`
   - Understand how to delete content from Pieces.app
   - Have a plan for handling accidental sensitive data capture

### **If Sensitive Data is Accidentally Captured:**

1. **Immediately stop the service**
2. **Review Pieces.app for the captured content**
3. **Delete any sensitive data from Pieces.app**
4. **Consider changing any exposed credentials**
5. **Report the incident according to your organization's policies**

## 🐛 Troubleshooting

### Common Issues

**Service won't start:**
- Check if Pieces.app is running
- Verify PiecesOS is accessible on port 39300
- Check Python dependencies are installed

**Images not importing:**
- Ensure image is valid format (PNG, JPEG, etc.)
- Check image size (very large images may timeout)
- Verify PiecesOS API is responding

**Text not importing:**
- Check clipboard contains actual text content
- Verify PiecesOS connection
- Check service logs for error messages

### Log Analysis

```bash
# View recent activity
Get-Content logs/robust_clipboard_service.log -Tail 50

# Search for errors
Select-String -Path logs/robust_clipboard_service.log -Pattern "ERROR"

# Search for successful imports
Select-String -Path logs/robust_clipboard_service.log -Pattern "SUCCESS"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📖 [Documentation](docs/)
- 🐛 [Report Issues](https://github.com/yourusername/clipboard-to-pieces/issues)
- 💬 [Discussions](https://github.com/yourusername/clipboard-to-pieces/discussions)

## 🙏 Acknowledgments

- Built for Pieces.app integration
- Inspired by the need for seamless clipboard-to-AI workflows
- Community-driven development

---

**Note**: This is a focused clipboard monitoring service designed to work seamlessly with Pieces.app for AI-powered memory management.
