#!/usr/bin/env python3
"""
Robust Clipboard Service with Image Compression
Handles large images by compressing them before upload
"""

import time
import os
import json
import base64
import tempfile
import shutil
import logging
import hashlib
import sys
import msvcrt
import importlib
import threading
from datetime import datetime
from pathlib import Path
import pyperclip
from PIL import Image
import io
import win32clipboard
import win32con
from security_filter import SecurityFilter
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pieces_os_client.wrapper import PiecesClient
from pieces_os_client.models.classification_specific_enum import ClassificationSpecificEnum
from pieces_os_client.models.fragment_metadata import FragmentMetadata
from pieces_os_client.models.seed import Seed
from pieces_os_client.models.seeded_asset import SeededAsset
from pieces_os_client.models.seeded_format import SeededFormat
from pieces_os_client.models.seeded_file import SeededFile
from pieces_os_client.models.transferable_bytes import TransferableBytes
from pieces_os_client.models.seeded_classification import SeededClassification
from pieces_os_client.models.application import Application
from pieces_os_client.models.application_name_enum import ApplicationNameEnum
from pieces_os_client.models.platform_enum import PlatformEnum
from pieces_os_client.models.privacy_enum import PrivacyEnum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'robust_clipboard_service.log')),
        logging.StreamHandler()
    ]
)

class SecurityFilterReloader(FileSystemEventHandler):
    """File watcher for hot-reloading security filter changes"""
    
    def __init__(self, service_instance):
        self.service = service_instance
        self.last_reload = datetime.now()
        self.reload_count = 0
        
    def on_modified(self, event):
        if event.is_directory:
            return
            
        # Only watch for security filter changes
        if event.src_path.endswith('security_filter.py') or event.src_path.endswith('security_config.json'):
            try:
                # Prevent rapid reloads (debounce)
                if (datetime.now() - self.last_reload).total_seconds() < 2:
                    return
                
                self.last_reload = datetime.now()
                self.reload_count += 1
                
                # Reload the security filter module
                import security_filter
                importlib.reload(security_filter)
                
                # Create new filter instance
                old_filter = self.service.security_filter
                new_filter = security_filter.SecurityFilter(
                    enable_redaction=old_filter.enable_redaction if old_filter else True,
                    skip_sensitive=old_filter.skip_sensitive if old_filter else False
                )
                
                # Update service with new filter
                self.service.security_filter = new_filter
                
                # Log the reload with clear indicators
                reload_id = f"RELOAD-{self.reload_count:03d}"
                self.service.logger.info(f"🔄 {reload_id}: Security filter HOT-RELOADED successfully!")
                self.service.logger.info(f"🔄 {reload_id}: File changed: {os.path.basename(event.src_path)}")
                self.service.logger.info(f"🔄 {reload_id}: New patterns loaded: {len(new_filter.patterns)} pattern groups")
                self.service.logger.info(f"🔄 {reload_id}: Filter version: {id(new_filter)} (old: {id(old_filter)})")
                
                # Print to console for immediate feedback
                print(f"\n🔄 {reload_id}: SECURITY FILTER HOT-RELOADED!")
                print(f"🔄 {reload_id}: You are now on the NEW code path")
                print(f"🔄 {reload_id}: Filter ID: {id(new_filter)}")
                print(f"🔄 {reload_id}: Ready to test new patterns!\n")
                
            except Exception as e:
                self.service.logger.error(f"❌ HOT-RELOAD FAILED: {e}")
                print(f"\n❌ HOT-RELOAD FAILED: {e}")
                print("❌ Service continues with OLD code path\n")

class RobustClipboardService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.pieces_client = PiecesClient(host="http://localhost:39300")
        
        # Only use .clipboard-to-pieces directory for persistence
        self.pieces_dir = Path.home() / ".clipboard-to-pieces"
        self.pieces_dir.mkdir(exist_ok=True)
        
        # Track processed clipboard items with timestamps
        self.processed_items = {}
        self.max_cache_size = 100
        
        # Get application info once
        self.application = self._get_application()
        
        # Image compression settings
        self.max_image_size = 100000  # 100KB limit
        self.max_dimensions = (1920, 1080)  # Max width/height
        
        # Initialize security filter
        self.security_filter = self._load_security_config()
        
        # Initialize file watcher for hot reloading
        self.file_observer = None
        self._start_file_watcher()
        
        self.logger.info("Robust Clipboard Monitoring Service Initialized")
        self.logger.info(f"Will import text as text, screenshots as compressed binary files")
        self.logger.info(f"Files will be saved in: {self.pieces_dir}")
        if self.application:
            self.logger.info(f"Using application: {self.application.name}")
        else:
            self.logger.warning("No application available - image imports may fail")
        self.logger.info(f"Max image size: {self.max_image_size} bytes")
        if self.security_filter:
            self.logger.info("Security filtering enabled - sensitive data will be detected and redacted")
        else:
            self.logger.warning("Security filtering disabled - ALL clipboard content will be imported!")
    
    def _get_application(self):
        """Get the current application for asset creation"""
        try:
            applications = self.pieces_client.applications_api.applications_snapshot()
            if applications.iterable and len(applications.iterable) > 0:
                # Try to find a working application
                for app in applications.iterable:
                    try:
                        # Test if this application works by checking its properties
                        if hasattr(app, 'name') and app.name:
                            self.logger.info(f"Using existing application: {app.name}")
                            return app
                    except Exception as app_error:
                        self.logger.warning(f"Application {app} failed validation: {app_error}")
                        continue
                
                # If no working application found, create default
                self.logger.warning("No working applications found, creating default")
                return self._create_default_application()
            else:
                self.logger.warning("No applications found, creating default OS_SERVER application")
                return self._create_default_application()
        except Exception as e:
            self.logger.warning(f"Failed to get application info: {e}")
            self.logger.info("Creating default application for asset creation")
            return self._create_default_application()
    
    def _create_default_application(self):
        """Create a default application for asset creation"""
        try:
            # Create a complete application object with all required fields
            default_app = Application(
                id="clipboard-to-pieces-service",
                name=ApplicationNameEnum.OS_SERVER,
                version="2.0.0",
                platform=PlatformEnum.WINDOWS,
                onboarded=True,
                privacy=PrivacyEnum.CLOSED
            )
            self.logger.info("Created default OS_SERVER application")
            return default_app
        except Exception as e:
            self.logger.error(f"Failed to create default application: {e}")
            return None
    
    def _load_security_config(self):
        """Load security configuration and initialize filter"""
        try:
            # Look for security config file
            config_path = Path(__file__).parent.parent / "security_config.json"
            
            if not config_path.exists():
                self.logger.warning("No security_config.json found - security filtering disabled")
                return None
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            security_config = config.get('security_filter', {})
            
            if not security_config.get('enabled', False):
                self.logger.warning("Security filtering disabled in config")
                return None
            
            # Initialize security filter with config
            security_filter = SecurityFilter(
                enable_redaction=security_config.get('enable_redaction', True),
                skip_sensitive=security_config.get('skip_sensitive', False)
            )
            
            # Add custom patterns if configured
            for pattern_config in security_config.get('custom_patterns', []):
                try:
                    security_filter.add_custom_pattern(
                        pattern_config['pattern'],
                        pattern_config['name'],
                        pattern_config.get('group', 'custom')
                    )
                except Exception as e:
                    self.logger.error(f"Failed to add custom pattern: {e}")
            
            self.logger.info("Security filter initialized successfully")
            return security_filter
            
        except Exception as e:
            self.logger.error(f"Failed to load security config: {e}")
            self.logger.warning("Security filtering disabled due to config error")
            return None
    
    def _start_file_watcher(self):
        """Start file watcher for hot reloading security filter"""
        try:
            self.file_observer = Observer()
            event_handler = SecurityFilterReloader(self)
            
            # Watch the src directory for changes
            src_dir = Path(__file__).parent
            self.file_observer.schedule(event_handler, str(src_dir), recursive=False)
            
            # Also watch the parent directory for security_config.json
            parent_dir = src_dir.parent
            self.file_observer.schedule(event_handler, str(parent_dir), recursive=False)
            
            self.file_observer.start()
            self.logger.info("🔥 File watcher started - Security filter hot-reloading ENABLED")
            self.logger.info(f"🔥 Watching: {src_dir} and {parent_dir}")
            print("🔥 HOT-RELOAD ENABLED: Edit security_filter.py or security_config.json to reload!")
            
        except Exception as e:
            self.logger.warning(f"File watcher failed to start: {e}")
            self.logger.info("Service will continue without hot-reloading")
            self.file_observer = None
    
    def clear_processed_cache(self):
        """Clear the processed items cache for testing"""
        self.processed_items.clear()
        self.logger.info("Processed items cache cleared")
    
    def get_security_statistics(self):
        """Get security filter statistics if available"""
        if self.security_filter:
            return self.security_filter.get_statistics()
        return None
    
    def detect_clipboard_content_type(self):
        """Detect if clipboard contains text or image data"""
        try:
            # First try to get image data from Windows clipboard
            try:
                win32clipboard.OpenClipboard()
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIB):
                    # Get image data from clipboard
                    image_data = win32clipboard.GetClipboardData(win32con.CF_DIB)
                    win32clipboard.CloseClipboard()
                    
                    if image_data:
                        self.logger.debug("Detected Windows clipboard image data")
                        return "image", image_data
            except Exception as e:
                self.logger.debug(f"Windows clipboard check failed: {e}")
            finally:
                try:
                    win32clipboard.CloseClipboard()
                except:
                    pass
            
            # Fallback to pyperclip for text and base64 images
            clipboard_content = pyperclip.paste()
            
            if not clipboard_content:
                return None, None
            
            # Check if it's image data (base64)
            if isinstance(clipboard_content, str):
                # Check for common image base64 patterns
                if (clipboard_content.startswith('iVBORw0KGgo') or  # PNG
                    clipboard_content.startswith('/9j/') or          # JPEG
                    clipboard_content.startswith('data:image/') or  # Data URL
                    len(clipboard_content) > 1000 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in clipboard_content[:100])):
                    self.logger.debug("Detected base64 image data")
                    return "image", clipboard_content
            
            # Check if it's text content
            if isinstance(clipboard_content, str) and len(clipboard_content.strip()) > 0:
                self.logger.debug("Detected text content")
                return "text", clipboard_content
            
            return None, None
            
        except Exception as e:
            self.logger.debug(f"Error checking clipboard: {e}")
            return None, None
    
    def compress_image(self, image_path):
        """Compress image to reduce size for upload"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Resize if too large
                if img.size[0] > self.max_dimensions[0] or img.size[1] > self.max_dimensions[1]:
                    img.thumbnail(self.max_dimensions, Image.Resampling.LANCZOS)
                    self.logger.info(f"Resized image to {img.size}")
                
                # Save compressed version
                compressed_path = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                
                # Try different quality levels to get under size limit
                for quality in [85, 70, 50, 30]:
                    img.save(compressed_path.name, 'JPEG', quality=quality, optimize=True)
                    
                    # Check file size
                    file_size = os.path.getsize(compressed_path.name)
                    self.logger.info(f"Compressed image: {file_size} bytes (quality: {quality})")
                    
                    if file_size <= self.max_image_size:
                        break
                
                return compressed_path.name
                
        except Exception as e:
            self.logger.error(f"Error compressing image: {e}")
            return None
    
    def save_image_to_file(self, image_data):
        """Save clipboard image data to temporary file"""
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_path = Path(temp_file.name)
            
            # Handle different image data formats
            if isinstance(image_data, bytes):
                # Windows clipboard image data
                temp_file.write(image_data)
            elif image_data.startswith('data:image/'):
                # Data URL format
                base64_data = image_data.split(',')[1]
                image_bytes = base64.b64decode(base64_data)
                temp_file.write(image_bytes)
            elif image_data.startswith('iVBORw0KGgo'):
                # PNG base64
                image_bytes = base64.b64decode(image_data)
                temp_file.write(image_bytes)
            else:
                # Assume base64
                image_bytes = base64.b64decode(image_data)
                temp_file.write(image_bytes)
            
            temp_file.close()
            
            # Verify it's a valid image
            try:
                with Image.open(temp_path) as img:
                    img.verify()
                self.logger.info(f"Saved valid image: {temp_path}")
                return temp_path
            except Exception:
                os.unlink(temp_path)
                self.logger.warning("Invalid image data in clipboard")
                return None
                
        except Exception as e:
            self.logger.error(f"Error saving clipboard image: {e}")
            return None
    
    def create_filename(self, content_type):
        """Create a unique filename based on content type"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if content_type == "image":
            return f"Screenshot_{timestamp}.jpg"  # Use JPG for compressed images
        else:
            return f"Text_{timestamp}.txt"
    
    def import_text_content(self, text_content):
        """Import text content to Pieces OS as text (simple method)"""
        try:
            self.logger.info(f"Importing text content ({len(text_content)} chars)")
            
            # Apply security filtering if enabled
            filtered_content = text_content
            security_tags = []
            
            if self.security_filter:
                filtered_content, should_skip, detected_items = self.security_filter.filter_content(text_content)
                
                if should_skip:
                    self.logger.warning("SECURITY: Skipping text import due to sensitive content detection")
                    return "SKIPPED_SENSITIVE"
                
                if detected_items:
                    security_tags = ["security-filtered", "redacted"]
                    self.logger.info(f"Applied security filtering: {len(detected_items)} items processed")
            
            # Create metadata for text
            tags = ["text", "clipboard", "auto-imported"] + security_tags
            metadata = FragmentMetadata(
                ext=ClassificationSpecificEnum.TXT,
                tags=tags,
                description=f"Text content captured from clipboard: {datetime.now().isoformat()}"
            )
            
            # Create asset with filtered content (simple method)
            asset_id = self.pieces_client.create_asset(filtered_content, metadata)
            
            self.logger.info(f"SUCCESS: Text content imported with ID: {asset_id}")
            return asset_id
            
        except Exception as e:
            self.logger.error(f"Error importing text content: {e}")
            return None
    
    def import_image_as_binary_file(self, image_path, filename):
        """Import image file to Pieces OS using proper binary upload with compression"""
        try:
            self.logger.info(f"Importing image file as compressed binary: {filename}")
            
            # Compress the image first
            compressed_path = self.compress_image(image_path)
            if not compressed_path:
                self.logger.error("Failed to compress image")
                return None
            
            try:
                # Read compressed image file
                with open(compressed_path, 'rb') as f:
                    image_data = f.read()
                
                file_size = len(image_data)
                self.logger.info(f"Compressed image size: {file_size} bytes")
                
                if file_size > self.max_image_size:
                    self.logger.warning(f"Image still too large after compression: {file_size} bytes")
                    return None
                
                # Convert bytes to array of integers
                byte_array = list(image_data)
                self.logger.debug(f"Converted {file_size} bytes to {len(byte_array)} integers")
                
                # Create TransferableBytes
                transferable_bytes = TransferableBytes(raw=byte_array)
                
                # Create SeededFile
                seeded_file = SeededFile(bytes=transferable_bytes)
                
                # Create SeededClassification (use JPEG since we compressed to JPEG)
                seeded_classification = SeededClassification(specific=ClassificationSpecificEnum.JPG)
                
                # Create SeededFormat
                seeded_format = SeededFormat(
                    file=seeded_file,
                    classification=seeded_classification
                )
                
                # Try creating SeededAsset without application first
                try:
                    seeded_asset = SeededAsset(
                        format=seeded_format
                    )
                    self.logger.info("Created SeededAsset without application")
                except Exception as e:
                    self.logger.warning(f"Failed to create SeededAsset without application: {e}")
                    if self.application is None:
                        self.logger.error("No application available for image import - skipping image")
                        return None
                    
                    try:
                        seeded_asset = SeededAsset(
                            application=self.application,
                            format=seeded_format
                        )
                        self.logger.info("Created SeededAsset with application")
                    except Exception as e2:
                        self.logger.error(f"Failed to create SeededAsset with application: {e2}")
                        return None
                
                # Create Seed
                seed = Seed(asset=seeded_asset)
                
                # Try simple create_asset method first (like text imports)
                try:
                    self.logger.info("Trying simple create_asset method for image...")
                    # Read the compressed image file
                    with open(compressed_path, 'rb') as f:
                        image_data = f.read()
                    
                    # Create metadata for image
                    metadata = FragmentMetadata(
                        ext=ClassificationSpecificEnum.JPG,
                        tags=["image", "clipboard", "auto-imported", "compressed"],
                        description=f"Compressed image captured from clipboard: {datetime.now().isoformat()}"
                    )
                    
                    # Use simple create_asset method (same as text)
                    result_id = self.pieces_client.create_asset(image_data, metadata)
                    self.logger.info(f"Simple method successful: {result_id}")
                    return result_id
                    
                except Exception as simple_error:
                    self.logger.warning(f"Simple method failed: {simple_error}")
                    # Fall back to complex binary upload method
                    try:
                        self.logger.info("Trying complex binary upload method...")
                        result = self.pieces_client.assets_api.assets_create_new_asset(
                            transferables=True,
                            seed=seed,
                            _request_timeout=30
                        )
                        self.logger.info(f"Complex method successful: {result.id}")
                        return result.id
                    except Exception as complex_error:
                        self.logger.error(f"Complex method also failed: {complex_error}")
                        return None
                
            finally:
                # Clean up compressed file
                try:
                    os.unlink(compressed_path)
                except:
                    pass
            
        except Exception as e:
            self.logger.error(f"Error importing image file: {e}")
            if hasattr(e, 'response'):
                self.logger.error(f"Response status: {e.response.status_code}")
                self.logger.error(f"Response text: {e.response.text}")
            return None
    
    def save_to_pieces_dir(self, content_or_path, filename, content_type, security_info=None):
        """Save files to .clipboard-to-pieces directory only"""
        try:
            # Create the file in .clipboard-to-pieces directory
            file_path = self.pieces_dir / filename
            
            if content_type == "text":
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content_or_path)
            else:
                shutil.copy2(content_or_path, file_path)
            
            # Create metadata file with security information
            metadata_path = self.pieces_dir / f"{filename}.pieces.json"
            metadata = {
                "filename": filename,
                "content_type": content_type,
                "timestamp": datetime.now().isoformat(),
                "source": "clipboard_monitor"
            }
            
            # Add security information if available
            if security_info:
                metadata["security"] = security_info
            
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
            
            self.logger.info(f"Saved files to: {self.pieces_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving to .pieces directory: {e}")
            return False
    
    def process_clipboard_item(self, content_type, content):
        """Process clipboard item based on its type"""
        try:
            # Create unique identifier for this clipboard item
            if isinstance(content, bytes):
                item_hash = hashlib.md5(content).hexdigest()
            else:
                item_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
            
            current_time = datetime.now()
            
            # Check if we've processed this exact item recently (within last 30 minutes)
            if item_hash in self.processed_items:
                last_processed = self.processed_items[item_hash]
                time_diff = (current_time - last_processed).total_seconds()
                
                if time_diff < 1800:  # 30 minutes
                    self.logger.debug(f"Item processed {time_diff:.1f}s ago, skipping duplicate")
                    return None  # Return None to indicate no processing was done
                else:
                    self.logger.debug(f"Item processed {time_diff:.1f}s ago, processing again")
            
            self.logger.info(f"Processing new {content_type} content...")
            
            # Create filename
            filename = self.create_filename(content_type)
            
            if content_type == "text":
                # Apply security filtering first if enabled
                filtered_content = content
                security_info = None
                
                if self.security_filter:
                    filtered_content, should_skip, detected_items = self.security_filter.filter_content(content)
                    
                    if should_skip:
                        self.logger.warning("SECURITY: Skipping clipboard item due to sensitive content")
                        return None  # Skip processing entirely
                    
                    if detected_items:
                        security_info = {
                            "filtered": True,
                            "detected_items": len(detected_items),
                            "detection_types": list(set(item['type'] for item in detected_items)),
                            "filter_timestamp": datetime.now().isoformat()
                        }
                        self.logger.info(f"Security filter applied: {len(detected_items)} sensitive items processed")
                
                # Import filtered text content
                asset_id = self.import_text_content(filtered_content)
                
                # Handle special case where import was skipped due to sensitivity
                if asset_id == "SKIPPED_SENSITIVE":
                    return None
                
                # Save filtered content to .pieces directory
                save_success = self.save_to_pieces_dir(filtered_content, filename, content_type, security_info)
                
            elif content_type == "image":
                # Save image to temporary file
                temp_image_path = self.save_image_to_file(content)
                if not temp_image_path:
                    self.logger.warning("Failed to save clipboard image")
                    return False
                
                try:
                    # Import image as compressed binary file (proper method)
                    asset_id = self.import_image_as_binary_file(temp_image_path, filename)
                    
                    # Save original to .pieces directory (images not filtered for now)
                    save_success = self.save_to_pieces_dir(temp_image_path, filename, content_type)
                    
                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(temp_image_path)
                    except:
                        pass
            else:
                self.logger.warning(f"Unknown content type: {content_type}")
                return False
            
            # Mark as processed if file was saved successfully (regardless of API success)
            if save_success:
                self.processed_items[item_hash] = current_time
                
                if asset_id:
                    self.logger.info(f"SUCCESS: {content_type.title()} content imported as {filename}")
                    self.logger.info(f"Asset ID: {asset_id}")
                    self.logger.info(f"Files saved to .clipboard-to-pieces directory")
                else:
                    self.logger.info(f"SUCCESS: {content_type.title()} content saved to .clipboard-to-pieces directory")
                    self.logger.info(f"Note: API import failed, but file saved for Pieces.app auto-import")
                
                # Clean up old entries to prevent memory growth
                if len(self.processed_items) > self.max_cache_size:
                    sorted_items = sorted(self.processed_items.items(), key=lambda x: x[1])
                    for key, _ in sorted_items[:len(sorted_items) - self.max_cache_size]:
                        del self.processed_items[key]
                
                return True
            else:
                self.logger.error(f"FAILED: {content_type.title()} content save failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error processing {content_type} content: {e}")
            return False
    
    def run_service(self, check_interval=2):
        """Run the clipboard monitoring service"""
        self.logger.info(f"Starting robust clipboard monitoring service (checking every {check_interval} seconds)")
        
        try:
            while True:
                try:
                    # Check clipboard content type
                    content_type, content = self.detect_clipboard_content_type()
                    
                    if content_type and content:
                        self.logger.debug(f"{content_type.title()} detected in clipboard ({len(content)} chars)")
                        
                        # Process the clipboard item
                        success = self.process_clipboard_item(content_type, content)
                        
                        # Only log if there was an actual processing attempt (not just skipped duplicate)
                        if success is not None:
                            if success:
                                self.logger.info(f"{content_type.title()} content successfully imported!")
                            else:
                                self.logger.warning(f"{content_type.title()} content import failed")
                    
                    # Wait before next check
                    time.sleep(check_interval)
                    
                except KeyboardInterrupt:
                    self.logger.info("Service stopped by user")
                    break
                except Exception as e:
                    self.logger.error(f"Error in service loop: {e}")
                    time.sleep(check_interval)
                    
        except KeyboardInterrupt:
            self.logger.info("Service stopped")
        finally:
            # Cleanup file watcher
            if self.file_observer:
                self.file_observer.stop()
                self.file_observer.join()
                self.logger.info("File watcher stopped")
            
            self.pieces_client.close()
            self.logger.info("Service shutdown complete")
            
            # Log security statistics if available
            if self.security_filter:
                stats = self.security_filter.get_statistics()
                if stats['total_processed'] > 0:
                    self.logger.info(f"Security Filter Statistics:")
                    self.logger.info(f"  Total processed: {stats['total_processed']}")
                    self.logger.info(f"  Sensitive detected: {stats['sensitive_detected']}")
                    self.logger.info(f"  Items redacted: {stats['redacted_items']}")
                    self.logger.info(f"  Items skipped: {stats['skipped_items']}")

def main():
    # Create a lock file to prevent multiple instances (Windows compatible)
    lock_file_path = Path(__file__).parent / "clipboard_service.lock"
    
    try:
        # Try to create and lock the file (Windows compatible)
        lock_file = open(lock_file_path, 'w')
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        
        print("Robust Clipboard Monitoring Service")
        print("=" * 60)
        print("⚠️  SECURITY WARNING: This service monitors ALL clipboard content!")
        print("⚠️  Sensitive data (passwords, API keys, etc.) will be captured!")
        print("⚠️  Use only on trusted development machines!")
        print("=" * 60)
        print("This service monitors clipboard and imports:")
        print("- Text content -> as text assets (simple method)")
        print("- Screenshots -> as compressed binary file uploads (robust method)")
        print("- Fixed duplicate detection (30 minute window)")
        print("- Fixed Windows + Shift + A screenshot detection")
        print("- Image compression for large screenshots")
        print("- Files saved to: C:\\Users\\dash\\.clipboard-to-pieces")
        print("=" * 60)
        
        # Check .clipboard-to-pieces directory
        service = RobustClipboardService()
        
        if not service.pieces_dir.exists():
            print(f"Creating .clipboard-to-pieces directory: {service.pieces_dir}")
            service.pieces_dir.mkdir(parents=True, exist_ok=True)
            print(f"Created: {service.pieces_dir}")
        
        print("\nService ready! Copy text or take screenshots.")
        print("The service will automatically detect and import them correctly.")
        print("Large images will be compressed for reliable upload!")
        print("Press Ctrl+C to stop the service.")
        
        # Start service
        service.run_service()
        
    except (IOError, OSError):
        print("ERROR: Another instance of the clipboard service is already running!")
        print("Please stop the existing service before starting a new one.")
        print("Use 'taskkill /f /im python.exe' to stop all instances if needed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
