#!/usr/bin/env python3
"""
Pieces.app MCP Bridge
Connects to Pieces.app MCP server and provides standard MCP protocol interface.
"""

import json
import sys
import requests
import asyncio
import os
from typing import Dict, Any, List
from pathlib import Path

class PiecesMCPBridge:
    def __init__(self, base_url: str = "http://localhost:39300"):
        self.base_url = base_url
        self.mcp_endpoint = f"{base_url}/model_context_protocol/2024-11-05/sse"
        self.clipboard_data_dir = Path.home() / ".clipboard-to-pieces"
        
    def get_clipboard_history(self) -> List[Dict[str, Any]]:
        """Get clipboard history from local storage"""
        history = []
        if not self.clipboard_data_dir.exists():
            return history
            
        # Look for text and image files
        for file_path in self.clipboard_data_dir.glob("*"):
            if file_path.is_file():
                try:
                    stat = file_path.stat()
                    item = {
                        "name": file_path.name,
                        "path": str(file_path),
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                        "type": "text" if file_path.suffix == ".txt" else "image"
                    }
                    
                    # For text files, include content preview
                    if file_path.suffix == ".txt" and stat.st_size < 10000:  # < 10KB
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                item["content"] = content[:500] + "..." if len(content) > 500 else content
                        except Exception:
                            item["content"] = "[Unable to read content]"
                    
                    history.append(item)
                except Exception:
                    continue
                    
        # Sort by modification time (newest first)
        history.sort(key=lambda x: x["modified"], reverse=True)
        return history
    
    def search_pieces_api(self, query: str) -> Dict[str, Any]:
        """Search Pieces.app via API"""
        try:
            # Try to search using PiecesOS API
            search_url = f"{self.base_url}/assets/search"
            response = requests.get(search_url, params={"query": query}, timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            return {"error": f"API search failed: {str(e)}"}
            
        return {"error": "Search not available"}
        
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP protocol requests"""
        method = request.get("method", "")
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "resources": {"subscribe": True, "listChanged": True},
                        "tools": {},
                        "prompts": {}
                    },
                    "serverInfo": {
                        "name": "pieces-mcp-bridge",
                        "version": "1.0.0"
                    }
                }
            }
        elif method == "resources/list":
            # Return available resources from Pieces
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "resources": [
                        {
                            "uri": "pieces://clipboard-history",
                            "name": "Clipboard History",
                            "description": "Recent clipboard content stored in Pieces",
                            "mimeType": "application/json"
                        },
                        {
                            "uri": "pieces://search",
                            "name": "Pieces Search",
                            "description": "Search through Pieces.app content",
                            "mimeType": "application/json"
                        }
                    ]
                }
            }
        elif method == "resources/read":
            # Read a specific resource
            params = request.get("params", {})
            uri = params.get("uri", "")
            
            if uri == "pieces://clipboard-history":
                history = self.get_clipboard_history()
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "contents": [
                            {
                                "uri": uri,
                                "mimeType": "application/json",
                                "text": json.dumps({
                                    "clipboard_history": history,
                                    "total_items": len(history),
                                    "data_directory": str(self.clipboard_data_dir)
                                }, indent=2)
                            }
                        ]
                    }
                }
            elif uri.startswith("pieces://search"):
                # Extract query from URI or params
                query = params.get("query", "")
                if not query and "?" in uri:
                    query = uri.split("?", 1)[1].replace("query=", "")
                
                if not query:
                    return {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "error": {
                            "code": -32602,
                            "message": "Search query required"
                        }
                    }
                
                search_results = self.search_pieces_api(query)
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "contents": [
                            {
                                "uri": uri,
                                "mimeType": "application/json",
                                "text": json.dumps({
                                    "query": query,
                                    "results": search_results
                                }, indent=2)
                            }
                        ]
                    }
                }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {
                        "code": -32602,
                        "message": f"Unknown resource: {uri}"
                    }
                }
        else:
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }

async def main():
    """Main MCP bridge loop"""
    bridge = PiecesMCPBridge()
    
    # Read from stdin, write to stdout (MCP protocol)
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
                
            request = json.loads(line.strip())
            response = await bridge.handle_request(request)
            print(json.dumps(response), flush=True)
            
        except json.JSONDecodeError:
            # Skip invalid JSON
            continue
        except Exception as e:
            # Send error response
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            print(json.dumps(error_response), flush=True)

if __name__ == "__main__":
    asyncio.run(main())