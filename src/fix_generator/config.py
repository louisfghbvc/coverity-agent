"""
Configuration management for LLM Fix Generator with NVIDIA NIM integration.

This module provides configuration classes and validation for NIM providers,
prompt engineering, and fix generation parameters.
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from pathlib import Path


@dataclass
class NIMProviderConfig:
    """Configuration for a NVIDIA NIM provider."""
    
    name: str
    base_url: str
    api_key: str
    model: str
    max_tokens: int = 2000
    temperature: float = 0.1
    timeout: int = 30
    
    # NIM-specific settings
    use_streaming: bool = False
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Cost and rate limiting
    max_requests_per_minute: int = 60
    estimated_cost_per_1k_tokens: Optional[float] = None
    
    def __post_init__(self):
        """Validate provider configuration."""
        if not self.base_url:
            raise ValueError(f"Base URL is required for provider {self.name}")
        
        if not self.api_key:
            raise ValueError(f"API key is required for provider {self.name}")
        
        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError(f"Temperature must be 0.0-2.0, got {self.temperature}")
        
        if self.max_tokens <= 0:
            raise ValueError(f"Max tokens must be positive, got {self.max_tokens}")
        
        if self.timeout <= 0:
            raise ValueError(f"Timeout must be positive, got {self.timeout}")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], name: str) -> 'NIMProviderConfig':
        """Create provider config from dictionary."""
        # Expand environment variables in configuration values
        expanded_data = {}
        for key, value in data.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                expanded_data[key] = os.getenv(env_var, value)
            else:
                expanded_data[key] = value
        
        return cls(name=name, **expanded_data)


@dataclass
class AnalysisConfig:
    """Configuration for defect analysis and fix generation."""
    
    # Fix generation settings
    generate_multiple_candidates: bool = True
    num_candidates: int = 3
    include_reasoning_trace: bool = True
    
    # Classification settings
    enable_defect_categorization: bool = True
    confidence_threshold: float = 0.6
    include_severity_assessment: bool = True
    
    # Context settings
    max_context_lines: int = 50
    include_function_signature: bool = True
    include_surrounding_code: bool = True
    
    def __post_init__(self):
        """Validate analysis configuration."""
        if not (1 <= self.num_candidates <= 10):
            raise ValueError(f"Number of candidates must be 1-10, got {self.num_candidates}")
        
        if not (0.0 <= self.confidence_threshold <= 1.0):
            raise ValueError(f"Confidence threshold must be 0.0-1.0, got {self.confidence_threshold}")
        
        if self.max_context_lines <= 0:
            raise ValueError(f"Max context lines must be positive, got {self.max_context_lines}")


@dataclass
class QualityConfig:
    """Configuration for quality control and validation."""
    
    # Style consistency
    enforce_style_consistency: bool = True
    style_consistency_threshold: float = 0.6
    
    # Safety checks
    validate_syntax: bool = True
    safety_checks: bool = True
    require_explanation: bool = True
    
    # Fix constraints
    max_files_per_fix: int = 3
    max_lines_per_fix: int = 100
    
    # Validation thresholds
    min_confidence_for_auto_apply: float = 0.8
    min_style_score_for_auto_apply: float = 0.7
    
    def __post_init__(self):
        """Validate quality configuration."""
        if not (0.0 <= self.style_consistency_threshold <= 1.0):
            raise ValueError(f"Style consistency threshold must be 0.0-1.0, got {self.style_consistency_threshold}")
        
        if not (0.0 <= self.min_confidence_for_auto_apply <= 1.0):
            raise ValueError(f"Min confidence threshold must be 0.0-1.0, got {self.min_confidence_for_auto_apply}")
        
        if not (0.0 <= self.min_style_score_for_auto_apply <= 1.0):
            raise ValueError(f"Min style score threshold must be 0.0-1.0, got {self.min_style_score_for_auto_apply}")
        
        if self.max_files_per_fix <= 0:
            raise ValueError(f"Max files per fix must be positive, got {self.max_files_per_fix}")


@dataclass
class OptimizationConfig:
    """Configuration for performance optimization and cost control."""
    
    # Caching
    cache_similar_defects: bool = True
    cache_duration_hours: int = 24
    cache_max_size: int = 1000
    
    # Token optimization
    token_limit_per_defect: int = 2000
    enable_prompt_compression: bool = True
    context_window_optimization: bool = True
    
    # Performance monitoring
    enable_performance_tracking: bool = True
    log_token_usage: bool = True
    track_generation_time: bool = True
    
    # Cost control
    max_cost_per_defect: Optional[float] = 1.0
    daily_cost_limit: Optional[float] = None
    
    def __post_init__(self):
        """Validate optimization configuration."""
        if self.cache_duration_hours <= 0:
            raise ValueError(f"Cache duration must be positive, got {self.cache_duration_hours}")
        
        if self.cache_max_size <= 0:
            raise ValueError(f"Cache max size must be positive, got {self.cache_max_size}")
        
        if self.token_limit_per_defect <= 0:
            raise ValueError(f"Token limit must be positive, got {self.token_limit_per_defect}")


@dataclass
class LLMFixGeneratorConfig:
    """Main configuration class for the LLM Fix Generator."""
    
    # Provider configuration
    providers: Dict[str, NIMProviderConfig] = field(default_factory=dict)
    primary_provider: str = "nvidia_nim"
    fallback_providers: List[str] = field(default_factory=list)
    
    # Component configurations
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)
    
    # Logging and debugging
    log_level: str = "INFO"
    debug_mode: bool = False
    save_raw_responses: bool = False
    
    def __post_init__(self):
        """Validate main configuration."""
        if not self.providers:
            raise ValueError("At least one provider must be configured")
        
        if self.primary_provider not in self.providers:
            raise ValueError(f"Primary provider '{self.primary_provider}' not found in providers")
        
        for fallback in self.fallback_providers:
            if fallback not in self.providers:
                raise ValueError(f"Fallback provider '{fallback}' not found in providers")
        
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(f"Invalid log level: {self.log_level}")
    
    @classmethod
    def from_yaml_file(cls, config_path: str) -> 'LLMFixGeneratorConfig':
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        return cls.from_dict(config_data)
    
    @classmethod
    def from_dict(cls, config_data: Dict[str, Any]) -> 'LLMFixGeneratorConfig':
        """Create configuration from dictionary."""
        llm_config = config_data.get('llm_fix_generator', {})
        
        # Parse providers
        providers = {}
        providers_data = llm_config.get('providers_config', {})
        for provider_name, provider_data in providers_data.items():
            if provider_name not in ['primary', 'fallback']:  # Skip meta fields
                providers[provider_name] = NIMProviderConfig.from_dict(provider_data, provider_name)
        
        # Parse other configurations
        analysis_config = AnalysisConfig(**llm_config.get('analysis', {}))
        quality_config = QualityConfig(**llm_config.get('quality', {}))
        optimization_config = OptimizationConfig(**llm_config.get('optimization', {}))
        
        return cls(
            providers=providers,
            primary_provider=llm_config.get('providers', {}).get('primary', 'nvidia_nim'),
            fallback_providers=llm_config.get('providers', {}).get('fallback', []),
            analysis=analysis_config,
            quality=quality_config,
            optimization=optimization_config,
            log_level=llm_config.get('log_level', 'INFO'),
            debug_mode=llm_config.get('debug_mode', False),
            save_raw_responses=llm_config.get('save_raw_responses', False)
        )
    
    @classmethod
    def create_default(cls) -> 'LLMFixGeneratorConfig':
        """Create a default configuration with NVIDIA NIM setup."""
        # Default NVIDIA NIM provider
        nvidia_nim = NIMProviderConfig(
            name="nvidia_nim",
            base_url=os.getenv("NIM_API_ENDPOINT", "https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions"),
            api_key=os.getenv("NIM_API_KEY", ""),
            model=os.getenv("NIM_MODEL", "codellama-13b-instruct"),
            max_tokens=2000,
            temperature=0.1,
            timeout=30
        )
        
        # Local NIM fallback
        local_nim = NIMProviderConfig(
            name="local_nim",
            base_url=os.getenv("LOCAL_NIM_ENDPOINT", "http://localhost:8000"),
            api_key=os.getenv("LOCAL_NIM_API_KEY", "local"),
            model=os.getenv("LOCAL_NIM_MODEL", "codellama-7b-instruct"),
            max_tokens=1500,
            temperature=0.1,
            timeout=60
        )
        
        return cls(
            providers={
                "nvidia_nim": nvidia_nim,
                "local_nim": local_nim
            },
            primary_provider="nvidia_nim",
            fallback_providers=["local_nim"]
        )
    
    def get_provider_config(self, provider_name: str) -> NIMProviderConfig:
        """Get configuration for a specific provider."""
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not configured")
        return self.providers[provider_name]
    
    def validate_environment(self) -> List[str]:
        """Validate that required environment variables are set."""
        errors = []
        
        for provider_name, provider in self.providers.items():
            if not provider.api_key or provider.api_key.startswith("${"):
                errors.append(f"API key not set for provider '{provider_name}'")
            
            if not provider.base_url or provider.base_url.startswith("${"):
                errors.append(f"Base URL not set for provider '{provider_name}'")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "llm_fix_generator": {
                "providers": {
                    "primary": self.primary_provider,
                    "fallback": self.fallback_providers
                },
                "providers_config": {
                    name: {
                        "base_url": provider.base_url,
                        "model": provider.model,
                        "max_tokens": provider.max_tokens,
                        "temperature": provider.temperature,
                        "timeout": provider.timeout,
                        "use_streaming": provider.use_streaming,
                        "retry_attempts": provider.retry_attempts,
                        "retry_delay": provider.retry_delay,
                        "max_requests_per_minute": provider.max_requests_per_minute,
                        "estimated_cost_per_1k_tokens": provider.estimated_cost_per_1k_tokens
                    }
                    for name, provider in self.providers.items()
                },
                "analysis": {
                    "generate_multiple_candidates": self.analysis.generate_multiple_candidates,
                    "num_candidates": self.analysis.num_candidates,
                    "include_reasoning_trace": self.analysis.include_reasoning_trace,
                    "enable_defect_categorization": self.analysis.enable_defect_categorization,
                    "confidence_threshold": self.analysis.confidence_threshold,
                    "include_severity_assessment": self.analysis.include_severity_assessment,
                    "max_context_lines": self.analysis.max_context_lines,
                    "include_function_signature": self.analysis.include_function_signature,
                    "include_surrounding_code": self.analysis.include_surrounding_code
                },
                "quality": {
                    "enforce_style_consistency": self.quality.enforce_style_consistency,
                    "style_consistency_threshold": self.quality.style_consistency_threshold,
                    "validate_syntax": self.quality.validate_syntax,
                    "safety_checks": self.quality.safety_checks,
                    "require_explanation": self.quality.require_explanation,
                    "max_files_per_fix": self.quality.max_files_per_fix,
                    "max_lines_per_fix": self.quality.max_lines_per_fix,
                    "min_confidence_for_auto_apply": self.quality.min_confidence_for_auto_apply,
                    "min_style_score_for_auto_apply": self.quality.min_style_score_for_auto_apply
                },
                "optimization": {
                    "cache_similar_defects": self.optimization.cache_similar_defects,
                    "cache_duration_hours": self.optimization.cache_duration_hours,
                    "cache_max_size": self.optimization.cache_max_size,
                    "token_limit_per_defect": self.optimization.token_limit_per_defect,
                    "enable_prompt_compression": self.optimization.enable_prompt_compression,
                    "context_window_optimization": self.optimization.context_window_optimization,
                    "enable_performance_tracking": self.optimization.enable_performance_tracking,
                    "log_token_usage": self.optimization.log_token_usage,
                    "track_generation_time": self.optimization.track_generation_time,
                    "max_cost_per_defect": self.optimization.max_cost_per_defect,
                    "daily_cost_limit": self.optimization.daily_cost_limit
                },
                "log_level": self.log_level,
                "debug_mode": self.debug_mode,
                "save_raw_responses": self.save_raw_responses
            }
        } 