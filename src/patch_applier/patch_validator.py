"""
Patch Validator Component

This module provides validation of patches before application.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from .data_structures import PatchValidationResult, ValidationIssue, ValidationSeverity
from .config import ValidationConfig
from .exceptions import PatchValidationError


class PatchValidator:
    """Patch validation system."""
    
    def __init__(self, config: ValidationConfig):
        """Initialize the patch validator with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def validate_patch(self, analysis_result, working_directory: str = ".") -> PatchValidationResult:
        """
        Validate a patch for application readiness.
        
        Args:
            analysis_result: The DefectAnalysisResult containing fix candidates
            working_directory: Base directory for file operations
            
        Returns:
            PatchValidationResult with validation status and issues
        """
        self.logger.info(f"Validating patch for defect {analysis_result.defect_id}")
        
        result = PatchValidationResult(is_valid=True)
        
        try:
            # Validate analysis result itself
            if not analysis_result.is_ready_for_application:
                result.add_issue(
                    ValidationSeverity.ERROR,
                    "Analysis result is not ready for application"
                )
            
            # Check confidence score
            if analysis_result.confidence_score < self.config.min_confidence_for_auto_apply:
                result.add_issue(
                    ValidationSeverity.WARNING,
                    f"Confidence score {analysis_result.confidence_score} below threshold"
                )
            
            # Validate files
            if analysis_result.fix_candidates:
                recommended_fix = analysis_result.recommended_fix
                for file_path in recommended_fix.affected_files:
                    self._validate_file(file_path, working_directory, result)
            
            # Final validation check
            if result.has_errors:
                result.is_valid = False
                
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            result.add_issue(ValidationSeverity.ERROR, f"Validation failed: {str(e)}")
            result.is_valid = False
        
        return result
    
    def _validate_file(self, file_path: str, working_directory: str, result: PatchValidationResult):
        """Validate a single file for patch application."""
        full_path = Path(working_directory) / file_path
        
        # Check file existence
        if self.config.check_file_existence and not full_path.exists():
            result.add_issue(ValidationSeverity.ERROR, f"File does not exist: {file_path}")
            result.files_missing.append(file_path)
            return
        
        # Check file permissions
        if self.config.check_file_permissions:
            if not os.access(full_path, os.R_OK):
                result.add_issue(ValidationSeverity.ERROR, f"File not readable: {file_path}")
            if not os.access(full_path, os.W_OK):
                result.add_issue(ValidationSeverity.ERROR, f"File not writable: {file_path}")
        
        result.files_to_modify.append(file_path) 