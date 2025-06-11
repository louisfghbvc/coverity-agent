"""
Configuration management for Code Retriever component.

This module defines configuration structures and validation for Code Retriever,
following the established configuration pattern from Issue Parser.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Any
from pathlib import Path

from .exceptions import ConfigurationError


@dataclass
class ContextWindowConfig:
    """Configuration for context window extraction."""
    
    # Default context window sizes (lines before/after defect)
    default_before_lines: int = 10
    default_after_lines: int = 10
    max_total_lines: int = 100
    
    # Adaptive sizing based on classification hints
    enable_adaptive_sizing: bool = True
    defect_type_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "BUFFER_OVERFLOW": 1.5,
        "NULL_RETURNS": 1.2,
        "RESOURCE_LEAK": 1.8,
        "DEADCODE": 0.8,
        "UNINIT": 1.3
    })
    
    def get_window_size(self, defect_type: str = None) -> tuple[int, int]:
        """Get context window size for a specific defect type."""
        before = self.default_before_lines
        after = self.default_after_lines
        
        if self.enable_adaptive_sizing and defect_type:
            multiplier = self.defect_type_multipliers.get(defect_type, 1.0)
            before = min(int(before * multiplier), self.max_total_lines // 2)
            after = min(int(after * multiplier), self.max_total_lines // 2)
            
        return before, after


@dataclass
class CodeRetrieverConfig:
    """Complete configuration for Code Retriever component."""
    
    context_window: ContextWindowConfig = field(default_factory=ContextWindowConfig)
    
    # File access settings
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    default_encoding: str = "utf-8"
    fallback_encodings: List[str] = field(default_factory=lambda: ["utf-8", "ascii", "latin-1"])
    
    # Language settings
    primary_languages: List[str] = field(default_factory=lambda: ["c", "cpp"])
    extension_mappings: Dict[str, str] = field(default_factory=lambda: {
        ".c": "c", ".h": "c", ".cpp": "cpp", ".cxx": "cpp", 
        ".cc": "cpp", ".hpp": "cpp", ".hxx": "cpp"
    })
    
    # Performance settings
    enable_file_cache: bool = True
    enable_detailed_logging: bool = False
    
    @classmethod
    def from_environment(cls) -> 'CodeRetrieverConfig':
        """Create configuration with environment variable overrides."""
        config = cls()
        
        if os.getenv("CODE_RETRIEVER_MAX_FILE_SIZE"):
            try:
                config.max_file_size = int(os.getenv("CODE_RETRIEVER_MAX_FILE_SIZE"))
            except ValueError:
                pass
        
        if os.getenv("CODE_RETRIEVER_ENABLE_CACHE"):
            config.enable_file_cache = os.getenv("CODE_RETRIEVER_ENABLE_CACHE").lower() in ("true", "1", "yes")
        
        return config
    
    def validate(self) -> bool:
        """Validate configuration settings."""
        if self.context_window.default_before_lines < 0 or self.context_window.default_after_lines < 0:
            raise ConfigurationError("Context window sizes must be non-negative")
        
        if self.max_file_size < 1024:
            raise ConfigurationError("Maximum file size too small (minimum 1KB)")
        
        return True
