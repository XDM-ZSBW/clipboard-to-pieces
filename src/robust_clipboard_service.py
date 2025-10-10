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
from ocr_service import get_ocr_service
from context_analyzer import ContextAnalyzer, ContentContext
from state_manager import StateManager, ProcessingState
from feedback_system import FeedbackSystem, FeedbackType, AdaptiveProcessor
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pieces_os_client.wrapper import PiecesClient
from pieces_os_client.models.classification_specific_enum import ClassificationSpecificEnum
from pieces_os_client.models.fragment_metadata import FragmentMetadata
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
    """File watcher for hot-reloading security filter changes
    
    This class monitors security_filter.py and security_config.json for changes
    and automatically reloads the security filter without restarting the service.
    """
    
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
                self.service.logger.info(f"[RELOAD] {reload_id}: Security filter HOT-RELOADED successfully!")
                self.service.logger.info(f"[RELOAD] {reload_id}: File changed: {os.path.basename(event.src_path)}")
                self.service.logger.info(f"[RELOAD] {reload_id}: New patterns loaded: {len(new_filter.patterns)} pattern groups")
                self.service.logger.info(f"[RELOAD] {reload_id}: Filter version: {id(new_filter)} (old: {id(old_filter)})")
                
                # Print to console for immediate feedback
                print(f"\n[RELOAD] {reload_id}: SECURITY FILTER HOT-RELOADED!")
                print(f"[RELOAD] {reload_id}: You are now on the NEW code path")
                print(f"[RELOAD] {reload_id}: Filter ID: {id(new_filter)}")
                print(f"[RELOAD] {reload_id}: Ready to test new patterns!\n")
                
            except Exception as e:
                self.service.logger.error(f"[ERROR] HOT-RELOAD FAILED: {e}")
                print(f"\n[ERROR] HOT-RELOAD FAILED: {e}")
                print("[ERROR] Service continues with OLD code path\n")

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
        self.max_image_size = 500000  # 500KB limit
        self.max_dimensions = (1920, 1080)  # Max width/height
        
        # Initialize security filter
        self.security_filter = self._load_security_config()
        
        # Initialize OCR service
        self.ocr_service = get_ocr_service()
        self.ocr_config = self._load_ocr_config()
        
        # Initialize agentic components
        self.context_analyzer = ContextAnalyzer()
        self.state_manager = StateManager()
        self.feedback_system = FeedbackSystem()
        self.adaptive_processor = AdaptiveProcessor(self.feedback_system)
        
        # Register feedback handlers
        self._register_feedback_handlers()
        
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
        
        # Log OCR availability
        if self.ocr_config.get('enabled', True) and self.ocr_service.is_available():
            engines = self.ocr_service.get_available_engines()
            preferred = self.ocr_service.get_preferred_engine()
            self.logger.info(f"OCR service available - engines: {engines}, preferred: {preferred}")
            self.logger.info("Screenshots will be OCR'd for sensitive content detection")
            print("OCR Service: ENABLED - Screenshots will be scanned for sensitive content")
        else:
            self.logger.warning("OCR service not available - screenshots will not be scanned for text")
            print("OCR Service: DISABLED - Install Tesseract for screenshot scanning")
        
        # Test security patterns on startup
        if self.security_filter:
            self.test_security_patterns()
    
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
    
    def _load_ocr_config(self):
        """Load OCR configuration from security_config.json"""
        try:
            # Look for security config file
            config_path = Path(__file__).parent.parent / "security_config.json"
            
            if not config_path.exists():
                self.logger.warning("No security_config.json found - using default OCR settings")
                return {
                    'enabled': True,
                    'engine': 'tesseract',
                    'extract_text_from_images': True,
                    'apply_security_filtering': True,
                    'skip_images_with_sensitive_text': False,
                    'privacy_mode': True,
                    'local_processing_only': True
                }
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            ocr_config = config.get('ocr', {})
            
            # Set defaults for privacy-focused Tesseract-only configuration
            default_config = {
                'enabled': True,
                'engine': 'tesseract',
                'extract_text_from_images': True,
                'apply_security_filtering': True,
                'skip_images_with_sensitive_text': False,
                'privacy_mode': True,
                'local_processing_only': True
            }
            
            # Merge with defaults
            default_config.update(ocr_config)
            
            self.logger.info("OCR configuration loaded successfully")
            return default_config
            
        except Exception as e:
            self.logger.error(f"Failed to load OCR config: {e}")
            self.logger.warning("Using default OCR settings")
            return {
                'enabled': True,
                'engine': 'tesseract',
                'extract_text_from_images': True,
                'apply_security_filtering': True,
                'skip_images_with_sensitive_text': False,
                'privacy_mode': True,
                'local_processing_only': True
            }
    
    def _start_file_watcher(self):
        """Start file watcher for hot reloading security filter
        
        This method initializes the watchdog observer to monitor for changes
        in security_filter.py and security_config.json files.
        """
        try:
            # Use Windows-specific approach to avoid threading issues
            import threading
            import time
            
            # Create a simple polling-based file watcher instead of watchdog
            self.file_watcher_active = True
            self.watched_files = {
                'security_filter.py': Path(__file__).parent / 'security_filter.py',
                'security_config.json': Path(__file__).parent.parent / 'security_config.json'
            }
            self.file_timestamps = {}
            
            # Initialize timestamps
            for name, path in self.watched_files.items():
                if path.exists():
                    self.file_timestamps[name] = path.stat().st_mtime
            
            def file_watcher_loop():
                reload_count = 0
                while self.file_watcher_active:
                    try:
                        for name, path in self.watched_files.items():
                            if path.exists():
                                current_mtime = path.stat().st_mtime
                                if name in self.file_timestamps and current_mtime > self.file_timestamps[name]:
                                    # File changed!
                                    reload_count += 1
                                    reload_id = f"RELOAD-{reload_count:03d}"
                                    
                                    try:
                                        # Reload the security filter module
                                        import security_filter
                                        importlib.reload(security_filter)
                                        
                                        # Create new filter instance
                                        old_filter = self.security_filter
                                        new_filter = security_filter.SecurityFilter(
                                            enable_redaction=old_filter.enable_redaction if old_filter else True,
                                            skip_sensitive=old_filter.skip_sensitive if old_filter else False
                                        )
                                        
                                        # Update service with new filter
                                        self.security_filter = new_filter
                                        
                                        # Log the reload with clear indicators
                                        self.logger.info(f"[RELOAD] {reload_id}: Security filter HOT-RELOADED successfully!")
                                        self.logger.info(f"[RELOAD] {reload_id}: File changed: {name}")
                                        self.logger.info(f"[RELOAD] {reload_id}: New patterns loaded: {len(new_filter.patterns)} pattern groups")
                                        self.logger.info(f"[RELOAD] {reload_id}: Filter version: {id(new_filter)} (old: {id(old_filter)})")
                                        
                                        # Print to console for immediate feedback
                                        print(f"\n[RELOAD] {reload_id}: SECURITY FILTER HOT-RELOADED!")
                                        print(f"[RELOAD] {reload_id}: You are now on the NEW code path")
                                        print(f"[RELOAD] {reload_id}: Filter ID: {id(new_filter)}")
                                        print(f"[RELOAD] {reload_id}: Ready to test new patterns!\n")
                                        
                                    except Exception as e:
                                        self.logger.error(f"[ERROR] HOT-RELOAD FAILED: {e}")
                                        print(f"\n[ERROR] HOT-RELOAD FAILED: {e}")
                                        print("[ERROR] Service continues with OLD code path\n")
                                    
                                    # Update timestamp
                                    self.file_timestamps[name] = current_mtime
                                elif name not in self.file_timestamps:
                                    self.file_timestamps[name] = current_mtime
                        
                        time.sleep(1)  # Check every second
                        
                    except Exception as e:
                        self.logger.error(f"File watcher error: {e}")
                        time.sleep(5)  # Wait longer on error
            
            # Start the file watcher in a separate thread
            self.file_watcher_thread = threading.Thread(target=file_watcher_loop, daemon=True)
            self.file_watcher_thread.start()
            
            self.logger.info("[HOT-RELOAD] File watcher started - Security filter hot-reloading ENABLED")
            self.logger.info(f"[HOT-RELOAD] Watching: {list(self.watched_files.keys())}")
            print("[HOT-RELOAD] ENABLED: Edit security_filter.py or security_config.json to reload!")
            
        except Exception as e:
            self.logger.warning(f"File watcher setup failed: {e}")
            self.logger.info("Service will continue without hot-reloading")
            self.file_watcher_active = False
    
    def clear_processed_cache(self):
        """Clear the processed items cache for testing"""
        self.processed_items.clear()
        self.logger.info("Processed items cache cleared")
    
    def get_security_statistics(self):
        """Get security filter statistics if available"""
        if self.security_filter:
            return self.security_filter.get_statistics()
        return None
    
    def test_security_patterns(self):
        """Test security patterns with sample data"""
        if not self.security_filter:
            print("Security filter not available")
            return
        
        test_data = [
            "Email: test@example.com",
            "Credit Card: 4111 1111 1111 1111", 
            "SSN: 123-45-6789",
            "Phone: +1-555-123-4567",
            "mycompany_secret: MyCompanySecretKey2024",
            "internal_api_key: int_ak_9876543210fedcba9876543210fedcba",
            "company_password: CompanyPassword@2024"
        ]
        
        print("\nTesting Security Patterns:")
        print("=" * 50)
        
        for test_text in test_data:
            filtered_content, should_skip, detected_items = self.security_filter.filter_content(test_text)
            if detected_items:
                print(f"DETECTED: {test_text}")
                for item in detected_items:
                    print(f"   - {item['type']}: {item['match']}")
            else:
                print(f"NOT DETECTED: {test_text}")
        
        print("=" * 50)
    
    def _register_feedback_handlers(self):
        """Register feedback handlers for agentic learning"""
        
        def success_handler(event):
            self.logger.info(f"Success feedback: {event.message}")
            # Update success metrics
            
        def failure_handler(event):
            self.logger.warning(f"Failure feedback: {event.message}")
            # Trigger retry logic if needed
            
        def performance_handler(event):
            self.logger.info(f"Performance feedback: {event.message}")
            # Update performance metrics
            
        def quality_handler(event):
            self.logger.info(f"Quality feedback: {event.message}")
            # Update quality scores
        
        self.feedback_system.register_handler(FeedbackType.SUCCESS, success_handler)
        self.feedback_system.register_handler(FeedbackType.FAILURE, failure_handler)
        self.feedback_system.register_handler(FeedbackType.PERFORMANCE, performance_handler)
        self.feedback_system.register_handler(FeedbackType.QUALITY, quality_handler)
    
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
                for quality in [90, 85, 70, 50]:
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
                    print(f"\nSECURITY: Sensitive content detected in text and redacted from Pieces.app")
            
            # Create metadata for text
            tags = ["text", "clipboard", "auto-imported"] + security_tags
            
            # Create description with security notice if sensitive content detected
            description = f"Text content captured from clipboard: {datetime.now().isoformat()}"
            if security_tags:
                description += " | Sensitive content detected and redacted"
            
            metadata = FragmentMetadata(
                ext=ClassificationSpecificEnum.TXT,
                tags=tags,
                description=description
            )
            
            # Create asset with filtered content (simple method)
            asset_id = self.pieces_client.create_asset(filtered_content, metadata)
            
            self.logger.info(f"SUCCESS: Text content imported with ID: {asset_id}")
            return asset_id
            
        except Exception as e:
            self.logger.error(f"Error importing text content: {e}")
            return None
    
    def extract_text_from_image(self, image_path):
        """Extract text from image using OCR for security filtering"""
        if not self.ocr_config.get('enabled', True):
            self.logger.debug("OCR disabled in configuration")
            return None
            
        if not self.ocr_service.is_available():
            self.logger.debug("OCR not available, skipping text extraction")
            return None
        
        try:
            self.logger.info("Extracting text from image using OCR...")
            extracted_text, success = self.ocr_service.extract_text(image_path)
            
            if success and extracted_text.strip():
                self.logger.info(f"OCR extracted {len(extracted_text)} characters from image")
                self.logger.debug(f"OCR extracted text: {extracted_text[:200]}...")  # First 200 chars for debugging
                return extracted_text
            else:
                self.logger.debug("No text extracted from image")
                return None
                
        except Exception as e:
            self.logger.error(f"OCR text extraction failed: {e}")
            return None
    
    def extract_text_from_image_with_boxes(self, image_path):
        """Extract text from image using OCR with bounding boxes for redaction"""
        if not self.ocr_config.get('enabled', True):
            self.logger.debug("OCR disabled in configuration")
            return None, False, []
            
        if not self.ocr_service.is_available():
            self.logger.debug("OCR not available, skipping text extraction")
            return None, False, []
        
        try:
            self.logger.info("Extracting text from image using OCR with bounding boxes...")
            extracted_text, success, bounding_boxes = self.ocr_service.extract_text_with_boxes(image_path)
            
            if success and extracted_text.strip():
                self.logger.info(f"OCR extracted {len(extracted_text)} characters from image with {len(bounding_boxes)} bounding boxes")
                self.logger.debug(f"OCR extracted text: {extracted_text[:200]}...")  # First 200 chars for debugging
                return extracted_text, success, bounding_boxes
            else:
                self.logger.debug("No text extracted from image")
                return None, False, []
                
        except Exception as e:
            self.logger.error(f"OCR text extraction with boxes failed: {e}")
            return None, False, []
    
    def redact_sensitive_areas_in_image(self, image_path, detected_items, bounding_boxes):
        """Draw black rectangles over sensitive areas in the image using OCR bounding boxes"""
        try:
            from PIL import Image, ImageDraw
            
            # Open the image
            with Image.open(image_path) as img:
                # Create a copy to draw on
                redacted_img = img.copy()
                draw = ImageDraw.Draw(redacted_img)
                
                # Draw black rectangles over detected sensitive areas
                redacted_count = 0
                for item in detected_items:
                    # Find matching bounding box for this sensitive text
                    sensitive_text = item['match'].lower()
                    
                    for box in bounding_boxes:
                        box_text = box['text'].lower()
                        
                        # Check if this bounding box contains the sensitive text
                        if sensitive_text in box_text or box_text in sensitive_text:
                            # Draw black rectangle over the sensitive area
                            x1 = box['x']
                            y1 = box['y']
                            x2 = x1 + box['width']
                            y2 = y1 + box['height']
                            
                            # Add small padding around the text
                            padding = 2
                            x1 = max(0, x1 - padding)
                            y1 = max(0, y1 - padding)
                            x2 = min(img.width, x2 + padding)
                            y2 = min(img.height, y2 + padding)
                            
                            # Draw black rectangle
                            draw.rectangle([x1, y1, x2, y2], fill='black')
                            
                            self.logger.debug(f"Redacted sensitive area: {item['type']} '{item['match']}' at ({x1},{y1})-({x2},{y2})")
                            redacted_count += 1
                            break  # Found match, move to next sensitive item
                
                if redacted_count > 0:
                    # Save redacted image
                    redacted_path = image_path.replace('.png', '_redacted.png').replace('.jpg', '_redacted.jpg')
                    redacted_img.save(redacted_path)
                    
                    self.logger.info(f"Created redacted image with {redacted_count} sensitive areas covered: {redacted_path}")
                    return redacted_path
                else:
                    self.logger.debug("No sensitive areas found to redact")
                    return image_path
                
        except Exception as e:
            self.logger.error(f"Failed to redact sensitive areas in image: {e}")
            return image_path  # Return original if redaction fails
    
    def import_image_as_binary_file(self, image_path, filename):
        """Import image file to Pieces OS using proper binary upload with compression"""
        try:
            self.logger.info(f"Importing image file as compressed binary: {filename}")
            
            # OCR disabled - skip text extraction and security filtering
            extracted_text = None
            security_info = None
            redacted_image_path = image_path
            
            # Compress the redacted image (or original if no redaction)
            compressed_path = self.compress_image(redacted_image_path)
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
                
                # Try to create image asset using binary upload method
                try:
                    self.logger.info("Creating image asset using binary upload method...")
                    
                    # Read the compressed image file
                    with open(compressed_path, 'rb') as f:
                        image_data = f.read()

                    # Create metadata for image
                    tags = ["image", "clipboard", "auto-imported", "compressed"]
                    description = f"Compressed image captured from clipboard: {datetime.now().isoformat()}"

                    metadata = FragmentMetadata(
                        ext=ClassificationSpecificEnum.JPG,
                        tags=tags,
                        description=description
                    )

                    # Use the original working method from commit 340991a
                    try:
                        # Convert bytes to array of integers
                        byte_array = list(image_data)
                        self.logger.debug(f"Converted {file_size} bytes to {len(byte_array)} integers")
                        
                        # Create TransferableBytes
                        from pieces_os_client.models.transferable_bytes import TransferableBytes
                        transferable_bytes = TransferableBytes(raw=byte_array)
                        
                        # Create SeededFile
                        from pieces_os_client.models.seeded_file import SeededFile
                        seeded_file = SeededFile(bytes=transferable_bytes)
                        
                        # Create SeededClassification (use JPEG since we compressed to JPEG)
                        from pieces_os_client.models.seeded_classification import SeededClassification
                        seeded_classification = SeededClassification(specific=ClassificationSpecificEnum.JPG)
                        
                        # Create SeededFormat
                        from pieces_os_client.models.seeded_format import SeededFormat
                        seeded_format = SeededFormat(
                            file=seeded_file,
                            classification=seeded_classification
                        )
                        
                        # Try creating SeededAsset without application first
                        try:
                            from pieces_os_client.models.seeded_asset import SeededAsset
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
                        from pieces_os_client.models.seed import Seed
                        seed = Seed(asset=seeded_asset)
                        
                        # Try binary upload method first (creates proper image assets)
                        try:
                            self.logger.info("Creating image asset via binary upload method...")
                            result = self.pieces_client.assets_api.assets_create_new_asset(seeded_asset)
                            result_id = result.id
                            self.logger.info(f"Image asset created successfully via binary upload: {result_id}")
                            return result_id
                            
                        except Exception as e:
                            self.logger.error(f"Binary upload method failed: {e}")
                            self.logger.error(f"Binary upload error type: {type(e)}")
                            
                            # Fallback: Use create_asset with base64 (creates text snippets but at least imports something)
                            self.logger.info("Falling back to create_asset method with base64...")
                            try:
                                # Read the compressed image file
                                with open(compressed_path, 'rb') as f:
                                    image_data = f.read()
                                
                                # Create metadata for image
                                metadata = FragmentMetadata(
                                    ext=ClassificationSpecificEnum.JPG,
                                    tags=["image", "clipboard", "auto-imported", "compressed", "fallback"],
                                    description=f"Compressed image captured from clipboard: {datetime.now().isoformat()} (imported as text due to binary upload failure)"
                                )

                                # Use create_asset method with base64 string
                                base64_data = base64.b64encode(image_data).decode('utf-8')
                                result_id = self.pieces_client.create_asset(base64_data, metadata)
                                self.logger.info(f"Image import successful via create_asset fallback: {result_id}")
                                return result_id
                                
                            except Exception as e2:
                                self.logger.error(f"Fallback create_asset method also failed: {e2}")
                                return None
                        
                    except Exception as e:
                        self.logger.error(f"Image import failed: {e}")
                        return None
                
                except Exception as error:
                    self.logger.error(f"Image import failed: {error}")
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
        """Process clipboard item using agentic patterns"""
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
            
            # Use agentic processing
            return self._process_with_agentic_patterns(item_hash, content_type, content, current_time)
            
        except Exception as e:
            self.logger.error(f"Error processing clipboard item: {e}")
            self.feedback_system.provide_feedback(
                FeedbackType.FAILURE,
                item_hash,
                f"Error processing clipboard item: {e}",
                {'error': str(e)},
                severity=8
            )
            return None
    
    def _process_with_agentic_patterns(self, content_id: str, content_type: str, content, current_time):
        """Process content using agentic patterns"""
        
        # Analyze content context
        if content_type == "text":
            context = self.context_analyzer.analyze_content(content)
        else:
            context = self.context_analyzer.analyze_content("", content_type)
        
        # Get optimal strategy from state manager
        optimal_strategy = self.state_manager.get_optimal_strategy(context.content_type.value)
        
        # Start processing record
        record = self.state_manager.start_processing(content_id, context.content_type.value, optimal_strategy)
        
        start_time = time.time()
        
        try:
            # Create filename
            filename = self.create_filename(content_type)
            
            if content_type == "text":
                # Use existing text import method
                result = self.import_text_content(content)
                if result == "SKIPPED_SENSITIVE":
                    return None
                asset_id = result
                
                # Save text content to .pieces directory
                save_success = self.save_to_pieces_dir(content, filename, content_type, None)
                
            elif content_type == "image":
                # Save image to temporary file
                temp_image_path = self.save_image_to_file(content)
                if not temp_image_path:
                    self.logger.warning("Failed to save clipboard image")
                    return False
                
                try:
                    # Extract text from image for security filtering
                    extracted_text = self.extract_text_from_image(temp_image_path)
                    security_info = None
                    
                    # Apply security filtering to extracted text if available
                    if extracted_text and self.security_filter and self.ocr_config.get('apply_security_filtering', True):
                        filtered_text, should_skip, detected_items = self.security_filter.filter_content(extracted_text)
                        
                        if should_skip and self.ocr_config.get('skip_images_with_sensitive_text', False):
                            self.logger.warning("SECURITY: Skipping image import due to sensitive content detected in OCR text")
                            return None  # Skip processing entirely
                        
                        if detected_items:
                            security_info = {
                                "ocr_filtered": True,
                                "extracted_text_length": len(extracted_text),
                                "detected_items": len(detected_items),
                                "detection_types": list(set(item['type'] for item in detected_items)),
                                "filter_timestamp": datetime.now().isoformat()
                            }
                            self.logger.info(f"Security filter applied to OCR text: {len(detected_items)} sensitive items processed")
                            print(f"\n🔒 SECURITY: Sensitive content detected in screenshot and redacted from Pieces.app")
                    
                    # Import image as compressed binary file (proper method)
                    asset_id = self.import_image_as_binary_file(temp_image_path, filename)
                    
                    # Handle special case where import was skipped due to sensitivity
                    if asset_id == "SKIPPED_SENSITIVE":
                        return None
                    
                    # Save original to .pieces directory with security info
                    save_success = self.save_to_pieces_dir(temp_image_path, filename, content_type, security_info)
                    
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
                self.processed_items[content_id] = current_time
                
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
            if hasattr(self, 'file_watcher_active'):
                self.file_watcher_active = False
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
        print("***  SECURITY WARNING: This service monitors ALL clipboard content!")
        print("***  Sensitive data (passwords, API keys, etc.) will be captured!")
        print("***  Use only on trusted development machines!")
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
