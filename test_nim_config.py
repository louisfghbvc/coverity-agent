#!/usr/bin/env python3
"""
NVIDIA NIM Configuration Test Script

This script validates your .env configuration for the LLM Fix Generator
and tests basic connectivity to NVIDIA NIM services.

Usage:
    python test_nim_config.py [path_to_env_file]
"""

import os
import sys
from pathlib import Path

# Add src directory to path for imports
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    """Main test function."""
    print("🔧 NVIDIA NIM Configuration Test")
    print("=" * 50)
    
    # Get .env file path from command line or use default
    env_file_path = sys.argv[1] if len(sys.argv) > 1 else ".env"
    
    # Test 1: Check if .env file exists
    print(f"\n1. Checking for environment file: {env_file_path}")
    if Path(env_file_path).exists():
        print(f"✅ Found {env_file_path}")
    else:
        print(f"❌ Environment file {env_file_path} not found")
        print("   Create it by copying: cp env.example .env")
        return False
    
    # Test 2: Load dotenv and check basic imports
    print("\n2. Testing python-dotenv import")
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file_path)
        print("✅ Successfully loaded python-dotenv")
    except ImportError:
        print("❌ python-dotenv not installed")
        print("   Install it with: pip install python-dotenv")
        return False
    except Exception as e:
        print(f"❌ Error loading .env file: {e}")
        return False
    
    # Test 3: Validate required environment variables
    print("\n3. Validating NVIDIA NIM environment variables")
    required_vars = {
        'NVIDIA_NIM_API_KEY': 'NVIDIA NIM API key',
        'NVIDIA_NIM_BASE_URL': 'NVIDIA NIM base URL',  
        'NVIDIA_NIM_MODEL': 'NVIDIA NIM model'
    }
    
    all_vars_valid = True
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        if not value or value.strip() == '' or value == 'your_nim_api_token_here':
            print(f"❌ {var_name}: {description} not set or invalid")
            all_vars_valid = False
        else:
            # Mask API key for security
            if 'API_KEY' in var_name:
                masked_value = value[:8] + '...' + value[-4:] if len(value) > 12 else '***'
                print(f"✅ {var_name}: {masked_value}")
            else:
                print(f"✅ {var_name}: {value}")
    
    if not all_vars_valid:
        print("\n❌ Some required environment variables are missing or invalid")
        print("   Please check your .env file and set the required values")
        return False
    
    # Test 4: Validate optional environment variables
    print("\n4. Checking optional environment variables")
    optional_vars = {
        'NVIDIA_NIM_MAX_TOKENS': 'Maximum tokens',
        'NVIDIA_NIM_TEMPERATURE': 'Temperature setting',
        'NVIDIA_NIM_TIMEOUT': 'Timeout setting',
        'OPENAI_API_KEY': 'OpenAI fallback API key',
        'ANTHROPIC_API_KEY': 'Anthropic fallback API key'
    }
    
    for var_name, description in optional_vars.items():
        value = os.getenv(var_name)
        if value and value != 'your_openai_key_here' and value != 'your_anthropic_key_here':
            if 'API_KEY' in var_name:
                masked_value = value[:8] + '...' + value[-4:] if len(value) > 12 else '***'
                print(f"✅ {var_name}: {masked_value}")
            else:
                print(f"✅ {var_name}: {value}")
        else:
            print(f"⚠️  {var_name}: {description} not set (optional)")
    
    # Test 5: Test LLM Fix Generator configuration loading
    print("\n5. Testing LLM Fix Generator configuration loading")
    try:
        from fix_generator.config import LLMFixGeneratorConfig
        
        config = LLMFixGeneratorConfig.create_from_env(env_file_path)
        print("✅ Successfully created configuration from environment")
        
        # Validate NVIDIA NIM specific configuration
        nim_errors = config.validate_nvidia_nim_environment()
        if nim_errors:
            print(f"❌ NVIDIA NIM validation errors:")
            for error in nim_errors:
                print(f"   - {error}")
            return False
        else:
            print("✅ NVIDIA NIM environment validation passed")
            
    except Exception as e:
        print(f"❌ Error creating configuration: {e}")
        return False
    
    # Test 6: Test basic NIM manager initialization
    print("\n6. Testing LLM Manager initialization")
    try:
        from fix_generator.llm_manager import UnifiedLLMManager
        
        manager = UnifiedLLMManager.create_from_env(env_file_path)
        print("✅ Successfully initialized LLM Manager")
        
        # Check available providers
        print(f"   Primary provider: {manager.config.primary_provider}")
        print(f"   Fallback providers: {manager.config.fallback_providers}")
        print(f"   Available providers: {list(manager.providers.keys())}")
        
    except Exception as e:
        print(f"❌ Error initializing LLM Manager: {e}")
        return False
    
    # Test 7: Test connectivity (optional)
    print("\n7. Testing NVIDIA NIM connectivity (optional)")
    try:
        import requests
        
        api_key = os.getenv('NVIDIA_NIM_API_KEY')
        base_url = os.getenv('NVIDIA_NIM_BASE_URL')
        
        # Simple connectivity test (adjust based on actual NIM API)
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Note: This is a basic test - actual endpoint may vary
        test_url = f"{base_url.rstrip('/')}"
        response = requests.get(test_url, headers=headers, timeout=5)
        
        if response.status_code in [200, 404, 401]:  # 404/401 means we reached the server
            print("✅ NVIDIA NIM endpoint is reachable")
        else:
            print(f"⚠️  NVIDIA NIM endpoint responded with status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("⚠️  Could not connect to NVIDIA NIM endpoint (check network/URL)")
    except requests.exceptions.Timeout:
        print("⚠️  Connection to NVIDIA NIM timed out")
    except Exception as e:
        print(f"⚠️  NIM connectivity test failed: {e}")
    
    # Final summary
    print("\n" + "=" * 50)
    print("🎉 Configuration test completed!")
    print("✅ Your NVIDIA NIM environment is properly configured")
    print("\nNext steps:")
    print("1. Run the LLM Fix Generator with your configuration")
    print("2. Test with actual defect analysis")
    print("3. Monitor token usage and costs")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during test: {e}")
        sys.exit(1) 