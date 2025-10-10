#!/usr/bin/env python3
"""
Check Pieces.app assets using the SDK to see if images are imported as image assets or text snippets
"""

from pieces_os_client.wrapper import PiecesClient
import json
from datetime import datetime, timedelta

def check_assets_with_sdk():
    """Check recent assets using the Pieces OS Client SDK"""
    try:
        # Initialize the client
        client = PiecesClient()
        
        # Get all assets
        assets = client.assets_api.assets_snapshot()
        
        print(f"Found {len(assets.iterable)} assets")
        
        # Look for recent assets (last 10 minutes)
        recent_time = datetime.now() - timedelta(minutes=10)
        
        for asset in assets.iterable:
            # Check if asset was created recently
            created_time = asset.created
            if created_time:
                try:
                    # Parse timestamp
                    asset_time = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
                    
                    if asset_time > recent_time:
                        print(f"\nRecent Asset:")
                        print(f"  ID: {asset.id}")
                        print(f"  Name: {asset.name}")
                        print(f"  Type: {getattr(asset, 'type', 'N/A')}")
                        print(f"  Format: {getattr(asset, 'format', 'N/A')}")
                        print(f"  Created: {created_time}")
                        
                        # Check the format/classification
                        if hasattr(asset, 'format') and asset.format:
                            format_info = asset.format
                            print(f"  Format Details: {format_info}")
                            
                            # Check if it's classified as an image
                            if hasattr(format_info, 'classification') and format_info.classification:
                                classification = format_info.classification
                                print(f"  Classification: {classification}")
                                
                                if hasattr(classification, 'generic') and classification.generic:
                                    generic = classification.generic
                                    print(f"  Generic Type: {generic}")
                                    
                                    if generic == 'IMAGE':
                                        print(f"  ✅ IMAGE ASSET")
                                    elif generic == 'TEXT':
                                        print(f"  ⚠️  TEXT SNIPPET")
                                    else:
                                        print(f"  ❓ Unknown classification: {generic}")
                        
                        # Check content preview
                        if hasattr(asset, 'value') and asset.value:
                            content = asset.value
                            if isinstance(content, str):
                                if content.startswith('/9j/') or content.startswith('iVBORw0KGgo'):
                                    print(f"  ⚠️  Contains base64 image data")
                                elif len(content) > 100:
                                    print(f"  Content preview: {content[:100]}...")
                                else:
                                    print(f"  Content: {content}")
                                    
                except Exception as e:
                    print(f"  Error parsing asset: {e}")
                    
    except Exception as e:
        print(f"Error using SDK: {e}")
        
        # Try alternative approach
        try:
            print("Trying alternative SDK approach...")
            client = PiecesClient()
            
            # Try to get assets using different method
            if hasattr(client, 'assets_api'):
                api = client.assets_api
                if hasattr(api, 'assets_list'):
                    assets = api.assets_list()
                    print(f"Alternative method found {len(assets)} assets")
                else:
                    print("No assets_list method found")
            else:
                print("No assets_api found")
                
        except Exception as e2:
            print(f"Alternative approach also failed: {e2}")

if __name__ == "__main__":
    print("Checking Pieces.app assets using SDK...")
    check_assets_with_sdk()




