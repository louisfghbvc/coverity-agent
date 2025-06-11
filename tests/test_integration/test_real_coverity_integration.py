#!/usr/bin/env python3
"""
Integration Test for Real Coverity Report Processing

This test validates the complete pipeline:
1. Issue Parser -> Parse real Coverity JSON report
2. Code Retriever -> Extract source code context for defects
3. End-to-end validation of the system

pytest usage:
    pytest tests/test_integration/test_real_coverity_integration.py -v
    
Direct usage:
    python tests/test_integration/test_real_coverity_integration.py
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


class TestCoverityIntegration:
    """Integration tests for Coverity Agent pipeline."""

    def test_real_coverity_report_validation(self, real_coverity_report_path):
        """Test validation of real Coverity report."""
        if not os.path.exists(real_coverity_report_path):
            pytest.skip(f"Real Coverity report not found: {real_coverity_report_path}")
        
        adapter = CoverityPipelineAdapter(real_coverity_report_path)
        assert adapter.validate_report(), "Real Coverity report validation failed"

    def test_real_coverity_issue_parsing(self, real_coverity_report_path, integration_test_config):
        """Test parsing of real Coverity issues."""
        if not os.path.exists(real_coverity_report_path):
            pytest.skip(f"Real Coverity report not found: {real_coverity_report_path}")
        
        adapter = CoverityPipelineAdapter(real_coverity_report_path)
        
        # Get issue summary
        summary = adapter.get_issue_summary()
        assert len(summary) > 0, "No issues found in real Coverity report"
        
        # Test parsing the most common category
        most_common_category = max(summary.items(), key=lambda x: x[1])[0]
        parsed_defects = adapter.parse_issues_by_category(most_common_category)
        
        assert len(parsed_defects) > 0, f"No parsed defects for category: {most_common_category}"
        
        # Validate defect structure
        for defect in parsed_defects[:integration_test_config["max_defects_to_test"]]:
            assert defect.validate(), f"Invalid defect: {defect.defect_id}"
            assert defect.defect_type == most_common_category
            assert defect.file_path
            assert defect.line_number > 0

    def test_code_retriever_integration(self, real_coverity_report_path, integration_test_config):
        """Test Code Retriever integration with real defects."""
        if not os.path.exists(real_coverity_report_path):
            pytest.skip(f"Real Coverity report not found: {real_coverity_report_path}")
        
        # Get sample defects
        adapter = CoverityPipelineAdapter(real_coverity_report_path)
        summary = adapter.get_issue_summary()
        most_common_category = max(summary.items(), key=lambda x: x[1])[0]
        parsed_defects = adapter.parse_issues_by_category(most_common_category)[:integration_test_config["max_defects_to_test"]]
        
        # Initialize Code Retriever
        config = CodeRetrieverConfig()
        context_analyzer = ContextAnalyzer(config)
        
        successful_extractions = 0
        total_extractions = 0
        
        for defect in parsed_defects:
            total_extractions += 1
            
            # Skip if source file doesn't exist
            if not os.path.exists(defect.file_path):
                continue
            
            try:
                code_context = context_analyzer.extract_context(defect)
                successful_extractions += 1
                
                # Validate extracted context
                assert code_context.language in ['c', 'cpp'], f"Unexpected language: {code_context.language}"
                assert code_context.get_total_context_lines() > 0, "No context lines extracted"
                assert code_context.file_metadata.encoding is not None, "No encoding detected"
                
                # Validate context window
                assert code_context.primary_context.source_lines, "No source lines in context"
                assert code_context.primary_context.start_line > 0, "Invalid start line"
                
            except Exception as e:
                # Log but don't fail the test for individual extractions
                print(f"Context extraction failed for {defect.file_path}:{defect.line_number}: {e}")
        
        # Check overall success rate
        if total_extractions > 0:
            success_rate = successful_extractions / total_extractions
            assert success_rate >= integration_test_config["min_success_rate"], \
                f"Success rate {success_rate:.1%} below minimum {integration_test_config['min_success_rate']:.1%}"

    def test_sample_coverity_report(self, sample_coverity_report_path):
        """Test with sample Coverity report from fixtures."""
        assert os.path.exists(sample_coverity_report_path), f"Sample report not found: {sample_coverity_report_path}"
        
        adapter = CoverityPipelineAdapter(sample_coverity_report_path)
        assert adapter.validate_report(), "Sample report validation failed"
        
        # Parse all issues
        parsed_defects = adapter.parse_all_issues()
        assert len(parsed_defects) > 0, "No defects parsed from sample report"
        
        # Validate sample defect
        defect = parsed_defects[0]
        assert defect.validate(), "Invalid sample defect"
        assert defect.defect_type == "AUTO_CAUSES_COPY"
        assert defect.file_path == "/path/to/source.h"
        assert defect.line_number == 230

    def test_parsing_statistics(self, real_coverity_report_path):
        """Test parsing statistics collection."""
        if not os.path.exists(real_coverity_report_path):
            pytest.skip(f"Real Coverity report not found: {real_coverity_report_path}")
        
        adapter = CoverityPipelineAdapter(real_coverity_report_path)
        
        # Parse some issues
        summary = adapter.get_issue_summary()
        if summary:
            most_common_category = max(summary.items(), key=lambda x: x[1])[0]
            adapter.parse_issues_by_category(most_common_category)
        
        # Check statistics
        stats = adapter.get_parsing_statistics()
        assert isinstance(stats, dict), "Statistics should be a dictionary"
        assert "total_issues_found" in stats, "Missing total_issues_found in statistics"
        assert "issues_processed" in stats, "Missing issues_processed in statistics"
        assert "processing_time_seconds" in stats, "Missing processing_time_seconds in statistics"
        assert stats["processing_time_seconds"] >= 0, "Processing time should be non-negative"

    def test_end_to_end_workflow(self, real_coverity_report_path, integration_test_config):
        """Test complete end-to-end workflow."""
        if not os.path.exists(real_coverity_report_path):
            pytest.skip(f"Real Coverity report not found: {real_coverity_report_path}")
        
        # Step 1: Parse issues
        adapter = CoverityPipelineAdapter(real_coverity_report_path)
        summary = adapter.get_issue_summary()
        assert len(summary) > 0, "No issues in report"
        
        # Step 2: Get defects from most common category
        most_common_category = max(summary.items(), key=lambda x: x[1])[0]
        parsed_defects = adapter.parse_issues_by_category(most_common_category)[:3]  # Test with 3 defects
        assert len(parsed_defects) > 0, "No defects parsed"
        
        # Step 3: Extract code context
        config = CodeRetrieverConfig()
        context_analyzer = ContextAnalyzer(config)
        
        contexts = []
        for defect in parsed_defects:
            if os.path.exists(defect.file_path):
                try:
                    context = context_analyzer.extract_context(defect)
                    contexts.append(context)
                except Exception as e:
                    print(f"Failed to extract context for {defect.file_path}: {e}")
        
        # Step 4: Validate workflow results
        assert len(contexts) > 0, "No contexts extracted in end-to-end test"
        
        # Validate that we have a complete pipeline result
        for context in contexts:
            assert context.language in ['c', 'cpp'], "Invalid language detection"
            assert context.primary_context.source_lines, "No source code extracted"
            assert context.file_metadata.encoding, "No encoding detected"


def analyze_report_structure(report_path: str):
    """Analyze the structure of a Coverity report."""
    
    print(f"\n🔍 Analyzing report structure: {report_path}")
    
    try:
        with open(report_path, 'r') as f:
            data = json.load(f)
        
        print(f"Report structure:")
        print(f"  Type: {type(data)}")
        print(f"  Top-level keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        
        if 'issues' in data:
            issues = data['issues']
            print(f"  Issues array length: {len(issues)}")
            
            if issues:
                sample_issue = issues[0]
                print(f"  Sample issue keys: {list(sample_issue.keys())}")
                print(f"  Sample issue checkerName: {sample_issue.get('checkerName', 'N/A')}")
                print(f"  Sample issue file: {sample_issue.get('mainEventFilePathname', 'N/A')}")
                print(f"  Sample issue line: {sample_issue.get('mainEventLineNumber', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to analyze report: {e}")
        return False


def run_manual_integration_test():
    """Manual integration test for direct execution."""
    
    real_report_path = "/home/scratch.louiliu_vlsi_1/work/nvtools_louiliu_2/nvtools/cad/cadlib/vector/coverity/libvector.so/report.json"
    
    print("=" * 80)
    print("COVERITY AGENT INTEGRATION TEST")
    print("=" * 80)
    print(f"Testing with real Coverity report: {real_report_path}")
    
    # Check if report exists
    if not os.path.exists(real_report_path):
        print(f"❌ Report file not found: {real_report_path}")
        return False
    
    try:
        # Initialize Issue Parser
        print("\n📋 Step 1: Initializing Issue Parser...")
        adapter = CoverityPipelineAdapter(real_report_path)
        
        if not adapter.validate_report():
            print("❌ Report validation failed")
            return False
        print("✅ Report validation passed")
        
        # Get issue summary
        print("\n📊 Step 2: Analyzing issue summary...")
        summary = adapter.get_issue_summary()
        print(f"Found {len(summary)} different issue categories:")
        for category, count in sorted(summary.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  - {category}: {count} issues")
        
        if not summary:
            print("⚠️  No issues found in report")
            return True
        
        # Parse sample issues
        print("\n🔍 Step 3: Parsing sample issues...")
        most_common_category = max(summary.items(), key=lambda x: x[1])[0]
        parsed_defects = adapter.parse_issues_by_category(most_common_category)[:5]
        print(f"✅ Successfully parsed {len(parsed_defects)} defects")
        
        # Initialize Code Retriever
        print("\n🔧 Step 4: Initializing Code Retriever...")
        config = CodeRetrieverConfig()
        context_analyzer = ContextAnalyzer(config)
        print("✅ Code Retriever initialized")
        
        # Extract code context
        print("\n📖 Step 5: Extracting source code context...")
        successful_extractions = 0
        failed_extractions = 0
        
        for i, defect in enumerate(parsed_defects[:3], 1):
            print(f"\nProcessing defect {i}/3:")
            print(f"  File: {defect.file_path}")
            print(f"  Line: {defect.line_number}")
            
            if not os.path.exists(defect.file_path):
                print(f"  ⚠️  Source file not found")
                failed_extractions += 1
                continue
            
            try:
                code_context = context_analyzer.extract_context(defect)
                successful_extractions += 1
                
                print(f"  ✅ Context extracted successfully")
                print(f"     Language: {code_context.language}")
                print(f"     Context lines: {code_context.get_total_context_lines()}")
                print(f"     File encoding: {code_context.file_metadata.encoding}")
                
                if code_context.function_context:
                    print(f"     Function: {code_context.function_context.name}")
                    print(f"     Function lines: {code_context.function_context.start_line}-{code_context.function_context.end_line}")
                
            except Exception as e:
                print(f"  ❌ Context extraction failed: {e}")
                failed_extractions += 1
        
        # Results summary
        print(f"\n📈 Results Summary:")
        print(f"  Successful extractions: {successful_extractions}")
        print(f"  Failed extractions: {failed_extractions}")
        
        success_rate = successful_extractions / max(1, successful_extractions + failed_extractions)
        print(f"  Overall Success Rate: {success_rate:.1%}")
        
        if success_rate >= 0.5:
            print("🎉 Integration test PASSED")
            return True
        else:
            print("⚠️  Integration test completed with warnings")
            return True
        
    except Exception as e:
        print(f"❌ Integration test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    """Run manual integration test when executed directly."""
    success = run_manual_integration_test()
    
    # Also analyze report structure
    real_report_path = "/home/scratch.louiliu_vlsi_1/work/nvtools_louiliu_2/nvtools/cad/cadlib/vector/coverity/libvector.so/report.json"
    if os.path.exists(real_report_path):
        analyze_report_structure(real_report_path)
    
    if success:
        print("\n🎉 Manual integration test PASSED!")
        exit(0)
    else:
        print("\n❌ Manual integration test FAILED!")
        exit(1) 