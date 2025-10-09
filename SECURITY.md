# Security Features

This document describes the security filtering capabilities of the Clipboard-to-Pieces service designed to protect sensitive information from being imported into Pieces.app.

## ⚠️ **Critical Security Notice**

**By default, this service monitors ALL clipboard content on your system. The security filter is designed to detect and redact sensitive information, but it's not foolproof. Always use caution when running this service.**

## 🔐 **Security Filter Overview**

The security filter automatically detects and handles sensitive data in clipboard content before it gets imported to Pieces.app. It can operate in two modes:

1. **Redaction Mode** (default): Replaces sensitive data with `[REDACTED-TYPE]` placeholders
2. **Skip Mode**: Skips importing content entirely when sensitive data is detected

## 🎯 **Detected Sensitive Data Types**

### API Keys and Tokens
- Generic API keys, access tokens, secret keys
- Service-specific tokens (GitHub, AWS, OpenAI, Stripe, Slack, Discord)
- JWT tokens
- Bearer tokens

### Passwords
- Password fields in configurations
- Database passwords
- Authentication credentials

### Database Connections
- PostgreSQL, MySQL, MongoDB, Redis connection strings with passwords
- JDBC connection strings
- SQL Server connection strings

### SSH and Private Keys
- Private key blocks (RSA, EC, Ed25519)
- SSH public keys

### Credit Card Numbers
- Major credit card formats (Visa, MasterCard, Amex, etc.)

### Environment Variables
- Environment exports containing API, KEY, TOKEN, SECRET, PASSWORD

### URLs with Credentials
- HTTP/HTTPS URLs with embedded passwords
- FTP URLs with credentials

## ⚙️ **Configuration**

### Security Configuration File: `security_config.json`

```json
{
  "security_filter": {
    "enabled": true,
    "enable_redaction": true,
    "skip_sensitive": false,
    "custom_patterns": [
      {
        "pattern": "(?i)license[_\\-]?key\\s*[:=]\\s*['\"]?([a-zA-Z0-9\\-]{20,})['\"]?",
        "name": "License Key",
        "group": "custom"
      }
    ]
  },
  "logging": {
    "log_detections": true,
    "log_level": "WARNING",
    "detailed_logging": false
  }
}
```

### Configuration Options

- **`enabled`**: Enable/disable security filtering entirely
- **`enable_redaction`**: Replace sensitive data with redaction markers
- **`skip_sensitive`**: Skip importing content with sensitive data entirely
- **`custom_patterns`**: Add your own regex patterns for detection

## 🚀 **Usage Examples**

### Example 1: API Key Detection and Redaction

**Input:**
```
export OPENAI_API_KEY=sk-1234567890abcdef1234567890abcdef1234567890abcdef
```

**Output (with redaction):**
```
export OPENAI_API_KEY=[REDACTED-OPENAI API KEY]
```

### Example 2: Database Password Redaction

**Input:**
```python
DATABASE_URL = "postgresql://user:my_secret_password@localhost:5432/mydb"
```

**Output (with redaction):**
```python
DATABASE_URL = "postgresql://user:[REDACTED-DATABASE PASSWORD]@localhost:5432/mydb"
```

### Example 3: Multiple Sensitive Items

**Input:**
```bash
export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

**Output (with redaction):**
```bash
export AWS_ACCESS_KEY_ID=[REDACTED-AWS ACCESS KEY]
export AWS_SECRET_ACCESS_KEY=[REDACTED-AWS SECRET]
```

## 🔧 **Testing the Security Filter**

Run the test script to verify security filtering:

```powershell
python test_security_filter.py
```

This will test various types of sensitive data and show how they are detected and redacted.

## 📊 **Security Statistics**

The service tracks security filter statistics:

- Total items processed
- Sensitive content detected
- Items redacted
- Items skipped
- Pattern match counts

Statistics are logged when the service shuts down and can be accessed via the service API.

## 🛡️ **Security Levels**

### Level 1: Detection Only
```json
{
  "security_filter": {
    "enabled": true,
    "enable_redaction": false,
    "skip_sensitive": false
  }
}
```
- Detects and logs sensitive data but doesn't modify content
- Useful for monitoring what sensitive data is being copied

### Level 2: Redaction (Recommended)
```json
{
  "security_filter": {
    "enabled": true,
    "enable_redaction": true,
    "skip_sensitive": false
  }
}
```
- Replaces sensitive data with redaction markers
- Maintains context while protecting sensitive values

### Level 3: Skip Sensitive Content
```json
{
  "security_filter": {
    "enabled": true,
    "enable_redaction": false,
    "skip_sensitive": true
  }
}
```
- Completely skips importing any content with detected sensitive data
- Maximum security but may skip legitimate content

## 🔍 **Custom Pattern Examples**

### License Keys
```json
{
  "pattern": "(?i)license[_\\-]?key\\s*[:=]\\s*['\"]?([A-Z0-9\\-]{20,})['\"]?",
  "name": "License Key",
  "group": "custom"
}
```

### Social Security Numbers
```json
{
  "pattern": "\\b\\d{3}-\\d{2}-\\d{4}\\b",
  "name": "SSN",
  "group": "personal"
}
```

### Internal API Endpoints
```json
{
  "pattern": "https://internal\\.company\\.com/api/[^\\s]+",
  "name": "Internal API",
  "group": "company"
}
```

## ⚠️ **Limitations**

1. **Pattern-based detection**: May not catch all variations of sensitive data
2. **False positives**: May occasionally flag non-sensitive content
3. **Context-unaware**: Cannot understand semantic context
4. **No image analysis**: Images are not scanned for sensitive text
5. **Performance impact**: Regex processing adds slight overhead

## 🛠️ **Best Practices**

1. **Test thoroughly**: Use the test script to verify patterns work for your use cases
2. **Monitor logs**: Check for detection patterns in your environment
3. **Custom patterns**: Add patterns specific to your organization
4. **Regular updates**: Review and update patterns as needed
5. **Backup strategy**: Always have a way to recover if legitimate data is filtered

## 🚨 **Emergency Procedures**

### Disable Security Filtering
1. Set `"enabled": false` in `security_config.json`
2. Restart the service
3. Or delete/rename `security_config.json`

### Recover Accidentally Filtered Content
1. Check `.clipboard-to-pieces` directory for original content
2. Review service logs for detection details
3. Adjust patterns if needed to reduce false positives

### Report Security Issues
If you discover sensitive data that isn't being detected, please:
1. Create a test pattern (without real sensitive data)
2. Add it to the custom patterns in your config
3. Consider contributing the pattern back to the project

## 📝 **File Metadata**

When content is filtered, additional metadata is saved:

```json
{
  "filename": "Text_2025-01-08_15-30-45.txt",
  "content_type": "text",
  "timestamp": "2025-01-08T15:30:45.123456",
  "source": "clipboard_monitor",
  "security": {
    "filtered": true,
    "detected_items": 2,
    "detection_types": ["API Key", "Password"],
    "filter_timestamp": "2025-01-08T15:30:45.123456"
  }
}
```

This helps you track what content has been filtered and why.