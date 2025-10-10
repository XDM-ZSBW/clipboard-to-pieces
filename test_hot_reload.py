#!/usr/bin/env python3
"""
Test script to verify hot reloading functionality
"""

import time
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from robust_clipboard_service import RobustClipboardService

def test_hot_reload():
    """Test hot reloading by creating service and monitoring file changes"""
    print("🧪 Testing Hot Reload Functionality")
    print("=" * 50)
    
    try:
        # Create service instance
        service = RobustClipboardService()
        
        print("✅ Service created successfully")
        print(f"📁 Watching files: {list(service.watched_files.keys())}")
        print(f"🔍 OCR available: {service.ocr_service.is_available()}")
        print(f"🛡️ Security filter: {service.security_filter is not None}")
        
        if service.security_filter:
            print("\n🧪 Running security pattern tests...")
            service.test_security_patterns()
        
        print("\n⏰ Monitoring for file changes...")
        print("💡 Edit security_filter.py or security_config.json to test hot reload")
        print("🛑 Press Ctrl+C to stop")
        
        # Keep running to test hot reload
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping test...")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_hot_reload()




