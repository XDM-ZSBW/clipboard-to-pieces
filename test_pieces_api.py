#!/usr/bin/env python3
"""
Test Pieces API availability
"""

import requests
import json

def test_api():
    print("Testing Pieces API availability...")
    
    # Test different endpoints
    endpoints = [
        "http://localhost:39300/api",
        "http://localhost:39300/api/health",
        "http://localhost:39300/api/assets",
        "http://localhost:39300/api/applications"
    ]
    
    for endpoint in endpoints:
        try:
            print(f"Testing: {endpoint}")
            response = requests.get(endpoint, timeout=5)
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                print(f"  Response: {response.text[:100]}...")
            else:
                print(f"  Error: {response.text[:100]}...")
        except requests.exceptions.ConnectionError:
            print(f"  Connection failed")
        except requests.exceptions.Timeout:
            print(f"  Timeout")
        except Exception as e:
            print(f"  Error: {e}")
        print()

if __name__ == "__main__":
    test_api()

