#!/usr/bin/env python3
"""
Security Filter for Clipboard Content
Detects and filters sensitive information from clipboard content
"""

import re
import json
from typing import List, Dict, Tuple, Optional
from datetime import datetime

class SecurityFilter:
    def __init__(self, enable_redaction=True, skip_sensitive=False):
        self.enable_redaction = enable_redaction
        self.skip_sensitive = skip_sensitive
        self.stats = {
            'total_processed': 0,
            'sensitive_detected': 0,
            'redacted_items': 0,
            'skipped_items': 0
        }
        
        # Define sensitive patterns
        self.patterns = {
            'passwords': [
                r'(?i)password\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
                r'(?i)pass\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
                r'(?i)pwd\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
            ],
            'api_keys': [
                r'(?i)api[_-]?key\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
                r'(?i)apikey\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
                r'(?i)access[_-]?key\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
                r'(?i)secret[_-]?key\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
            ],
            'tokens': [
                r'(?i)token\s*[:=]\s*["\']?([a-zA-Z0-9_.-]{20,})["\']?',
                r'(?i)bearer\s+([a-zA-Z0-9_.-]{20,})',
                r'(?i)auth[_-]?token\s*[:=]\s*["\']?([a-zA-Z0-9_.-]{20,})["\']?',
            ],
            'database_urls': [
                r'(?i)database[_-]?url\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
                r'(?i)db[_-]?url\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
                r'(?i)connection[_-]?string\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
                r'(?i)mongodb://[^"\'\s]+',
                r'(?i)postgres://[^"\'\s]+',
                r'(?i)mysql://[^"\'\s]+',
            ],
            'ssh_keys': [
                r'-----BEGIN [A-Z ]+ PRIVATE KEY-----',
                r'-----BEGIN RSA PRIVATE KEY-----',
                r'-----BEGIN OPENSSH PRIVATE KEY-----',
                r'-----BEGIN EC PRIVATE KEY-----',
            ],
            'emails': [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            ],
            'credit_cards': [
                r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b',
            ],
            'ssn': [
                r'\b\d{3}-\d{2}-\d{4}\b',
                r'\b\d{3}\s\d{2}\s\d{4}\b',
            ]
        }
        
        # High-risk patterns that should cause skipping
        self.high_risk_patterns = [
            r'(?i)password\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
            r'-----BEGIN [A-Z ]+ PRIVATE KEY-----',
            r'(?i)secret[_-]?key\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
            r'(?i)api[_-]?key\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
        ]
    
    def add_custom_pattern(self, pattern: str, name: str, group: str = 'custom'):
        """Add a custom pattern for detection"""
        if group not in self.patterns:
            self.patterns[group] = []
        
        self.patterns[group].append({
            'pattern': pattern,
            'name': name,
            'custom': True
        })
    
    def detect_sensitive_content(self, content: str) -> List[Dict]:
        """Detect sensitive content in the given text"""
        detected_items = []
        
        for group, patterns in self.patterns.items():
            for pattern in patterns:
                if isinstance(pattern, dict):
                    # Custom pattern
                    regex = pattern['pattern']
                    name = pattern['name']
                else:
                    # Built-in pattern
                    regex = pattern
                    name = f"{group}_pattern"
                
                try:
                    matches = re.finditer(regex, content, re.MULTILINE | re.IGNORECASE)
                    for match in matches:
                        detected_items.append({
                            'type': group,
                            'name': name,
                            'match': match.group(0),
                            'start': match.start(),
                            'end': match.end(),
                            'severity': 'high' if regex in self.high_risk_patterns else 'medium'
                        })
                except re.error as e:
                    # Skip invalid regex patterns
                    continue
        
        return detected_items
    
    def redact_content(self, content: str, detected_items: List[Dict]) -> str:
        """Redact sensitive content by replacing with placeholders"""
        if not self.enable_redaction:
            return content
        
        # Sort by position (reverse order to maintain indices)
        sorted_items = sorted(detected_items, key=lambda x: x['start'], reverse=True)
        
        redacted_content = content
        for item in sorted_items:
            # Replace with redaction placeholder
            placeholder = f"[REDACTED_{item['type'].upper()}]"
            redacted_content = (
                redacted_content[:item['start']] + 
                placeholder + 
                redacted_content[item['end']:]
            )
        
        return redacted_content
    
    def filter_content(self, content: str) -> Tuple[str, bool, List[Dict]]:
        """
        Filter content for sensitive information
        
        Returns:
            Tuple of (filtered_content, should_skip, detected_items)
        """
        self.stats['total_processed'] += 1
        
        # Detect sensitive content
        detected_items = self.detect_sensitive_content(content)
        
        if not detected_items:
            return content, False, []
        
        self.stats['sensitive_detected'] += 1
        
        # Check if we should skip this content entirely
        should_skip = False
        if self.skip_sensitive:
            # Check for high-risk patterns
            for item in detected_items:
                if item['severity'] == 'high':
                    should_skip = True
                    self.stats['skipped_items'] += 1
                    break
        
        if should_skip:
            return content, True, detected_items
        
        # Redact sensitive content
        if self.enable_redaction:
            filtered_content = self.redact_content(content, detected_items)
            self.stats['redacted_items'] += 1
            return filtered_content, False, detected_items
        
        # Return original content if redaction is disabled
        return content, False, detected_items
    
    def get_statistics(self) -> Dict:
        """Get security filter statistics"""
        return self.stats.copy()
    
    def reset_statistics(self):
        """Reset statistics counters"""
        self.stats = {
            'total_processed': 0,
            'sensitive_detected': 0,
            'redacted_items': 0,
            'skipped_items': 0
        }