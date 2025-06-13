"""
Main Patch Applier Component

This module provides the main PatchApplier class that orchestrates
patch validation, backup, application, and Perforce integration.
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import difflib

from .config import PatchApplierConfig
from .data_structures import (
    PatchApplicationResult, AppliedChange, ApplicationStatus,
    FileModification, PerforceWorkspaceState
)
from .patch_validator import PatchValidator
from .backup_manager import BackupManager
from .perforce_manager import PerforceManager
from .exceptions import (
    PatchApplierError, PatchValidationError, BackupError,
    PerforceError, PatchApplicationError, RollbackError
)


class PatchApplier:
    """
    Main patch application orchestrator.
    
    Coordinates validation, backup, Perforce integration, and
    safe application of patches to target codebases.
    """
    
    def __init__(self, config: PatchApplierConfig = None):
        """Initialize the patch applier with configuration."""
        self.config = config or PatchApplierConfig.create_default()
        self.logger = logging.getLogger(__name__)
        
        # Initialize component managers
        self.validator = PatchValidator(self.config.validation, self.config)
        self.backup_manager = BackupManager(self.config.backup)
        self.perforce_manager = PerforceManager(self.config.perforce)
        
        self.logger.info("PatchApplier initialized")
    
    def apply_patch(self, analysis_result, working_directory: str = None) -> PatchApplicationResult:
        """
        Apply a patch from DefectAnalysisResult.
        
        Args:
            analysis_result: DefectAnalysisResult from LLM Fix Generator
            working_directory: Directory to apply patches in (defaults to config)
            
        Returns:
            PatchApplicationResult with complete application status
        """
        start_time = datetime.utcnow()
        working_dir = working_directory or self.config.working_directory
        patch_id = f"patch_{analysis_result.defect_id}_{uuid.uuid4().hex[:8]}"
        
        self.logger.info(f"Starting patch application for defect {analysis_result.defect_id}")
        
        # Initialize result
        result = PatchApplicationResult(
            patch_id=patch_id,
            defect_analysis_result=analysis_result
        )
        
        try:
            # Phase 1: Validation
            self.logger.info("Phase 1: Validating patch")
            validation_result = self.validator.validate_patch(analysis_result, working_dir)
            result.validation_result = validation_result
            
            if not validation_result.is_valid:
                result.add_error("Patch validation failed")
                result.overall_status = ApplicationStatus.FAILED
                return result
            
            # Phase 2: Perforce workspace validation
            if self.config.perforce.enabled:
                self.logger.info("Phase 2: Validating Perforce workspace")
                workspace_state = self.perforce_manager.validate_workspace()
                result.workspace_state = workspace_state
                
                if self.config.safety.require_clean_workspace and workspace_state.has_pending_changes:
                    result.add_error("Workspace has pending changes")
                    result.overall_status = ApplicationStatus.FAILED
                    return result
            
            # Phase 3: Create backups
            self.logger.info("Phase 3: Creating backups")
            files_to_backup = validation_result.files_to_modify
            backup_manifest = self.backup_manager.create_backup(
                files_to_backup, patch_id, working_dir
            )
            
            # Phase 4: Prepare files for editing (Perforce)
            perforce_files = []
            if self.config.perforce.enabled and self.config.perforce.auto_checkout:
                self.logger.info("Phase 4: Preparing files for Perforce edit")
                try:
                    perforce_files = self.perforce_manager.prepare_files_for_edit(
                        files_to_backup, working_dir
                    )
                except PerforceError as e:
                    self.logger.error(f"Perforce preparation failed: {e}")
                    result.add_error(f"Perforce error: {e}")
                    if self.config.safety.automatic_rollback_on_failure:
                        self._rollback_changes(result, backup_manifest, perforce_files)
                    return result
            
            # Phase 5: Apply the patch
            self.logger.info("Phase 5: Applying patch")
            if self.config.safety.dry_run_mode:
                self.logger.info("Dry run mode - patch application simulated")
                applied_change = self._simulate_patch_application(
                    analysis_result, working_dir, backup_manifest
                )
            else:
                applied_change = self._apply_patch_to_files(
                    analysis_result, working_dir, backup_manifest
                )
            
            # Add Perforce information
            if perforce_files:
                applied_change.perforce_operations = [
                    {"action": "edit", "file": pf.client_path, "status": pf.status.value}
                    for pf in perforce_files
                ]
            
            result.add_applied_change(applied_change)
            
            # Phase 6: Post-application tasks
            if not self.config.safety.dry_run_mode:
                # Create changelist if enabled
                if self.config.perforce.enabled and self.config.perforce.create_changelist:
                    changelist_description = self.config.perforce.changelist_description_template.format(
                        defect_id=analysis_result.defect_id,
                        defect_type=analysis_result.defect_type
                    )
                    changelist_number = self.perforce_manager.create_changelist(
                        changelist_description, files_to_backup
                    )
                    if changelist_number:
                        applied_change.perforce_operations.append({
                            "action": "create_changelist",
                            "changelist": changelist_number,
                            "description": changelist_description
                        })
                
                # Cleanup backups if successful and configured
                if self.config.backup.cleanup_on_success:
                    self.backup_manager.cleanup_backup(backup_manifest)
            
            # Calculate final metrics
            end_time = datetime.utcnow()
            result.processing_time_seconds = (end_time - start_time).total_seconds()
            
            self.logger.info(f"Patch application completed successfully in "
                           f"{result.processing_time_seconds:.2f} seconds")
            
        except Exception as e:
            self.logger.error(f"Patch application failed: {e}")
            result.add_error(f"Application failed: {str(e)}")
            result.overall_status = ApplicationStatus.FAILED
            
            # Attempt rollback if enabled
            if self.config.safety.automatic_rollback_on_failure:
                try:
                    self._rollback_changes(result, backup_manifest, perforce_files)
                except Exception as rollback_error:
                    self.logger.error(f"Rollback failed: {rollback_error}")
                    result.add_error(f"Rollback failed: {str(rollback_error)}")
        
        return result
    
    def _apply_patch_to_files(self, analysis_result, working_directory: str,
                             backup_manifest) -> AppliedChange:
        """Apply the actual patch to files."""
        recommended_fix = analysis_result.recommended_fix
        
        applied_change = AppliedChange(
            defect_id=analysis_result.defect_id,
            file_path=analysis_result.file_path,
            line_number=analysis_result.line_number,
            fix_candidate_index=analysis_result.recommended_fix_index,
            applied_content=recommended_fix.fix_code,
            confidence_score=recommended_fix.confidence_score,
            backup_manifest=backup_manifest
        )
        
        # Apply changes to each affected file
        for file_path in recommended_fix.affected_files:
            try:
                modification = self._apply_fix_to_file(
                    file_path, recommended_fix.fix_code, working_directory
                )
                applied_change.add_modification(modification)
                
            except Exception as e:
                self.logger.error(f"Failed to apply fix to {file_path}: {e}")
                applied_change.status = ApplicationStatus.FAILED
                applied_change.error_message = f"Failed to apply fix to {file_path}: {e}"
                raise PatchApplicationError(f"Failed to apply fix to {file_path}: {e}")
        
        return applied_change
    
    def _apply_fix_to_file(self, file_path: str, fix_code: str, 
                          working_directory: str) -> FileModification:
        """Apply fix to a single file."""
        full_path = Path(working_directory) / file_path
        
        # Read original content
        with open(full_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # For simplicity, we'll replace the entire file content with the fix
        # In a more sophisticated implementation, this would apply line-specific changes
        modified_content = fix_code
        
        # Write modified content
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        # Calculate line changes
        original_lines = original_content.splitlines()
        modified_lines = modified_content.splitlines()
        
        # Simple diff analysis
        differ = difflib.unified_diff(original_lines, modified_lines, lineterm='')
        diff_lines = list(differ)
        
        lines_added = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
        lines_removed = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
        lines_changed = min(lines_added, lines_removed)
        
        return FileModification(
            file_path=file_path,
            original_content=original_content,
            modified_content=modified_content,
            lines_added=lines_added - lines_changed,
            lines_removed=lines_removed - lines_changed,
            lines_changed=lines_changed
        )
    
    def _simulate_patch_application(self, analysis_result, working_directory: str,
                                   backup_manifest) -> AppliedChange:
        """Simulate patch application for dry run mode."""
        recommended_fix = analysis_result.recommended_fix
        
        applied_change = AppliedChange(
            defect_id=analysis_result.defect_id,
            file_path=analysis_result.file_path,
            line_number=analysis_result.line_number,
            fix_candidate_index=analysis_result.recommended_fix_index,
            applied_content=recommended_fix.fix_code,
            confidence_score=recommended_fix.confidence_score,
            backup_manifest=backup_manifest
        )
        
        # Simulate modifications
        for file_path in recommended_fix.affected_files:
            modification = FileModification(
                file_path=file_path,
                original_content="[Original content - dry run]",
                modified_content=recommended_fix.fix_code,
                lines_added=10,  # Simulated values
                lines_removed=5,
                lines_changed=3
            )
            applied_change.add_modification(modification)
        
        return applied_change
    
    def _rollback_changes(self, result: PatchApplicationResult, backup_manifest, 
                         perforce_files: List):
        """Rollback changes on failure."""
        self.logger.info("Starting rollback process")
        
        try:
            # Restore files from backup
            if backup_manifest and backup_manifest.entries:
                restored_files = self.backup_manager.restore_backup(
                    backup_manifest, self.config.working_directory
                )
                self.logger.info(f"Restored {len(restored_files)} files from backup")
            
            # Revert Perforce files
            if self.config.perforce.enabled and perforce_files:
                file_paths = [pf.client_path for pf in perforce_files]
                reverted_files = self.perforce_manager.revert_files(file_paths)
                self.logger.info(f"Reverted {len(reverted_files)} Perforce files")
            
            # Update result status
            result.overall_status = ApplicationStatus.ROLLED_BACK
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            raise RollbackError(f"Rollback failed: {e}")
    
    def rollback_patch(self, patch_application_result: PatchApplicationResult) -> bool:
        """
        Manually rollback a previously applied patch.
        
        Args:
            patch_application_result: Result from previous patch application
            
        Returns:
            True if rollback was successful
        """
        if not self.config.safety.enable_rollback:
            self.logger.warning("Rollback is disabled in configuration")
            return False
        
        self.logger.info(f"Rolling back patch {patch_application_result.patch_id}")
        
        try:
            for applied_change in patch_application_result.applied_changes:
                if applied_change.backup_manifest:
                    self.backup_manager.restore_backup(
                        applied_change.backup_manifest,
                        self.config.working_directory
                    )
                
                # Revert Perforce operations if applicable
                if self.config.perforce.enabled and applied_change.perforce_operations:
                    perforce_files = [
                        op.get("file") for op in applied_change.perforce_operations
                        if op.get("action") == "edit" and op.get("file")
                    ]
                    if perforce_files:
                        self.perforce_manager.revert_files(perforce_files)
            
            self.logger.info("Rollback completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False 