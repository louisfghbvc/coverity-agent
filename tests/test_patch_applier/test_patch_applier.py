"""
Test cases for Patch Applier component.

Tests the core functionality of patch application, validation,
backup management, and Perforce integration.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from src.patch_applier import (
    PatchApplier, PatchApplierConfig,
    PatchValidationResult, ApplicationStatus
)
from src.fix_generator.data_structures import (
    DefectAnalysisResult, FixCandidate, DefectSeverity, FixComplexity
)


class TestPatchApplierConfig:
    """Test PatchApplierConfig functionality."""
    
    def test_create_default_config(self):
        """Test creating default configuration."""
        config = PatchApplierConfig.create_default()
        
        assert config is not None
        assert config.perforce.enabled is True
        assert config.backup.enabled is True
        assert config.validation.check_file_existence is True
        assert config.safety.enable_rollback is True
    
    def test_config_validation_settings(self):
        """Test validation configuration settings."""
        config = PatchApplierConfig.create_default()
        
        assert config.validation.min_confidence_for_auto_apply == 0.7
        assert config.validation.check_file_permissions is True
        assert config.validation.validate_syntax is True


class TestPatchApplier:
    """Test PatchApplier functionality."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        config = PatchApplierConfig.create_default()
        # Disable Perforce for most tests
        config.perforce.enabled = False
        config.safety.dry_run_mode = True  # Safe for testing
        return config
    
    @pytest.fixture
    def patch_applier(self, config):
        """Create PatchApplier instance."""
        return PatchApplier(config)
    
    @pytest.fixture
    def real_patch_applier(self):
        """Create PatchApplier instance for real patch application (non-dry-run)."""
        config = PatchApplierConfig.create_default()
        # Disable Perforce for testing
        config.perforce.enabled = False
        # Disable dry run mode for actual patch testing
        config.safety.dry_run_mode = False
        # Enable our new patch application features
        config.patch_application.enable_keyword_replacement = True
        return PatchApplier(config)
    
    @pytest.fixture
    def mock_analysis_result(self):
        """Create mock DefectAnalysisResult."""
        fix_candidate = FixCandidate(
            fix_code="// Fixed code here\nint x = 0;",
            explanation="Fix null pointer by initializing variable",
            confidence_score=0.85,
            complexity=FixComplexity.SIMPLE,
            risk_assessment="Low risk",
            affected_files=["test_file.c"],
            line_ranges=[{"start": 10, "end": 12}]
        )
        
        analysis_result = DefectAnalysisResult(
            defect_id="test_defect_001",
            defect_type="NULL_POINTER",
            file_path="test_file.c",
            line_number=10,
            defect_category="pointer_issues",
            severity_assessment=DefectSeverity.HIGH,
            fix_complexity=FixComplexity.SIMPLE,
            confidence_score=0.85,
            fix_candidates=[fix_candidate],
            recommended_fix_index=0,
            safety_checks_passed=True,
            style_consistency_score=0.8
        )
        
        return analysis_result
    
    def test_patch_applier_initialization(self, patch_applier):
        """Test PatchApplier initialization."""
        assert patch_applier is not None
        assert patch_applier.config is not None
        assert patch_applier.validator is not None
        assert patch_applier.backup_manager is not None
        assert patch_applier.perforce_manager is not None
    
    def test_apply_patch_dry_run(self, patch_applier, mock_analysis_result):
        """Test patch application in dry run mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = Path(temp_dir) / "test_file.c"
            test_file.write_text("int main() {\n    return 0;\n}")
            
            # Apply patch
            result = patch_applier.apply_patch(
                mock_analysis_result, 
                working_directory=temp_dir
            )
            
            assert result is not None
            assert result.patch_id.startswith("patch_test_defect_001")
            assert result.overall_status == ApplicationStatus.SUCCESS
            assert len(result.applied_changes) == 1
            
            applied_change = result.applied_changes[0]
            assert applied_change.defect_id == "test_defect_001"
            assert applied_change.confidence_score == 0.85
    
    def test_apply_patch_validation_failure(self, patch_applier, mock_analysis_result):
        """Test patch application with validation failure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Don't create the test file to trigger validation failure
            
            result = patch_applier.apply_patch(
                mock_analysis_result,
                working_directory=temp_dir
            )
            
            assert result.overall_status == ApplicationStatus.FAILED
            assert "validation failed" in result.errors[0].lower()
    
    def test_apply_patch_low_confidence(self, patch_applier):
        """Test patch application with low confidence score."""
        # Create analysis result with low confidence
        fix_candidate = FixCandidate(
            fix_code="// Low confidence fix",
            explanation="Uncertain fix",
            confidence_score=0.3,  # Below threshold
            complexity=FixComplexity.SIMPLE,
            risk_assessment="Low risk",
            affected_files=["test_file.c"],
            line_ranges=[{"start": 1, "end": 1}]
        )
        
        analysis_result = DefectAnalysisResult(
            defect_id="test_defect_002",
            defect_type="UNKNOWN",
            file_path="test_file.c",
            line_number=1,
            defect_category="unknown",
            severity_assessment=DefectSeverity.LOW,
            fix_complexity=FixComplexity.SIMPLE,
            confidence_score=0.3,
            fix_candidates=[fix_candidate],
            recommended_fix_index=0,
            safety_checks_passed=True,
            style_consistency_score=0.8
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = Path(temp_dir) / "test_file.c"
            test_file.write_text("int main() { return 0; }")
            
            result = patch_applier.apply_patch(
                analysis_result,
                working_directory=temp_dir
            )
            
            # Should fail due to low confidence (0.3 < 0.5 minimum threshold)
            assert result.overall_status == ApplicationStatus.FAILED
            assert result.validation_result.has_warnings
            assert not result.validation_result.is_valid
    
    def test_line_range_replacement(self, real_patch_applier):
        """Test line range based patch replacement."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file with multiple lines
            test_file = Path(temp_dir) / "test_file.c"
            original_content = """int main() {
    int x;  // Line 2 - Uninitialized variable
    int y = 5;
    printf("Value: %d\\n", x);  // Line 4 - Using uninitialized x
    return 0;
}"""
            test_file.write_text(original_content)
            
            # Create analysis result with line ranges
            fix_candidate = FixCandidate(
                fix_code="""    int x = 0;  // Initialized variable
    int y = 5;""",
                explanation="Initialize variable to prevent null pointer",
                confidence_score=0.9,
                complexity=FixComplexity.SIMPLE,
                risk_assessment="Low risk",
                affected_files=["test_file.c"],
                line_ranges=[{"start": 2, "end": 3}]  # Replace lines 2-3
            )
            
            analysis_result = DefectAnalysisResult(
                defect_id="test_line_range_001",
                defect_type="UNINITIALIZED_VARIABLE",
                file_path="test_file.c",
                line_number=2,
                defect_category="variable_issues",
                severity_assessment=DefectSeverity.HIGH,
                fix_complexity=FixComplexity.SIMPLE,
                confidence_score=0.9,
                fix_candidates=[fix_candidate],
                recommended_fix_index=0,
                safety_checks_passed=True,
                style_consistency_score=0.9
            )
            
            # Apply patch with line range replacement
            result = real_patch_applier.apply_patch(analysis_result, temp_dir)
            
            assert result.overall_status == ApplicationStatus.SUCCESS
            assert len(result.applied_changes) == 1
            
            # Verify the file was modified correctly
            modified_content = test_file.read_text()
            lines = modified_content.splitlines()
            
            # Check that lines 2-3 were replaced correctly
            assert "int x = 0;" in lines[1]  # Line 2 (0-indexed as 1)
            assert "int y = 5;" in lines[2]  # Line 3 (0-indexed as 2)
            assert "printf" in lines[3]      # Line 4 should remain unchanged
    
    def test_keyword_replacement(self, real_patch_applier):
        """Test keyword-based patch replacement."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Keyword replacement is already enabled in real_patch_applier config
            
            # Create test file
            test_file = Path(temp_dir) / "test_file.c"
            original_content = """int main() {
    char *ptr = NULL;
    printf("Value: %s\\n", ptr);  // Line 3 - Null pointer usage
    return 0;
}"""
            test_file.write_text(original_content)
            
            # Create analysis result without line ranges (to trigger keyword mode)
            fix_candidate = FixCandidate(
                fix_code="""    char *ptr = "Hello World";
    if (ptr != NULL) {
        printf("Value: %s\\n", ptr);
    }""",
                explanation="Add null check before usage",
                confidence_score=0.85,
                complexity=FixComplexity.SIMPLE,
                risk_assessment="Low risk",
                affected_files=["test_file.c"],
                line_ranges=[]  # No line ranges - will use keyword replacement
            )
            
            analysis_result = DefectAnalysisResult(
                defect_id="test_keyword_001",
                defect_type="NULL_POINTER",
                file_path="test_file.c",
                line_number=3,
                defect_category="pointer_issues",
                severity_assessment=DefectSeverity.HIGH,
                fix_complexity=FixComplexity.SIMPLE,
                confidence_score=0.85,
                fix_candidates=[fix_candidate],
                recommended_fix_index=0,
                safety_checks_passed=True,
                style_consistency_score=0.8
            )
            
            # Apply patch
            result = real_patch_applier.apply_patch(analysis_result, temp_dir)
            
            assert result.overall_status == ApplicationStatus.SUCCESS
            
            # Verify the fix was applied
            modified_content = test_file.read_text()
            assert "Hello World" in modified_content
            assert "if (ptr != NULL)" in modified_content
    
    def test_multiple_line_ranges(self, real_patch_applier):
        """Test handling multiple line ranges in a single patch."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = Path(temp_dir) / "test_file.c"
            original_content = """int main() {
    int x;      // Line 2 - Issue 1
    int y;      // Line 3 - Issue 2  
    int z = 5;  // Line 4 - OK
    printf("%d %d %d\\n", x, y, z);  // Line 5 - Usage
    return 0;
}"""
            test_file.write_text(original_content)
            
            # Create analysis result with multiple line ranges
            fix_candidate = FixCandidate(
                fix_code="""    int x = 0;  // Fixed
    int y = 1;  // Fixed""",
                explanation="Initialize both variables",
                confidence_score=0.95,
                complexity=FixComplexity.SIMPLE,
                risk_assessment="Very low risk",
                affected_files=["test_file.c"],
                line_ranges=[
                    {"start": 2, "end": 2},  # Fix line 2
                    {"start": 3, "end": 3}   # Fix line 3
                ]
            )
            
            analysis_result = DefectAnalysisResult(
                defect_id="test_multi_range_001",
                defect_type="MULTIPLE_UNINITIALIZED",
                file_path="test_file.c",
                line_number=2,
                defect_category="variable_issues",
                severity_assessment=DefectSeverity.MEDIUM,
                fix_complexity=FixComplexity.SIMPLE,
                confidence_score=0.95,
                fix_candidates=[fix_candidate],
                recommended_fix_index=0,
                safety_checks_passed=True,
                style_consistency_score=0.95
            )
            
            # Apply patch
            result = real_patch_applier.apply_patch(analysis_result, temp_dir)
            
            assert result.overall_status == ApplicationStatus.SUCCESS
            
            # Verify both fixes were applied
            modified_content = test_file.read_text()
            lines = modified_content.splitlines()
            
            # The line ranges are processed in reverse order, so the fix code replaces both ranges
            assert "int x = 0;" in modified_content
            assert "int y = 1;" in modified_content
            assert "int z = 5;" in lines[3]  # Line 4 should remain unchanged


class TestPatchValidator:
    """Test PatchValidator functionality."""
    
    @pytest.fixture
    def validator(self):
        """Create PatchValidator instance."""
        from src.patch_applier.patch_validator import PatchValidator
        from src.patch_applier.config import ValidationConfig
        
        config = ValidationConfig()
        return PatchValidator(config, None)
    
    def test_validate_existing_file(self, validator):
        """Test validation of existing file."""
        fix_candidate = FixCandidate(
            fix_code="// Test fix",
            explanation="Test explanation",
            confidence_score=0.8,
            complexity=FixComplexity.SIMPLE,
            risk_assessment="Low risk",
            affected_files=["existing_file.c"],
            line_ranges=[{"start": 1, "end": 1}]
        )
        
        analysis_result = DefectAnalysisResult(
            defect_id="test_001",
            defect_type="TEST",
            file_path="existing_file.c",
            line_number=1,
            defect_category="test",
            severity_assessment=DefectSeverity.LOW,
            fix_complexity=FixComplexity.SIMPLE,
            confidence_score=0.8,
            fix_candidates=[fix_candidate],
            safety_checks_passed=True,
            style_consistency_score=0.8
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            test_file = Path(temp_dir) / "existing_file.c"
            test_file.write_text("int main() { return 0; }")
            
            result = validator.validate_patch(analysis_result, temp_dir)
            
            assert result.is_valid is True
            assert "existing_file.c" in result.files_to_modify
    
    def test_validate_missing_file(self, validator):
        """Test validation of missing file."""
        fix_candidate = FixCandidate(
            fix_code="// Test fix",
            explanation="Test explanation", 
            confidence_score=0.8,
            complexity=FixComplexity.SIMPLE,
            risk_assessment="Low risk",
            affected_files=["missing_file.c"],
            line_ranges=[{"start": 1, "end": 1}]
        )
        
        analysis_result = DefectAnalysisResult(
            defect_id="test_002",
            defect_type="TEST",
            file_path="missing_file.c",
            line_number=1,
            defect_category="test",
            severity_assessment=DefectSeverity.LOW,
            fix_complexity=FixComplexity.SIMPLE,
            confidence_score=0.8,
            fix_candidates=[fix_candidate],
            safety_checks_passed=True,
            style_consistency_score=0.8
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Don't create the file
            
            result = validator.validate_patch(analysis_result, temp_dir)
            
            assert result.is_valid is False
            assert "missing_file.c" in result.files_missing
            assert result.has_errors is True


class TestBackupManager:
    """Test BackupManager functionality."""
    
    @pytest.fixture
    def backup_manager(self):
        """Create BackupManager instance."""
        from src.patch_applier.backup_manager import BackupManager
        from src.patch_applier.config import BackupConfig
        
        config = BackupConfig()
        return BackupManager(config)
    
    def test_create_backup(self, backup_manager):
        """Test backup creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            test_file1 = Path(temp_dir) / "file1.c"
            test_file1.write_text("int main() { return 0; }")
            
            test_file2 = Path(temp_dir) / "file2.c"
            test_file2.write_text("void func() { }")
            
            # Create backup
            manifest = backup_manager.create_backup(
                ["file1.c", "file2.c"],
                "test_patch_001",
                temp_dir
            )
            
            assert manifest is not None
            assert manifest.patch_id == "test_patch_001"
            assert manifest.total_files == 2
            assert len(manifest.entries) == 2
            
            # Check backup files exist
            backup_dir = Path(manifest.backup_directory)
            assert backup_dir.exists()
    
    def test_restore_backup(self, backup_manager):
        """Test backup restoration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create and backup test file
            test_file = Path(temp_dir) / "test.c"
            original_content = "int main() { return 0; }"
            test_file.write_text(original_content)
            
            # Create backup
            manifest = backup_manager.create_backup(
                ["test.c"],
                "test_patch_002", 
                temp_dir
            )
            
            # Modify original file
            test_file.write_text("// Modified content")
            
            # Restore backup
            restored_files = backup_manager.restore_backup(manifest, temp_dir)
            
            assert len(restored_files) == 1
            assert "test.c" in restored_files
            
            # Check content was restored
            restored_content = test_file.read_text()
            assert restored_content == original_content


if __name__ == "__main__":
    pytest.main([__file__]) 