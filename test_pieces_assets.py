#!/usr/bin/env python3
"""
Test script to check Pieces.app assets and see if images are imported as image assets or text snippets
"""

import requests
import json
from datetime import datetime, timedelta

def check_pieces_assets():
    """Check recent assets in Pieces.app to see their types"""
    base_url = "http://localhost:39300"
    
    try:
        # Try to get recent assets
        assets_url = f"{base_url}/assets"
        response = requests.get(assets_url, timeout=5)
        
        if response.status_code == 200:
            assets = response.json()
            print(f"Found {len(assets)} assets")
            
            # Look for recent assets (last 10 minutes)
            recent_time = datetime.now() - timedelta(minutes=10)
            
            for asset in assets:
                # Check if asset was created recently
                created_time = asset.get('created', '')
                if created_time:
                    try:
                        # Parse timestamp if it's in ISO format
                        if 'T' in created_time:
                            asset_time = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
                        else:
                            continue
                        
                        if asset_time > recent_time:
                            print(f"\nRecent Asset:")
                            print(f"  ID: {asset.get('id', 'N/A')}")
                            print(f"  Name: {asset.get('name', 'N/A')}")
                            print(f"  Type: {asset.get('type', 'N/A')}")
                            print(f"  Format: {asset.get('format', 'N/A')}")
                            print(f"  Created: {created_time}")
                            
                            # Check if it's a text snippet with base64 content
                            if asset.get('type') == 'text' or asset.get('format') == 'text':
                                content = asset.get('content', '')
                                if content.startswith('/9j/') or content.startswith('iVBORw0KGgo'):
                                    print(f"  ⚠️  TEXT SNIPPET with base64 image content")
                                else:
                                    print(f"  ✅ Text content (not base64)")
                            elif asset.get('type') == 'image' or asset.get('format') == 'image':
                                print(f"  ✅ IMAGE ASSET")
                            else:
                                print(f"  ❓ Unknown type")
                                
                    except Exception as e:
                        print(f"  Error parsing time: {e}")
                        
        else:
            print(f"Failed to get assets: {response.status_code}")
            
    except Exception as e:
        print(f"Error connecting to Pieces.app: {e}")
        
        # Try alternative endpoint
        try:
            search_url = f"{base_url}/assets/search"
            response = requests.get(search_url, params={"query": "clipboard"}, timeout=5)
            if response.status_code == 200:
                results = response.json()
                print(f"Search results: {json.dumps(results, indent=2)}")
        except Exception as e2:
            print(f"Search also failed: {e2}")

if __name__ == "__main__":
    print("Checking Pieces.app assets...")
    check_pieces_assets()




