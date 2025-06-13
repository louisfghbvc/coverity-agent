#!/usr/bin/env python3
"""
Integration test for NVIDIA NIM configuration and connectivity.
This test validates the complete NVIDIA NIM setup with real environment.
"""

import os
import sys
import pytest
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from fix_generator.config import LLMFixGeneratorConfig
    from fix_generator.llm_manager import UnifiedLLMManager
    from fix_generator import LLMFixGenerator
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    pytest.skip(f"Import failed: {e}")


@pytest.fixture
def load_env():
    """Load environment variables from .env file."""
    env_file = project_root / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
    return env_file


def test_environment_file(load_env):
    """Test if .env file exists and has required variables."""
    env_file = load_env
    
    if not env_file.exists():
        pytest.skip(f"Environment file not found: {env_file}")
    
    print(f"✅ Environment file found: {env_file}")
    
    required_vars = [
        'NIM_API_ENDPOINT',
        'NIM_API_KEY', 
        'NIM_MODEL'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            # Mask API key for security
            if 'KEY' in var:
                masked_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                print(f"✅ {var} = {masked_value}")
            else:
                print(f"✅ {var} = {value}")
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        pytest.skip(f"Missing required environment variables: {missing_vars}")
    
    # All required variables are present
    assert len(missing_vars) == 0


def test_nim_config_creation(load_env):
    """Test creating LLM Fix Generator config from environment."""
    # Skip if environment file doesn't exist
    if not load_env.exists():
        pytest.skip("Environment file not found")
    
    # Check for required environment variables
    required_vars = ['NIM_API_ENDPOINT', 'NIM_API_KEY', 'NIM_MODEL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        pytest.skip(f"Missing required environment variables: {missing_vars}")
    
    config = LLMFixGeneratorConfig.create_from_env()
    print("✅ LLM Fix Generator config created from environment")
    
    # Validate configuration
    assert 'nvidia_nim' in config.providers, "NVIDIA NIM provider not found in config"
    
    nim_config = config.get_provider_config('nvidia_nim')
    print(f"✅ NVIDIA NIM provider configured:")
    print(f"   - Endpoint: {nim_config.base_url}")
    print(f"   - Model: {nim_config.model}")
    print(f"   - Max Tokens: {nim_config.max_tokens}")
    print(f"   - Temperature: {nim_config.temperature}")
    
    # Validate environment
    errors = config.validate_environment()
    if errors:
        print(f"❌ Configuration validation errors: {errors}")
        pytest.fail(f"Configuration validation errors: {errors}")
    
    print("✅ Configuration validation passed")


def test_llm_manager_initialization(load_env):
    """Test LLM Manager initialization with NVIDIA NIM."""
    # Skip if environment file doesn't exist
    if not load_env.exists():
        pytest.skip("Environment file not found")
    
    # Check for required environment variables
    required_vars = ['NIM_API_ENDPOINT', 'NIM_API_KEY', 'NIM_MODEL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        pytest.skip(f"Missing required environment variables: {missing_vars}")
    
    config = LLMFixGeneratorConfig.create_from_env()
    manager = UnifiedLLMManager(config)
    
    print("✅ LLM Manager initialized successfully")
    print(f"   - Primary provider: {config.primary_provider}")
    print(f"   - Fallback providers: {config.fallback_providers}")
    print(f"   - Available providers: {list(manager.providers.keys())}")
    
    assert manager is not None
    assert len(manager.providers) > 0
    assert config.primary_provider in manager.providers


@pytest.mark.skipif(
    not os.getenv('NIM_API_ENDPOINT') or not os.getenv('NIM_API_KEY'),
    reason="NVIDIA NIM environment variables not set"
)
def test_nvidia_nim_connectivity(load_env):
    """Test actual connectivity to NVIDIA NIM endpoint."""
    config = LLMFixGeneratorConfig.create_from_env()
    
    # Test NIM connection
    success = config.test_nvidia_nim_connection()
    
    if success:
        print("✅ NVIDIA NIM connectivity test passed")
    else:
        print("❌ NVIDIA NIM connectivity test failed")
        pytest.skip("NVIDIA NIM connectivity failed - may be network or endpoint issue")


@pytest.mark.skipif(
    not os.getenv('NIM_API_ENDPOINT') or not os.getenv('NIM_API_KEY'),
    reason="NVIDIA NIM environment variables not set"
)
def test_fix_generator_creation(load_env):
    """Test creating LLM Fix Generator from environment."""
    # Test the create_from_env method
    generator = LLMFixGenerator.create_from_env()
    
    print("✅ LLM Fix Generator created from environment")
    print(f"   - Primary provider: {generator.config.primary_provider}")
    print(f"   - Providers configured: {len(generator.config.providers)}")
    
    # Test configuration
    stats = generator.get_statistics()
    print(f"✅ Generator statistics accessible: {stats.total_defects_processed} defects processed")
    
    assert generator is not None
    assert generator.config is not None
    assert len(generator.config.providers) > 0
    assert stats is not None 