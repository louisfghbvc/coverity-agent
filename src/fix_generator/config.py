"""
Configuration management for LLM Fix Generator with NVIDIA NIM integration.

This module provides configuration classes and validation for NIM providers,
prompt engineering, and fix generation parameters with dotenv support.
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from pathlib import Path

# Import dotenv with fallback for environments where it's not available
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    
    def load_dotenv(*args, **kwargs):
        """Fallback function when python-dotenv is not available."""
        pass


@dataclass
class NIMProviderConfig:
    """Configuration for a NVIDIA NIM provider."""
    
    name: str
    base_url: str
    api_key: str
    model: str
    max_tokens: int = 4096
    temperature: float = 0.6
    timeout: int = 30
    
    # Additional OpenAI-compatible parameters
    top_p: float = 0.95
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    
    # NIM-specific settings
    use_streaming: bool = True
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Cost and rate limiting
    max_requests_per_minute: int = 60
    estimated_cost_per_1k_tokens: Optional[float] = None
    
    def __post_init__(self):
        """Validate provider configuration."""
        if not self.base_url:
            raise ValueError(f"Base URL is required for provider {self.name}")
        
        # Skip API key validation if _skip_validation flag is set (for testing)
        if hasattr(self, '_skip_validation') and self._skip_validation:
            return
            
        if not self.api_key:
            raise ValueError(f"API key is required for provider {self.name}")
        
        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError(f"Temperature must be 0.0-2.0, got {self.temperature}")
        
        if not (0.0 <= self.top_p <= 1.0):
            raise ValueError(f"Top_p must be 0.0-1.0, got {self.top_p}")
        
        if not (-2.0 <= self.frequency_penalty <= 2.0):
            raise ValueError(f"Frequency penalty must be -2.0 to 2.0, got {self.frequency_penalty}")
        
        if not (-2.0 <= self.presence_penalty <= 2.0):
            raise ValueError(f"Presence penalty must be -2.0 to 2.0, got {self.presence_penalty}")
        
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
    def load_environment_variables(cls, env_file_path: Optional[str] = None) -> None:
        """
        Load environment variables from .env file using python-dotenv.
        
        Args:
            env_file_path: Path to .env file. If None, looks for .env in current directory.
        """
        if not DOTENV_AVAILABLE:
            import warnings
            warnings.warn("python-dotenv not available. Environment variables must be set manually.")
            return
        
        if env_file_path is None:
            env_file_path = ".env"
        
        env_path = Path(env_file_path)
        if env_path.exists():
            load_dotenv(env_path)
            print(f"✅ Loaded environment variables from {env_file_path}")
        else:
            print(f"⚠️  Environment file {env_file_path} not found. Using system environment variables.")
    
    @classmethod
    def from_yaml_file(cls, config_path: str, load_env: bool = True, 
                       env_file_path: Optional[str] = None) -> 'LLMFixGeneratorConfig':
        """
        Load configuration from YAML file with optional environment variable loading.
        
        Args:
            config_path: Path to YAML configuration file
            load_env: Whether to load environment variables from .env file
            env_file_path: Path to .env file (defaults to .env in current directory)
        """
        if load_env:
            cls.load_environment_variables(env_file_path)
        
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
    def create_default(cls, skip_validation: bool = False) -> 'LLMFixGeneratorConfig':
        """Create a default configuration with standard settings."""
        # Default provider configurations
        api_key = "test-key-placeholder" if skip_validation else ""
        
        nvidia_nim = NIMProviderConfig(
            name="nvidia_nim",
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key,
            model="nvidia/llama-3.3-nemotron-super-49b-v1",
            max_tokens=4096,
            temperature=0.6,
            top_p=0.95,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            use_streaming=True,
            retry_attempts=3,
            retry_delay=1.0,
            max_requests_per_minute=60
        )
        
        # Temporarily disable validation for test configs
        if skip_validation:
            nvidia_nim.__dict__['_skip_validation'] = True
        
        return cls(
            providers={"nvidia_nim": nvidia_nim},
            primary_provider="nvidia_nim",
            fallback_providers=[],
            analysis=AnalysisConfig(),
            quality=QualityConfig(),
            optimization=OptimizationConfig(),
            log_level="INFO",
            debug_mode=False,
            save_raw_responses=False
        )
    
    @classmethod  
    def create_test_default(cls) -> 'LLMFixGeneratorConfig':
        """Create a test-friendly default configuration."""
        return cls.create_default(skip_validation=True)
    
    @classmethod
    def create_from_env(cls, env_file_path: Optional[str] = None) -> 'LLMFixGeneratorConfig':
        """
        Create configuration from environment variables using dotenv.
        
        Args:
            env_file_path: Path to .env file. If None, looks for .env in current directory.
        """
        # Load environment variables
        cls.load_environment_variables(env_file_path)
        
        # Create NVIDIA NIM provider config from environment
        nvidia_nim = NIMProviderConfig(
            name="nvidia_nim",
            base_url=os.getenv('NVIDIA_NIM_BASE_URL', 'https://integrate.api.nvidia.com/v1'),
            api_key=os.getenv('NVIDIA_NIM_API_KEY', ''),
            model=os.getenv('NVIDIA_NIM_MODEL', 'nvidia/llama-3.3-nemotron-super-49b-v1'),
            max_tokens=int(os.getenv('NVIDIA_NIM_MAX_TOKENS', '4096')),
            temperature=float(os.getenv('NVIDIA_NIM_TEMPERATURE', '0.6')),
            top_p=float(os.getenv('NVIDIA_NIM_TOP_P', '0.95')),
            frequency_penalty=float(os.getenv('NVIDIA_NIM_FREQUENCY_PENALTY', '0.0')),
            presence_penalty=float(os.getenv('NVIDIA_NIM_PRESENCE_PENALTY', '0.0')),
            timeout=int(os.getenv('NVIDIA_NIM_TIMEOUT', '30')),
            use_streaming=os.getenv('NVIDIA_NIM_STREAMING', 'true').lower() == 'true',
            retry_attempts=int(os.getenv('NIM_RETRY_ATTEMPTS', '3')),
            retry_delay=float(os.getenv('NIM_RETRY_DELAY', '1.0')),
            max_requests_per_minute=int(os.getenv('NIM_MAX_REQUESTS_PER_MINUTE', '60')),
            estimated_cost_per_1k_tokens=float(os.getenv('NIM_COST_PER_1K_TOKENS', '0.01'))
        )
        
        # Create fallback providers if configured
        providers = {"nvidia_nim": nvidia_nim}
        fallback_providers = []
        
        # Add OpenAI if configured
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            providers["openai"] = NIMProviderConfig(
                name="openai",
                base_url="https://api.openai.com/v1",
                api_key=openai_key,
                model="gpt-4",
                max_tokens=2000,
                temperature=0.1,
                timeout=30
            )
            fallback_providers.append("openai")
        
        # Add Anthropic if configured
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_key:
            providers["anthropic"] = NIMProviderConfig(
                name="anthropic",
                base_url="https://api.anthropic.com/v1",
                api_key=anthropic_key,
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                temperature=0.1,
                timeout=30
            )
            fallback_providers.append("anthropic")
        
        # Create analysis config from environment
        analysis_config = AnalysisConfig(
            generate_multiple_candidates=os.getenv('ENABLE_MULTIPLE_CANDIDATES', 'true').lower() == 'true',
            num_candidates=int(os.getenv('NUM_FIX_CANDIDATES', '3')),
            confidence_threshold=float(os.getenv('CONFIDENCE_THRESHOLD', '0.7')),
            max_context_lines=int(os.getenv('MAX_CONTEXT_LINES', '50')),
            include_reasoning_trace=True,
            enable_defect_categorization=True,
            include_severity_assessment=True,
            include_function_signature=True,
            include_surrounding_code=True
        )
        
        # Create quality config from environment  
        quality_config = QualityConfig(
            enforce_style_consistency=os.getenv('ENFORCE_STYLE_CONSISTENCY', 'true').lower() == 'true',
            validate_syntax=os.getenv('VALIDATE_SYNTAX', 'true').lower() == 'true',
            safety_checks=os.getenv('SAFETY_CHECKS', 'true').lower() == 'true',
            max_files_per_fix=int(os.getenv('MAX_FILES_PER_FIX', '3')),
            min_confidence_for_auto_apply=float(os.getenv('MIN_CONFIDENCE_FOR_AUTO_APPLY', '0.8')),
            min_style_score_for_auto_apply=float(os.getenv('MIN_STYLE_SCORE_FOR_AUTO_APPLY', '0.7')),
            require_explanation=True,
            style_consistency_threshold=0.6,
            max_lines_per_fix=100
        )
        
        # Create optimization config from environment
        optimization_config = OptimizationConfig(
            cache_similar_defects=os.getenv('CACHE_SIMILAR_DEFECTS', 'true').lower() == 'true',
            cache_max_size=int(os.getenv('CACHE_MAX_SIZE', '1000')),
            token_limit_per_defect=int(os.getenv('TOKEN_LIMIT_PER_DEFECT', '2000')),
            enable_prompt_compression=os.getenv('ENABLE_PROMPT_COMPRESSION', 'true').lower() == 'true',
            enable_performance_tracking=os.getenv('ENABLE_PERFORMANCE_TRACKING', 'true').lower() == 'true',
            max_cost_per_defect=float(os.getenv('MAX_COST_PER_DEFECT', '0.50')),
            daily_cost_limit=float(os.getenv('DAILY_COST_LIMIT', '100.0')) if os.getenv('DAILY_COST_LIMIT') else None,
            cache_duration_hours=24,
            log_token_usage=True,
            track_generation_time=True,
            context_window_optimization=True
        )
        
        return cls(
            providers=providers,
            primary_provider="nvidia_nim",
            fallback_providers=fallback_providers,
            analysis=analysis_config,
            quality=quality_config,
            optimization=optimization_config,
            log_level=os.getenv('LOG_LEVEL', 'DEBUG'),
            debug_mode=os.getenv('DEBUG_MODE', 'true').lower() == 'true',
            save_raw_responses=os.getenv('SAVE_RAW_RESPONSES', 'true').lower() == 'true'
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
    
    def validate_nvidia_nim_environment(self) -> List[str]:
        """
        Validate that required NVIDIA NIM environment variables are set.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Check required NVIDIA NIM variables
        required_vars = {
            'NVIDIA_NIM_API_KEY': 'NVIDIA NIM API key is required',
            'NVIDIA_NIM_BASE_URL': 'NVIDIA NIM base URL is required',
            'NVIDIA_NIM_MODEL': 'NVIDIA NIM model is required'
        }
        
        for var_name, error_msg in required_vars.items():
            value = os.getenv(var_name)
            if not value or value.strip() == '' or value == 'your_nim_api_token_here':
                errors.append(error_msg)
        
        # Check optional but recommended variables
        optional_vars = {
            'NVIDIA_NIM_MAX_TOKENS': 'Maximum tokens setting',
            'NVIDIA_NIM_TEMPERATURE': 'Temperature setting',
            'NVIDIA_NIM_TIMEOUT': 'Timeout setting'
        }
        
        warnings = []
        for var_name, desc in optional_vars.items():
            value = os.getenv(var_name)
            if not value:
                warnings.append(f"Optional: {desc} not set, using default")
        
        if warnings:
            print("⚠️  Configuration warnings:")
            for warning in warnings:
                print(f"   - {warning}")
        
        return errors
    
    @staticmethod
    def test_nvidia_nim_connection() -> bool:
        """
        Test if NVIDIA NIM connection can be established with current environment.
        
        Returns:
            True if connection test passes, False otherwise
        """
        try:
            import requests
            
            api_key = os.getenv('NVIDIA_NIM_API_KEY')
            base_url = os.getenv('NVIDIA_NIM_BASE_URL')
            
            if not api_key or not base_url:
                print("❌ NVIDIA NIM API key or base URL not configured")
                return False
            
            # Simple connectivity test (without making actual API call)
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # Test basic connectivity (this might need adjustment based on actual NIM API)
            response = requests.get(
                f"{base_url.rstrip('/')}/health",  # Health endpoint if available
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                print("✅ NVIDIA NIM connection test passed")
                return True
            else:
                print(f"⚠️  NVIDIA NIM connection test returned status {response.status_code}")
                return False
        
        except requests.exceptions.RequestException as e:
            print(f"❌ NVIDIA NIM connection test failed: {e}")
            return False
        except Exception as e:
            print(f"❌ NVIDIA NIM connection test error: {e}")
            return False
    
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
                        "top_p": provider.top_p,
                        "frequency_penalty": provider.frequency_penalty,
                        "presence_penalty": provider.presence_penalty,
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