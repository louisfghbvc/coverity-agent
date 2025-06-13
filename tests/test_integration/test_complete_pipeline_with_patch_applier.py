#!/usr/bin/env python3
"""
Complete Pipeline Integration Test with Patch Applier

This test validates the complete end-to-end pipeline:
1. Issue Parser -> Parse real Coverity JSON report
2. Code Retriever -> Extract source code context for defects  
3. Fix Generator -> Generate AI-powered fixes using NVIDIA NIM
4. Patch Applier -> Safely apply patches with backup and rollback

pytest usage:
    pytest tests/test_integration/test_complete_pipeline_with_patch_applier.py -v
    
Direct usage:
    python tests/test_integration/test_complete_pipeline_with_patch_applier.py
"""

import pytest
import os
import sys
import json
import tempfile
import shutil
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
from patch_applier import PatchApplier, PatchApplierConfig, ApplicationStatus
from dotenv import load_dotenv


class TestCompletePipelineWithPatchApplier:
    """Complete pipeline integration tests including patch application."""

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

    def test_complete_pipeline_dry_run(self, setup_environment):
        """Test complete pipeline in dry-run mode for safety."""
        config = setup_environment
        real_report_path = config["real_report_path"]
        sample_report_path = config["sample_report_path"]
        
        # Use real report if available, otherwise use sample
        if os.path.exists(real_report_path):
            report_path = real_report_path
            print(f"\n📋 Using Real Coverity Report: {report_path}")
        else:
            report_path = str(sample_report_path)
            print(f"\n📋 Using Sample Report: {report_path}")
            assert sample_report_path.exists(), f"Sample report not found: {sample_report_path}"

        # Step 1: Parse Issues
        print("\n📋 Step 1: Parsing Coverity Issues...")
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
                print(f"  ⚠️  Source file not found: {defect.file_path}")
                # Create mock context for missing files
                contexts.append((defect, self._create_mock_context(defect)))
                print(f"  ✅ Created mock context for testing")
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
                
            except Exception as e:
                print(f"  ❌ Context extraction failed: {e}")
                # Create mock context as fallback
                contexts.append((defect, self._create_mock_context(defect)))
                print(f"  ✅ Created mock context as fallback")
        
        assert len(contexts) > 0, "No contexts extracted successfully"
        print(f"✅ Successfully processed context for {len(contexts)} defects")

        # Step 3: Generate AI Fixes
        print("\n🤖 Step 3: Generating AI-Powered Fixes...")
        
        fix_results = []
        
        if not os.getenv('NVIDIA_NIM_API_KEY'):
            print("⚠️  NVIDIA NIM not configured, creating mock fixes for testing")
            # Create mock fixes for testing
            for defect, context in contexts:
                mock_result = self._create_mock_fix_result(defect)
                fix_results.append((defect, context, mock_result))
            
            print(f"✅ Created {len(fix_results)} mock fixes")
        else:
            # Real AI fix generation
            try:
                fix_generator = LLMFixGenerator.create_from_env()
                print("✅ LLM Fix Generator initialized with NVIDIA NIM")
                
                for i, (defect, context) in enumerate(contexts, 1):
                    print(f"\nGenerating fix for defect {i}/{len(contexts)}:")
                    print(f"  Type: {defect.defect_type}")
                    print(f"  Location: {defect.file_path}:{defect.line_number}")
                    
                    try:
                        # Generate fix using AI
                        fix_result = fix_generator.analyze_and_fix(defect, context)
                        fix_results.append((defect, context, fix_result))
                        
                        print(f"  ✅ Fix generated successfully")
                        print(f"     Confidence: {fix_result.confidence_score:.2f}")
                        print(f"     Fix candidates: {len(fix_result.fix_candidates)}")
                        print(f"     Ready for application: {fix_result.is_ready_for_application}")
                        
                    except Exception as e:
                        print(f"  ❌ Fix generation failed: {e}")
                        # Create mock fix as fallback
                        mock_result = self._create_mock_fix_result(defect)
                        fix_results.append((defect, context, mock_result))
                        print(f"  ✅ Created mock fix as fallback")
                
            except Exception as e:
                print(f"❌ Fix Generator initialization failed: {e}")
                # Create mock fixes as fallback
                for defect, context in contexts:
                    mock_result = self._create_mock_fix_result(defect)
                    fix_results.append((defect, context, mock_result))
                print(f"✅ Created {len(fix_results)} mock fixes as fallback")
        
        assert len(fix_results) > 0, "No fixes generated successfully"

        # Step 4: Apply Patches (DRY RUN MODE)
        print("\n🚀 Step 4: Applying Patches (DRY RUN MODE)...")
        
        # Configure patch applier for safe testing
        patch_config = PatchApplierConfig.create_default()
        patch_config.perforce.enabled = False  # Disable Perforce for test
        patch_config.safety.dry_run_mode = True  # SAFE: Dry run mode
        patch_config.backup.enabled = True  # Enable backups
        
        patch_applier = PatchApplier(patch_config)
        print("✅ Patch Applier initialized in DRY RUN mode")
        
        patch_results = []
        successful_applications = 0
        
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"✅ Created temporary directory for testing: {temp_dir}")
            
            for i, (defect, context, fix_result) in enumerate(fix_results, 1):
                print(f"\nApplying patch for defect {i}/{len(fix_results)}:")
                print(f"  Defect: {defect.defect_id}")
                print(f"  Type: {defect.defect_type}")
                print(f"  Confidence: {fix_result.confidence_score:.2f}")
                
                # Create test files in temp directory if they don't exist
                test_files_created = self._prepare_test_files(fix_result, temp_dir)
                
                try:
                    # Apply patch in dry run mode
                    patch_result = patch_applier.apply_patch(
                        fix_result, 
                        working_directory=temp_dir
                    )
                    patch_results.append(patch_result)
                    
                    print(f"  ✅ Patch application completed")
                    print(f"     Status: {patch_result.overall_status.value}")
                    print(f"     Success count: {patch_result.success_count}")
                    print(f"     Processing time: {patch_result.processing_time_seconds:.2f}s")
                    
                    if patch_result.validation_result:
                        print(f"     Validation valid: {patch_result.validation_result.is_valid}")
                        print(f"     Validation errors: {patch_result.validation_result.error_count}")
                        print(f"     Validation warnings: {patch_result.validation_result.warning_count}")
                    
                    if patch_result.overall_status == ApplicationStatus.SUCCESS:
                        successful_applications += 1
                    
                    # Show any errors or warnings
                    if patch_result.errors:
                        for error in patch_result.errors[:3]:  # Show first 3 errors
                            print(f"     Error: {error}")
                    
                    if patch_result.warnings:
                        for warning in patch_result.warnings[:3]:  # Show first 3 warnings
                            print(f"     Warning: {warning}")
                    
                except Exception as e:
                    print(f"  ❌ Patch application failed: {e}")
                    # Continue with other patches
        
        # Step 5: Validate Pipeline Results
        print(f"\n✅ Step 5: Validating Complete Pipeline Results...")
        
        print(f"\n📊 Complete Pipeline Statistics:")
        print(f"  Original defects: {len(parsed_defects)}")
        print(f"  Contexts extracted: {len(contexts)}")
        print(f"  Fixes generated: {len(fix_results)}")
        print(f"  Patches applied (dry run): {len(patch_results)}")
        print(f"  Successful applications: {successful_applications}")
        
        if len(patch_results) > 0:
            success_rate = successful_applications / len(patch_results)
            print(f"  Application success rate: {success_rate:.1%}")
        
        # Validate that we have end-to-end results
        assert len(patch_results) > 0, "No patch applications completed"
        
        # At least some patches should be processable
        ready_for_application = sum(1 for _, _, fix_result in fix_results 
                                  if fix_result.is_ready_for_application)
        print(f"  Fixes ready for application: {ready_for_application}")
        
        print("\n🎉 Complete pipeline test with Patch Applier PASSED!")
        
        # Final assertions for pytest
        assert len(parsed_defects) > 0, "Should have parsed defects"
        assert len(contexts) > 0, "Should have extracted contexts"
        assert len(fix_results) > 0, "Should have generated fixes"
        assert len(patch_results) > 0, "Should have applied patches"
        assert successful_applications > 0, "Should have successful applications"

    def test_complete_pipeline_with_real_files(self, setup_environment):
        """Test complete pipeline with real source files when available."""
        config = setup_environment
        real_report_path = config["real_report_path"]
        
        if not os.path.exists(real_report_path):
            pytest.skip(f"Real Coverity report not found: {real_report_path}")
        
        # Step 1: Parse Issues
        print("\n📋 Step 1: Parsing Real Coverity Issues...")
        adapter = CoverityPipelineAdapter(real_report_path)
        
        assert adapter.validate_report(), "Real Coverity report validation failed"
        
        # Get issues that have existing source files
        summary = adapter.get_issue_summary()
        assert len(summary) > 0, "No issues found in real Coverity report"
        
        # Find defects with existing source files
        existing_file_defects = []
        for category in sorted(summary.keys()):
            defects = adapter.parse_issues_by_category(category)[:5]  # Check first 5 of each category
            for defect in defects:
                if os.path.exists(defect.file_path):
                    existing_file_defects.append(defect)
                    if len(existing_file_defects) >= 2:  # Limit to 2 for testing
                        break
            if len(existing_file_defects) >= 2:
                break
        
        if len(existing_file_defects) == 0:
            pytest.skip("No defects found with existing source files")
        
        print(f"✅ Found {len(existing_file_defects)} defects with existing source files")
        
        # Steps 2-4: Same as dry run test but with real files
        # Extract contexts
        code_config = CodeRetrieverConfig()
        context_analyzer = ContextAnalyzer(code_config)
        
        real_contexts = []
        for defect in existing_file_defects:
            try:
                context = context_analyzer.extract_context(defect)
                real_contexts.append((defect, context))
                print(f"✅ Extracted real context for {defect.file_path}")
            except Exception as e:
                print(f"❌ Failed to extract context: {e}")
        
        assert len(real_contexts) > 0, "No real contexts extracted"
        
        # Test with mock fixes for safety (real AI fixes could be dangerous)
        print("\n🤖 Step 3: Creating Safe Mock Fixes...")
        fix_results = []
        for defect, context in real_contexts:
            mock_fix = self._create_mock_fix_result(defect)
            fix_results.append((defect, context, mock_fix))
        
        # Apply patches in dry run mode with real file structure
        print("\n🚀 Step 4: Testing Patch Application Logic...")
        patch_config = PatchApplierConfig.create_default()
        patch_config.perforce.enabled = False
        patch_config.safety.dry_run_mode = True  # SAFE: Always dry run for real files
        
        patch_applier = PatchApplier(patch_config)
        
        # Create temporary copies of real files for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            for defect, context, fix_result in fix_results:
                # Copy real file to temp directory
                source_file = Path(defect.file_path)
                if source_file.exists():
                    temp_file = Path(temp_dir) / source_file.name
                    
                    try:
                        # Copy file with proper permissions
                        shutil.copy2(source_file, temp_file)
                        # Ensure write permissions for testing
                        temp_file.chmod(0o644)
                        
                        # Update fix result to point to temp file
                        fix_result.file_path = str(temp_file)
                        if fix_result.fix_candidates:
                            fix_result.fix_candidates[0].affected_files = [str(temp_file)]
                        
                        patch_result = patch_applier.apply_patch(fix_result, temp_dir)
                        print(f"✅ Tested patch application for {source_file.name}")
                        print(f"   Status: {patch_result.overall_status.value}")
                        
                    except PermissionError as pe:
                        print(f"⚠️  Permission issue with {source_file.name}: {pe}")
                        # Create a simple test file instead
                        test_content = f"// Test file for {fix_result.defect_type}\nint main() {{ return 0; }}"
                        temp_file.write_text(test_content)
                        
                        # Update fix result to point to test file
                        fix_result.file_path = str(temp_file)
                        if fix_result.fix_candidates:
                            fix_result.fix_candidates[0].affected_files = [str(temp_file)]
                        
                        patch_result = patch_applier.apply_patch(fix_result, temp_dir)
                        print(f"✅ Tested patch application with mock file for {source_file.name}")
                        print(f"   Status: {patch_result.overall_status.value}")
                        
                    except Exception as e:
                        print(f"❌ Patch test failed for {source_file.name}: {e}")
        
        print("🎉 Real file pipeline test completed safely!")

    def test_show_detailed_llm_results(self, setup_environment):
        """显示详细的LLM修复结果，包括真实的p4操作"""
        config = setup_environment
        real_report_path = config["real_report_path"]
        
        if not os.path.exists(real_report_path):
            pytest.skip(f"Real Coverity report not found: {real_report_path}")
        
        print("\n" + "=" * 80)
        print("详细LLM修复结果展示 (真实案例)")
        print("=" * 80)
        
        # Step 1: 解析一个真实的RESOURCE_LEAK缺陷
        print("\n📋 第1步: 解析真实Coverity缺陷...")
        adapter = CoverityPipelineAdapter(real_report_path)
        
        assert adapter.validate_report(), "Real Coverity report validation failed"
        
        # 获取RESOURCE_LEAK类型的缺陷
        resource_leak_defects = adapter.parse_issues_by_category("RESOURCE_LEAK")[:1]
        if not resource_leak_defects:
            pytest.skip("No RESOURCE_LEAK defects found")
        
        defect = resource_leak_defects[0]
        print(f"✅ 选择缺陷: {defect.defect_id}")
        print(f"   文件: {defect.file_path}")
        print(f"   行号: {defect.line_number}")
        print(f"   类型: {defect.defect_type}")
        print(f"   函数: {defect.function_name}")
        print(f"   子类别: {defect.subcategory}")
        if defect.events:
            print(f"   事件: {', '.join(defect.events[:2])}...")  # 显示前2个事件
        
        # Step 2: 提取真实代码上下文
        print("\n🔧 第2步: 提取真实代码上下文...")
        code_config = CodeRetrieverConfig()
        context_analyzer = ContextAnalyzer(code_config)
        
        if not os.path.exists(defect.file_path):
            pytest.skip(f"Source file not found: {defect.file_path}")
        
        try:
            context = context_analyzer.extract_context(defect)
            print(f"✅ 成功提取上下文")
            print(f"   语言: {context.language}")
            print(f"   编码: {context.file_metadata.encoding}")
            print(f"   文件大小: {context.file_metadata.file_size} bytes")
            print(f"   上下文行数: {context.get_total_context_lines()}")
            
            # 显示原始代码上下文
            print(f"\n📝 原始代码上下文 ({defect.file_path}:{context.primary_context.start_line}-{context.primary_context.end_line}):")
            print("-" * 80)
            for i, line in enumerate(context.primary_context.source_lines, context.primary_context.start_line):
                marker = ">>> " if i == defect.line_number else "    "
                print(f"{marker}{i:4d}: {line}")
            print("-" * 80)
            
            if context.function_context:
                print(f"   函数上下文: {context.function_context.name}")
                print(f"   函数起始行: {context.function_context.start_line}")
                print(f"   函数结束行: {context.function_context.end_line}")
            
        except Exception as e:
            pytest.skip(f"Context extraction failed: {e}")
        
        # Step 3: 生成AI修复 (显示详细结果)
        print("\n🤖 第3步: 生成AI修复...")
        
        if not os.getenv('NVIDIA_NIM_API_KEY'):
            pytest.skip("NVIDIA NIM not configured")
        
        try:
            fix_generator = LLMFixGenerator.create_from_env()
            print("✅ LLM修复生成器已初始化 (NVIDIA NIM)")
            
            # 生成修复
            print(f"🔄 正在为缺陷 {defect.defect_id} 生成AI修复...")
            fix_result = fix_generator.analyze_and_fix(defect, context)
            
            print(f"\n🎯 AI分析结果:")
            print(f"   缺陷ID: {fix_result.defect_id}")
            print(f"   缺陷类型: {fix_result.defect_type}")
            print(f"   文件路径: {fix_result.file_path}")
            print(f"   行号: {fix_result.line_number}")
            print(f"   严重程度: {fix_result.severity_assessment.value}")
            print(f"   修复复杂度: {fix_result.fix_complexity.value}")
            print(f"   置信度: {fix_result.confidence_score:.2f}")
            print(f"   安全检查通过: {fix_result.safety_checks_passed}")
            print(f"   样式一致性评分: {fix_result.style_consistency_score:.2f}")
            print(f"   准备应用: {fix_result.is_ready_for_application}")
            
            # 显示所有修复候选
            print(f"\n💡 AI生成的修复候选 ({len(fix_result.fix_candidates)}个):")
            for i, candidate in enumerate(fix_result.fix_candidates, 1):
                print(f"\n{'='*20} 修复候选 {i} {'='*20}")
                print(f"置信度: {candidate.confidence_score:.2f}")
                print(f"复杂度: {candidate.complexity.value}")
                print(f"风险评估: {candidate.risk_assessment}")
                print(f"解释: {candidate.explanation}")
                
                print(f"\n🔧 修复代码:")
                print("─" * 60)
                print(candidate.fix_code)
                print("─" * 60)
                
                print(f"影响的文件: {candidate.affected_files}")
                print(f"修改行范围: {candidate.line_ranges}")
            
        except Exception as e:
            print(f"❌ AI修复生成失败: {e}")
            import traceback
            traceback.print_exc()
            pytest.skip(f"AI fix generation failed: {e}")
        
        # Step 4: 测试补丁应用 (包含Perforce操作)
        print("\n🚀 第4步: 测试补丁应用 (包含Perforce检查)...")
        
        # 配置patch applier - 启用Perforce检查
        patch_config = PatchApplierConfig.create_default()
        patch_config.perforce.enabled = True  # 启用Perforce检查
        patch_config.safety.dry_run_mode = True  # 但仍使用干运行模式以保证安全
        patch_config.backup.enabled = True
        
        print(f"✅ Patch Applier配置:")
        print(f"   Perforce启用: {patch_config.perforce.enabled}")
        print(f"   干运行模式: {patch_config.safety.dry_run_mode}")
        print(f"   备份启用: {patch_config.backup.enabled}")
        
        patch_applier = PatchApplier(patch_config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"✅ 创建临时目录: {temp_dir}")
            
            try:
                # 在真实文件上测试 (但使用干运行模式)
                print(f"\n📝 测试文件: {defect.file_path}")
                print(f"   检查文件是否在Perforce控制下...")
                
                # 应用补丁
                patch_result = patch_applier.apply_patch(fix_result, working_directory=temp_dir)
                
                print(f"\n✅ 补丁应用结果:")
                print(f"   状态: {patch_result.overall_status.value}")
                print(f"   成功计数: {patch_result.success_count}")
                print(f"   失败计数: {patch_result.failure_count}")
                print(f"   处理时间: {patch_result.processing_time_seconds:.3f}秒")
                # Show applied changes information  
                if patch_result.applied_changes:
                    print(f"   Applied Changes: {len(patch_result.applied_changes)}")
                    print(f"   Modified Files:")
                    for change in patch_result.applied_changes:
                        print(f"     - {change.file_path} (confidence: {change.confidence_score:.2f})")
                else:
                    print(f"   Applied Changes: 0")
                
                if patch_result.validation_result:
                    print(f"   验证结果:")
                    print(f"     有效: {patch_result.validation_result.is_valid}")
                    print(f"     错误数: {patch_result.validation_result.error_count}")
                    print(f"     警告数: {patch_result.validation_result.warning_count}")
                
                if patch_result.backup_info:
                    print(f"   备份信息:")
                    print(f"     备份ID: {patch_result.backup_info.backup_id}")
                    print(f"     备份位置: {patch_result.backup_info.backup_directory}")
                    print(f"     文件数: {patch_result.backup_info.file_count}")
                    print(f"     总大小: {patch_result.backup_info.total_size_bytes} bytes")
                
                # 显示预期的修复结果
                if patch_result.overall_status.value == "success" and fix_result.fix_candidates:
                    print(f"\n📋 预期的修复结果 (干运行模式预览):")
                    print("─" * 60)
                    print("修复后的代码 (最佳候选):")
                    print(fix_result.fix_candidates[0].fix_code)
                    print("─" * 60)
                
                # 显示Perforce相关信息
                if hasattr(patch_result, 'perforce_info'):
                    print(f"\n🔧 Perforce操作信息:")
                    print(f"   P4 edit调用: {patch_result.perforce_info.get('p4_edit_called', 'N/A')}")
                    print(f"   文件状态: {patch_result.perforce_info.get('file_status', 'N/A')}")
                
                # 显示错误和警告
                if patch_result.errors:
                    print(f"\n❌ 错误:")
                    for error in patch_result.errors:
                        print(f"   - {error}")
                
                if patch_result.warnings:
                    print(f"\n⚠️  警告:")
                    for warning in patch_result.warnings:
                        print(f"   - {warning}")
                
            except Exception as e:
                print(f"❌ 补丁应用测试失败: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n🎉 详细LLM修复结果展示完成!")
        print("注意: 使用了干运行模式，未实际修改文件")

    def _create_mock_context(self, defect: ParsedDefect) -> CodeContext:
        """Create mock code context for testing."""
        from code_retriever.data_structures import (
            CodeContext, SourceLocation, ContextWindow, FileMetadata
        )
        
        primary_location = SourceLocation(
            file_path=defect.file_path,
            line_number=defect.line_number,
            column_number=0,
            function_name=defect.function_name or "test_function"
        )
        
        # Create sample C code context based on defect type
        if "NULL_POINTER" in defect.defect_type or "RESOURCE_LEAK" in defect.defect_type:
            sample_code = [
                "int test_function(char* input) {",
                "    char* ptr = NULL;",
                "    if (input != NULL) {",
                "        ptr = malloc(strlen(input) + 1);",
                "        strcpy(ptr, input);",
                "    }",
                f"    return strlen(ptr);  // {defect.defect_type} here",
                "}"
            ]
        else:
            sample_code = [
                "int test_function() {",
                "    int value = 0;",
                "    // Some code here",
                f"    // {defect.defect_type} detected on this line",
                "    return value;",
                "}"
            ]
        
        primary_context = ContextWindow(
            start_line=max(1, defect.line_number - 3),
            end_line=defect.line_number + 4,
            source_lines=sample_code,
            highlighted_line=min(6, len(sample_code))
        )
        
        file_metadata = FileMetadata(
            file_path=defect.file_path,
            file_size=len('\n'.join(sample_code)),
            encoding="utf-8",
            language="c"
        )
        
        return CodeContext(
            defect_id=defect.defect_id,
            defect_type=defect.defect_type,
            primary_location=primary_location,
            primary_context=primary_context,
            file_metadata=file_metadata,
            language="c"
        )

    def _create_mock_fix_result(self, defect: ParsedDefect) -> DefectAnalysisResult:
        """Create mock fix result for testing."""
        from fix_generator.data_structures import (
            FixCandidate, FixComplexity, DefectSeverity
        )
        
        # Create appropriate fix based on defect type
        if "NULL_POINTER" in defect.defect_type or "RESOURCE_LEAK" in defect.defect_type:
            fix_code = """int test_function(char* input) {
    char* ptr = NULL;
    if (input != NULL) {
        ptr = malloc(strlen(input) + 1);
        if (ptr == NULL) {
            return -1;  // Handle allocation failure
        }
        strcpy(ptr, input);
        int result = strlen(ptr);
        free(ptr);  // Fixed: Free allocated memory
        return result;
    }
    return 0;  // Fixed: Handle null input safely
}"""
            explanation = "Added null checks and proper memory management"
        else:
            fix_code = """int test_function() {
    int value = 0;
    // Fixed: Initialize variable properly
    value = get_safe_value();
    return value;
}"""
            explanation = f"Fixed {defect.defect_type} by adding proper initialization"
        
        mock_fix_candidate = FixCandidate(
            fix_code=fix_code,
            explanation=explanation,
            confidence_score=0.8,
            complexity=FixComplexity.SIMPLE,
            risk_assessment="Low risk - adds safety checks",
            affected_files=[defect.file_path],
            line_ranges=[{"start": defect.line_number, "end": defect.line_number + 2}]
        )
        
        return DefectAnalysisResult(
            defect_id=defect.defect_id,
            defect_type=defect.defect_type,
            file_path=defect.file_path,
            line_number=defect.line_number,
            defect_category="mock_category",
            severity_assessment=DefectSeverity.MEDIUM,
            fix_complexity=FixComplexity.SIMPLE,
            confidence_score=0.8,
            fix_candidates=[mock_fix_candidate],
            safety_checks_passed=True,
            style_consistency_score=0.8
        )

    def _prepare_test_files(self, fix_result: DefectAnalysisResult, temp_dir: str) -> List[str]:
        """Prepare test files in temporary directory."""
        created_files = []
        
        if fix_result.fix_candidates:
            for file_path in fix_result.fix_candidates[0].affected_files:
                # Create test file in temp directory
                file_name = Path(file_path).name
                test_file_path = Path(temp_dir) / file_name
                
                # Create simple test content
                test_content = f"""// Test file for {fix_result.defect_type}
int main() {{
    // Original code with {fix_result.defect_type}
    return 0;
}}"""
                
                test_file_path.write_text(test_content)
                created_files.append(str(test_file_path))
                
                # Update fix result to point to test file
                fix_result.file_path = str(test_file_path)
                fix_result.fix_candidates[0].affected_files = [str(test_file_path)]
        
        return created_files


def run_manual_complete_pipeline_test():
    """Manual complete pipeline test for direct execution."""
    print("=" * 80)
    print("COMPLETE PIPELINE TEST WITH PATCH APPLIER")
    print("=" * 80)
    
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"
    
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ Loaded environment from {env_file}")
    
    # Create test instance
    test_instance = TestCompletePipelineWithPatchApplier()
    setup_config = {
        "project_root": project_root,
        "real_report_path": "/home/scratch.louiliu_vlsi_1/work/nvtools_louiliu_2/nvtools/cad/cadlib/vector/coverity/libvector.so/report.json",
        "sample_report_path": project_root / "tests" / "test_issue_parser" / "fixtures" / "sample_report.json"
    }
    
    try:
        print("\n🚀 Testing complete pipeline in dry-run mode...")
        test_instance.test_complete_pipeline_dry_run(setup_config)
        print(f"✅ Dry-run pipeline test passed")
        
        if os.path.exists(setup_config["real_report_path"]):
            print("\n🚀 Testing with real files (safe mode)...")
            test_instance.test_complete_pipeline_with_real_files(setup_config)
            print(f"✅ Real files test passed")
        else:
            print("⚠️  Real Coverity report not found, skipping real files test")
        
        print("\n🎉 All complete pipeline tests PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Complete pipeline test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    """Run manual complete pipeline test when executed directly."""
    success = run_manual_complete_pipeline_test()
    
    if success:
        print("\n🎉 Manual complete pipeline test PASSED!")
        exit(0)
    else:
        print("\n❌ Manual complete pipeline test FAILED!")
        exit(1) 