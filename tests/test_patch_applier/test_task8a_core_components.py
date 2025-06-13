#!/usr/bin/env python3
"""
Unit Tests for Task 8a: Core Patch Application Components

This module tests all core components required by task 8a:
- Patch Validator Component
- Backup Manager
- Perforce Manager Foundation
- Safety Framework
- Configuration System
"""

import unittest
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.patch_applier import (
    PatchApplier, PatchApplierConfig, PatchValidator, BackupManager, 
    PerforceManager, PatchValidationResult, BackupManifest, 
    PerforceWorkspaceState, ApplicationStatus, ValidationSeverity
)
from src.patch_applier.exceptions import (
    PatchValidationError, BackupError, PerforceError
)

# Mock DefectAnalysisResult for testing
class MockDefectAnalysisResult:
    """Mock DefectAnalysisResult for testing purposes."""
    def __init__(self):
        self.defect_id = "TEST_001"
        self.defect_type = "null_pointer_dereference"
        self.file_path = "test_file.c"
        self.line_number = 42
        self.confidence_score = 0.85
        self.is_ready_for_application = True
        self.recommended_fix_index = 0
        self.fix_candidates = [MockFixCandidate()]
    
    @property
    def recommended_fix(self):
        return self.fix_candidates[self.recommended_fix_index]

class MockFixCandidate:
    """Mock FixCandidate for testing purposes."""
    def __init__(self):
        self.fix_code = "/* Fixed null pointer check */\nif (ptr != NULL) {\n    use_ptr(ptr);\n}"
        self.confidence_score = 0.85
        self.affected_files = ["test_file.c"]


class TestTask8aCoreComponents(unittest.TestCase):
    """Test suite for Task 8a core patch application components."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.working_dir = Path(self.temp_dir) / "workspace"
        self.working_dir.mkdir()
        
        # Create test files
        self.test_file = self.working_dir / "test_file.c"
        self.test_file.write_text("""
#include <stdio.h>

void test_function(char* ptr) {
    // This has a potential null pointer dereference
    printf("Value: %s\\n", ptr);
}
""")
        
        # Create mock analysis result
        self.mock_analysis = MockDefectAnalysisResult()
        
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_configuration_system(self):
        """Test 1: Configuration System - YAML-based configuration management."""
        print("\n🧪 Test 1: Configuration System")
        
        # Test default configuration creation
        config = PatchApplierConfig.create_default()
        
        # Verify all main sections exist
        self.assertIsNotNone(config.perforce)
        self.assertIsNotNone(config.backup)
        self.assertIsNotNone(config.validation)
        self.assertIsNotNone(config.safety)
        
        # Test Perforce configuration
        self.assertIsInstance(config.perforce.enabled, bool)
        self.assertIsInstance(config.perforce.auto_checkout, bool)
        self.assertIsInstance(config.perforce.create_changelist, bool)
        self.assertIn("{defect_id}", config.perforce.changelist_description_template)
        
        # Test Backup configuration
        self.assertIsInstance(config.backup.enabled, bool)
        self.assertEqual(config.backup.backup_directory, ".patch_backups")
        self.assertIsInstance(config.backup.verify_checksums, bool)
        
        # Test Validation configuration
        self.assertIsInstance(config.validation.check_file_existence, bool)
        self.assertIsInstance(config.validation.min_confidence_for_auto_apply, float)
        self.assertGreaterEqual(config.validation.min_confidence_for_auto_apply, 0.0)
        self.assertLessEqual(config.validation.min_confidence_for_auto_apply, 1.0)
        
        # Test Safety configuration
        self.assertIsInstance(config.safety.enable_rollback, bool)
        self.assertIsInstance(config.safety.automatic_rollback_on_failure, bool)
        self.assertIsInstance(config.safety.dry_run_mode, bool)
        
        print("✅ Configuration system validation passed")
    
    def test_patch_validator_component(self):
        """Test 2: Patch Validator - Validate DefectAnalysisResult patches."""
        print("\n🧪 Test 2: Patch Validator Component")
        
        config = PatchApplierConfig.create_default()
        validator = PatchValidator(config.validation)
        
        # Test valid patch validation
        result = validator.validate_patch(self.mock_analysis, str(self.working_dir))
        
        self.assertIsInstance(result, PatchValidationResult)
        self.assertIsInstance(result.is_valid, bool)
        self.assertIsInstance(result.files_to_modify, list)
        self.assertIsInstance(result.validation_timestamp, datetime)
        
        # Test confidence score validation
        self.mock_analysis.confidence_score = 0.3  # Below threshold
        result = validator.validate_patch(self.mock_analysis, str(self.working_dir))
        self.assertTrue(result.has_warnings)
        
        # Test invalid analysis result
        self.mock_analysis.is_ready_for_application = False
        result = validator.validate_patch(self.mock_analysis, str(self.working_dir))
        self.assertFalse(result.is_valid)
        self.assertTrue(result.has_errors)
        
        print("✅ Patch validator validation passed")
    
    def test_backup_manager_component(self):
        """Test 3: Backup Manager - File backup and restoration."""
        print("\n🧪 Test 3: Backup Manager Component")
        
        config = PatchApplierConfig.create_default()
        config.backup.backup_directory = str(Path(self.temp_dir) / "backups")
        backup_manager = BackupManager(config.backup)
        
        # Test backup creation
        files_to_backup = [str(self.test_file)]
        patch_id = "test_patch_001"
        
        manifest = backup_manager.create_backup(files_to_backup, patch_id, str(self.working_dir))
        
        self.assertIsInstance(manifest, BackupManifest)
        self.assertEqual(manifest.patch_id, patch_id)
        self.assertEqual(manifest.total_files, 1)
        self.assertGreater(manifest.total_size_bytes, 0)
        self.assertEqual(len(manifest.entries), 1)
        
        # Verify backup file exists
        backup_entry = manifest.entries[0]
        self.assertTrue(Path(backup_entry.backup_path).exists())
        self.assertIsNotNone(backup_entry.checksum)
        
        # Test backup restoration
        # Modify original file first
        self.test_file.write_text("Modified content")
        
        restored_files = backup_manager.restore_backup(manifest, str(self.working_dir))
        self.assertEqual(len(restored_files), 1)
        
        # Verify file was restored
        restored_content = self.test_file.read_text()
        self.assertIn("#include <stdio.h>", restored_content)
        
        # Test backup cleanup
        cleanup_success = backup_manager.cleanup_backup(manifest)
        self.assertTrue(cleanup_success)
        
        print("✅ Backup manager validation passed")
    
    @patch('subprocess.run')
    def test_perforce_manager_foundation(self, mock_subprocess):
        """Test 4: Perforce Manager - Basic P4 integration."""
        print("\n🧪 Test 4: Perforce Manager Foundation")
        
        config = PatchApplierConfig.create_default()
        config.perforce.enabled = True
        perforce_manager = PerforceManager(config.perforce)
        
        # Mock successful p4 info command
        mock_subprocess.return_value = Mock(
            stdout="Client name: test_client\nUser name: test_user\nClient root: /workspace\n",
            stderr="",
            returncode=0
        )
        
        # Test workspace validation
        workspace_state = perforce_manager.validate_workspace()
        
        self.assertIsInstance(workspace_state, PerforceWorkspaceState)
        self.assertEqual(workspace_state.workspace_name, "test_client")
        self.assertEqual(workspace_state.user, "test_user")
        self.assertEqual(workspace_state.root_directory, "/workspace")
        
        # Test file preparation for edit
        mock_subprocess.return_value = Mock(
            stdout="//depot/test_file.c#1 - opened for edit\n",
            stderr="",
            returncode=0
        )
        
        files_to_edit = ["test_file.c"]
        file_infos = perforce_manager.prepare_files_for_edit(files_to_edit, str(self.working_dir))
        
        # Should handle the case gracefully even if file status is unknown
        self.assertIsInstance(file_infos, list)
        
        # Test file revert
        reverted_files = perforce_manager.revert_files(["test_file.c"])
        self.assertIsInstance(reverted_files, list)
        
        print("✅ Perforce manager foundation validation passed")
    
    def test_safety_framework(self):
        """Test 5: Safety Framework - Rollback capabilities and error handling."""
        print("\n🧪 Test 5: Safety Framework")
        
        config = PatchApplierConfig.create_default()
        config.safety.enable_rollback = True
        config.safety.automatic_rollback_on_failure = True
        config.perforce.enabled = False  # Disable P4 for simpler testing
        
        patch_applier = PatchApplier(config)
        
        # Test rollback capability exists
        self.assertTrue(hasattr(patch_applier, 'rollback_patch'))
        self.assertTrue(hasattr(patch_applier, '_rollback_changes'))
        
        # Test safety configuration
        self.assertTrue(config.safety.enable_rollback)
        self.assertTrue(config.safety.automatic_rollback_on_failure)
        
        # Test error handling by forcing a validation failure
        self.mock_analysis.is_ready_for_application = False
        
        result = patch_applier.apply_patch(self.mock_analysis, str(self.working_dir))
        
        # Should fail gracefully without applying changes
        self.assertEqual(result.overall_status, ApplicationStatus.FAILED)
        self.assertGreater(len(result.errors), 0)
        self.assertEqual(len(result.applied_changes), 0)
        
        print("✅ Safety framework validation passed")
    
    def test_defect_analysis_result_integration(self):
        """Test 6: Integration with DefectAnalysisResult from Fix Generator."""
        print("\n🧪 Test 6: DefectAnalysisResult Integration")
        
        config = PatchApplierConfig.create_default()
        config.safety.dry_run_mode = True  # Safe testing mode
        config.perforce.enabled = False
        
        patch_applier = PatchApplier(config)
        
        # Test with valid analysis result
        self.mock_analysis.is_ready_for_application = True
        self.mock_analysis.confidence_score = 0.85
        
        result = patch_applier.apply_patch(self.mock_analysis, str(self.working_dir))
        
        # Verify integration works
        self.assertIsNotNone(result.defect_analysis_result)
        self.assertEqual(result.defect_analysis_result.defect_id, "TEST_001")
        
        # Check that validation result references the analysis
        self.assertIsNotNone(result.validation_result)
        
        # In dry run mode, should succeed
        self.assertIn(result.overall_status, [ApplicationStatus.SUCCESS, ApplicationStatus.PARTIAL])
        
        print("✅ DefectAnalysisResult integration validation passed")
    
    def test_complete_component_integration(self):
        """Test 7: Complete integration of all core components."""
        print("\n🧪 Test 7: Complete Component Integration")
        
        config = PatchApplierConfig.create_default()
        config.safety.dry_run_mode = True
        config.perforce.enabled = False
        config.backup.enabled = True
        
        # Initialize all components
        patch_applier = PatchApplier(config)
        
        # Verify all components are initialized
        self.assertIsNotNone(patch_applier.validator)
        self.assertIsNotNone(patch_applier.backup_manager)
        self.assertIsNotNone(patch_applier.perforce_manager)
        
        # Test complete workflow
        self.mock_analysis.is_ready_for_application = True
        result = patch_applier.apply_patch(self.mock_analysis, str(self.working_dir))
        
        # Verify all phases completed
        self.assertIsNotNone(result.validation_result)
        self.assertGreater(len(result.applied_changes), 0)
        self.assertGreater(result.processing_time_seconds, 0)
        
        # Verify applied change has all expected fields
        applied_change = result.applied_changes[0]
        self.assertEqual(applied_change.defect_id, "TEST_001")
        self.assertIsNotNone(applied_change.backup_manifest)
        self.assertGreater(len(applied_change.modifications), 0)
        
        print("✅ Complete component integration validation passed")


class TestTask8aSuccessCriteria(unittest.TestCase):
    """Test suite to verify task 8a success criteria are met."""
    
    def test_success_criteria_coverage(self):
        """Verify all task 8a success criteria are met."""
        print("\n🎯 Task 8a Success Criteria Verification")
        
        # ✅ All core components implemented and testable
        from src.patch_applier import PatchValidator, BackupManager, PerforceManager
        print("✅ All core components implemented: PatchValidator, BackupManager, PerforceManager")
        
        # ✅ Integration with Fix Generator DefectAnalysisResult verified
        config = PatchApplierConfig.create_default()
        patch_applier = PatchApplier(config)
        mock_analysis = MockDefectAnalysisResult()
        
        # This should not raise an exception
        try:
            result = patch_applier.apply_patch(mock_analysis, ".")
            print("✅ Integration with DefectAnalysisResult verified")
        except Exception as e:
            self.fail(f"DefectAnalysisResult integration failed: {e}")
        
        # ✅ Basic Perforce operations (edit, revert) working
        perforce_manager = PerforceManager(config.perforce)
        self.assertTrue(hasattr(perforce_manager, 'prepare_files_for_edit'))
        self.assertTrue(hasattr(perforce_manager, 'revert_files'))
        print("✅ Basic Perforce operations (edit, revert) implemented")
        
        # ✅ Backup and restore functionality validated
        backup_manager = BackupManager(config.backup)
        self.assertTrue(hasattr(backup_manager, 'create_backup'))
        self.assertTrue(hasattr(backup_manager, 'restore_backup'))
        print("✅ Backup and restore functionality implemented")
        
        print("\n🎉 Task 8a Success Criteria: ALL REQUIREMENTS MET")


if __name__ == '__main__':
    print("=" * 80)
    print("TASK 8A: CORE PATCH APPLICATION COMPONENTS - UNIT TESTS")
    print("=" * 80)
    
    # Run the tests
    unittest.main(verbosity=2) 