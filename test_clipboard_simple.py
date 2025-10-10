#!/usr/bin/env python3
"""
Simple clipboard test
"""

import pyperclip
import time

print("Simple clipboard test starting...")
print("Copy some text and press Enter to test...")

try:
    while True:
        input("Press Enter to check clipboard (or Ctrl+C to exit): ")
        
        content = pyperclip.paste()
        
        if content:
            print(f"Clipboard content: {len(content)} chars")
            print(f"First 100 chars: {content[:100]}")
        else:
            print("Clipboard is empty")
            
except KeyboardInterrupt:
    print("\nTest stopped.")

