#!/usr/bin/env python3
from pieces_os_client.wrapper import PiecesClient

def check_latest_asset():
    try:
        pc = PiecesClient()
        assets = pc.assets_api.assets_snapshot()
        
        if not assets.iterable:
            print("No assets found")
            return
            
        latest = assets.iterable[-1]
        print(f"Latest asset: {latest.name}")
        print(f"Asset ID: {latest.id}")
        print(f"Created: {latest.created}")
        
        if latest.format:
            print(f"Format: {latest.format}")
            if latest.format.classification:
                print(f"Classification: {latest.format.classification}")
                if latest.format.classification.generic:
                    print(f"Generic type: {latest.format.classification.generic}")
        
        # Check if it's base64 image content
        if hasattr(latest, 'value') and latest.value:
            content = latest.value
            if isinstance(content, str) and (content.startswith('/9j/') or content.startswith('iVBORw0KGgo')):
                print("⚠️  This is a TEXT SNIPPET with base64 image content")
            else:
                print("✅ This appears to be proper content")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_latest_asset()




