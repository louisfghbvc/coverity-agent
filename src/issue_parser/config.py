"""
Configuration Bridge for Issue Parser

This module provides configuration management for the Coverity pipeline adapter,
bridging between pipeline configuration systems and existing CoverityReportTool settings.
"""

import os
from typing import Dict, List, Any, Optional
from pathlib import Path


class CoverityParserConfig:
    """Configuration adapter for CoverityPipelineAdapter and related components.
    
    This class bridges between pipeline configuration systems and the existing
    CoverityReportTool settings, providing a clean property-based API for
    configuration access and validation.
    """
    
    # Default configuration values
    DEFAULT_CONFIG = {
        "exclude_paths": ["DebugUtils/*"],
        "batch_size": 1000,
        "enable_caching": True,
        "parallel_processing": False,
        "validation": {
            "required_fields": ["checkerName", "mainEventFilePathname", "mainEventLineNumber"],
            "validate_json_structure": True,
            "check_issues_array": True
        },
        "output": {
            "format": "pipeline_standard",
            "include_raw_data": True,
            "generate_defect_ids": True,
            "normalize_paths": False
        },
        "exclusion": {
            "enable_default_exclusions": True,
            "custom_patterns": [],
            "case_sensitive": False
        },
        "logging": {
            "level": "INFO",
            "include_parsing_time": True,
            "log_excluded_issues": False
        },
        "performance": {
            "max_memory_mb": 1024,
            "timeout_seconds": 300,
            "max_issues_per_batch": 10000
        }
    }
    
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """Initialize configuration with optional custom values.
        
        Args:
            config_dict: Custom configuration dictionary. If None, uses defaults.
        """
        self.config = self._merge_config(config_dict or {})
        self._validate_config()
    
    def _merge_config(self, user_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge user configuration with defaults.
        
        Args:
            user_config: User-provided configuration
            
        Returns:
            Merged configuration dictionary
        """
        merged = self.DEFAULT_CONFIG.copy()
        
        # Deep merge nested dictionaries
        for key, value in user_config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key].update(value)
            else:
                merged[key] = value
                
        return merged
    
    def _validate_config(self) -> None:
        """Validate configuration values.
        
        Raises:
            ValueError: If configuration values are invalid
        """
        # Validate batch_size
        if not isinstance(self.batch_size, int) or self.batch_size <= 0:
            raise ValueError("batch_size must be a positive integer")
        
        # Validate exclude paths
        if not isinstance(self.default_exclude_paths, list):
            raise ValueError("exclude_paths must be a list")
        
        if not all(isinstance(path, str) for path in self.default_exclude_paths):
            raise ValueError("All exclude_paths must be strings")
        
        # Validate required fields
        if not isinstance(self.validation_required_fields, list):
            raise ValueError("validation.required_fields must be a list")
        
        if not all(isinstance(field, str) for field in self.validation_required_fields):
            raise ValueError("All validation.required_fields must be strings")
        
        # Validate logging level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.logging_level not in valid_levels:
            raise ValueError(f"logging.level must be one of {valid_levels}")
        
        # Validate performance limits
        if not isinstance(self.max_memory_mb, int) or self.max_memory_mb <= 0:
            raise ValueError("performance.max_memory_mb must be a positive integer")
        
        if not isinstance(self.timeout_seconds, int) or self.timeout_seconds <= 0:
            raise ValueError("performance.timeout_seconds must be a positive integer")
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'CoverityParserConfig':
        """Create configuration from YAML file.
        
        Args:
            yaml_path: Path to YAML configuration file
            
        Returns:
            CoverityParserConfig instance
            
        Raises:
            FileNotFoundError: If YAML file doesn't exist
            ValueError: If YAML content is invalid
        """
        import yaml
        
        yaml_path = Path(yaml_path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")
        
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f) or {}
                
            # Extract issue_parser section if it exists
            if 'issue_parser' in config_data:
                config_data = config_data['issue_parser']
                
            return cls(config_data)
            
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration: {e}")
        except Exception as e:
            raise ValueError(f"Error loading configuration: {e}")
    
    @classmethod
    def from_file(cls, file_path: str) -> 'CoverityParserConfig':
        """Create configuration from file (auto-detects YAML/JSON).
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            CoverityParserConfig instance
        """
        file_path = Path(file_path)
        
        if file_path.suffix.lower() in ['.yaml', '.yml']:
            return cls.from_yaml(str(file_path))
        elif file_path.suffix.lower() == '.json':
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            return cls(config_data)
        else:
            raise ValueError(f"Unsupported configuration file format: {file_path.suffix}")
    
    @property
    def default_exclude_paths(self) -> List[str]:
        """Get default path exclusion patterns."""
        return self.config.get('exclude_paths', self.DEFAULT_CONFIG['exclude_paths'])
    
    @property
    def batch_size(self) -> int:
        """Get processing batch size."""
        return self.config.get('batch_size', self.DEFAULT_CONFIG['batch_size'])
    
    @property
    def enable_caching(self) -> bool:
        """Get caching enablement flag."""
        return self.config.get('enable_caching', self.DEFAULT_CONFIG['enable_caching'])
    
    @property
    def parallel_processing(self) -> bool:
        """Get parallel processing enablement flag."""
        return self.config.get('parallel_processing', self.DEFAULT_CONFIG['parallel_processing'])
    
    @property
    def validation_required_fields(self) -> List[str]:
        """Get required JSON fields for validation."""
        return self.config.get('validation', {}).get('required_fields', 
                                                     self.DEFAULT_CONFIG['validation']['required_fields'])
    
    @property
    def validate_json_structure(self) -> bool:
        """Get JSON structure validation flag."""
        return self.config.get('validation', {}).get('validate_json_structure', 
                                                     self.DEFAULT_CONFIG['validation']['validate_json_structure'])
    
    @property
    def check_issues_array(self) -> bool:
        """Get issues array validation flag."""
        return self.config.get('validation', {}).get('check_issues_array', 
                                                     self.DEFAULT_CONFIG['validation']['check_issues_array'])
    
    @property
    def output_format(self) -> str:
        """Get output format specification."""
        return self.config.get('output', {}).get('format', 
                                                 self.DEFAULT_CONFIG['output']['format'])
    
    @property
    def include_raw_data(self) -> bool:
        """Get raw data inclusion flag."""
        return self.config.get('output', {}).get('include_raw_data', 
                                                 self.DEFAULT_CONFIG['output']['include_raw_data'])
    
    @property
    def generate_defect_ids(self) -> bool:
        """Get defect ID generation flag."""
        return self.config.get('output', {}).get('generate_defect_ids', 
                                                 self.DEFAULT_CONFIG['output']['generate_defect_ids'])
    
    @property
    def normalize_paths(self) -> bool:
        """Get path normalization flag."""
        return self.config.get('output', {}).get('normalize_paths', 
                                                 self.DEFAULT_CONFIG['output']['normalize_paths'])
    
    @property
    def enable_default_exclusions(self) -> bool:
        """Get default exclusions enablement flag."""
        return self.config.get('exclusion', {}).get('enable_default_exclusions', 
                                                    self.DEFAULT_CONFIG['exclusion']['enable_default_exclusions'])
    
    @property
    def custom_patterns(self) -> List[str]:
        """Get custom exclusion patterns."""
        return self.config.get('exclusion', {}).get('custom_patterns', 
                                                    self.DEFAULT_CONFIG['exclusion']['custom_patterns'])
    
    @property
    def case_sensitive_exclusion(self) -> bool:
        """Get case sensitivity flag for exclusions."""
        return self.config.get('exclusion', {}).get('case_sensitive', 
                                                    self.DEFAULT_CONFIG['exclusion']['case_sensitive'])
    
    @property
    def logging_level(self) -> str:
        """Get logging level."""
        return self.config.get('logging', {}).get('level', 
                                                  self.DEFAULT_CONFIG['logging']['level'])
    
    @property
    def include_parsing_time(self) -> bool:
        """Get parsing time inclusion flag."""
        return self.config.get('logging', {}).get('include_parsing_time', 
                                                  self.DEFAULT_CONFIG['logging']['include_parsing_time'])
    
    @property
    def log_excluded_issues(self) -> bool:
        """Get excluded issues logging flag."""
        return self.config.get('logging', {}).get('log_excluded_issues', 
                                                  self.DEFAULT_CONFIG['logging']['log_excluded_issues'])
    
    @property
    def max_memory_mb(self) -> int:
        """Get maximum memory limit in MB."""
        return self.config.get('performance', {}).get('max_memory_mb', 
                                                      self.DEFAULT_CONFIG['performance']['max_memory_mb'])
    
    @property
    def timeout_seconds(self) -> int:
        """Get processing timeout in seconds."""
        return self.config.get('performance', {}).get('timeout_seconds', 
                                                      self.DEFAULT_CONFIG['performance']['timeout_seconds'])
    
    @property
    def max_issues_per_batch(self) -> int:
        """Get maximum issues per batch."""
        return self.config.get('performance', {}).get('max_issues_per_batch', 
                                                      self.DEFAULT_CONFIG['performance']['max_issues_per_batch'])
    
    def get_effective_exclude_paths(self) -> List[str]:
        """Get effective exclude paths combining defaults and custom patterns.
        
        Returns:
            Combined list of exclusion patterns
        """
        patterns = []
        
        if self.enable_default_exclusions:
            patterns.extend(self.default_exclude_paths)
        
        patterns.extend(self.custom_patterns)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_patterns = []
        for pattern in patterns:
            if pattern not in seen:
                seen.add(pattern)
                unique_patterns.append(pattern)
        
        return unique_patterns
    
    def validate(self) -> bool:
        """Validate the current configuration.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        try:
            self._validate_config()
            return True
        except ValueError:
            raise
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Returns:
            Configuration as dictionary
        """
        return self.config.copy()
    
    def save_to_yaml(self, yaml_path: str) -> None:
        """Save configuration to YAML file.
        
        Args:
            yaml_path: Path where to save the YAML file
        """
        import yaml
        
        yaml_path = Path(yaml_path)
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Wrap in issue_parser section for clarity
        output_config = {"issue_parser": self.config}
        
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(output_config, f, default_flow_style=False, sort_keys=False, indent=2)
    
    def __str__(self) -> str:
        """String representation for debugging."""
        return f"CoverityParserConfig(batch_size={self.batch_size}, exclude_paths={len(self.default_exclude_paths)} patterns)"
    
    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"CoverityParserConfig(config={self.config})" 