#!/usr/bin/env python3
"""
Auto clipboard test - checks clipboard every 2 seconds
"""

import pyperclip
import time
import hashlib

print("Auto clipboard test starting...")
print("Copy some text or images to test...")
print("Press Ctrl+C to stop.")

processed_items = {}

try:
    while True:
        content = pyperclip.paste()
        
        if content:
            # Create hash for duplicate detection
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            if content_hash not in processed_items:
                processed_items[content_hash] = time.time()
                
                print(f"[{time.strftime('%H:%M:%S')}] New content detected:")
                print(f"  Length: {len(content)} chars")
                print(f"  Type: {'Image (base64)' if content.startswith(('iVBORw0KGgo', '/9j/')) else 'Text'}")
                print(f"  Preview: {content[:50]}...")
                print()
            else:
                print(f"[{time.strftime('%H:%M:%S')}] Duplicate content detected")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] Clipboard empty")
        
        time.sleep(2)
        
except KeyboardInterrupt:
    print("\nTest stopped.")

