"""
Main Patch Applier Component

This module provides the main PatchApplier class that orchestrates
patch validation, backup, application, and Perforce integration.
"""

import logging
import uuid
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
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
        
        # Initialize variables for exception handling
        backup_manifest = None
        perforce_files = []
        
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
                    file_path, recommended_fix, working_directory, analysis_result
                )
                applied_change.add_modification(modification)
                
            except Exception as e:
                self.logger.error(f"Failed to apply fix to {file_path}: {e}")
                applied_change.status = ApplicationStatus.FAILED
                applied_change.error_message = f"Failed to apply fix to {file_path}: {e}"
                raise PatchApplicationError(f"Failed to apply fix to {file_path}: {e}")
        
        return applied_change
    
    def _apply_fix_to_file(self, file_path: str, fix_candidate, 
                          working_directory: str, analysis_result=None) -> FileModification:
        """
        Apply fix to a single file using line ranges and fix code.
        
        This method uses the standard FixCandidate attributes (line_ranges and fix_code)
        to apply the fix to the specified file.
        """
        full_path = Path(working_directory) / file_path
        
        with open(full_path, 'r', encoding='utf-8') as f:
            original_lines = f.read().splitlines()
            
        # Use line range replacement as the primary method
        if hasattr(fix_candidate, 'line_ranges') and fix_candidate.line_ranges:
            modified_lines = self._apply_line_range_replacement(
                original_lines, fix_candidate.fix_code, fix_candidate.line_ranges
            )
            self.logger.info(f"Applied line range replacement to {file_path}")
        else:
            # Fallback: try to detect the defect line and apply fix there
            defect_line = analysis_result.line_number if analysis_result else 1
            # Create a simple line range for the defect line
            line_ranges = [{"start": defect_line, "end": defect_line}]
            modified_lines = self._apply_line_range_replacement(
                original_lines, fix_candidate.fix_code, line_ranges
            )
            self.logger.info(f"Applied fallback line replacement at line {defect_line} in {file_path}")

        modified_content = '\n'.join(modified_lines)
        if original_lines and not modified_content.endswith('\n'):
             modified_content += '\n'

        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)

        # Calculate line changes
        original_content_for_diff = '\n'.join(original_lines)
        diff = difflib.unified_diff(
            original_content_for_diff.splitlines(keepends=True),
            modified_content.splitlines(keepends=True),
            fromfile='original',
            tofile='modified',
        )
        
        diff_str = "".join(diff)
        lines_added = len([line for line in diff_str.splitlines() if line.startswith('+') and not line.startswith('+++')])
        lines_removed = len([line for line in diff_str.splitlines() if line.startswith('-') and not line.startswith('---')])
        
        return FileModification(
            file_path=str(full_path),
            original_content=original_content_for_diff,
            modified_content=modified_content,
            lines_added=lines_added,
            lines_removed=lines_removed,
            lines_changed=min(lines_added, lines_removed)
        )
    
    def _has_content_markers(self, fix_code: str) -> bool:
        # This is now obsolete with the instruction-based approach
        return False
    
    def _apply_content_marker_replacement(self, original_content: str, fix_code: str, analysis_result) -> str:
        """
        Apply content marker-based replacement for surgical fixes.
        
        This method processes content markers like:
        - <<<REPLACE_START>>>old_content<<<REPLACE_END>>>new_content
        - <<<INSERT_AFTER_LINE:42>>>new_content<<<INSERT_END>>>
        - <<<LINE_REPLACE:42>>>new_line<<<LINE_REPLACE_END>>>
        """
        modified_content = original_content
        
        # Handle INSERT_AFTER_LINE markers
        insert_pattern = r'<<<INSERT_AFTER_LINE:(\d+)>>>(.*?)<<<INSERT_END>>>'
        for match in re.finditer(insert_pattern, fix_code, re.DOTALL):
            line_num = int(match.group(1))
            insert_content = match.group(2).strip()
            
            lines = modified_content.splitlines()
            if 0 < line_num <= len(lines):
                # Insert after the specified line (1-indexed)
                lines.insert(line_num, insert_content)
                modified_content = '\n'.join(lines)
                self.logger.debug(f"Inserted content after line {line_num}")
        
        # Handle REPLACE_START/REPLACE_END markers
        replace_pattern = r'([^<]*)<<<REPLACE_START>>>(.*?)<<<REPLACE_END>>>(.*?)(?=<<<|$)'
        for match in re.finditer(replace_pattern, fix_code, re.DOTALL):
            context_before = match.group(1).strip()
            old_content = match.group(2)
            new_content = match.group(3)
            
            # Find the line containing the old content to replace
            lines = modified_content.splitlines()
            for i, line in enumerate(lines):
                if old_content in line:
                    # Replace within the line
                    lines[i] = line.replace(old_content, new_content)
                    modified_content = '\n'.join(lines)
                    self.logger.debug(f"Replaced '{old_content}' with '{new_content}' in line {i+1}")
                    break
        
        # Handle LINE_REPLACE markers
        line_replace_pattern = r'<<<LINE_REPLACE:(\d+)>>>(.*?)<<<LINE_REPLACE_END>>>'
        for match in re.finditer(line_replace_pattern, fix_code, re.DOTALL):
            line_num = int(match.group(1))
            new_line = match.group(2).strip()
            
            lines = modified_content.splitlines()
            if 0 < line_num <= len(lines):
                lines[line_num - 1] = new_line  # 1-indexed to 0-indexed
                modified_content = '\n'.join(lines)
                self.logger.debug(f"Replaced line {line_num} with new content")
        
        return modified_content
    
    def _apply_line_range_replacement(self, original_lines: List[str], 
                                    fix_code: str, line_ranges: List[Dict[str, int]]) -> List[str]:
        """
        Apply fix using line ranges for precise replacement.
        
        Args:
            original_lines: Original file lines
            fix_code: New code to insert
            line_ranges: List of {"start": n, "end": m} ranges (1-indexed)
            
        Returns:
            Modified lines
        """
        modified_lines = original_lines.copy()
        fix_lines = fix_code.splitlines()
        
        # Sort ranges by start line in reverse order to avoid index shifting
        sorted_ranges = sorted(line_ranges, key=lambda r: r['start'], reverse=True)
        
        if len(sorted_ranges) == 1:
            # Single range: replace with entire fix code
            line_range = sorted_ranges[0]
            start_line = line_range['start'] - 1  # Convert to 0-indexed
            end_line = line_range['end'] - 1      # Convert to 0-indexed
            
            # Validate range
            if start_line < 0 or end_line >= len(original_lines) or start_line > end_line:
                self.logger.warning(f"Invalid line range: {line_range}, skipping")
                return modified_lines
            
            # Replace the specified range with fix code
            modified_lines[start_line:end_line + 1] = fix_lines
            
            self.logger.debug(f"Replaced lines {start_line + 1}-{end_line + 1} "
                            f"with {len(fix_lines)} new lines")
            
        else:
            # Multiple ranges: smart distribution of fix lines
            self.logger.debug(f"Processing {len(sorted_ranges)} line ranges")
            
            # Strategy 1: If we have exactly the same number of fix lines as ranges,
            # assign one fix line per range
            if len(fix_lines) == len(sorted_ranges):
                for i, line_range in enumerate(sorted_ranges):
                    start_line = line_range['start'] - 1
                    end_line = line_range['end'] - 1
                    
                    # Validate range
                    if start_line < 0 or end_line >= len(original_lines) or start_line > end_line:
                        self.logger.warning(f"Invalid line range: {line_range}, skipping")
                        continue
                    
                    # Use the corresponding fix line (reversed order due to sorting)
                    fix_line_index = len(sorted_ranges) - 1 - i
                    if fix_line_index < len(fix_lines):
                        modified_lines[start_line:end_line + 1] = [fix_lines[fix_line_index]]
                        self.logger.debug(f"Replaced line {start_line + 1} with fix line {fix_line_index}")
            
            # Strategy 2: If we have fewer fix lines than ranges, 
            # distribute them proportionally
            elif len(fix_lines) < len(sorted_ranges):
                lines_per_range = max(1, len(fix_lines) // len(sorted_ranges))
                remaining_lines = fix_lines.copy()
                
                for i, line_range in enumerate(sorted_ranges):
                    start_line = line_range['start'] - 1
                    end_line = line_range['end'] - 1
                    
                    if start_line < 0 or end_line >= len(original_lines) or start_line > end_line:
                        continue
                    
                    # Take appropriate number of lines for this range
                    if remaining_lines:
                        lines_for_this_range = remaining_lines[:lines_per_range] or [remaining_lines[0]]
                        remaining_lines = remaining_lines[len(lines_for_this_range):]
                        modified_lines[start_line:end_line + 1] = lines_for_this_range
                        self.logger.debug(f"Replaced lines {start_line + 1}-{end_line + 1} "
                                        f"with {len(lines_for_this_range)} lines")
            
            # Strategy 3: If we have more fix lines than ranges,
            # distribute all fix lines across ranges
            else:
                lines_per_range = len(fix_lines) // len(sorted_ranges)
                extra_lines = len(fix_lines) % len(sorted_ranges)
                current_fix_index = 0
                
                for i, line_range in enumerate(sorted_ranges):
                    start_line = line_range['start'] - 1
                    end_line = line_range['end'] - 1
                    
                    if start_line < 0 or end_line >= len(original_lines) or start_line > end_line:
                        continue
                    
                    # Calculate how many lines to assign to this range
                    lines_for_this_range = lines_per_range
                    if i < extra_lines:
                        lines_for_this_range += 1
                    
                    # Get the appropriate fix lines for this range
                    range_fix_lines = fix_lines[current_fix_index:current_fix_index + lines_for_this_range]
                    current_fix_index += lines_for_this_range
                    
                    modified_lines[start_line:end_line + 1] = range_fix_lines
                    self.logger.debug(f"Replaced lines {start_line + 1}-{end_line + 1} "
                                    f"with {len(range_fix_lines)} fix lines")
        
        return modified_lines
    
    def _apply_keyword_replacement(self, original_lines: List[str], 
                                 fix_code: str, analysis_result) -> List[str]:
        """
        Apply fix using keyword-based block replacement.
        
        This method adds keywords around the defect area and then replaces
        the entire marked block with the fix code.
        
        Args:
            original_lines: Original file lines
            fix_code: New code to insert
            analysis_result: Analysis result with line number info
            
        Returns:
            Modified lines with keyword-marked replacement
        """
        if not analysis_result or not hasattr(analysis_result, 'line_number'):
            # Fallback to line 1 if no line info available
            target_line = 0
        else:
            target_line = max(0, analysis_result.line_number - 1)  # Convert to 0-indexed
        
        # Generate unique keywords for this defect
        defect_id = getattr(analysis_result, 'defect_id', 'unknown')
        start_keyword = f"// COVERITY_PATCH_START_{defect_id}"
        end_keyword = f"// COVERITY_PATCH_END_{defect_id}"
        
        # Create marked version first
        marked_lines = self._add_patch_keywords(
            original_lines, target_line, start_keyword, end_keyword
        )
        
        # Then replace the marked block
        return self._replace_keyword_block(
            marked_lines, fix_code, start_keyword, end_keyword
        )
    
    def _add_patch_keywords(self, lines: List[str], target_line: int, 
                          start_keyword: str, end_keyword: str) -> List[str]:
        """
        Add patch keywords around the target line area.
        
        Args:
            lines: Original lines
            target_line: Target line index (0-indexed)
            start_keyword: Start marker keyword
            end_keyword: End marker keyword
            
        Returns:
            Lines with keywords added
        """
        modified_lines = lines.copy()
        
        # Determine the block size to mark (configurable)
        block_size = getattr(self.config.patch_application, 'keyword_block_size', 3)
        
        # Calculate start and end positions
        start_pos = max(0, target_line - block_size // 2)
        end_pos = min(len(lines) - 1, target_line + block_size // 2)
        
        # Insert keywords
        modified_lines.insert(start_pos, start_keyword)
        modified_lines.insert(end_pos + 2, end_keyword)  # +2 because we inserted one line
        
        self.logger.debug(f"Added keywords around lines {start_pos + 1}-{end_pos + 1}")
        
        return modified_lines
    
    def _replace_keyword_block(self, lines: List[str], fix_code: str,
                             start_keyword: str, end_keyword: str) -> List[str]:
        """
        Replace the block between start and end keywords with fix code.
        
        Args:
            lines: Lines with keywords
            fix_code: New code to insert
            start_keyword: Start marker keyword
            end_keyword: End marker keyword
            
        Returns:
            Lines with keyword block replaced
        """
        # Find keyword positions
        start_idx = None
        end_idx = None
        
        for i, line in enumerate(lines):
            if start_keyword in line:
                start_idx = i
            elif end_keyword in line:
                end_idx = i
                break
        
        if start_idx is None or end_idx is None:
            self.logger.warning("Patch keywords not found, using fallback replacement")
            return fix_code.splitlines()
        
        # Replace the block (including keywords) with fix code
        fix_lines = fix_code.splitlines()
        result_lines = lines[:start_idx] + fix_lines + lines[end_idx + 1:]
        
        self.logger.debug(f"Replaced keyword block (lines {start_idx + 1}-{end_idx + 1}) "
                        f"with {len(fix_lines)} fix lines")
        
        return result_lines
    
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
            # Determine simulation mode based on available data
            if hasattr(recommended_fix, 'line_ranges') and recommended_fix.line_ranges:
                # Simulate line range replacement
                total_ranges = len(recommended_fix.line_ranges)
                simulated_lines_changed = min(total_ranges * 5, 20)  # Estimate
                replacement_mode = "line_range"
            elif self.config.patch_application.enable_keyword_replacement:
                # Simulate keyword replacement
                simulated_lines_changed = self.config.patch_application.keyword_block_size + 2
                replacement_mode = "keyword_based"
            else:
                # Simulate full file replacement
                simulated_lines_changed = 50  # Estimate for full file
                replacement_mode = "full_file"
            
            modification = FileModification(
                file_path=file_path,
                original_content=f"[Original content - dry run - {replacement_mode}]",
                modified_content=f"[Modified with fix - {replacement_mode}]\n{recommended_fix.fix_code}",
                lines_added=simulated_lines_changed // 2,
                lines_removed=simulated_lines_changed // 3,
                lines_changed=simulated_lines_changed // 4
            )
            applied_change.add_modification(modification)
            
            self.logger.info(f"Simulated {replacement_mode} replacement for {file_path}")
        
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