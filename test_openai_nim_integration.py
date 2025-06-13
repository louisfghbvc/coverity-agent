#!/usr/bin/env python3
"""
Test script for the new OpenAI client-based NVIDIA NIM integration.

This script demonstrates the updated NVIDIA NIM integration using OpenAI client library
instead of direct requests.
"""

import os
import sys
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    from openai import OpenAI
except ImportError:
    print("❌ OpenAI library not installed. Install with: pip install openai>=1.0.0")
    sys.exit(1)

from dotenv import load_dotenv

def test_direct_openai_client():
    """Test direct OpenAI client connection to NVIDIA NIM."""
    print("🧪 Testing direct OpenAI client connection to NVIDIA NIM...")
    
    # Load environment variables
    load_dotenv('.env')
    
    # Get configuration from environment
    api_key = os.getenv('NVIDIA_NIM_API_KEY')
    base_url = os.getenv('NVIDIA_NIM_BASE_URL', 'https://integrate.api.nvidia.com/v1')
    model = os.getenv('NVIDIA_NIM_MODEL', 'nvidia/llama-3.3-nemotron-super-49b-v1')
    
    if not api_key or api_key == 'your_nim_api_token_here':
        print("❌ NVIDIA_NIM_API_KEY not configured in .env file")
        return False
    
    try:
        # Initialize OpenAI client for NVIDIA NIM
        client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )
        
        print(f"✅ OpenAI client initialized")
        print(f"   Base URL: {base_url}")
        print(f"   Model: {model}")
        
        # Test simple completion
        print("\n🔄 Testing chat completion...")
        
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello in exactly 5 words."}
            ],
            temperature=0.6,
            top_p=0.95,
            max_tokens=50,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            stream=False  # Test non-streaming first
        )
        
        response_content = completion.choices[0].message.content
        print(f"✅ Non-streaming response received: {response_content}")
        
        # Test streaming completion
        print("\n🔄 Testing streaming completion...")
        
        stream = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Count from 1 to 5."}
            ],
            temperature=0.6,
            top_p=0.95,
            max_tokens=50,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            stream=True
        )
        
        streaming_content = []
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                streaming_content.append(chunk.choices[0].delta.content)
        
        full_streaming_response = ''.join(streaming_content)
        print(f"✅ Streaming response received: {full_streaming_response}")
        
        return True
        
    except Exception as e:
        print(f"❌ OpenAI client test failed: {e}")
        return False


def test_fix_generator_integration():
    """Test the updated fix generator with OpenAI client."""
    print("\n🧪 Testing LLM Fix Generator with new OpenAI client integration...")
    
    try:
        # Import fix generator components
        from fix_generator import LLMFixGenerator
        from fix_generator.config import LLMFixGeneratorConfig
        
        # Create generator from environment
        print("🔄 Creating LLM Fix Generator from environment...")
        generator = LLMFixGenerator.create_from_env()
        
        print("✅ LLM Fix Generator created successfully")
        print(f"   Primary provider: {generator.config.primary_provider}")
        print(f"   Available providers: {list(generator.config.providers.keys())}")
        
        # Test configuration
        nim_config = generator.config.providers.get('nvidia_nim')
        if nim_config:
            print(f"   NIM Model: {nim_config.model}")
            print(f"   Max tokens: {nim_config.max_tokens}")
            print(f"   Temperature: {nim_config.temperature}")
            print(f"   Top-p: {nim_config.top_p}")
            print(f"   Streaming: {nim_config.use_streaming}")
        
        return True
        
    except Exception as e:
        print(f"❌ Fix generator integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_environment_validation():
    """Test environment variable validation."""
    print("\n🧪 Testing environment variable validation...")
    
    try:
        from fix_generator.config import LLMFixGeneratorConfig
        
        # Load environment variables
        load_dotenv('.env')
        
        # Test NVIDIA NIM environment validation
        config = LLMFixGeneratorConfig.create_from_env()
        
        # Validate environment
        nim_errors = config.validate_nvidia_nim_environment()
        if nim_errors:
            print("❌ NVIDIA NIM environment validation errors:")
            for error in nim_errors:
                print(f"   - {error}")
            return False
        else:
            print("✅ NVIDIA NIM environment validation passed")
        
        # General environment validation
        env_errors = config.validate_environment()
        if env_errors:
            print("❌ General environment validation errors:")
            for error in env_errors:
                print(f"   - {error}")
            return False
        else:
            print("✅ General environment validation passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Environment validation test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Testing NVIDIA NIM Integration with OpenAI Client\n")
    
    # Check if .env file exists
    if not Path('.env').exists():
        print("❌ .env file not found. Please copy env.example to .env and configure it.")
        return
    
    tests = [
        ("Environment Validation", test_environment_validation),
        ("Direct OpenAI Client", test_direct_openai_client),
        ("Fix Generator Integration", test_fix_generator_integration),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        success = test_func()
        results.append((test_name, success))
        print()
    
    # Summary
    print("="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    all_passed = True
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name:30} {status}")
        if not success:
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("🎉 All tests passed! NVIDIA NIM integration with OpenAI client is working.")
    else:
        print("⚠️  Some tests failed. Please check the error messages above.")
    print("="*50)


if __name__ == "__main__":
    main() 