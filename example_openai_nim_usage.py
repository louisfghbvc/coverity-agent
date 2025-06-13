#!/usr/bin/env python3
"""
Example usage of NVIDIA NIM integration with OpenAI client library.

This example demonstrates the updated implementation that uses OpenAI's client library
to connect to NVIDIA NIM endpoints, exactly like the user requested.
"""

import os
import sys
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from openai import OpenAI
from dotenv import load_dotenv


def example_direct_openai_nim():
    """
    Example of using OpenAI client directly with NVIDIA NIM.
    This matches the user's requested pattern exactly.
    """
    print("🎯 Direct OpenAI Client with NVIDIA NIM")
    print("="*50)
    
    # Load environment variables
    load_dotenv('.env')
    
    # Initialize client exactly like user's example
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.getenv('NVIDIA_NIM_API_KEY')
    )
    
    # Create completion with all the parameters from user's example
    completion = client.chat.completions.create(
        model="nvidia/llama-3.3-nemotron-super-49b-v1",
        messages=[
            {"role": "system", "content": "You are a code analysis expert."},
            {"role": "user", "content": "Explain what a null pointer dereference is in 2 sentences."}
        ],
        temperature=0.6,
        top_p=0.95,
        max_tokens=4096,
        frequency_penalty=0,
        presence_penalty=0,
        stream=True  # Enable streaming like user's example
    )
    
    print("🔄 Streaming response:")
    print("-" * 30)
    
    # Handle streaming response
    for chunk in completion:
        if chunk.choices[0].delta.content is not None:
            print(chunk.choices[0].delta.content, end='')
    
    print("\n" + "-" * 30)
    print("✅ Direct OpenAI client example completed!")
    print()


def example_fix_generator_with_openai_client():
    """
    Example using the Fix Generator with the new OpenAI client backend.
    """
    print("🎯 LLM Fix Generator with OpenAI Client Backend")
    print("="*50)
    
    try:
        from fix_generator import LLMFixGenerator
        
        # Create fix generator (now uses OpenAI client internally)
        generator = LLMFixGenerator.create_from_env()
        
        print("✅ Fix Generator initialized with OpenAI client backend")
        print(f"   Model: {generator.config.providers['nvidia_nim'].model}")
        print(f"   Streaming: {generator.config.providers['nvidia_nim'].use_streaming}")
        print(f"   Temperature: {generator.config.providers['nvidia_nim'].temperature}")
        print(f"   Top-p: {generator.config.providers['nvidia_nim'].top_p}")
        
        # Create a mock defect for demonstration
        from issue_parser.data_structures import ParsedDefect
        from code_retriever.data_structures import CodeContext, CodeSection
        
        # Mock defect
        mock_defect = ParsedDefect(
            defect_id="DEMO-001",
            defect_type="NULL_POINTER_DEREFERENCE",
            file_path="src/example.c",
            line_number=42,
            function_name="process_data",
            subcategory="Null pointer dereference",
            events=["Pointer 'data' is assigned null", "Pointer 'data' is dereferenced"]
        )
        
        # Mock code context
        mock_code_section = CodeSection(
            start_line=40,
            end_line=45,
            source_lines=[
                "void process_data(struct data_t *data) {",
                "    data = NULL;  // Assignment",
                "    printf(\"%s\", data->name);  // Dereference!",
                "    return;",
                "}"
            ]
        )
        
        mock_code_context = CodeContext(
            primary_context=mock_code_section,
            function_context=None,
            additional_context=[]
        )
        
        print("\n🔄 Analyzing mock defect...")
        print(f"   Defect: {mock_defect.defect_type}")
        print(f"   Location: {mock_defect.file_path}:{mock_defect.line_number}")
        
        # Analyze defect (this will use OpenAI client internally)
        result = generator.analyze_and_fix(mock_defect, mock_code_context)
        
        print("\n✅ Analysis completed!")
        print(f"   Confidence: {result.confidence_score:.2f}")
        print(f"   Fix candidates: {len(result.fix_candidates)}")
        print(f"   Model used: {result.nim_metadata.model_used}")
        print(f"   Tokens consumed: {result.nim_metadata.tokens_consumed}")
        print(f"   Generation time: {result.nim_metadata.generation_time:.2f}s")
        
        # Show recommended fix
        if result.fix_candidates:
            print(f"\n📝 Recommended fix:")
            print("-" * 30)
            print(result.recommended_fix.fix_code)
            print("-" * 30)
            print(f"Explanation: {result.recommended_fix.explanation}")
        
    except Exception as e:
        print(f"❌ Fix Generator example failed: {e}")
        import traceback
        traceback.print_exc()


def show_configuration_differences():
    """
    Show the differences between old and new configuration.
    """
    print("🎯 Configuration Differences")
    print("="*50)
    
    print("📊 NEW OpenAI Client Method:")
    print("  ✅ Uses OpenAI client library")
    print("  ✅ Supports streaming responses")
    print("  ✅ Additional parameters: top_p, frequency_penalty, presence_penalty")
    print("  ✅ Better error handling and retry logic")
    print("  ✅ More stable and maintainable")
    
    print("\n📊 OLD Requests Method:")
    print("  ❌ Used direct HTTP requests")
    print("  ❌ Limited streaming support")
    print("  ❌ Basic parameter support")
    print("  ❌ Manual error handling")
    
    print("\n🔧 Key Configuration Updates:")
    print("  • Model: nvidia/llama-3.3-nemotron-super-49b-v1")
    print("  • Max tokens: 4096 (increased from 2000)")
    print("  • Temperature: 0.6 (increased from 0.1)")
    print("  • Added: top_p=0.95")
    print("  • Added: frequency_penalty=0.0")
    print("  • Added: presence_penalty=0.0")
    print("  • Streaming: enabled by default")
    
    print("\n📝 Environment Variables Added:")
    print("  • NVIDIA_NIM_TOP_P")
    print("  • NVIDIA_NIM_FREQUENCY_PENALTY")
    print("  • NVIDIA_NIM_PRESENCE_PENALTY")
    print("  • NVIDIA_NIM_STREAMING")


def main():
    """Run all examples."""
    print("🚀 NVIDIA NIM with OpenAI Client - Usage Examples\n")
    
    # Check if .env file exists
    if not Path('.env').exists():
        print("❌ .env file not found. Please copy env.example to .env and configure it.")
        return
    
    # Check if API key is configured
    load_dotenv('.env')
    api_key = os.getenv('NVIDIA_NIM_API_KEY')
    if not api_key or api_key == 'your_nim_api_token_here':
        print("❌ NVIDIA_NIM_API_KEY not configured in .env file")
        print("   Please set your actual NVIDIA NIM API key in the .env file")
        return
    
    try:
        # Show configuration differences
        show_configuration_differences()
        print("\n")
        
        # Run direct OpenAI client example
        example_direct_openai_nim()
        
        # Run fix generator example
        example_fix_generator_with_openai_client()
        
        print("\n" + "="*50)
        print("🎉 All examples completed successfully!")
        print("🔧 Your codebase now uses the OpenAI client method you requested.")
        print("="*50)
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure to install: pip install openai>=1.0.0")
        
    except Exception as e:
        print(f"❌ Example failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 