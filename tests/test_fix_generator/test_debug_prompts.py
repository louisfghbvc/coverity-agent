#!/usr/bin/env python3
"""
Debug script to see prompt outputs and LLM responses.

This script runs a simple defect analysis to show the actual prompts
being sent to the LLM and the responses received.
"""

import logging
import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from issue_parser import CoverityPipelineAdapter, ParsedDefect
from code_retriever import ContextAnalyzer, CodeRetrieverConfig, CodeContext
from fix_generator import LLMFixGenerator
from fix_generator.config import LLMFixGeneratorConfig
from dotenv import load_dotenv

def setup_debug_logging():
    """Setup debug logging to see prompts and responses."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Enable debug for specific modules
    loggers = [
        'fix_generator.llm_manager',
        'fix_generator.prompt_engineering',
        'fix_generator.response_parser'
    ]
    
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)

def create_test_defect() -> ParsedDefect:
    """Create a test defect for debugging."""
    return ParsedDefect(
        defect_id="debug_test_001",
        defect_type="RESOURCE_LEAK",
        file_path="/tmp/test.c",
        line_number=10,
        function_name="test_function",
        subcategory="Memory leak detected",
        events=[
            "Memory allocated at line 8",
            "Function returns without freeing memory at line 10"
        ]
    )

def create_test_context() -> CodeContext:
    """Create a test code context."""
    from code_retriever.data_structures import (
        CodeContext, SourceLocation, ContextWindow, FileMetadata
    )
    
    primary_location = SourceLocation(
        file_path="/tmp/test.c",
        line_number=10,
        column_number=4,
        function_name="test_function"
    )
    
    sample_code = [
        "int test_function(char* input) {",
        "    char* buffer = NULL;",
        "    if (input != NULL) {",
        "        buffer = malloc(strlen(input) + 1);",
        "        strcpy(buffer, input);",
        "        if (strlen(input) > 100) {",
        "            printf(\"Input too long\\n\");",
        "            return -1;  // Memory leak here!",
        "        }",
        "        printf(\"Buffer: %s\\n\", buffer);",
        "        free(buffer);",
        "    }",
        "    return 0;",
        "}"
    ]
    
    primary_context = ContextWindow(
        start_line=1,
        end_line=14,
        source_lines=sample_code,
        highlighted_line=8  # Line with the leak
    )
    
    file_metadata = FileMetadata(
        file_path="/tmp/test.c",
        file_size=len('\n'.join(sample_code)),
        encoding="utf-8",
        language="c"
    )
    
    return CodeContext(
        defect_id="debug_test_001",
        defect_type="RESOURCE_LEAK",
        primary_location=primary_location,
        primary_context=primary_context,
        file_metadata=file_metadata,
        language="c"
    )

def main():
    """Main debug function."""
    print("🔍 DEBUG: Setting up environment...")
    
    # Load environment variables
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ Loaded environment from {env_file}")
    else:
        print(f"⚠️  No .env file found at {env_file}")
        return
    
    # Setup debug logging
    setup_debug_logging()
    print("🔍 DEBUG: Logging configured")
    
    # Check if NVIDIA NIM is configured
    if not os.getenv('NVIDIA_NIM_API_KEY'):
        print("❌ NVIDIA NIM API key not configured")
        return
    
    try:
        print("🔍 DEBUG: Initializing LLM Fix Generator...")
        
        # Create config with debug mode enabled
        config = LLMFixGeneratorConfig.create_from_env()
        config.debug_mode = True
        config.log_level = "DEBUG"
        config.save_raw_responses = True
        
        fix_generator = LLMFixGenerator(config)
        print("✅ LLM Fix Generator initialized")
        
        # Create test data
        print("🔍 DEBUG: Creating test defect and context...")
        test_defect = create_test_defect()
        test_context = create_test_context()
        
        print(f"Test defect: {test_defect.defect_type} at {test_defect.file_path}:{test_defect.line_number}")
        print(f"Code context: {test_context.get_total_context_lines()} lines")
        
        # Generate fix - this will show prompts and responses
        print("\n🚀 DEBUG: Generating fix (prompts and responses will be shown)...")
        print("=" * 80)
        
        fix_result = fix_generator.analyze_and_fix(test_defect, test_context)
        
        print("=" * 80)
        print("✅ DEBUG: Fix generation completed!")
        print(f"   Confidence: {fix_result.confidence_score:.2f}")
        print(f"   Fix candidates: {len(fix_result.fix_candidates)}")
        print(f"   Ready for application: {fix_result.is_ready_for_application}")
        
        if fix_result.fix_candidates:
            recommended_fix = fix_result.recommended_fix
            print(f"   Recommended fix confidence: {recommended_fix.confidence_score:.2f}")
            print(f"   Fix preview: {recommended_fix.fix_code[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ DEBUG: Error occurred: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Debug session completed successfully!")
    else:
        print("\n❌ Debug session failed!")
        sys.exit(1) 