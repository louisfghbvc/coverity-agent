"""
Unit tests for LLM Fix Generator configuration management.
"""

import os
import tempfile
import pytest
import yaml
from unittest.mock import patch

from fix_generator.config import (
    LLMFixGeneratorConfig, NIMProviderConfig, AnalysisConfig,
    QualityConfig, OptimizationConfig
)


class TestNIMProviderConfig:
    """Test NIMProviderConfig class."""
    
    def test_nim_provider_config_creation(self):
        """Test creating a valid NIMProviderConfig."""
        config = NIMProviderConfig(
            name="test_nim",
            base_url="https://test.com",
            api_key="test-key",
            model="test-model"
        )
        
        assert config.name == "test_nim"
        assert config.base_url == "https://test.com"
        assert config.api_key == "test-key"
        assert config.model == "test-model"
        assert config.max_tokens == 4096  # Updated to match actual default
        assert config.temperature == 0.6  # Updated to match actual default
    
    def test_nim_provider_config_validation(self):
        """Test NIMProviderConfig validation."""
        # Test missing base URL
        with pytest.raises(ValueError, match="Base URL is required"):
            NIMProviderConfig(
                name="test",
                base_url="",
                api_key="test-key",
                model="test-model"
            )
        
        # Test missing API key
        with pytest.raises(ValueError, match="API key is required"):
            NIMProviderConfig(
                name="test",
                base_url="https://test.com",
                api_key="",
                model="test-model"
            )
        
        # Test invalid temperature
        with pytest.raises(ValueError, match="Temperature must be 0.0-2.0"):
            NIMProviderConfig(
                name="test",
                base_url="https://test.com",
                api_key="test-key",
                model="test-model",
                temperature=3.0
            )
        
        # Test invalid max_tokens
        with pytest.raises(ValueError, match="Max tokens must be positive"):
            NIMProviderConfig(
                name="test",
                base_url="https://test.com",
                api_key="test-key",
                model="test-model",
                max_tokens=-100
            )
        
        # Test invalid timeout
        with pytest.raises(ValueError, match="Timeout must be positive"):
            NIMProviderConfig(
                name="test",
                base_url="https://test.com",
                api_key="test-key",
                model="test-model",
                timeout=-30
            )
    
    def test_from_dict_with_env_vars(self):
        """Test creating provider config from dict with environment variables."""
        # Set test environment variables
        os.environ["TEST_API_KEY"] = "secret-key"
        os.environ["TEST_ENDPOINT"] = "https://test-endpoint.com"
        
        try:
            data = {
                "base_url": "${TEST_ENDPOINT}",
                "api_key": "${TEST_API_KEY}",
                "model": "test-model"
            }
            
            config = NIMProviderConfig.from_dict(data, "test_provider")
            
            assert config.name == "test_provider"
            assert config.base_url == "https://test-endpoint.com"
            assert config.api_key == "secret-key"
            assert config.model == "test-model"
        
        finally:
            # Clean up environment variables
            os.environ.pop("TEST_API_KEY", None)
            os.environ.pop("TEST_ENDPOINT", None)


class TestAnalysisConfig:
    """Test AnalysisConfig class."""
    
    def test_analysis_config_defaults(self):
        """Test AnalysisConfig default values."""
        config = AnalysisConfig()
        
        assert config.generate_multiple_candidates is True
        assert config.num_candidates == 1
        assert config.include_reasoning_trace is True
        assert config.confidence_threshold == 0.6
        assert config.max_context_lines == 50
    
    def test_analysis_config_validation(self):
        """Test AnalysisConfig validation."""
        # Test invalid num_candidates
        with pytest.raises(ValueError, match="Number of candidates must be 1-10"):
            AnalysisConfig(num_candidates=15)
        
        with pytest.raises(ValueError, match="Number of candidates must be 1-10"):
            AnalysisConfig(num_candidates=0)
        
        # Test invalid confidence_threshold
        with pytest.raises(ValueError, match="Confidence threshold must be 0.0-1.0"):
            AnalysisConfig(confidence_threshold=1.5)
        
        # Test invalid max_context_lines
        with pytest.raises(ValueError, match="Max context lines must be positive"):
            AnalysisConfig(max_context_lines=-10)


class TestQualityConfig:
    """Test QualityConfig class."""
    
    def test_quality_config_defaults(self):
        """Test QualityConfig default values."""
        config = QualityConfig()
        
        assert config.enforce_style_consistency is True
        assert config.validate_syntax is True
        assert config.safety_checks is True
        assert config.require_explanation is True
        assert config.max_files_per_fix == 3
        assert config.min_confidence_for_auto_apply == 0.8
    
    def test_quality_config_validation(self):
        """Test QualityConfig validation."""
        # Test invalid style_consistency_threshold
        with pytest.raises(ValueError, match="Style consistency threshold must be 0.0-1.0"):
            QualityConfig(style_consistency_threshold=1.5)
        
        # Test invalid confidence thresholds
        with pytest.raises(ValueError, match="Min confidence threshold must be 0.0-1.0"):
            QualityConfig(min_confidence_for_auto_apply=1.5)
        
        with pytest.raises(ValueError, match="Min style score threshold must be 0.0-1.0"):
            QualityConfig(min_style_score_for_auto_apply=-0.1)
        
        # Test invalid max_files_per_fix
        with pytest.raises(ValueError, match="Max files per fix must be positive"):
            QualityConfig(max_files_per_fix=0)


class TestOptimizationConfig:
    """Test OptimizationConfig class."""
    
    def test_optimization_config_defaults(self):
        """Test OptimizationConfig default values."""
        config = OptimizationConfig()
        
        assert config.cache_similar_defects is True
        assert config.cache_duration_hours == 24
        assert config.token_limit_per_defect == 2000
        assert config.enable_prompt_compression is True
        assert config.enable_performance_tracking is True
    
    def test_optimization_config_validation(self):
        """Test OptimizationConfig validation."""
        # Test invalid cache_duration_hours
        with pytest.raises(ValueError, match="Cache duration must be positive"):
            OptimizationConfig(cache_duration_hours=-5)
        
        # Test invalid cache_max_size
        with pytest.raises(ValueError, match="Cache max size must be positive"):
            OptimizationConfig(cache_max_size=0)
        
        # Test invalid token_limit_per_defect
        with pytest.raises(ValueError, match="Token limit must be positive"):
            OptimizationConfig(token_limit_per_defect=-100)


class TestLLMFixGeneratorConfig:
    """Test LLMFixGeneratorConfig main configuration class."""
    
    def test_config_creation_with_defaults(self):
        """Test creating config with default values."""
        # Use the test-friendly default that skips validation
        config = LLMFixGeneratorConfig.create_test_default()
        
        assert "nvidia_nim" in config.providers
        assert config.primary_provider == "nvidia_nim"
        assert config.log_level == "INFO"
        assert config.debug_mode is False
    
    def test_config_validation(self, test_config):
        """Test configuration validation."""
        # Valid config should pass
        assert test_config.primary_provider == "test_nim"
        
        # Test missing providers
        with pytest.raises(ValueError, match="At least one provider must be configured"):
            LLMFixGeneratorConfig(
                providers={},
                primary_provider="missing",
                fallback_providers=[]
            )
        
        # Test primary provider not in providers
        with pytest.raises(ValueError, match="Primary provider .* not found"):
            LLMFixGeneratorConfig(
                providers={"test": test_config.providers["test_nim"]},
                primary_provider="missing",
                fallback_providers=[]
            )
        
        # Test fallback provider not in providers
        with pytest.raises(ValueError, match="Fallback provider .* not found"):
            LLMFixGeneratorConfig(
                providers={"test": test_config.providers["test_nim"]},
                primary_provider="test",
                fallback_providers=["missing"]
            )
        
        # Test invalid log level
        with pytest.raises(ValueError, match="Invalid log level"):
            LLMFixGeneratorConfig(
                providers={"test": test_config.providers["test_nim"]},
                primary_provider="test",
                fallback_providers=[],
                log_level="INVALID"
            )
    
    def test_get_provider_config(self, test_config):
        """Test getting provider configuration."""
        provider_config = test_config.get_provider_config("test_nim")
        
        assert provider_config.name == "test_nim"
        assert provider_config.base_url == "https://test-nim-endpoint.com"
        
        # Test missing provider
        with pytest.raises(ValueError, match="Provider .* not configured"):
            test_config.get_provider_config("missing_provider")
    
    def test_validate_environment(self):
        """Test environment validation."""
        # Create config with missing environment variables
        config = LLMFixGeneratorConfig(
            providers={
                "test": NIMProviderConfig(
                    name="test",
                    base_url="${MISSING_URL}",
                    api_key="${MISSING_KEY}",
                    model="test-model"
                )
            },
            primary_provider="test",
            fallback_providers=[]
        )
        
        errors = config.validate_environment()
        
        assert len(errors) == 2
        assert any("API key not set" in error for error in errors)
        assert any("Base URL not set" in error for error in errors)
    
    def test_from_yaml_file(self):
        """Test loading configuration from YAML file."""
        # Create temporary YAML file
        config_data = {
            "llm_fix_generator": {
                "providers": {
                    "primary": "test_nim",
                    "fallback": []
                },
                "providers_config": {
                    "test_nim": {
                        "base_url": "https://test.com",
                        "api_key": "test-key",
                        "model": "test-model",
                        "max_tokens": 1000
                    }
                },
                "analysis": {
                    "num_candidates": 2,
                    "confidence_threshold": 0.7
                },
                "quality": {
                    "enforce_style_consistency": False
                },
                "log_level": "DEBUG"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = LLMFixGeneratorConfig.from_yaml_file(temp_path)
            
            assert config.primary_provider == "test_nim"
            assert config.analysis.num_candidates == 2
            assert config.analysis.confidence_threshold == 0.7
            assert config.quality.enforce_style_consistency is False
            assert config.log_level == "DEBUG"
            
            # Test provider config
            provider = config.get_provider_config("test_nim")
            assert provider.base_url == "https://test.com"
            assert provider.max_tokens == 1000
        
        finally:
            os.unlink(temp_path)
    
    def test_from_yaml_file_missing(self):
        """Test loading from missing YAML file."""
        with pytest.raises(FileNotFoundError):
            LLMFixGeneratorConfig.from_yaml_file("nonexistent.yaml")
    
    def test_to_dict(self, test_config):
        """Test converting configuration to dictionary."""
        result = test_config.to_dict()
        
        assert "llm_fix_generator" in result
        config_dict = result["llm_fix_generator"]
        
        assert config_dict["providers"]["primary"] == "test_nim"
        assert "test_nim" in config_dict["providers_config"]
        assert "analysis" in config_dict
        assert "quality" in config_dict
        assert "optimization" in config_dict
        
        # Test provider config details
        provider_config = config_dict["providers_config"]["test_nim"]
        assert provider_config["base_url"] == "https://test-nim-endpoint.com"
        assert provider_config["model"] == "test-model" 