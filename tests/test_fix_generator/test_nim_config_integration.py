#!/usr/bin/env python3
"""
Integration test for NVIDIA NIM configuration and connectivity.
This test validates the complete NVIDIA NIM setup with real environment.
"""

import os
import sys
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
    sys.exit(1)


def test_environment_file():
    """Test if .env file exists and has required variables."""
    env_file = project_root / ".env"
    
    if not env_file.exists():
        print(f"❌ Environment file not found: {env_file}")
        return False
    
    print(f"✅ Environment file found: {env_file}")
    
    # Load and check environment variables
    from dotenv import load_dotenv
    load_dotenv(env_file)
    
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
        return False
    
    return True


def test_nim_config_creation():
    """Test creating LLM Fix Generator config from environment."""
    try:
        # Load environment explicitly
        from dotenv import load_dotenv
        load_dotenv(project_root / ".env")
        
        config = LLMFixGeneratorConfig.create_from_env()
        print("✅ LLM Fix Generator config created from environment")
        
        # Validate configuration
        if 'nvidia_nim' not in config.providers:
            print("❌ NVIDIA NIM provider not found in config")
            return False
        
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
            return False
        
        print("✅ Configuration validation passed")
        return True
        
    except Exception as e:
        print(f"❌ Config creation failed: {e}")
        return False


def test_llm_manager_initialization():
    """Test LLM Manager initialization with NVIDIA NIM."""
    try:
        from dotenv import load_dotenv
        load_dotenv(project_root / ".env")
        
        config = LLMFixGeneratorConfig.create_from_env()
        manager = UnifiedLLMManager(config)
        
        print("✅ LLM Manager initialized successfully")
        print(f"   - Primary provider: {config.primary_provider}")
        print(f"   - Fallback providers: {config.fallback_providers}")
        print(f"   - Available providers: {list(manager.providers.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM Manager initialization failed: {e}")
        return False


def test_nvidia_nim_connectivity():
    """Test actual connectivity to NVIDIA NIM endpoint."""
    try:
        from dotenv import load_dotenv
        load_dotenv(project_root / ".env")
        
        config = LLMFixGeneratorConfig.create_from_env()
        
        # Test NIM connection
        success = config.test_nvidia_nim_connection()
        
        if success:
            print("✅ NVIDIA NIM connectivity test passed")
            return True
        else:
            print("❌ NVIDIA NIM connectivity test failed")
            return False
            
    except Exception as e:
        print(f"❌ Connectivity test failed: {e}")
        return False


def test_fix_generator_creation():
    """Test creating LLM Fix Generator from environment."""
    try:
        from dotenv import load_dotenv
        load_dotenv(project_root / ".env")
        
        # Test the create_from_env method
        generator = LLMFixGenerator.create_from_env()
        
        print("✅ LLM Fix Generator created from environment")
        print(f"   - Primary provider: {generator.config.primary_provider}")
        print(f"   - Providers configured: {len(generator.config.providers)}")
        
        # Test configuration
        stats = generator.get_statistics()
        print(f"✅ Generator statistics accessible: {stats.total_defects_processed} defects processed")
        
        return True
        
    except Exception as e:
        print(f"❌ Fix Generator creation failed: {e}")
        return False


def run_all_tests():
    """Run all NVIDIA NIM integration tests."""
    print("=" * 80)
    print("NVIDIA NIM CONFIGURATION INTEGRATION TESTS")
    print("=" * 80)
    
    tests = [
        ("Environment File Check", test_environment_file),
        ("NIM Config Creation", test_nim_config_creation),
        ("LLM Manager Initialization", test_llm_manager_initialization),
        ("NVIDIA NIM Connectivity", test_nvidia_nim_connectivity),
        ("Fix Generator Creation", test_fix_generator_creation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 40)
        
        try:
            success = test_func()
            results.append((test_name, success))
            
            if success:
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
                
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests PASSED! NVIDIA NIM integration is working correctly.")
        return True
    else:
        print("⚠️  Some tests FAILED. Please check the configuration.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 