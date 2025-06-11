"""
Source File Manager for Code Retriever

This module handles file reading, encoding detection, and caching for source files.
Provides memory-efficient access to source code content.
"""

import chardet
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from collections import OrderedDict

from .config import CodeRetrieverConfig
from .data_structures import FileMetadata
from .exceptions import FileAccessError, EncodingDetectionError


class SourceFileCache:
    """LRU cache for source file content with TTL support."""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, dict] = OrderedDict()
    
    def get(self, file_path: str) -> Optional[dict]:
        """Get cached file content if still valid."""
        if file_path not in self._cache:
            return None
        
        entry = self._cache[file_path]
        
        # Check TTL
        if datetime.now() - entry['timestamp'] > timedelta(seconds=self.ttl_seconds):
            del self._cache[file_path]
            return None
        
        # Move to end (LRU)
        self._cache.move_to_end(file_path)
        return entry['data']
    
    def put(self, file_path: str, data: dict):
        """Cache file content with timestamp."""
        # Remove oldest entries if at capacity
        while len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)
        
        self._cache[file_path] = {
            'data': data,
            'timestamp': datetime.now()
        }
    
    def clear(self):
        """Clear all cached content."""
        self._cache.clear()


class SourceFileManager:
    """Manages access to source files with encoding detection and caching."""
    
    def __init__(self, config: CodeRetrieverConfig):
        self.config = config
        self._cache = None
        if config.enable_file_cache:
            self._cache = SourceFileCache(max_size=100, ttl_seconds=3600)
    
    def detect_encoding(self, file_path: Union[str, Path]) -> str:
        """Detect file encoding using chardet with fallback strategies.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Detected encoding string
            
        Raises:
            EncodingDetectionError: If encoding cannot be detected
        """
        file_path = Path(file_path)
        
        try:
            # Read sample of file for detection
            sample_size = min(8192, file_path.stat().st_size)
            with open(file_path, 'rb') as f:
                sample = f.read(sample_size)
            
            if not sample:
                return self.config.default_encoding
            
            # Try chardet detection
            detection = chardet.detect(sample)
            if detection and detection['encoding'] and detection['confidence'] > 0.7:
                return detection['encoding']
            
            # Try fallback encodings
            for encoding in self.config.fallback_encodings:
                try:
                    sample.decode(encoding)
                    return encoding
                except UnicodeDecodeError:
                    continue
            
            # If all else fails, use default
            return self.config.default_encoding
            
        except (OSError, IOError) as e:
            raise EncodingDetectionError(f"Failed to detect encoding for {file_path}: {e}")
    
    def read_file_content(self, file_path: Union[str, Path]) -> Tuple[List[str], str, FileMetadata]:
        """Read file content with encoding detection and metadata.
        
        Args:
            file_path: Path to the source file
            
        Returns:
            Tuple of (lines, encoding, metadata)
            
        Raises:
            FileAccessError: If file cannot be read
            EncodingDetectionError: If encoding cannot be detected
        """
        file_path = Path(file_path)
        str_path = str(file_path)
        
        # Check cache first
        if self._cache:
            cached = self._cache.get(str_path)
            if cached:
                return cached['lines'], cached['encoding'], cached['metadata']
        
        # Validate file access
        if not self._validate_file_access(file_path):
            raise FileAccessError(f"File access denied: {file_path}")
        
        try:
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > self.config.max_file_size:
                raise FileAccessError(f"File too large: {file_size} bytes > {self.config.max_file_size}")
            
            # Detect encoding
            encoding = self.detect_encoding(file_path)
            
            # Read file content
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                lines = f.readlines()
            
            # Strip newlines but preserve empty lines
            lines = [line.rstrip('\n\r') for line in lines]
            
            # Create metadata
            language = self._detect_language(file_path)
            metadata = FileMetadata.from_path(file_path, encoding, language)
            
            # Cache if enabled
            if self._cache:
                self._cache.put(str_path, {
                    'lines': lines,
                    'encoding': encoding,
                    'metadata': metadata
                })
            
            return lines, encoding, metadata
            
        except (OSError, IOError) as e:
            raise FileAccessError(f"Failed to read file {file_path}: {e}")
        except UnicodeDecodeError as e:
            raise EncodingDetectionError(f"Failed to decode file {file_path}: {e}")
    
    def get_line_range(self, file_path: Union[str, Path], start_line: int, end_line: int) -> List[str]:
        """Get a specific range of lines from a file.
        
        Args:
            file_path: Path to the source file
            start_line: Starting line number (1-indexed)
            end_line: Ending line number (1-indexed, inclusive)
            
        Returns:
            List of lines in the specified range
            
        Raises:
            FileAccessError: If file cannot be read
            ValueError: If line range is invalid
        """
        if start_line < 1 or end_line < start_line:
            raise ValueError(f"Invalid line range: {start_line}-{end_line}")
        
        lines, _, _ = self.read_file_content(file_path)
        
        # Convert to 0-indexed and handle bounds
        start_idx = max(0, start_line - 1)
        end_idx = min(len(lines), end_line)
        
        if start_idx >= len(lines):
            return []
        
        return lines[start_idx:end_idx]
    
    def get_context_window(self, file_path: Union[str, Path], center_line: int, 
                          before_lines: int, after_lines: int) -> Tuple[List[str], int, int]:
        """Get context window around a specific line.
        
        Args:
            file_path: Path to the source file
            center_line: Center line number (1-indexed)
            before_lines: Number of lines before center
            after_lines: Number of lines after center
            
        Returns:
            Tuple of (context_lines, start_line, end_line)
        """
        lines, _, _ = self.read_file_content(file_path)
        total_lines = len(lines)
        
        # Calculate range
        start_line = max(1, center_line - before_lines)
        end_line = min(total_lines, center_line + after_lines)
        
        # Get context lines
        context_lines = self.get_line_range(file_path, start_line, end_line)
        
        return context_lines, start_line, end_line
    
    def _validate_file_access(self, file_path: Path) -> bool:
        """Validate that file access is allowed."""
        # Check if file exists and is readable
        if not file_path.exists() or not file_path.is_file():
            return False
        
        # Check extension
        if file_path.suffix.lower() not in [".c", ".h", ".cpp", ".cxx", ".cc", ".hpp", ".hxx"]:
            return False
        
        # Check for security issues (basic path traversal protection)
        str_path = str(file_path.resolve())
        if ".." in str_path or str_path.startswith("/etc/") or str_path.startswith("/proc/"):
            return False
        
        return True
    
    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension."""
        extension = file_path.suffix.lower()
        return self.config.extension_mappings.get(extension, "unknown")
    
    def clear_cache(self):
        """Clear the file cache."""
        if self._cache:
            self._cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        if not self._cache:
            return {"enabled": False}
        
        return {
            "enabled": True,
            "entries": len(self._cache._cache),
            "max_size": self._cache.max_size,
            "ttl_seconds": self._cache.ttl_seconds
        }
