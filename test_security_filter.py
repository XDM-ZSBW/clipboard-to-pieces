#!/usr/bin/env python3
"""
Test script for Security Filter functionality
Demonstrates detection and redaction of sensitive data
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.security_filter import SecurityFilter

def test_security_filter():
    """Test the security filter with various sensitive data types"""
    
    print("=== Security Filter Test ===\n")
    
    # Test cases with different types of sensitive data
    test_cases = [
        {
            "name": "API Key",
            "content": "Here is my API key: api_key=sk-1234567890abcdef1234567890abcdef",
            "expected_sensitive": True
        },
        {
            "name": "Password in config",
            "content": "database_config = {\n  'host': 'localhost',\n  'password': 'my_secret_password123'\n}",
            "expected_sensitive": True
        },
        {
            "name": "JWT Token",
            "content": "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
            "expected_sensitive": True
        },
        {
            "name": "Database URL with password",
            "content": "DATABASE_URL=postgresql://user:secretpassword123@localhost:5432/mydb",
            "expected_sensitive": True
        },
        {
            "name": "AWS Keys",
            "content": "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE\nAWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "expected_sensitive": True
        },
        {
            "name": "Safe content",
            "content": "This is just normal text content with no sensitive information. Just some code: print('hello world')",
            "expected_sensitive": False
        },
        {
            "name": "Environment export",
            "content": "export STRIPE_SECRET_KEY=sk_live_1234567890abcdef1234567890abcdef",
            "expected_sensitive": True
        }
    ]
    
    # Test with redaction enabled
    print("🔍 Testing with REDACTION enabled:")
    print("-" * 50)
    
    filter_with_redaction = SecurityFilter(enable_redaction=True, skip_sensitive=False)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {test_case['name']}")
        print(f"Original content:\n{test_case['content']}")
        
        filtered_content, should_skip, detected_items = filter_with_redaction.filter_content(test_case['content'])
        
        has_sensitive = len(detected_items) > 0
        
        if has_sensitive:
            print(f"✅ Sensitive data detected: {len(detected_items)} items")
            for item in detected_items:
                print(f"   - {item['type']}: {item['matched_text']}")
            print(f"Filtered content:\n{filtered_content}")
        else:
            print("✅ No sensitive data detected")
        
        # Verify expectation
        if has_sensitive == test_case['expected_sensitive']:
            print("🎯 Test result matches expectation")
        else:
            print(f"❌ Test failed! Expected sensitive: {test_case['expected_sensitive']}, Got: {has_sensitive}")
    
    # Test with skip mode
    print("\n\n🚫 Testing with SKIP mode enabled:")
    print("-" * 50)
    
    filter_with_skip = SecurityFilter(enable_redaction=False, skip_sensitive=True)
    
    sensitive_test = test_cases[0]  # API Key test
    print(f"Testing: {sensitive_test['name']}")
    print(f"Content: {sensitive_test['content']}")
    
    filtered_content, should_skip, detected_items = filter_with_skip.filter_content(sensitive_test['content'])
    
    if should_skip:
        print("✅ Content was marked for skipping due to sensitive data")
    else:
        print("❌ Content was not marked for skipping")
    
    # Show statistics
    print("\n\n📊 Security Filter Statistics:")
    print("-" * 50)
    stats = filter_with_redaction.get_statistics()
    print(f"Total processed: {stats['total_processed']}")
    print(f"Sensitive detected: {stats['sensitive_detected']}")
    print(f"Items redacted: {stats['redacted_items']}")
    print(f"Items skipped: {stats['skipped_items']}")
    print(f"Patterns matched: {stats['patterns_matched']}")

def test_custom_patterns():
    """Test adding custom patterns"""
    print("\n\n🔧 Testing Custom Patterns:")
    print("-" * 50)
    
    security_filter = SecurityFilter()
    
    # Add a custom pattern for license keys
    security_filter.add_custom_pattern(
        r'(?i)license[_\-]?key\s*[:=]\s*[\'"]?([A-Z0-9\-]{20,})[\'"]?',
        'License Key',
        'custom'
    )
    
    test_content = "Please use this license_key = 'ABCD-EFGH-IJKL-MNOP-QRST-UVWX' for activation"
    
    filtered_content, should_skip, detected_items = security_filter.filter_content(test_content)
    
    if detected_items:
        print(f"✅ Custom pattern detected: {detected_items[0]['type']}")
        print(f"Original: {test_content}")
        print(f"Filtered: {filtered_content}")
    else:
        print("❌ Custom pattern not detected")

if __name__ == "__main__":
    try:
        test_security_filter()
        test_custom_patterns()
        print("\n🎉 Security filter tests completed!")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()