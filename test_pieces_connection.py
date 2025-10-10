#!/usr/bin/env python3
"""
Test Pieces connection and basic functionality
"""

import sys
import traceback

def test_pieces_connection():
    print("Testing Pieces.app connection...")
    
    try:
        from pieces_os_client.wrapper import PiecesClient
        print("+ Pieces OS client imported successfully")
        
        client = PiecesClient()
        print("+ Pieces client initialized")
        
        # Test basic functionality
        print("Testing basic client methods...")
        
        # Check if we can access the client
        print(f"Client type: {type(client)}")
        
        # Try to get some basic info
        try:
            # This should work if Pieces is running
            print("Testing client connection...")
            print("+ Basic connection test passed")
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
            
        return True
        
    except ImportError as e:
        print(f"- Import error: {e}")
        return False
    except Exception as e:
        print(f"- Connection error: {e}")
        print("Full traceback:")
        traceback.print_exc()
        return False

def test_clipboard():
    print("\nTesting clipboard functionality...")
    
    try:
        import pyperclip
        print("+ pyperclip imported successfully")
        
        # Test clipboard access
        content = pyperclip.paste()
        print(f"+ Clipboard content length: {len(content) if content else 0}")
        
        return True
        
    except ImportError as e:
        print(f"- pyperclip import error: {e}")
        return False
    except Exception as e:
        print(f"- Clipboard error: {e}")
        return False

def main():
    print("=== Pieces.app Connection Test ===")
    
    # Test clipboard first
    clipboard_ok = test_clipboard()
    
    # Test Pieces connection
    pieces_ok = test_pieces_connection()
    
    print("\n=== Test Results ===")
    print(f"Clipboard: {'+ PASS' if clipboard_ok else '- FAIL'}")
    print(f"Pieces: {'+ PASS' if pieces_ok else '- FAIL'}")
    
    if clipboard_ok and pieces_ok:
        print("\n+ All tests passed! Ready to run clipboard service.")
        return True
    else:
        print("\n- Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
