#!/usr/bin/env python3
"""
Context Analyzer for Agentic Content Processing
Analyzes clipboard content to determine optimal processing strategy
"""

import re
import mimetypes
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class ContentType(Enum):
    CODE = "code"
    IMAGE = "image"
    TEXT = "text"
    CONFIG = "config"
    LOG = "log"
    DATA = "data"
    UNKNOWN = "unknown"

class ProcessingStrategy(Enum):
    IMMEDIATE = "immediate"
    BATCH = "batch"
    PRIORITY = "priority"
    DEFER = "defer"

@dataclass
class ContentContext:
    content_type: ContentType
    strategy: ProcessingStrategy
    confidence: float
    metadata: Dict
    tags: List[str]
    priority: int

class ContextAnalyzer:
    """Analyzes content context to determine optimal processing strategy"""
    
    def __init__(self):
        self.code_patterns = [
            r'^(function|def|class|import|from|const|let|var|#include)',
            r'^\s*(if|for|while|switch|case|try|catch)',
            r'^\s*[{}()\[\]]',
            r'^\s*//|^\s*#|^\s*/\*',
            r'^\s*<\?php|^\s*<script|^\s*<html',
        ]
        
        self.config_patterns = [
            r'^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*[:=]',
            r'^\s*\[.*\]\s*$',
            r'^\s*\{.*\}\s*$',
            r'^\s*<!--.*-->\s*$',
        ]
        
        self.log_patterns = [
            r'^\d{4}-\d{2}-\d{2}',
            r'^\d{2}:\d{2}:\d{2}',
            r'\[(ERROR|WARN|INFO|DEBUG|TRACE)\]',
            r'Exception|Error|Warning|Traceback',
        ]
        
        self.data_patterns = [
            r'^\s*[\{\[]\s*$',
            r'^\s*".*":\s*',
            r'^\s*\d+\.\d+',
            r'^\s*[A-Z_]{3,}',
        ]

    def analyze_content(self, content: str, content_type: str = None) -> ContentContext:
        """Analyze content and determine processing strategy"""
        
        # Determine content type
        detected_type = self._detect_content_type(content, content_type)
        
        # Determine processing strategy
        strategy = self._determine_strategy(detected_type, content)
        
        # Calculate confidence
        confidence = self._calculate_confidence(detected_type, content)
        
        # Generate metadata and tags
        metadata = self._generate_metadata(detected_type, content)
        tags = self._generate_tags(detected_type, content)
        
        # Determine priority
        priority = self._calculate_priority(detected_type, content)
        
        return ContentContext(
            content_type=detected_type,
            strategy=strategy,
            confidence=confidence,
            metadata=metadata,
            tags=tags,
            priority=priority
        )

    def _detect_content_type(self, content: str, hint: str = None) -> ContentType:
        """Detect the type of content"""
        
        # Use hint if provided
        if hint:
            if 'image' in hint.lower():
                return ContentType.IMAGE
            elif 'code' in hint.lower():
                return ContentType.CODE
        
        # Analyze content patterns
        lines = content.split('\n')[:10]  # Analyze first 10 lines
        
        # Check for code patterns
        code_score = sum(1 for line in lines if any(re.match(pattern, line, re.IGNORECASE) for pattern in self.code_patterns))
        if code_score >= 2:
            return ContentType.CODE
        
        # Check for config patterns
        config_score = sum(1 for line in lines if any(re.match(pattern, line, re.IGNORECASE) for pattern in self.config_patterns))
        if config_score >= 2:
            return ContentType.CONFIG
        
        # Check for log patterns
        log_score = sum(1 for line in lines if any(re.match(pattern, line, re.IGNORECASE) for pattern in self.log_patterns))
        if log_score >= 2:
            return ContentType.LOG
        
        # Check for data patterns
        data_score = sum(1 for line in lines if any(re.match(pattern, line, re.IGNORECASE) for pattern in self.data_patterns))
        if data_score >= 2:
            return ContentType.DATA
        
        # Default to text
        return ContentType.TEXT

    def _determine_strategy(self, content_type: ContentType, content: str) -> ProcessingStrategy:
        """Determine processing strategy based on content type"""
        
        if content_type == ContentType.CODE:
            return ProcessingStrategy.PRIORITY
        elif content_type == ContentType.IMAGE:
            return ProcessingStrategy.IMMEDIATE
        elif content_type == ContentType.CONFIG:
            return ProcessingStrategy.PRIORITY
        elif content_type == ContentType.LOG:
            return ProcessingStrategy.BATCH
        elif content_type == ContentType.DATA:
            return ProcessingStrategy.IMMEDIATE
        else:
            return ProcessingStrategy.IMMEDIATE

    def _calculate_confidence(self, content_type: ContentType, content: str) -> float:
        """Calculate confidence in content type detection"""
        
        lines = content.split('\n')[:10]
        total_lines = len(lines)
        
        if total_lines == 0:
            return 0.0
        
        if content_type == ContentType.CODE:
            matches = sum(1 for line in lines if any(re.match(pattern, line, re.IGNORECASE) for pattern in self.code_patterns))
        elif content_type == ContentType.CONFIG:
            matches = sum(1 for line in lines if any(re.match(pattern, line, re.IGNORECASE) for pattern in self.config_patterns))
        elif content_type == ContentType.LOG:
            matches = sum(1 for line in lines if any(re.match(pattern, line, re.IGNORECASE) for pattern in self.log_patterns))
        elif content_type == ContentType.DATA:
            matches = sum(1 for line in lines if any(re.match(pattern, line, re.IGNORECASE) for pattern in self.data_patterns))
        else:
            matches = total_lines // 2  # Default confidence for text
        
        return min(matches / total_lines, 1.0)

    def _generate_metadata(self, content_type: ContentType, content: str) -> Dict:
        """Generate metadata for the content"""
        
        metadata = {
            'content_length': len(content),
            'line_count': len(content.split('\n')),
            'word_count': len(content.split()),
        }
        
        if content_type == ContentType.CODE:
            metadata['language_hints'] = self._detect_language_hints(content)
        elif content_type == ContentType.LOG:
            metadata['log_levels'] = self._extract_log_levels(content)
        elif content_type == ContentType.DATA:
            metadata['data_format'] = self._detect_data_format(content)
        
        return metadata

    def _generate_tags(self, content_type: ContentType, content: str) -> List[str]:
        """Generate tags for the content"""
        
        tags = [content_type.value]
        
        if content_type == ContentType.CODE:
            tags.extend(self._detect_language_hints(content))
        elif content_type == ContentType.LOG:
            tags.append('log')
            tags.extend(self._extract_log_levels(content))
        elif content_type == ContentType.DATA:
            tags.append('data')
            tags.append(self._detect_data_format(content))
        
        return tags

    def _calculate_priority(self, content_type: ContentType, content: str) -> int:
        """Calculate processing priority (1-10, higher is more important)"""
        
        base_priority = {
            ContentType.CODE: 8,
            ContentType.IMAGE: 7,
            ContentType.CONFIG: 6,
            ContentType.DATA: 5,
            ContentType.TEXT: 4,
            ContentType.LOG: 3,
            ContentType.UNKNOWN: 2,
        }
        
        priority = base_priority.get(content_type, 2)
        
        # Adjust based on content characteristics
        if len(content) > 1000:
            priority += 1
        if any(keyword in content.lower() for keyword in ['error', 'exception', 'fail']):
            priority += 2
        
        return min(priority, 10)

    def _detect_language_hints(self, content: str) -> List[str]:
        """Detect programming language hints"""
        
        hints = []
        content_lower = content.lower()
        
        if 'function' in content_lower or 'const' in content_lower or 'let' in content_lower:
            hints.append('javascript')
        if 'def ' in content_lower or 'import ' in content_lower:
            hints.append('python')
        if '#include' in content_lower or 'int main' in content_lower:
            hints.append('c')
        if 'class ' in content_lower and 'public ' in content_lower:
            hints.append('java')
        if '<?php' in content_lower:
            hints.append('php')
        if '<html' in content_lower or '<script' in content_lower:
            hints.append('html')
        
        return hints

    def _extract_log_levels(self, content: str) -> List[str]:
        """Extract log levels from content"""
        
        levels = []
        for line in content.split('\n')[:20]:
            if re.search(r'\[(ERROR|WARN|INFO|DEBUG|TRACE)\]', line, re.IGNORECASE):
                level = re.search(r'\[(ERROR|WARN|INFO|DEBUG|TRACE)\]', line, re.IGNORECASE).group(1).lower()
                if level not in levels:
                    levels.append(level)
        
        return levels

    def _detect_data_format(self, content: str) -> str:
        """Detect data format"""
        
        content_stripped = content.strip()
        
        if content_stripped.startswith('{') and content_stripped.endswith('}'):
            return 'json'
        elif content_stripped.startswith('[') and content_stripped.endswith(']'):
            return 'json-array'
        elif '<' in content_stripped and '>' in content_stripped:
            return 'xml'
        elif '=' in content_stripped and '\n' in content_stripped:
            return 'key-value'
        else:
            return 'text'


