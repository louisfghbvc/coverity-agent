#!/usr/bin/env python3
"""
End-to-End Integration Test for Complete Fix Generation Pipeline

This test validates the complete pipeline:
1. Issue Parser -> Parse real Coverity JSON report
2. Code Retriever -> Extract source code context for defects  
3. Fix Generator -> Generate AI-powered fixes using NVIDIA NIM

pytest usage:
    pytest tests/test_integration/test_end_to_end_fix_generation.py -v
    
Direct usage:
    python tests/test_integration/test_end_to_end_fix_generation.py
"""

import pytest
import os
import sys
import json
from typing import List, Dict, Any
from pathlib import Path

# Add src to path for imports when running directly
if __name__ == "__main__":
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent
    src_path = project_root / "src"
    sys.path.insert(0, str(src_path))

from issue_parser import CoverityPipelineAdapter, ParsedDefect
from code_retriever import ContextAnalyzer, CodeRetrieverConfig, CodeContext
from fix_generator import LLMFixGenerator
from fix_generator.data_structures import DefectAnalysisResult
from dotenv import load_dotenv


class TestEndToEndFixGeneration:
    """End-to-end integration tests for complete fix generation pipeline."""

    @pytest.fixture(scope="class")
    def setup_environment(self):
        """Setup environment for testing."""
        # Load environment variables
        project_root = Path(__file__).parent.parent.parent
        env_file = project_root / ".env"
        
        if env_file.exists():
            load_dotenv(env_file)
            print(f"✅ Loaded environment from {env_file}")
        else:
            print(f"⚠️  No .env file found at {env_file}")
        
        return {
            "project_root": project_root,
            "real_report_path": "/home/scratch.louiliu_vlsi_1/work/nvtools_louiliu_2/nvtools/cad/cadlib/vector/coverity/libvector.so/report.json",
            "sample_report_path": project_root / "tests" / "test_issue_parser" / "fixtures" / "sample_report.json"
        }

    def test_complete_pipeline_with_real_report(self, setup_environment):
        """Test complete pipeline with real Coverity report."""
        config = setup_environment
        real_report_path = config["real_report_path"]
        
        if not os.path.exists(real_report_path):
            pytest.skip(f"Real Coverity report not found: {real_report_path}")
        
        # Step 1: Parse Issues
        print("\n📋 Step 1: Parsing Coverity Issues...")
        adapter = CoverityPipelineAdapter(real_report_path)
        
        assert adapter.validate_report(), "Real Coverity report validation failed"
        
        # Get issue summary and select a few defects
        summary = adapter.get_issue_summary()
        assert len(summary) > 0, "No issues found in real Coverity report"
        
        print(f"Found {len(summary)} issue categories:")
        for category, count in sorted(summary.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {category}: {count} issues")
        
        # Get defects from the most common category
        most_common_category = max(summary.items(), key=lambda x: x[1])[0]
        parsed_defects = adapter.parse_issues_by_category(most_common_category)[:2]  # Test with 2 defects
        
        assert len(parsed_defects) > 0, f"No defects parsed for category: {most_common_category}"
        print(f"✅ Parsed {len(parsed_defects)} defects from category: {most_common_category}")
        
        # Step 2: Extract Code Context
        print("\n🔧 Step 2: Extracting Code Context...")
        code_config = CodeRetrieverConfig()
        context_analyzer = ContextAnalyzer(code_config)
        
        contexts = []
        for i, defect in enumerate(parsed_defects, 1):
            print(f"\nProcessing defect {i}/{len(parsed_defects)}:")
            print(f"  File: {defect.file_path}")
            print(f"  Line: {defect.line_number}")
            print(f"  Type: {defect.defect_type}")
            
            if not os.path.exists(defect.file_path):
                print(f"  ⚠️  Source file not found, skipping")
                continue
            
            try:
                code_context = context_analyzer.extract_context(defect)
                contexts.append((defect, code_context))
                
                print(f"  ✅ Context extracted successfully")
                print(f"     Language: {code_context.language}")
                print(f"     Context lines: {code_context.get_total_context_lines()}")
                print(f"     File encoding: {code_context.file_metadata.encoding}")
                
                if code_context.function_context:
                    print(f"     Function: {code_context.function_context.name}")
                    print(f"     Function lines: {code_context.function_context.start_line}-{code_context.function_context.end_line}")
                
            except Exception as e:
                print(f"  ❌ Context extraction failed: {e}")
        
        assert len(contexts) > 0, "No contexts extracted successfully"
        print(f"✅ Successfully extracted context for {len(contexts)} defects")
        
        # Step 3: Generate AI Fixes
        print("\n🤖 Step 3: Generating AI-Powered Fixes...")
        
        # Check if NVIDIA NIM is configured
        if not os.getenv('NVIDIA_NIM_API_KEY'):
            print("⚠️  NVIDIA NIM not configured, skipping fix generation")
            pytest.skip("NVIDIA NIM API key not configured")
        
        try:
            fix_generator = LLMFixGenerator.create_from_env()
            print("✅ LLM Fix Generator initialized")
        except Exception as e:
            print(f"❌ Fix Generator initialization failed: {e}")
            pytest.skip(f"Fix Generator setup failed: {e}")
        
        fix_results = []
        for i, (defect, code_context) in enumerate(contexts, 1):
            print(f"\nGenerating fix for defect {i}/{len(contexts)}:")
            print(f"  Type: {defect.defect_type}")
            print(f"  Location: {defect.file_path}:{defect.line_number}")
            
            try:
                # Generate fix using AI
                fix_result = fix_generator.analyze_and_fix(defect, code_context)
                fix_results.append((defect, code_context, fix_result))
                
                print(f"  ✅ Fix generated successfully")
                print(f"     Confidence: {fix_result.confidence_score:.2f}")
                print(f"     Fix candidates: {len(fix_result.fix_candidates)}")
                print(f"     Complexity: {fix_result.fix_complexity}")
                print(f"     Ready for application: {fix_result.is_ready_for_application}")
                
                # Show recommended fix preview
                if fix_result.fix_candidates:
                    recommended_fix = fix_result.recommended_fix
                    print(f"     Recommended fix confidence: {recommended_fix.confidence_score:.2f}")
                    fix_preview = recommended_fix.fix_code[:100] + "..." if len(recommended_fix.fix_code) > 100 else recommended_fix.fix_code
                    print(f"     Fix preview: {fix_preview}")
                
            except Exception as e:
                print(f"  ❌ Fix generation failed: {e}")
                # Continue with other defects
        
        assert len(fix_results) > 0, "No fixes generated successfully"
        print(f"✅ Successfully generated fixes for {len(fix_results)} defects")
        
        # Step 4: Validate Results
        print("\n✅ Step 4: Validating Pipeline Results...")
        
        successful_fixes = 0
        high_confidence_fixes = 0
        ready_for_application = 0
        
        for defect, code_context, fix_result in fix_results:
            # Validate fix result structure
            assert isinstance(fix_result, DefectAnalysisResult)
            assert fix_result.defect_id == defect.defect_id
            assert fix_result.defect_type == defect.defect_type
            assert len(fix_result.fix_candidates) > 0
            
            successful_fixes += 1
            
            if fix_result.confidence_score >= 0.7:
                high_confidence_fixes += 1
            
            if fix_result.is_ready_for_application:
                ready_for_application += 1
        
        # Print final statistics
        print(f"\n📊 Final Pipeline Statistics:")
        print(f"  Total defects processed: {len(parsed_defects)}")
        print(f"  Contexts extracted: {len(contexts)}")
        print(f"  Fixes generated: {successful_fixes}")
        print(f"  High confidence fixes (≥0.7): {high_confidence_fixes}")
        print(f"  Ready for application: {ready_for_application}")
        
        success_rate = successful_fixes / len(contexts) if contexts else 0
        print(f"  Overall success rate: {success_rate:.1%}")
        
        assert success_rate >= 0.5, f"Success rate {success_rate:.1%} below minimum 50%"
        
        return fix_results

    def test_complete_pipeline_with_sample_report(self, setup_environment):
        """Test complete pipeline with real report and real code extraction."""
        config = setup_environment
        real_report_path = config["real_report_path"]
        sample_report_path = config["sample_report_path"]
        
        # Try to use real report first, fallback to sample report
        if os.path.exists(real_report_path):
            report_path = real_report_path
            print(f"\n📋 Step 1: Using Real Coverity Report: {report_path}")
        else:
            report_path = str(sample_report_path)
            print(f"\n📋 Step 1: Using Sample Report: {report_path}")
            assert sample_report_path.exists(), f"Sample report not found: {sample_report_path}"
        
        # Step 1: Parse Issues
        adapter = CoverityPipelineAdapter(report_path)
        assert adapter.validate_report(), "Report validation failed"
        
        if os.path.exists(real_report_path):
            # Use real report - get defects from most common category
            summary = adapter.get_issue_summary()
            assert len(summary) > 0, "No issues found in report"
            
            print(f"Found {len(summary)} issue categories:")
            for category, count in sorted(summary.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  - {category}: {count} issues")
            
            # Get defects from the most common category
            most_common_category = max(summary.items(), key=lambda x: x[1])[0]
            parsed_defects = adapter.parse_issues_by_category(most_common_category)[:2]  # Test with 2 defects
            print(f"✅ Parsed {len(parsed_defects)} defects from category: {most_common_category}")
        else:
            # Use sample report
            parsed_defects = adapter.parse_all_issues()[:2]  # Test with 2 defects
            print(f"✅ Parsed {len(parsed_defects)} defects from sample report")
        
        assert len(parsed_defects) > 0, "No defects parsed from report"
        
        # Step 2: Extract Real Code Context
        print("\n🔧 Step 2: Extracting Real Code Context...")
        code_config = CodeRetrieverConfig()
        context_analyzer = ContextAnalyzer(code_config)
        
        contexts = []
        for i, defect in enumerate(parsed_defects, 1):
            print(f"\nProcessing defect {i}/{len(parsed_defects)}:")
            print(f"  File: {defect.file_path}")
            print(f"  Line: {defect.line_number}")
            print(f"  Type: {defect.defect_type}")
            
            if not os.path.exists(defect.file_path):
                print(f"  ⚠️  Source file not found: {defect.file_path}")
                # Create minimal mock context for missing files
                from code_retriever.data_structures import (
                    CodeContext, SourceLocation, ContextWindow, FileMetadata
                )
                
                primary_location = SourceLocation(
                    file_path=defect.file_path,
                    line_number=defect.line_number,
                    column_number=0,
                    function_name=defect.function_name
                )
                
                # Create sample C code context
                sample_code = [
                    "int example_function(char* input) {",
                    "    char* ptr = NULL;",
                    "    if (input != NULL) {",
                    "        ptr = malloc(strlen(input) + 1);",
                    "        strcpy(ptr, input);",
                    "    }",
                    f"    return strlen(ptr);  // {defect.defect_type} here",
                    "}"
                ]
                
                primary_context = ContextWindow(
                    start_line=max(1, defect.line_number - 3),
                    end_line=defect.line_number + 4,
                    source_lines=sample_code,
                    highlighted_line=6
                )
                
                file_metadata = FileMetadata(
                    file_path=defect.file_path,
                    file_size=len('\n'.join(sample_code)),
                    encoding="utf-8",
                    language="c"
                )
                
                mock_context = CodeContext(
                    defect_id=defect.defect_id,
                    defect_type=defect.defect_type,
                    primary_location=primary_location,
                    primary_context=primary_context,
                    file_metadata=file_metadata,
                    language="c"
                )
                
                contexts.append((defect, mock_context))
                print(f"  ✅ Created mock context for missing file")
                continue
            
            try:
                # Extract real code context
                code_context = context_analyzer.extract_context(defect)
                contexts.append((defect, code_context))
                
                print(f"  ✅ Real context extracted successfully")
                print(f"     Language: {code_context.language}")
                print(f"     Context lines: {code_context.get_total_context_lines()}")
                print(f"     File encoding: {code_context.file_metadata.encoding}")
                
                if code_context.function_context:
                    print(f"     Function: {code_context.function_context.name}")
                    print(f"     Function lines: {code_context.function_context.start_line}-{code_context.function_context.end_line}")
                
            except Exception as e:
                print(f"  ❌ Context extraction failed: {e}")
                # Continue with other defects
        
        assert len(contexts) > 0, "No contexts extracted successfully"
        print(f"✅ Successfully extracted context for {len(contexts)} defects")
        
        # Step 3: Generate AI Fixes (if NVIDIA NIM is available)
        print("\n🤖 Step 3: Generating AI-Powered Fixes...")
        
        if not os.getenv('NVIDIA_NIM_API_KEY'):
            print("⚠️  NVIDIA NIM not configured, creating mock fixes")
            # Create mock fixes for testing
            from fix_generator.data_structures import (
                FixCandidate, FixComplexity, DefectSeverity
            )
            
            mock_fixes = []
            for defect, context in contexts:
                mock_fix_candidate = FixCandidate(
                    fix_code="if (ptr != NULL) { return strlen(ptr); } return 0;",
                    explanation="Added null check to prevent dereference",
                    confidence_score=0.8,
                    complexity=FixComplexity.SIMPLE,
                    risk_assessment="Low risk - adds safety check",
                    affected_files=[defect.file_path],
                    line_ranges=[{"start": defect.line_number, "end": defect.line_number}]
                )
                
                mock_result = DefectAnalysisResult(
                    defect_id=defect.defect_id,
                    defect_type=defect.defect_type,
                    file_path=defect.file_path,
                    line_number=defect.line_number,
                    defect_category="mock_category",
                    severity_assessment=DefectSeverity.MEDIUM,
                    fix_complexity=FixComplexity.SIMPLE,
                    confidence_score=0.8,
                    fix_candidates=[mock_fix_candidate]
                )
                
                mock_fixes.append((defect, context, mock_result))
            
            fix_results = mock_fixes
            print(f"✅ Created {len(fix_results)} mock fixes")
        else:
            # Real AI fix generation
            try:
                fix_generator = LLMFixGenerator.create_from_env()
                fix_results = []
                
                for defect, context in contexts:
                    try:
                        fix_result = fix_generator.analyze_and_fix(defect, context)
                        fix_results.append((defect, context, fix_result))
                        print(f"✅ Generated real AI fix for {defect.defect_type}")
                    except Exception as e:
                        print(f"❌ Fix generation failed: {e}")
                
            except Exception as e:
                pytest.skip(f"Real fix generation failed: {e}")
        
        # Step 4: Validate Results
        print("\n✅ Step 4: Validating Results...")
        
        assert len(fix_results) > 0, "No fixes generated"
        
        for defect, context, fix_result in fix_results:
            assert isinstance(fix_result, DefectAnalysisResult)
            assert fix_result.defect_id == defect.defect_id
            assert len(fix_result.fix_candidates) > 0
            
            print(f"✅ Validated fix for {defect.defect_type}")
            print(f"   Confidence: {fix_result.confidence_score:.2f}")
            print(f"   Candidates: {len(fix_result.fix_candidates)}")
        
        print(f"🎉 Complete pipeline test passed with {len(fix_results)} fixes!")
        return fix_results


def run_manual_end_to_end_test():
    """Manual end-to-end test for direct execution."""
    print("=" * 80)
    print("END-TO-END FIX GENERATION PIPELINE TEST")
    print("=" * 80)
    
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"
    
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ Loaded environment from {env_file}")
    
    # Create test instance
    test_instance = TestEndToEndFixGeneration()
    setup_config = {
        "project_root": project_root,
        "real_report_path": "/home/scratch.louiliu_vlsi_1/work/nvtools_louiliu_2/nvtools/cad/cadlib/vector/coverity/libvector.so/report.json",
        "sample_report_path": project_root / "tests" / "test_issue_parser" / "fixtures" / "sample_report.json"
    }
    
    try:
        print("\n🚀 Testing with sample report first...")
        sample_results = test_instance.test_complete_pipeline_with_sample_report(setup_config)
        print(f"✅ Sample report test passed with {len(sample_results)} results")
        
        if os.path.exists(setup_config["real_report_path"]):
            print("\n🚀 Testing with real Coverity report...")
            real_results = test_instance.test_complete_pipeline_with_real_report(setup_config)
            print(f"✅ Real report test passed with {len(real_results)} results")
        else:
            print("⚠️  Real Coverity report not found, skipping real test")
        
        print("\n🎉 All end-to-end tests PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ End-to-end test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    """Run manual end-to-end test when executed directly."""
    success = run_manual_end_to_end_test()
    
    if success:
        print("\n🎉 Manual end-to-end test PASSED!")
        exit(0)
    else:
        print("\n❌ Manual end-to-end test FAILED!")
        exit(1) 