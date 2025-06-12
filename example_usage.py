#!/usr/bin/env python3
"""
Example usage of LLM Fix Generator with NVIDIA NIM integration.

This script demonstrates how to use the dotenv-based configuration
to analyze defects and generate fixes.
"""

import sys
from pathlib import Path

# Add src directory to path for imports
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    """Main example function."""
    print("🚀 LLM Fix Generator - NVIDIA NIM Example")
    print("=" * 50)
    
    # Method 1: Create from environment variables (.env file)
    print("\n1. Creating LLM Fix Generator from .env configuration")
    try:
        from fix_generator import LLMFixGenerator
        
        # This will automatically load from .env file
        fix_generator = LLMFixGenerator.create_from_env()
        print("✅ Successfully created LLM Fix Generator from environment")
        print(f"   Primary provider: {fix_generator.config.primary_provider}")
        print(f"   Fallback providers: {fix_generator.config.fallback_providers}")
        
    except Exception as e:
        print(f"❌ Error creating from environment: {e}")
        print("   Make sure your .env file is properly configured")
        return False
    
    # Method 2: Create with custom .env file path
    print("\n2. Alternative: Using custom .env file path")
    try:
        # You can specify a different .env file
        custom_env_path = "config/.env.production"  # Example custom path
        
        # This would load from the specified file (if it exists)
        if Path(custom_env_path).exists():
            fix_generator_custom = LLMFixGenerator.create_from_env(custom_env_path)
            print(f"✅ Successfully loaded from {custom_env_path}")
        else:
            print(f"⚠️  Custom env file {custom_env_path} not found, using default .env")
            
    except Exception as e:
        print(f"⚠️  Custom env loading failed: {e}")
    
    # Method 3: Create with YAML config + environment loading
    print("\n3. Using YAML configuration with environment variables")
    try:
        config_path = "config/llm_fix_generator_config.yaml"
        
        if Path(config_path).exists():
            # This loads YAML config and resolves environment variables
            fix_generator_yaml = LLMFixGenerator.create_with_config_file(
                config_path, 
                load_env=True  # Enable environment variable loading
            )
            print(f"✅ Successfully loaded from {config_path} with env vars")
        else:
            print(f"⚠️  Config file {config_path} not found")
            
    except Exception as e:
        print(f"⚠️  YAML config loading failed: {e}")
    
    # Example usage: Analyze a defect (mock example)
    print("\n4. Example defect analysis workflow")
    try:
        # This is a mock example - in real usage, you'd get these from Issue Parser and Code Retriever
        from issue_parser.data_structures import ParsedDefect
        from code_retriever.data_structures import CodeContext
        
        # Create mock defect (this would come from Issue Parser)
        mock_defect = ParsedDefect(
            defect_id="COVERITY_001",
            defect_type="NULL_RETURNS",
            file_path="src/example.c",
            line_number=42,
            function_name="process_data",
            subcategory="Dereference before null check",
            events=["Pointer 'data' returned by call to 'malloc' could be null"],
            language="c"
        )
        
        # Create mock code context (this would come from Code Retriever)
        mock_context = CodeContext(
            file_path="src/example.c",
            function_name="process_data",
            language="c",
            code_snippet="""
void process_data(int size) {
    char *data = malloc(size);
    strcpy(data, "example");  // Potential null pointer dereference
    printf("Data: %s\\n", data);
    free(data);
}
""",
            line_number=42,
            surrounding_context="Function processes user input data"
        )
        
        print("   Analyzing mock defect...")
        
        # Perform the analysis
        result = fix_generator.analyze_and_fix(mock_defect, mock_context)
        
        print("✅ Analysis completed!")
        print(f"   Defect category: {result.defect_category}")
        print(f"   Severity: {result.severity_assessment.value}")
        print(f"   Confidence: {result.confidence_score:.2f}")
        print(f"   Number of fix candidates: {len(result.fix_candidates)}")
        
        # Show the first fix candidate
        if result.fix_candidates:
            fix = result.fix_candidates[0]
            print(f"\n   Recommended fix (confidence: {fix.confidence_score:.2f}):")
            print(f"   {fix.explanation}")
            print(f"   Code preview: {fix.fix_code[:100]}...")
        
        # Show usage statistics
        stats = fix_generator.get_statistics()
        print(f"\n   Statistics:")
        print(f"   - Total requests: {stats.total_requests}")
        print(f"   - Successful: {stats.successful_requests}")
        print(f"   - Total tokens: {stats.total_tokens_consumed}")
        if stats.total_cost:
            print(f"   - Total cost: ${stats.total_cost:.4f}")
            
    except ImportError:
        print("⚠️  Mock analysis skipped (Issue Parser/Code Retriever not available)")
        print("   In real usage, these components would provide the defect and context data")
    except Exception as e:
        print(f"⚠️  Analysis example failed: {e}")
    
    # Configuration validation example
    print("\n5. Configuration validation")
    try:
        # Check if environment is properly configured
        config = fix_generator.config
        nim_errors = config.validate_nvidia_nim_environment()
        
        if nim_errors:
            print("❌ Environment validation errors:")
            for error in nim_errors:
                print(f"   - {error}")
        else:
            print("✅ Environment validation passed")
            
        # Test connectivity (if implemented)
        if hasattr(config, 'test_nvidia_nim_connection'):
            print("\n   Testing NVIDIA NIM connectivity...")
            config.test_nvidia_nim_connection()
            
    except Exception as e:
        print(f"⚠️  Validation failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Example completed successfully!")
    print("\nTo use in your own code:")
    print("1. Set up your .env file with NVIDIA NIM credentials")
    print("2. from fix_generator import LLMFixGenerator")
    print("3. generator = LLMFixGenerator.create_from_env()")
    print("4. result = generator.analyze_and_fix(defect, context)")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Example interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error in example: {e}")
        sys.exit(1) 