#!/usr/bin/env python3
"""
Test script for Coverity suppression functionality.

This script demonstrates how the AI can identify false positives
and add appropriate Coverity suppression comments.
"""

import sys
import os
import json
import logging
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from issue_parser.coverity_tool import CoverityReportTool
from code_retriever.code_retriever import CodeRetriever
from fix_generator.llm_manager import UnifiedLLMManager
from patch_applier.patch_applier import PatchApplier
from patch_applier.config import PatchApplierConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_suppression_functionality():
    """Test the suppression functionality with a potential false positive."""
    
    print("=" * 80)
    print("COVERITY SUPPRESSION FUNCTIONALITY TEST")
    print("=" * 80)
    
    # Initialize components
    try:
        parser = CoverityTool()
        code_retriever = CodeRetriever()
        llm_manager = UnifiedLLMManager.create_from_env()
        
        # Configure patch applier for dry run
        patch_config = PatchApplierConfig.create_default()
        patch_config.safety.dry_run_mode = True
        patch_applier = PatchApplier(patch_config)
        
        print("✓ All components initialized successfully")
        
    except Exception as e:
        print(f"✗ Failed to initialize components: {e}")
        return False
    
    # Parse Coverity results
    try:
        coverity_file = Path("tests/test_issue_parser/fixtures/coverity_results.json")
        if not coverity_file.exists():
            print(f"✗ Coverity results file not found: {coverity_file}")
            return False
        
        defects = parser.parse_file(str(coverity_file))
        print(f"✓ Parsed {len(defects)} defects from Coverity results")
        
        if not defects:
            print("✗ No defects found to test")
            return False
        
    except Exception as e:
        print(f"✗ Failed to parse Coverity results: {e}")
        return False
    
    # Test with different defect types to see if AI can identify false positives
    test_cases = [
        {
            "name": "FORWARD_NULL Test",
            "filter": lambda d: d.defect_type == "FORWARD_NULL",
            "description": "Testing null pointer dereference detection"
        },
        {
            "name": "RESOURCE_LEAK Test", 
            "filter": lambda d: d.defect_type == "RESOURCE_LEAK",
            "description": "Testing resource leak detection"
        },
        {
            "name": "OVERFLOW_BEFORE_WIDEN Test",
            "filter": lambda d: d.defect_type == "OVERFLOW_BEFORE_WIDEN", 
            "description": "Testing integer overflow detection"
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\n{'-' * 60}")
        print(f"TEST CASE: {test_case['name']}")
        print(f"Description: {test_case['description']}")
        print(f"{'-' * 60}")
        
        # Find defects matching this test case
        matching_defects = [d for d in defects if test_case['filter'](d)]
        
        if not matching_defects:
            print(f"⚠ No defects found for {test_case['name']}")
            continue
        
        # Test with the first matching defect
        defect = matching_defects[0]
        print(f"Testing defect: {defect.defect_id} in {defect.file_path}:{defect.line_number}")
        
        try:
            # Retrieve code context
            code_context = code_retriever.get_code_context(defect)
            print(f"✓ Retrieved code context: {len(code_context.surrounding_lines)} lines")
            
            # Generate AI analysis
            print("🤖 Analyzing defect with AI...")
            analysis_result = llm_manager.analyze_defect(defect, code_context)
            
            # Display results
            print(f"\n📊 ANALYSIS RESULTS:")
            print(f"   Defect Category: {analysis_result.defect_category}")
            print(f"   Severity: {analysis_result.severity_assessment.value}")
            print(f"   Confidence: {analysis_result.confidence_score:.2f}")
            print(f"   Is False Positive: {analysis_result.is_false_positive}")
            
            if analysis_result.is_false_positive:
                print(f"   False Positive Reason: {analysis_result.false_positive_reason}")
            
            print(f"\n🔧 FIX CANDIDATES ({len(analysis_result.fix_candidates)}):")
            
            for i, fix in enumerate(analysis_result.fix_candidates):
                print(f"\n   Candidate {i+1}:")
                print(f"     Type: {fix.fix_type.value}")
                print(f"     Confidence: {fix.confidence_score:.2f}")
                print(f"     Explanation: {fix.explanation}")
                
                # Show fix code preview
                fix_lines = fix.fix_code.splitlines()
                print(f"     Fix Code ({len(fix_lines)} lines):")
                for j, line in enumerate(fix_lines[:5]):  # Show first 5 lines
                    print(f"       {j+1}: {line}")
                if len(fix_lines) > 5:
                    print(f"       ... ({len(fix_lines) - 5} more lines)")
                
                # Check if this is a suppression
                if fix.fix_type.value == "suppression":
                    print(f"     🚫 SUPPRESSION DETECTED")
                    if "// coverity[" in fix.fix_code:
                        print(f"     ✓ Contains Coverity suppression comment")
                    else:
                        print(f"     ⚠ Missing Coverity suppression comment")
            
            # Test patch application (dry run)
            print(f"\n🔨 TESTING PATCH APPLICATION (DRY RUN):")
            try:
                patch_result = patch_applier.apply_patch(analysis_result, ".")
                
                if patch_result.overall_status.value == "success":
                    print(f"   ✓ Patch application successful")
                    print(f"   Files modified: {len(patch_result.applied_changes)}")
                    
                    for change in patch_result.applied_changes:
                        print(f"     - {change.file_path}")
                        for mod in change.file_modifications:
                            print(f"       Lines added: {mod.lines_added}, removed: {mod.lines_removed}")
                else:
                    print(f"   ✗ Patch application failed: {patch_result.overall_status.value}")
                    for error in patch_result.errors:
                        print(f"     Error: {error}")
                        
            except Exception as e:
                print(f"   ✗ Patch application error: {e}")
            
            # Store results for summary
            results.append({
                "test_case": test_case['name'],
                "defect_id": defect.defect_id,
                "defect_type": defect.defect_type,
                "confidence": analysis_result.confidence_score,
                "is_false_positive": analysis_result.is_false_positive,
                "fix_types": [fix.fix_type.value for fix in analysis_result.fix_candidates],
                "has_suppression": any(fix.fix_type.value == "suppression" for fix in analysis_result.fix_candidates)
            })
            
        except Exception as e:
            print(f"✗ Failed to analyze defect {defect.defect_id}: {e}")
            logger.exception("Detailed error:")
            results.append({
                "test_case": test_case['name'],
                "defect_id": defect.defect_id,
                "error": str(e)
            })
    
    # Print summary
    print(f"\n{'=' * 80}")
    print("SUPPRESSION FUNCTIONALITY TEST SUMMARY")
    print(f"{'=' * 80}")
    
    successful_tests = [r for r in results if 'error' not in r]
    failed_tests = [r for r in results if 'error' in r]
    suppression_tests = [r for r in successful_tests if r.get('has_suppression', False)]
    false_positive_tests = [r for r in successful_tests if r.get('is_false_positive', False)]
    
    print(f"Total tests: {len(results)}")
    print(f"Successful: {len(successful_tests)}")
    print(f"Failed: {len(failed_tests)}")
    print(f"False positives detected: {len(false_positive_tests)}")
    print(f"Suppressions generated: {len(suppression_tests)}")
    
    if successful_tests:
        avg_confidence = sum(r['confidence'] for r in successful_tests) / len(successful_tests)
        print(f"Average confidence: {avg_confidence:.2f}")
    
    print(f"\nDetailed Results:")
    for result in results:
        if 'error' in result:
            print(f"  ✗ {result['test_case']}: {result['error']}")
        else:
            status = "🚫 SUPPRESSION" if result['has_suppression'] else "🔧 CODE FIX"
            fp_status = " (FALSE POSITIVE)" if result['is_false_positive'] else ""
            print(f"  ✓ {result['test_case']}: {status}{fp_status} (confidence: {result['confidence']:.2f})")
    
    # Test success criteria
    success = (
        len(successful_tests) > 0 and
        len(failed_tests) == 0 and
        (len(suppression_tests) > 0 or len(false_positive_tests) > 0)  # At least some false positive detection
    )
    
    if success:
        print(f"\n🎉 SUPPRESSION FUNCTIONALITY TEST PASSED!")
        print(f"   The AI successfully demonstrated the ability to:")
        if len(false_positive_tests) > 0:
            print(f"   - Identify false positives ({len(false_positive_tests)} cases)")
        if len(suppression_tests) > 0:
            print(f"   - Generate suppression comments ({len(suppression_tests)} cases)")
        print(f"   - Maintain high confidence scores (avg: {avg_confidence:.2f})")
    else:
        print(f"\n❌ SUPPRESSION FUNCTIONALITY TEST FAILED!")
        print(f"   Issues detected:")
        if len(failed_tests) > 0:
            print(f"   - {len(failed_tests)} test failures")
        if len(successful_tests) == 0:
            print(f"   - No successful tests")
        if len(suppression_tests) == 0 and len(false_positive_tests) == 0:
            print(f"   - No false positive detection or suppression generation")
    
    return success

if __name__ == "__main__":
    success = test_suppression_functionality()
    sys.exit(0 if success else 1) 